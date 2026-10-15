"""Freeze released WallBlend 0.5.3 and prepare ContinuousScene compatibility.

Never writes the WallBlend checkout or release directory. Candidate changes
are the scene cache, regional color-sampling guards, and diagnostic version.
This script prepares sources/configuration; compilation and deployment belong
to ContinuousScene's caller and release gate.
"""
from pathlib import Path
import hashlib
import json
import subprocess
from xml.sax.saxutils import escape
import wallblend_perf

MOD = Path(__file__).resolve().parents[1]
ROOT = MOD.parents[1]
WB = ROOT / "mods/WallBlend"
STAGE = MOD / "build/generated/wb-production"
BASE = "f32e4a99643ccc901dc4f8e8caac29a6cde441b4"
RELEASE_VERSION = "0.5.3"
VERSION = "0.5.4-scene"
# Published provenance, not a requirement on the mutable installed binary.
# 0.5.2 partial/fake wall support and 0.5.3 relief sampling all live in
# BlendLayer.as. Its only compatibility edit excludes another region's tint
# from relief measurements; all native geometry/damage/relief rules remain.
BASELINE_RELEASE = {
    "version": RELEASE_VERSION,
    "bytes": 28092,
    "sha256": "A6AE7EF3CADA5D4C733A53CE72E2423C35724EF8075CA81393B26EE47F0302CA",
    "receipt": "mods/WallBlend/build/backups/upgrade-20261015-140121/receipt.json",
    "deployedSmoke": "mods/WallBlend/build/results/wallblend-test-20261015140150-f1cce3",
}


_CACHE = r'''package wallblend {
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.display.Sprite;
    import flash.geom.Point;
    import flash.geom.Rectangle;
    import flash.utils.Dictionary;

    /** Native surfaces stay resident. Each regional style owns an overlay pass;
     *  exact world-space clips compose passes, including boundaries inside a chunk.
     */
    public final class SceneBlendCache {
        private var entries:Dictionary=new Dictionary();
        private var materials:Object={front:{},back:{}};
        public var count:int=0;
        public var updates:int=0;
        public var regionalPasses:int=0;
        public var backdropCopies:int=0;
        public function SceneBlendCache() {}
        public function invalidate():void {
            for each(var state:Object in entries) {
                state.settings="";
                for each(var pass:Object in state.passes) { pass.front.invalidate();pass.back.invalidate(); }
            }
        }
        public function get visibleCount():int {
            var result:int=0;
            for each(var state:Object in entries) for each(var bitmap:Bitmap in state.overlays)
                if(bitmap.parent && bitmap.visible && bitmap.bitmapData) result++;
            return result;
        }
        public function clear():void {
            for each(var state:Object in entries) drop(state);
            entries=new Dictionary();count=0;regionalPasses=0;backdropCopies=0;
            materials={front:{},back:{}};
        }
        private function drop(state:Object):void {
            regionalPasses-=state.passes.length;
            for each(var pass:Object in state.passes) {
                pass.front.dispose();pass.back.dispose();
                // These two bitmaps borrow the native buffers; detach, never dispose.
                for each(var owner:Sprite in [pass.view.visFront,pass.view.visBack])
                    while(owner.numChildren) {
                        var child:Bitmap=owner.removeChildAt(0) as Bitmap;
                        if(child) child.bitmapData=null;
                    }
                pass.view.loc=null;pass.view.frontBmp=null;
                pass.front=null;pass.back=null;pass.view=null;
            }
            for each(var data:BitmapData in state.composite) data.dispose();
            for each(var bitmap:Bitmap in state.overlays) {
                if(bitmap.parent) bitmap.parent.removeChild(bitmap);
                bitmap.bitmapData=null;
            }
            state.passes=[];state.composite=[];state.overlays=[];
        }
        public function update(g:*,data:XML,width:int,style:String,tone:Number,spacing:Number,depth:Number,toneWidth:Number,enabled:Boolean):void {
            var alive:Dictionary=new Dictionary();
            var settings:String=[width,style,tone,spacing,depth,toneWidth].join(":");
            var surfaces:Array=g.sceneSurfaces();
            var viewport:Rectangle="sceneViewport" in g?g.sceneViewport():null;
            for each(var surface:Object in surfaces) alive[surface]=true;
            // Full native redraws replace every surface. Release old overlays
            // before allocating their replacements instead of doubling peak memory.
            for(var key:Object in entries) if(!alive[key]) {drop(entries[key]);delete entries[key];--count;}
            for each(surface in surfaces) {
                var state:Object=entries[surface];
                if(!state) {
                    state={passes:makePasses(g,surface),overlays:[],composite:[],revision:-1,settings:""};
                    entries[surface]=state;++count;
                    for(var i:int=0;i<2;++i) {
                        var bitmap:Bitmap=new Bitmap();
                        bitmap.scrollRect=new Rectangle(surface.gutter,surface.gutter,surface.side,surface.side);
                        bitmap.name=i==0?"WallBlendSceneFront":"WallBlendSceneBack";
                        bitmap.x=surface.x+surface.gutter;bitmap.y=surface.y+surface.gutter;
                        (i==0?g.visFront:g.visBack).addChild(bitmap);state.overlays.push(bitmap);
                    }
                }
                for(i=0;i<2;i++) {
                    bitmap=state.overlays[i];
                    var show:Boolean=enabled && (viewport==null || viewport.intersects(new Rectangle(surface.x+surface.gutter,surface.y+surface.gutter,surface.side,surface.side)));
                    if(bitmap.visible!=show) bitmap.visible=show;
                    var parent:Sprite=i==0?g.visFront:g.visBack;
                    if(bitmap.parent!==parent) parent.addChild(bitmap);
                    var native:Bitmap=surface.bitmaps?surface.bitmaps[i]:null;
                    if(native && native.parent===parent && parent.getChildIndex(bitmap)<parent.getChildIndex(native))
                        parent.setChildIndex(bitmap,parent.getChildIndex(native));
                }
                if(!enabled || (state.revision==surface.revision && state.settings==settings)) continue;
                for each(var pass:Object in state.passes) {
                    refreshView(g,surface,pass.view,pass.region);
                    pass.front.update(pass.view,data,width,style,tone,spacing,depth,toneWidth);
                    pass.back.update(pass.view,data,style);
                }
                var outputs:Array=compose(state,surface);
                for(i=0;i<2;++i) {
                    bitmap=state.overlays[i];bitmap.bitmapData=outputs[i];
                }
                state.revision=surface.revision;state.settings=settings;++updates;
            }
        }

        private function makePasses(g:*,surface:Object):Array {
            var full:Rectangle=surface.nativeBuffers[0].rect;
            var worldBounds:Rectangle=new Rectangle(surface.x,surface.y,full.width,full.height);
            var slices:Array="sceneRegionSlices" in g ? g.sceneRegionSlices(g.loc,worldBounds) : [];
            var groups:Array=[],byStyle:Object={},area:Number=0;
            for each(var slice:Object in slices) {
                var clip:Rectangle=Rectangle(slice.bounds).intersection(worldBounds);
                if(clip.isEmpty()) continue;
                clip.offset(-surface.x,-surface.y);
                var group:Object=byStyle[slice.style.key];
                if(!group) {
                    group={style:slice.style,clips:[]};byStyle[slice.style.key]=group;groups.push(group);
                }
                group.clips.push(clip);area+=clip.width*clip.height;
            }
            var inWorld:Rectangle=worldBounds.intersection(new Rectangle(0,0,g.loc.limX,g.loc.limY));
            if(groups.length==0) groups.push({style:null,clips:[full]});
            else if(area<inWorld.width*inWorld.height) groups.unshift({style:null,clips:uncovered(full,groups)});
            else if(groups.length==1) groups[0].clips=[full];
            var result:Array=[];
            for each(group in groups) {
                var passView:Object=view(g,surface,group.style);
                // Lighting estimates must not sample another region's already
                // composed tint. Full-surface passes retain the original hot path.
                if(group.clips.length!=1 || !full.equals(group.clips[0]))
                    passView.loc.paintRegionClips=group.clips;
                result.push({front:new BlendLayer(),back:new BackgroundBlendLayer(),
                    view:passView,region:group.style,clips:group.clips});
                ++regionalPasses;
            }
            return result;
        }

        private function uncovered(full:Rectangle,groups:Array):Array {
            var remaining:Array=[full];
            for each(var group:Object in groups) for each(var cut:Rectangle in group.clips) {
                var next:Array=[];
                for each(var area:Rectangle in remaining) {
                    var overlap:Rectangle=area.intersection(cut);
                    if(overlap.isEmpty()) {next.push(area);continue;}
                    if(overlap.top>area.top) next.push(new Rectangle(area.left,area.top,area.width,overlap.top-area.top));
                    if(overlap.bottom<area.bottom) next.push(new Rectangle(area.left,overlap.bottom,area.width,area.bottom-overlap.bottom));
                    if(overlap.left>area.left) next.push(new Rectangle(area.left,overlap.top,overlap.left-area.left,overlap.height));
                    if(overlap.right<area.right) next.push(new Rectangle(overlap.right,overlap.top,area.right-overlap.right,overlap.height));
                }
                remaining=next;
            }
            return remaining;
        }

        private function compose(state:Object,surface:Object):Array {
            if(state.passes.length==1)
                return [state.passes[0].front.outputData,state.passes[0].back.outputData];
            var full:Rectangle=surface.nativeBuffers[0].rect;
            if(state.composite.length==0) {
                state.composite.push(new BitmapData(full.width,full.height,true,0));
                state.composite.push(new BitmapData(full.width,full.height,true,0));
            }
            for(var i:int=0;i<2;++i) {
                var target:BitmapData=state.composite[i];target.fillRect(full,0);
                for each(var pass:Object in state.passes) {
                    var source:BitmapData=i==0?pass.front.outputData:pass.back.outputData;
                    if(source==null) continue;
                    for each(var clip:Rectangle in pass.clips)
                        target.copyPixels(source,clip,new Point(clip.x,clip.y));
                }
            }
            return state.composite;
        }

        private function view(g:*,s:Object,region:Object):Object {
            var native:*=g.loc;
            var loc:Object={spaceX:s.nativeBuffers[0].width/40,spaceY:s.nativeBuffers[0].height/40,space:[],backobjs:[],
                paintX:s.x,paintY:s.y,paintWorldWidth:native.limX,paintWorldHeight:native.limY,paintMaterials:materials};
            var front:Sprite=new Sprite(),back:Sprite=new Sprite();
            front.addChild(new Bitmap(s.nativeBuffers[0]));back.addChild(new Bitmap(s.nativeBuffers[1]));
            var result:Object={loc:loc,frontBmp:s.nativeBuffers[0],visFront:front,visBack:back,getObj:g.getObj};
            refreshView(g,s,result,region);
            return result;
        }

        private function refreshView(g:*,s:Object,view:Object,region:Object):void {
            var native:*=g.loc,loc:Object=view.loc;
            loc.homeStable=region?region.homeStable:native.homeStable;loc.lightOn=native.lightOn;
            loc.transpFon=region?region.transpFon:native.transpFon;
            loc.cTransform=region?region.cTransform:native.cTransform;
            loc.color=region?region.color:native.color;loc.darkness=region?region.darkness:native.darkness;
            loc.backwall=region?region.backwall:native.backwall;
            view.frontBmp=s.nativeBuffers[0];
            Bitmap(view.visFront.getChildAt(0)).bitmapData=s.nativeBuffers[0];
            Bitmap(view.visBack.getChildAt(0)).bitmapData=s.nativeBuffers[1];
            for(var x:int=0;x<loc.spaceX;++x) {
                if(!loc.space[x]) loc.space[x]=[];
                for(var y:int=0;y<loc.spaceY;++y) loc.space[x][y]=native.getTile(x+int(s.x/40),y+int(s.y/40));
            }
            var candidates:Array=s.backobjs as Array;
            if(candidates==null) candidates="sceneBackdropObjects" in g ?
                g.sceneBackdropObjects(s.x,s.y,s.nativeBuffers[0].width,s.nativeBuffers[0].height) : native.backobjs;
            loc.backobjs.length=candidates.length;
            for(var index:int=0;index<candidates.length;++index) {
                var bo:*=candidates[index],copy:Object=loc.backobjs[index];
                if(!copy) {copy={};loc.backobjs[index]=copy;++backdropCopies;}
                copy.id=bo.id;copy.X=bo.X-s.x;copy.Y=bo.Y-s.y;copy.scX=bo.scX;copy.scY=bo.scY;
                copy.frame=bo.frame;copy.sloy=bo.sloy;copy.alpha=bo.alpha;copy.er=bo.er;
                copy.vis=bo.vis;copy.erase=bo.erase;copy.light=bo.light;
            }
        }
    }
}
'''


def _once(source, old, new):
    if source.count(old) != 1:
        raise RuntimeError(f"WallBlend source anchor mismatch: {old[:100]}")
    return source.replace(old, new, 1)


def candidate_source(relative: str, content: bytes) -> bytes:
    if relative == "src/wallblend/SceneBlendCache.as":
        source = content.decode("utf-8-sig")
        for anchor in ["private function view(g:*,s:Object):Object", "for each(var bo:* in native.backobjs)",
                       "state.front.update(state.view,data,width,style,tone,spacing,depth,toneWidth);",
                       "state.back.update(state.view,data,style);"]:
            if source.count(anchor) != 1:
                raise RuntimeError(f"Unexpected released SceneBlendCache: {anchor}")
        return _CACHE.encode("utf-8")
    if relative == "src/wallblend/BackgroundBlendLayer.as":
        source = content.decode("utf-8-sig")
        source = _once(source, '            if(excluded[y*source.width+x]) return true;',
                       '            if("paintRegionClips" in location) {\n'
                       '                var insideRegion:Boolean=false;\n'
                       '                for each(var regionClip:Rectangle in location.paintRegionClips)\n'
                       '                    if(regionClip.contains(x,y)) {insideRegion=true;break;}\n'
                       '                if(!insideRegion) return true;\n'
                       '            }\n'
                       '            if(excluded[y*source.width+x]) return true;')
        return source.encode("utf-8")
    if relative == "src/wallblend/BlendLayer.as":
        source = content.decode("utf-8-sig")
        source = _once(source,
                       '                var pixel:uint=source.getPixel32(x,y),texture:uint=sample(id,x,y);',
                       '                // Scene buffers already contain each region\'s native tint.\n'
                       '                // Do not interpret another tint as material-edge relief.\n'
                       '                // Native rooms have no paintRegionClips and keep every sample.\n'
                       '                if("paintRegionClips" in location) {\n'
                       '                    var sceneInsideRegion:Boolean=false;\n'
                       '                    for each(var sceneRegionClip:Rectangle in location.paintRegionClips)\n'
                       '                        if(sceneRegionClip.contains(x,y)) {sceneInsideRegion=true;break;}\n'
                       '                    if(!sceneInsideRegion) continue;\n'
                       '                }\n'
                       '                var pixel:uint=source.getPixel32(x,y),texture:uint=sample(id,x,y);')
        return source.encode("utf-8")
    if relative == "src/WallBlendMod.as":
        source = content.decode("utf-8-sig")
        source = _once(source, '                host.stage.addEventListener(Event.ENTER_FRAME, onFrame, false, -100, true);',
                       '                host.stage.addEventListener(Event.ENTER_FRAME, onFrame, false, -100, true);\n'
                       '                host.addEventListener("continuousSceneBeforeRasterClear",onSceneClear,false,0,true);')
        source = _once(source, '        public static function setEnabled(value:Boolean):void {',
                       '        private static function onSceneClear(event:Event):void {\n'
                       '            if(sceneCache.count) sceneCache.clear();\n'
                       '        }\n\n        public static function setEnabled(value:Boolean):void {')
        source = _once(source, f'public static const VERSION:String = "{RELEASE_VERSION}";',
                       f'public static const VERSION:String = "{VERSION}";')
        source = _once(source, 'sceneVisible:sceneCache.visibleCount,display:displayStatus()};',
                       'sceneVisible:sceneCache.visibleCount,sceneRegionalPasses:sceneCache.regionalPasses,\n'
                       '                    sceneBackdropCopies:sceneCache.backdropCopies,display:displayStatus()};')
        return source.encode("utf-8")
    return content


def prepare():
    actual = subprocess.check_output(["git", "-C", str(WB), "rev-parse", BASE], text=True).strip()
    if actual != BASE:
        raise RuntimeError("Released WallBlend source commit changed")
    files = subprocess.check_output(["git", "-C", str(WB), "ls-tree", "-r", "--name-only", BASE, "src"], text=True).splitlines()
    if len(files) != 13 or "src/wallblend/SceneBlendCache.as" not in files:
        raise RuntimeError("Unexpected released WallBlend source inventory")
    targets = {STAGE / Path(relative).relative_to("src") for relative in files}
    extras = set(STAGE.rglob("*.as")) - targets if STAGE.exists() else set()
    if extras:
        raise RuntimeError("Untracked candidate AS3 files present; review before replacing: " + str(sorted(extras)))
    records = []
    for relative in files:
        original = subprocess.check_output(["git", "-C", str(WB), "show", BASE + ":" + relative])
        candidate = wallblend_perf.apply(relative, candidate_source(relative, original).decode('utf-8-sig')).encode('utf-8')
        target = STAGE / Path(relative).relative_to("src")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(candidate)
        records.append({"source": relative, "modified": candidate != original,
                        "sourceSHA256": hashlib.sha256(original).hexdigest(),
                        "candidateSHA256": hashlib.sha256(candidate).hexdigest()})
    air = ROOT / "mods/Sandevistan/build/tools/airsdk/frameworks/libs/air/airglobal.swc"
    config = f'''<flex-config>
  <compiler><external-library-path><path-element>{escape(str(air))}</path-element></external-library-path>
    <debug>false</debug><optimize>true</optimize><strict>true</strict><theme/>
  </compiler>
  <target-player>32.0</target-player><swf-version>32</swf-version>
  <use-network>false</use-network><static-link-runtime-shared-libraries>true</static-link-runtime-shared-libraries>
</flex-config>
'''
    (STAGE / "air-config.xml").write_text(config, encoding="utf-8")
    report = {"baseCommit": BASE, "baselineRelease": BASELINE_RELEASE, "version": VERSION, "modifiedFiles": [r["source"] for r in records if r["modified"]],
              "scope": "released 0.5.3 sources plus scene backdrop candidates, clipped regional overlay passes and tint-safe relief samples",
              "files": records}
    (STAGE / "source-manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"stage": str(STAGE), "version": VERSION, "sourceFiles": len(files), "modifiedFiles": report["modifiedFiles"]}))
    return report


if __name__ == "__main__":
    prepare()
