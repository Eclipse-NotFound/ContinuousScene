"""Reduce RV's large-scene per-frame dispatch without skipping logical work.

Apply to the reviewed, uninstrumented RV candidate after compat/camera patches.
This module only transforms the supplied string; it does not read or write RV's
working tree, build a SWF, or deploy anything.

Correctness boundary: native Location.space is a dense column-major Array of
Tile objects. The optimized path reads that live array afresh on every call;
it caches neither Tile values nor references across frames. Opacity, water,
topology, all wall-corner memory, and all wall alpha values still update every
call. Small rooms and classic retain their exact previous method bodies.

wallA must NOT be cropped to scenePaintBounds: fillWallTile also uses it for
currentSight and enemy masks. Preserve the full logical field, not just pixels
in the current camera viewport. This patch deliberately keeps the full scan.
"""
from __future__ import annotations


def _once(source: str, old: str, new: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"vision perf anchor expected once, found {count}: {old[:100]}")
    return source.replace(old, new, 1)


_HELPERS = r'''      // ContinuousScene exact full-field fast paths (no temporal or viewport culling).
      private function scenePrepareOcclusionFast(loc:Location, space:Array, changed:Boolean):Boolean
      {
         var width:int = this.spaceX;
         var height:int = this.spaceY;
         var ray:Vector.<Number> = this.rayOpac;
         var raw:Vector.<Number> = this.tileOpacity;
         var topology:Vector.<Boolean> = this.wallTopology;
         var waterOpacity:Number = loc.opacWater;
         // Native getTile(x,y) is exactly space[x][y] for these in-bounds cells.
         // Re-read columns and Tiles each call so replacement/door/water changes
         // remain visible immediately, including changes outside the camera.
         for(var x:int = 0; x < width; ++x)
         {
            var column:Array = space[x] as Array;
            var index:int = x;
            for(var y:int = 0; y < height; ++y, index += width)
            {
               var tile:Tile = column[y] as Tile;
               var tileOpacity:Number = tile.opac;
               var opacity:Number = tileOpacity;
               if(waterOpacity > 0 && tile.water > 0 && waterOpacity > opacity)
                  opacity = waterOpacity;
               var solid:Boolean = tileOpacity >= 1;
               if(ray[index] !== opacity) { ray[index] = opacity; changed = true; }
               if(raw[index] !== tileOpacity) { raw[index] = tileOpacity; changed = true; }
               if(topology[index] != solid)
               {
                  topology[index] = solid;
                  this.wallGeometryDirty = true;
                  changed = true;
               }
            }
         }
         return changed;
      }

      private function sceneRefreshWallFieldFast(loc:Location, space:Array, changed:Boolean, advance:Boolean):Boolean
      {
         var width:int = this.spaceX;
         var corners:Array = this.wallCorners;
         var alpha:Array = this.wallA;
         var memory:Array = this.memCur;
         var sight:Array = this.fov;
         var shared:Array = this.sharedLight;
         var bitmap:BitmapData = this.wallRaw;
         var retDark:Boolean = loc.retDark;
         var fade:Number = this.cfgFadeStep;
         var dim:Number = this.cfgDim;
         // Preserve the original corner order and every advanceMemory write.
         // These are scalar reads of native public fields, with no callbacks.
         for each(var index:int in corners)
         {
            var x:int = index % width;
            var y:int = int(index / width);
            var cur:Number = memory[index];
            if(advance)
            {
               var target:Number = !retDark && sight[index] == FOV_NONE ? 1 : 0;
               if(cur < target) cur = Math.min(target,cur + fade);
               else if(cur > target) cur = Math.max(target,cur - fade);
               memory[index] = cur;
            }
            var light:Number = 0;
            if(x != 0 && y != 0)
            {
               var tile:Tile = space[x][y] as Tile;
               light = Math.max(0,Math.min(1,tile.visi));
               if(!retDark && shared != null)
                  light = Math.max(light,Number(shared[index]));
            }
            var gameA:int = Math.floor((1-light)*255);
            var a:int = Math.round(255 - (255-gameA)*(1-cur+cur*dim));
            if(alpha[index] !== a)
            {
               changed = true;
               alpha[index] = a;
               bitmap.setPixel32(x,y+1,a << 24);
            }
         }
         return changed;
      }

'''


def apply(source: str) -> str:
    """Add current-mode large-scene fast paths; fail on changed source anchors."""
    if "scenePrepareOcclusionFast" in source or "sceneRefreshWallFieldFast" in source:
        raise RuntimeError("RV exact full-field performance patch already applied")
    if "csRvProfilePublish" in source:
        raise RuntimeError("Apply vision_perf_patch before profiling instrumentation")
    if "private function scenePaintBounds():Rectangle" not in source:
        raise RuntimeError("RV large-scene compatibility source is required")
    prepare_loop = """         for(var y:int=0;y<this.spaceY;y++) for(var x:int=0;x<this.spaceX;x++)
         {
            var i:int=x+y*this.spaceX;
            var tile:Tile=loc.getTile(x,y);"""
    source = _once(source, prepare_loop, """         if(this.cfgMode == "current" && (this.spaceX > 48 || this.spaceY > 25))
         {
            // Object access avoids expanding the external game API stub.
            var sceneSpace:Array = Object(loc).space as Array;
            if(sceneSpace != null && loc.spaceX == this.spaceX && loc.spaceY == this.spaceY)
               return this.scenePrepareOcclusionFast(loc,sceneSpace,changed);
         }
""" + prepare_loop)
    wall_loop = """         var changed:Boolean = fresh || rebuild;
         for each(var i:int in this.wallCorners)"""
    source = _once(source, wall_loop, """         var changed:Boolean = fresh || rebuild;
         if(this.cfgMode == "current" && (this.spaceX > 48 || this.spaceY > 25))
         {
            var sceneSpace:Array = Object(loc).space as Array;
            if(sceneSpace != null && loc.spaceX == this.spaceX && loc.spaceY == this.spaceY)
               return this.sceneRefreshWallFieldFast(loc,sceneSpace,changed,advance);
         }
         for each(var i:int in this.wallCorners)""")
    anchor = "      private function prepareOcclusion(loc:Location):Boolean"
    source = _once(source, anchor, _HELPERS + anchor)
    return source
