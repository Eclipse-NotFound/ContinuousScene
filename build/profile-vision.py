"""Create an instrumented *isolated-only* copy of the reviewed RV candidate.

No source under mods/RealisticVision or installed release is touched. Example:
    python build/profile-vision.py
    python build/profile-vision.py --fine --output build/generated/rv-profile-fine

The generated MovieClip carrier `ContinuousSceneVisionProfile` exposes `.api`:
    snapshot(): {dimensions, methods, frames, frameMs, ...}
    reset(): void                      # between probe phases, not inside RV
    enable(value:Boolean): void        # timing only; does not toggle vision

Times are getTimer milliseconds. `ms` is inclusive; `selfMs` excludes timed
descendants. Default timings intentionally cover coarse work plus per-enemy
classification/masks. --fine adds hot per-ray/per-tile helpers: its own overhead
must be measured; do not use its absolute frame time as a release benchmark.
The profiler accumulates in memory. Only the driving probe should save snapshots.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

MOD = Path(__file__).resolve().parents[1]
GENERATED = MOD / "build/generated"
COARSE = (
    "onFrame", "onFrameInner", "resetRoom", "ensureFog", "normalMode", "restoreAll",
    "structHash", "prepareOcclusion", "computeFov", "applyVision", "fillFogCache",
    "refreshWallField", "applyVisionClassic", "joinClassicWalls", "hideEnemies",
    "enemyState", "applyMask", "sweepMasks", "scanArms", "blockInvisibleHover",
    "enforceTele", "updateOptPanel", "debugStep",
)
FINE = (
    "castRay", "tileOpac", "recalcTile", "fillLitTile", "fillWallTile",
    "fillMemoryTile", "advanceMemory", "wallCornerAlpha", "personalWallAlpha",
    "unitBBox", "bboxFovCount", "nearAny", "setWeaponVis", "scenePaintBounds",
)
PIXEL_OPERATIONS = ("currentSight.getVector", "currentSight.clear", "fogBmp.applyFilter")


def _body(source: str, name: str) -> tuple[int, int]:
    heads = list(re.finditer(r"\bfunction\s+" + re.escape(name) + r"\s*\(", source))
    if len(heads) != 1:
        raise RuntimeError(f"RV profiler expected one {name} method, got {len(heads)}")
    start = source.index("{", heads[0].end())
    depth, i, state = 1, start + 1, "code"
    while i < len(source):
        char, pair = source[i], source[i:i + 2]
        if state == "line":
            if char == "\n":
                state = "code"
        elif state == "comment":
            if pair == "*/":
                state = "code"
                i += 1
        elif state in ('"', "'"):
            if char == "\\":
                i += 1
            elif char == state:
                state = "code"
        elif pair == "//":
            state = "line"
            i += 1
        elif pair == "/*":
            state = "comment"
            i += 1
        elif char in ('"', "'"):
            state = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return start, i
        i += 1
    raise RuntimeError(f"Unterminated AS3 method: {name}")


def _default_return(source: str, name: str, body_start: int) -> str:
    """Satisfy ASC's incomplete try/finally return analysis; tail is unreachable."""
    head = re.search(r"\bfunction\s+" + re.escape(name) + r"\s*\(", source)
    if head is None:
        raise RuntimeError(f"Missing AS3 method: {name}")
    signature = source[head.end():body_start]
    found = re.search(r"\)\s*:\s*([\w.*<>]+)\s*$", signature)
    if found is None:
        raise RuntimeError(f"Cannot determine AS3 return type: {name}")
    result_type = found.group(1)
    if result_type == "void":
        return ""
    value = {"Boolean": "false", "int": "0", "uint": "0", "Number": "NaN", "*": "undefined"}.get(result_type, "null")
    return "\n         return " + value + "; // ASC requires a typed tail after try/finally."


PROFILE = r'''
      // ISOLATED RV INSTRUMENTATION. No per-frame disk output.
      private var csRvProfileEnabled:Boolean = false;
      private var csRvProfileAllowed:Boolean = false;
      private var csRvProfileRows:Object = {};
      private var csRvProfileStack:Array = [];
      private var csRvProfileDepth:int = 0;
      private var csRvProfileFrames:int = 0;
      private var csRvProfileStarted:int = 0;
      private var csRvProfileHistogram:Object = {};

      private function csRvProfilePublish(main:*):void
      {
         var appId:String = String(NativeApplication.nativeApplication.applicationID);
         if(appId.indexOf("pfe-modsettings-continuous-") != 0)
            throw new Error("RV instrumentation is restricted to isolated ContinuousScene test IDs");
         this.csRvProfileAllowed = true;
         this.csRvProfileEnabled = true;
         this.csRvProfileReset();
         var carrier:flash.display.MovieClip = new flash.display.MovieClip();
         carrier.name = "ContinuousSceneVisionProfile";
         carrier.visible = false; carrier.mouseEnabled = carrier.mouseChildren = false;
         var self:RealisticVisionMod = this;
         carrier["api"] = {version:1,isolated:true,sourceSHA256:"__SOURCE_HASH__",fine:__FINE__,
            methods:__METHOD_NAMES__,
            snapshot:function():Object { return self.csRvProfileSnapshot(); },
            reset:function():void { self.csRvProfileReset(); },
            enable:function(value:Boolean):void { self.csRvProfileEnabled = self.csRvProfileAllowed && value; }};
         main.addChild(carrier);
      }

      private function csRvProfileReset():void
      {
         if(this.csRvProfileDepth != 0) throw new Error("Reset RV profiler between frames");
         this.csRvProfileRows = {}; this.csRvProfileFrames = 0;
         this.csRvProfileHistogram = {}; this.csRvProfileStarted = getTimer();
      }

      private function csRvProfileEnter(name:String):Boolean
      {
         if(!this.csRvProfileEnabled) return false;
         if(name == "onFrame")
         {
            ++this.csRvProfileFrames;
            for each(var previous:Object in this.csRvProfileRows)
            {
               previous.frameCalls = previous.frameMs = previous.frameSelfMs = 0;
            }
         }
         var stack:Object = this.csRvProfileStack[this.csRvProfileDepth];
         if(stack == null) this.csRvProfileStack[this.csRvProfileDepth] = stack = {};
         stack.name = name; stack.children = 0; stack.start = getTimer();
         ++this.csRvProfileDepth;
         return true;
      }

      private function csRvProfileLeave():void
      {
         var stack:Object = this.csRvProfileStack[--this.csRvProfileDepth];
         var elapsed:int = getTimer() - int(stack.start);
         var own:int = Math.max(0,elapsed - int(stack.children));
         var row:Object = this.csRvProfileRows[stack.name];
         if(row == null) this.csRvProfileRows[stack.name] = row = {
            calls:0,ms:0,selfMs:0,maxMs:0,maxSelfMs:0,frameCalls:0,frameMs:0,frameSelfMs:0};
         ++row.calls; row.ms += elapsed; row.selfMs += own;
         row.maxMs = Math.max(row.maxMs,elapsed); row.maxSelfMs = Math.max(row.maxSelfMs,own);
         ++row.frameCalls; row.frameMs += elapsed; row.frameSelfMs += own;
         if(this.csRvProfileDepth > 0)
            this.csRvProfileStack[this.csRvProfileDepth-1].children += elapsed;
         if(stack.name == "onFrame")
         {
            var key:String = String(elapsed);
            this.csRvProfileHistogram[key] = int(this.csRvProfileHistogram[key]) + 1;
         }
      }

      private function csRvProfileSnapshot():Object
      {
         var methods:Object = {};
         for(var name:String in this.csRvProfileRows)
         {
            var row:Object = this.csRvProfileRows[name];
            methods[name] = {calls:row.calls,ms:row.ms,selfMs:row.selfMs,maxMs:row.maxMs,maxSelfMs:row.maxSelfMs,
               meanMs:row.calls ? row.ms / row.calls : 0,
               callsPerFrame:this.csRvProfileFrames ? row.calls / this.csRvProfileFrames : 0,
               frameCalls:row.frameCalls,frameMs:row.frameMs,frameSelfMs:row.frameSelfMs};
         }
         var histogram:Object = {};
         for(var bucket:String in this.csRvProfileHistogram) histogram[bucket] = this.csRvProfileHistogram[bucket];
         var world:* = World.w;
         var view:Rectangle = null;
         var enabledBefore:Boolean = this.csRvProfileEnabled;
         this.csRvProfileEnabled = false;
         try { view = this.curLoc && world && world.cam ? this.scenePaintBounds() : null; }
         finally { this.csRvProfileEnabled = enabledBefore; }
         return {enabled:this.csRvProfileEnabled,frames:this.csRvProfileFrames,elapsedMs:getTimer()-this.csRvProfileStarted,
            mode:this.cfgMode,visionEnabled:this.cfgEnabled,methods:methods,frameMs:histogram,
            dimensions:{width:this.spaceX,height:this.spaceY,tiles:this.spaceX*this.spaceY,
               sightWidth:this.currentSight ? this.currentSight.width : 0,sightHeight:this.currentSight ? this.currentSight.height : 0,
               sightVectorAllocated:this.currentSightData != null,
               fogWidth:this.fogCache ? this.fogCache.width : 0,fogHeight:this.fogCache ? this.fogCache.height : 0,
               view:view ? {x:view.x,y:view.y,width:view.width,height:view.height,tiles:view.width*view.height} : null,
               wallTiles:this.wallTiles ? this.wallTiles.length : 0,wallCorners:this.wallCorners ? this.wallCorners.length : 0,
               units:this.curLoc && this.curLoc.units ? this.curLoc.units.length : 0,
               cameraScale:world && world.cam ? world.cam.scaleV : 0},
            state:{fovVersion:this.fovVersion,fogDirty:this.fogDirty,fogBlurPending:this.fogBlurPending,
               wallGeometryDirty:this.wallGeometryDirty,lastFrameMs:this.lastFrameMs,lastFovFrame:this.lastFovFrame}};
      }

      private function csRvProfileCopySight():Vector.<uint>
      {
         var measured:Boolean = this.csRvProfileEnter("currentSight.getVector");
         try { return this.currentSight.getVector(this.currentSight.rect); }
         finally { if(measured) this.csRvProfileLeave(); }
         return null; // ASC requires a typed tail after try/finally.
      }

      private function csRvProfileClearSight():void
      {
         var measured:Boolean = this.csRvProfileEnter("currentSight.clear");
         try { this.currentSight.fillRect(this.currentSight.rect,0); }
         finally { if(measured) this.csRvProfileLeave(); }
      }

      private function csRvProfileBlurFog(rect:Rectangle, point:Point):void
      {
         var measured:Boolean = this.csRvProfileEnter("fogBmp.applyFilter");
         try { this.fogBmp.applyFilter(this.fogRaw,rect,point,this.curBlur); }
         finally { if(measured) this.csRvProfileLeave(); }
      }
'''


def instrument(source: str, fine: bool = False) -> tuple[str, dict]:
    if "csRvProfilePublish" in source:
        raise RuntimeError("Source already contains RV instrumentation")
    source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
    names = COARSE + (FINE if fine else ())
    edits = []
    for name in names:
        start, end = _body(source, name)
        original = source[start + 1:end]
        wrapped = ('\n         var __csRvProfiled:Boolean = this.csRvProfileEnter("' + name + '");\n'
                   '         try\n         {\n' + original + '\n         }\n'
                   '         finally { if(__csRvProfiled) this.csRvProfileLeave(); }'
                   + _default_return(source, name, start) + '\n      ')
        edits.append((start + 1, end, wrapped))
    for start, end, body in sorted(edits, reverse=True):
        source = source[:start] + body + source[end:]
    import_anchor = "   import flash.display.Bitmap;"
    if source.count(import_anchor) != 1:
        raise RuntimeError("RV import anchor changed")
    source = source.replace(import_anchor, "   import flash.desktop.NativeApplication;\n" + import_anchor, 1)
    for old, new, expected in (
        ("this.currentSight.getVector(this.currentSight.rect)", "this.csRvProfileCopySight()", 3),
        ("this.currentSight.fillRect(this.currentSight.rect,0);", "this.csRvProfileClearSight();", 1),
        ("this.fogBmp.applyFilter(this.fogRaw,scenePixelBounds,scenePixelPoint,this.curBlur);",
         "this.csRvProfileBlurFog(scenePixelBounds,scenePixelPoint);", 1),
    ):
        count = source.count(old)
        if count != expected:
            raise RuntimeError(f"RV pixel operation anchor expected {expected}, got {count}: {old}")
        source = source.replace(old, new)
    start, _ = _body(source, "startup")
    source = source[:start + 1] + "\n         this.csRvProfilePublish(main);" + source[start + 1:]
    anchor = "      private static const VERSION:String = "
    if source.count(anchor) != 1:
        raise RuntimeError("RV version anchor changed")
    source = re.sub(r'(private static const VERSION:String = ")([^"]+)(";)', r'\1\2-instrumented\3', source, count=1)
    profile = PROFILE.replace("__SOURCE_HASH__", source_hash).replace("__FINE__", "true" if fine else "false")
    profile = profile.replace("__METHOD_NAMES__", json.dumps(names + PIXEL_OPERATIONS))
    point = source.index(anchor)
    source = source[:point] + profile + "\n" + source[point:]
    return source, {"sourceSHA256": source_hash, "fine": fine, "methods": list(names + PIXEL_OPERATIONS),
                    "carrier": "ContinuousSceneVisionProfile", "isolatedOnly": True,
                    "warning": "Milliseconds include profiler overhead; compare timing disabled/enabled before interpretation."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=GENERATED / "rv-production")
    parser.add_argument("--output", type=Path, default=GENERATED / "rv-profile")
    parser.add_argument("--fine", action="store_true")
    args = parser.parse_args()
    source_dir, output_dir = args.source.resolve(), args.output.resolve()
    generated = GENERATED.resolve()
    if not source_dir.is_relative_to(generated) or not output_dir.is_relative_to(generated):
        raise RuntimeError("Both source and output must be inside ContinuousScene/build/generated")
    if source_dir == output_dir or output_dir.is_relative_to(source_dir) or source_dir.is_relative_to(output_dir):
        raise RuntimeError("Profiler input/output directories must be separate siblings")
    source_file = source_dir / "RealisticVisionMod.as"
    source = source_file.read_text(encoding="utf-8-sig")
    patched, metadata = instrument(source, args.fine)
    # Includes the already-reviewed locale/carrier dependencies. Never copies RV
    # working-tree WIP and never writes an installed SWF or release directory.
    shutil.copytree(source_dir, output_dir, dirs_exist_ok=True)
    (output_dir / "RealisticVisionMod.as").write_text(patched, encoding="utf-8")
    (output_dir / "profile-manifest.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output_dir), **metadata}))


if __name__ == "__main__":
    main()
