from pathlib import Path
SOURCE=Path(__file__).resolve().parent.parent/'camera-atlas-pool-merged-20261026/SceneRasterPresentation.as'
def one(s,a,b):
    assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
def classic_source():return SOURCE.read_text('utf-8-sig').replace('class SceneRasterPresentation','class SceneClassicAtlas')
def persistent_source():
    s=SOURCE.read_text('utf-8-sig').replace('class SceneRasterPresentation','class ScenePersistentAtlas')
    s=one(s,'    import flash.geom.Point;','    import flash.geom.Point;\n    import flash.events.Event;')
    s=one(s,'        private var pages:Array=[];','''        private var atlasWorld:*;
        private var bindingParents:Array=[];
        private var bindingSurfaces:Array=[];
        private var bindingCells:Object={};
        private var bindingExtras:Array=[];
        private var expectedVisibility:Dictionary=new Dictionary();
        private var boundEpoch:int=-1,treeEpoch:int=0;
        private var boundResident:int=-1,boundRedraws:int=-1,boundEvictions:int=-1;
        private var visibilityKey:String="";
        private var bindingRefreshes:int=0,visibilityRefreshes:int=0,visibilityWrites:int=0,restoreWrites:int=0;
        private var bindingReuses:int=0;
        private var pages:Array=[];''')
    s=one(s,'            beginFrame();\n            requestedPages=0;requestedKeys=[];fallbackReason="";','            requestedPages=0;requestedKeys=[];fallbackReason="";')
    s=one(s,'                ++stationarySkips;return;','                beginFrame();++stationarySkips;return;')
    start=s.index('            var surfaces:Array=g.sceneSurfaces();');end=s.index('            ++clock;',start)
    s=s[:start]+'''            refreshBindings(g,parents);
            var surfaces:Array=bindingSurfaces;
            if(!surfaces.length){fallback("no-native-surfaces");return;}
            if(!backgroundCompatible(parents,surfaces)){fallback("background-order-or-effects");return;}
            refreshVisibility(view);
            var byCell:Object=bindingCells;
'''+s[end:]
    s=one(s,'for each(var nativeBitmap:Bitmap in toHide)if(nativeBitmap.visible){hidden.push(nativeBitmap);nativeBitmap.visible=false;}','for each(var nativeBitmap:Bitmap in toHide)if(nativeBitmap.visible){nativeBitmap.visible=false;++visibilityWrites;}\n                hidden=toHide;')
    # Parent styles are still checked every frame. Event-driven direct child membership
    # is cached; unknown pre-existing invisible children remain watched for activation.
    start=s.index('            var allowed:Dictionary=new Dictionary();',s.index('private function backgroundCompatible'))
    end=s.index('            for each(var parent:DisplayObjectContainer',start)
    s=s[:start]+s[end:]
    a='''                for(var index:int=0;index<parent.numChildren;++index) {
                    var child:*=parent.getChildAt(index);
                    if(child.visible && !allowed[child])return false;
                }'''
    s=one(s,a,'')
    pos=s.index('            return true;',s.index('private function backgroundCompatible'))
    s=s[:pos]+'''            for each(var extra:* in bindingExtras)if(extra.visible)return false;
'''+s[pos:]
    s=one(s,'            poolLocation=location=w.loc;','''            poolLocation=location=w.loc;atlasWorld=w;
            bindingParents=[w.grafon.visFront,w.grafon.visBack,w.grafon.visBack2,w.grafon.visVoda];
            for each(var parent:DisplayObjectContainer in bindingParents) {
                parent.addEventListener(Event.ADDED,onTreeMutation);
                parent.addEventListener(Event.REMOVED,onTreeMutation);
            }''')
    s=one(s,'record.sources[1]!==surface.nativeBuffers[1] ||\n                    record.sources[2]!==surface.nativeBuffers[2] || record.shown[1]!==surface.bitmaps[1].visible ||\n                    record.shown[2]!==surface.bitmaps[2].visible;','record.sources[1]!==surface.nativeBuffers[1] ||\n                    record.sources[2]!==surface.nativeBuffers[2] || record.shown[1]!==Boolean(expectedVisibility[surface.bitmaps[1]]) ||\n                    record.shown[2]!==Boolean(expectedVisibility[surface.bitmaps[2]]);')
    s=one(s,'                    var show:Boolean=bitmap.visible;','                    var show:Boolean=Boolean(expectedVisibility[bitmap]);')
    s=one(s,'            for each(var nativeBitmap:Bitmap in hidden)if(nativeBitmap.parent)nativeBitmap.visible=true;','''            if(atlasWorld && atlasWorld.loc===location && bindingSurfaces.length) {
                var view:Rectangle=atlasWorld.grafon.sceneViewport();
                for each(var surface:Object in bindingSurfaces) {
                    var wanted:Boolean=view==null || view.intersects(new Rectangle(surface.cx*CELL,surface.cy*CELL,CELL,CELL));
                    for each(var nativeBitmap:Bitmap in surface.bitmaps)if(nativeBitmap.parent && nativeBitmap.visible!=wanted) {
                        nativeBitmap.visible=wanted;++restoreWrites;
                    }
                }
            } else for each(nativeBitmap in hidden)if(nativeBitmap.parent)nativeBitmap.visible=true;''')
    s=one(s,'            return {version:"atlas-pool-1",','            return {version:"persistent-atlas-1",bindingRefreshes:bindingRefreshes,bindingReuses:bindingReuses,visibilityRefreshes:visibilityRefreshes,visibilityWrites:visibilityWrites,restoreWrites:restoreWrites,treeEpoch:treeEpoch,boundEpoch:boundEpoch,')
    s=one(s,'            poolLocation=null;location=null;poseValid=false;','''            for each(var parent:DisplayObjectContainer in bindingParents) {
                parent.removeEventListener(Event.ADDED,onTreeMutation);
                parent.removeEventListener(Event.REMOVED,onTreeMutation);
            }
            bindingParents=[];bindingSurfaces=[];bindingCells={};bindingExtras=[];expectedVisibility=new Dictionary();
            boundEpoch=-1;boundResident=boundRedraws=boundEvictions=-1;visibilityKey="";atlasWorld=null;
            poolLocation=null;location=null;poseValid=false;''')
    pos=s.index('        private function fallback(')
    extra='''        private function onTreeMutation(event:Event):void {
            var child:*=event.target;
            if(isOwnedLayer(child))return;
            ++treeEpoch;
        }

        private function isOwnedLayer(child:*):Boolean {
            for each(var page:Object in pages)for each(var layer:Bitmap in page.layers)if(child===layer)return true;
            for each(page in freePages)for each(layer in page.layers)if(child===layer)return true;
            return false;
        }

        private function refreshBindings(g:*,parents:Array):void {
            if(boundEpoch==treeEpoch && boundResident==g.sceneResident && boundRedraws==g.sceneRedraws && boundEvictions==g.sceneEvictions) {
                ++bindingReuses;return;
            }
            var surfaces:Array=g.sceneSurfaces(),cells:Object={},allowed:Dictionary=new Dictionary();
            for each(var surface:Object in surfaces) {
                if(int(surface.side)!=CELL || !isFinite(Number(surface.gutter)) || Number(surface.gutter)<0 ||
                    Number(surface.gutter)!=Math.floor(Number(surface.gutter)) ||
                    Number(surface.x)+Number(surface.gutter)!=Number(surface.cx)*CELL ||
                    Number(surface.y)+Number(surface.gutter)!=Number(surface.cy)*CELL ||
                    !surface.bitmaps || surface.bitmaps.length!=4 || !surface.nativeBuffers || surface.nativeBuffers.length!=4 ||
                    !isFinite(Number(surface.revision)))throw new Error("Persistent atlas native surface contract changed");
                var key:String=surface.cx+":"+surface.cy;
                if(cells[key])throw new Error("Persistent atlas duplicate cell");
                cells[key]=surface;
                for(var layer:int=0;layer<4;++layer) {
                    var bitmap:Bitmap=surface.bitmaps[layer];
                    if(!bitmap || bitmap.parent!==parents[layer] || bitmap.bitmapData!==surface.nativeBuffers[layer])throw new Error("Persistent atlas new native binding mismatch");
                    allowed[bitmap]=true;
                }
            }
            var extras:Array=[];
            for each(var parent:DisplayObjectContainer in [parents[1],parents[2]])for(var i:int=0;i<parent.numChildren;++i) {
                var child:*=parent.getChildAt(i);
                if(!allowed[child] && !isOwnedLayer(child))extras.push(child);
            }
            bindingSurfaces=surfaces;bindingCells=cells;bindingExtras=extras;
            boundEpoch=treeEpoch;boundResident=g.sceneResident;boundRedraws=g.sceneRedraws;boundEvictions=g.sceneEvictions;
            visibilityKey="";++bindingRefreshes;
        }

        private function refreshVisibility(view:Rectangle):void {
            var key:String=Math.floor(view.left/CELL)+":"+Math.floor(view.top/CELL)+":"+Math.ceil(view.right/CELL)+":"+Math.ceil(view.bottom/CELL)+":"+boundEpoch+":"+boundRedraws;
            if(key==visibilityKey)return;
            expectedVisibility=new Dictionary();
            for each(var surface:Object in bindingSurfaces) {
                var visible:Boolean=view.intersects(new Rectangle(surface.cx*CELL,surface.cy*CELL,CELL,CELL));
                for each(var bitmap:Bitmap in surface.bitmaps)expectedVisibility[bitmap]=visible;
            }
            visibilityKey=key;++visibilityRefreshes;
        }

'''
    return s[:pos]+extra+s[pos:]
