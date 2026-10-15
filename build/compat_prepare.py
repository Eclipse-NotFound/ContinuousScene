"""Build RV from its installed lineage, without publishing the separate authority WIP."""
from pathlib import Path
import subprocess
import render_camera_patch
import vision_perf_patch
MOD=Path(__file__).resolve().parents[1]
ROOT=MOD.parents[1]
RV=ROOT/'mods/RealisticVision'
STAGE=MOD/'build/generated/rv-production'
BASE='0735491'

def paint_region(source):
    source=paint_bounds(source)
    if 'var scenePixelBounds:Rectangle' in source: return source
    start=source.index('      private function applyVision(')
    end=source.index('      private function fillFogCache(',start)
    part=source[start:end]
    part=part.replace('         this.ensureFog(w);','''         this.ensureFog(w);
         var sceneLarge:Boolean = this.spaceX > 48 || this.spaceY > 25;
         var scenePixelBounds:Rectangle = sceneLarge ? new Rectangle(FOG_PAD + sceneBounds.x * FOG_SUB,
            FOG_PAD + sceneBounds.y * FOG_SUB,sceneBounds.width * FOG_SUB,sceneBounds.height * FOG_SUB) : this.fogRect;
         var scenePixelPoint:Point = sceneLarge ? new Point(scenePixelBounds.x,scenePixelBounds.y) : this.fogPoint;''')
    part=part.replace('this.fogRaw.copyPixels(this.fogCache,this.fogRect,this.fogPoint)',
                      'this.fogRaw.copyPixels(this.fogCache,scenePixelBounds,scenePixelPoint)')
    part=part.replace('this.fogBmp.applyFilter(this.fogRaw,this.fogRect,this.fogPoint,this.curBlur)',
                      'this.fogBmp.applyFilter(this.fogRaw,scenePixelBounds,scenePixelPoint,this.curBlur)')
    source=source[:start]+part+source[end:]
    anchor='         this.fogVis.visible = true;'
    assert source.count(anchor)==1
    source=source.replace(anchor,'''         // Cropping the display also bounds AIR's masked-surface composition.
         // scrollRect translates its content; restore the same world-space origin.
         if(this.spaceX > 48 || this.spaceY > 25)
         {
            var sceneView:Rectangle = this.scenePaintBounds();
            sceneView.x *= Tile.tileX; sceneView.y *= Tile.tileY;
            sceneView.width *= Tile.tileX; sceneView.height *= Tile.tileY;
            this.fogVis.scrollRect = sceneView;
            this.fogVis.x = sceneView.x; this.fogVis.y = sceneView.y;
         }
         else
         {
            this.fogVis.scrollRect = null;
            this.fogVis.x = this.fogVis.y = 0;
         }
'''+anchor)
    return source

def change(source):
    source=paint_region(source)
    # Remove the measured mask-bounds experiment; it did not improve frame time.
    if 'function sceneClipGeometry' in source:
        start=source.index('      private var sceneClipKey:')
        end=source.index('      private function refreshWallField(',start)
        source=source[:start]+source[end:]
        source=source.replace('         this.sceneClipGeometry(loc,fresh || rebuild);\n','')
    if '// Large scenes snapshot sight only when a visible unit needs it.' in source: return source
    source=source.replace('v0.30.3-scene','v0.30.4-scene')
    snapshot='this.currentSightData = this.currentSight.getVector(this.currentSight.rect);'
    assert source.count(snapshot)==2
    source=source.replace(snapshot,'this.currentSightData = sceneLarge ? null : this.currentSight.getVector(this.currentSight.rect);')
    anchor='         if(this.cfgMode == "current" && this.currentSightData != null)'
    assert source.count(anchor)==1
    source=source.replace(anchor,'''         // Large scenes snapshot sight only when a visible unit needs it.
         // Invalidation still happens on every fog/wall change; all units in a
         // frame share one exact snapshot. Empty and fully hidden areas allocate none.
         if(this.cfgMode == "current" && this.currentSightData == null && this.currentSight != null
            && (this.spaceX > 48 || this.spaceY > 25))
            this.currentSightData = this.currentSight.getVector(this.currentSight.rect);
'''+anchor)
    return source

def paint_bounds(source):
    if 'function scenePaintBounds' in source: return source
    source=source.replace('v0.30.2-candidate','v0.30.3-scene')
    helper='''      /** Large scenes keep native FOV/AI coordinates. Only the visible fog pixels
       * are repainted; the margin covers blur and camera interpolation. Small rooms
       * retain their complete original paint extent. */
      private function scenePaintBounds():Rectangle
      {
         if(this.spaceX <= 48 && this.spaceY <= 25) return new Rectangle(0,0,this.spaceX,this.spaceY);
         var world:* = World.w;
         var camera:* = world.cam;
         var left:int = Math.max(0,Math.floor(-camera.vx / Tile.tileX) - 4);
         var top:int = Math.max(0,Math.floor(-camera.vy / Tile.tileY) - 4);
         var right:int = Math.min(this.spaceX,Math.ceil((-camera.vx + camera.screenX) / Tile.tileX) + 4);
         var bottom:int = Math.min(this.spaceY,Math.ceil((-camera.vy + camera.screenY) / Tile.tileY) + 4);
         return new Rectangle(left,top,right-left,bottom-top);
      }

'''
    anchor='      private function applyVision(w:World, loc:Location, needFov:Boolean, occlusionPrepared:Boolean = false):void'
    assert source.count(anchor)==1
    source=source.replace(anchor,helper+anchor)
    for name,next_name in [('applyVision','fillFogCache'),('fillFogCache','recalcTile')]:
        start=source.index('      private function '+name+'(')
        end=source.index('      private function '+next_name+'(',start)
        part=source[start:end]
        brace=part.index('{')+1
        part=part[:brace]+'\n         var sceneBounds:Rectangle = this.scenePaintBounds();'+part[brace:]
        part=part.replace('tx = 0; tx < this.spaceX','tx = int(sceneBounds.left); tx < sceneBounds.right')
        part=part.replace('ty = 0; ty < this.spaceY','ty = int(sceneBounds.top); ty < sceneBounds.bottom')
        source=source[:start]+part+source[end:]
    return source

if __name__=='__main__':
    files=subprocess.check_output(['git','-C',str(RV),'ls-tree','-r','--name-only',BASE,'src'],text=True).splitlines()
    for relative in files:
        content=subprocess.check_output(['git','-C',str(RV),'show',BASE+':'+relative])
        path=STAGE/Path(relative).relative_to('src'); path.parent.mkdir(parents=True,exist_ok=True)
        if relative.endswith('/RealisticVisionMod.as'):
            text=vision_perf_patch.apply(render_camera_patch.apply_vision(change(content.decode('utf-8-sig'))))
            content=text.replace('v0.30.4-scene','v0.30.5-scene').encode('utf-8')
        path.write_bytes(content)
    print('RV stage based on installed source lineage '+BASE+'; authority WIP excluded')
