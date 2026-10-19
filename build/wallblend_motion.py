"""Slice only unpublished scene overlays; retain the released pixel algorithms."""
from pathlib import Path
import hashlib,json,shutil,subprocess
import wallblend_trim as base

B=Path(__file__).resolve().parent
OUT=B/'generated/wb-motion-source'
def once(s,a,b):
    assert s.count(a)==1,a
    return s.replace(a,b)

def patch(name,s):
    if name in ('BlendLayer.as','BackgroundBlendLayer.as'):
        anchor='        public function '+name[:-3]+'() {}'
        s=once(s,anchor,'''        public var sceneDeadline:int=0;
        private var sceneStep:Function;
        public function get scenePending():Boolean {return sceneStep!=null;}
'''+anchor)
        s=once(s,'            if(layer && layer.parent)' if name.startswith('Background') else '            if (layer && layer.parent)',
               '            sceneStep=null;\n'+('            if(layer && layer.parent)' if name.startswith('Background') else '            if (layer && layer.parent)'))
        anchor='            var loc:* = grafon.loc;' if name=='BlendLayer.as' else '            if(style!="material"'
        if name=='BlendLayer.as':
            s=s.replace(anchor,'            if(sceneStep!=null){sceneStep();return;}\n'+anchor,1)
            a=s.index('            metrics.pixels = 0;',s.index('private function rebuild'))
            b=s.index('\n        }',a)
            s=s[:a]+'''            metrics.pixels = 0;
            var position:int=0;
            sceneStep=function():void {
                while(position<rows*cols) {
                    var px:int=position%cols,py:int=int(position/cols);++position;
                    var id:String=cell(px,py);
                    if(id && (different(id,cell(px-1,py)) || different(id,cell(px+1,py)) ||
                        different(id,cell(px,py-1)) || different(id,cell(px,py+1))))makePatch(px,py,id);
                    if(sceneDeadline && getTimer()>=sceneDeadline)return;
                }
                sceneStep=null;metrics.patches=patches.length;metrics.rebuilds++;
                metrics.rebuildMs=getTimer()-started;
            };
            sceneStep();'''+s[b:]
        else:
            s=once(s,anchor,'            if(sceneStep!=null){sceneStep();return;}\n'+anchor)
            a=s.index('                for(y=0;y<loc.spaceY;++y) for(x=0;x<loc.spaceX;++x) {')
            b=s.index('\n            } else syncDamage();',a)
            s=s[:a]+'''                var position:int=0;
                sceneStep=function():void {
                    while(position<loc.spaceX*loc.spaceY) {
                        var px:int=position%loc.spaceX,py:int=int(position/loc.spaceX);++position;
                        var a:String=cell(px,py),b:String;
                        if(a) {
                            b=cell(px+1,py);if(b && b!=a)addStrip(a,b,(px+1)*40,py*40,true);
                            b=cell(px,py+1);if(b && b!=a)addStrip(a,b,(py+1)*40,px*40,false);
                        }
                        if(sceneDeadline && getTimer()>=sceneDeadline)return;
                    }
                    sceneStep=null;native=null;protectedMemo=null;
                    metrics.rebuilds++;metrics.patches=patches.length;metrics.rebuildMs=getTimer()-started;
                };
                sceneStep();'''+s[b:]
    if name=='SceneBlendCache.as':
        s=once(s,'    import flash.utils.Dictionary;','    import flash.utils.Dictionary;\n    import flash.utils.getTimer;')
        s=once(s,'        public static var trimPadding:', '        public static var sliced:Boolean=true;\n        public static var verify:Boolean=false;\n        public var comparisons:Array=[];\n        public var maxSliceMs:int=0;\n        public static var trimPadding:')
        # Explicit invalidation must also clear completed async-pass markers.
        # Otherwise unchanged settings skip both layers and republish old pixels.
        s=once(s,'                state.settings="";',
            '                state.settings="";state.pendingSettings=null;state.pendingRevision=-1;')
        s=once(s,'        public function SceneBlendCache() {}', '''        public function SceneBlendCache() {}
        public function rebuildCount():int {
            var total:int=0;
            for each(var state:Object in entries)for each(var pass:Object in state.passes)
                total+=int(pass.front.stats.rebuilds)+int(pass.back.stats.rebuilds);
            return total;
        }''')
        anchor='            for each(var surface:Object in surfaces) alive[surface]=true;'
        s=once(s,anchor,'''            var deadline:int=getTimer()+6;
            if(viewport)surfaces.sort(function(a:Object,b:Object):Number {
                var ax:Number=a.x+a.gutter+a.side/2,ay:Number=a.y+a.gutter+a.side/2;
                var bx:Number=b.x+b.gutter+b.side/2,by:Number=b.y+b.gutter+b.side/2;
                return Math.abs(ax-(viewport.x+viewport.width/2))+Math.abs(ay-(viewport.y+viewport.height/2))-
                    Math.abs(bx-(viewport.x+viewport.width/2))-Math.abs(by-(viewport.y+viewport.height/2));
            });
'''+anchor)
        a=s.index('                for each(var pass:Object in state.passes) {\n                    refreshView')
        b=s.index('\n                var outputs:Array=compose',a)
        s=s[:a]+'''                var visibleNow:Boolean=viewport==null || viewport.intersects(new Rectangle(surface.x+surface.gutter,surface.y+surface.gutter,surface.side,surface.side));
                var deferred:Boolean=sliced && !visibleNow && state.revision<0;
                if(deferred && getTimer()>=deadline)continue;
                if(state.pendingRevision!==surface.revision || state.pendingSettings!==settings) {
                    for each(var reset:Object in state.passes) {
                        if(reset.front.scenePending || reset.back.scenePending){reset.front.dispose();reset.back.dispose();}
                        reset.frontDone=false;reset.backDone=false;
                    }
                    state.pendingRevision=surface.revision;state.pendingSettings=settings;
                }
                var complete:Boolean=true;
                var sliceStart:int=getTimer();
                for each(var pass:Object in state.passes) {
                    refreshView(g,surface,pass.view,pass.region);
                    pass.front.sceneDeadline=pass.back.sceneDeadline=deferred?deadline:0;
                    if(!pass.frontDone) {
                        pass.front.update(pass.view,data,width,style,tone,spacing,depth,toneWidth);
                        pass.frontDone=!pass.front.scenePending;
                    }
                    if(pass.frontDone && !pass.backDone && (!deferred || getTimer()<deadline)) {
                        pass.back.update(pass.view,data,style);pass.backDone=!pass.back.scenePending;
                    }
                    if(!pass.frontDone || !pass.backDone){complete=false;break;}
                }
                maxSliceMs=Math.max(maxSliceMs,getTimer()-sliceStart);
                if(!complete)continue;
                if(verify) {
                    for each(pass in state.passes) {
                        var front:BlendLayer=new BlendLayer(),back:BackgroundBlendLayer=new BackgroundBlendLayer();
                        front.update(pass.view,data,width,style,tone,spacing,depth,toneWidth);back.update(pass.view,data,style);
                        var expected:Array=[front.outputData,back.outputData];var actual:Array=[pass.front.outputData,pass.back.outputData];
                        for(var n:int=0;n<2;++n) {
                            var difference:*=actual[n]==null && expected[n]==null?0:actual[n].compare(expected[n]);
                            comparisons.push({cx:surface.cx,cy:surface.cy,layer:n,equal:difference===0});
                            if(difference is BitmapData)difference.dispose();
                        }
                        front.dispose();back.dispose();
                    }
                }'''+s[b:]
    if name=='WallBlendMod.as':
        s=once(s,'"0.5.8-scene"','"0.5.9-scene"')
        a='                worldClass = getDefinitionByName("fe.World") as Class;'
        s=once(s,a,'''                if(NativeApplication.nativeApplication.applicationID.indexOf("pfe-modsettings-continuous-motion-")==0)
                    host.addEventListener("continuousSceneWallMotion",function(e:DataEvent):void {
                        if(e.data=="verify")SceneBlendCache.verify=true;
                        if(e.data=="sync")SceneBlendCache.sliced=false;
                        if(e.data=="invalidate")refreshNow();
                        e.data=JSON.stringify({comparisons:sceneCache.comparisons,maxSliceMs:sceneCache.maxSliceMs,rebuilds:sceneCache.rebuildCount()});
                    });
'''+a)
    return s

def prepare():
    base.prepare();OUT.mkdir(parents=True,exist_ok=True);records=[]
    for p in base.STAGE.rglob('*.as'):
        raw=p.read_text('utf-8-sig');s=patch(p.name,raw);dest=OUT/p.relative_to(base.STAGE)
        dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(s,'utf-8')
        records.append({'path':str(p.relative_to(base.STAGE)),'baseline':hashlib.sha256(raw.encode()).hexdigest(),'candidate':hashlib.sha256(s.encode()).hexdigest()})
    shutil.copy2(base.STAGE/'air-config.xml',OUT/'air-config.xml')
    (OUT/'source-manifest.json').write_text(json.dumps(records,indent=2),'utf-8')
    return OUT
if __name__=='__main__':
    source=prepare();tools=B.parents[2]/'mods/Sandevistan/build/tools'
    subprocess.run(['D:/Program Files/Adobe Animate 2024/jre/bin/java.exe','-Dfile.encoding=UTF-8','-jar',str(tools/'flexsdk/lib/mxmlc.jar'),'+flexlib='+str(tools/'flexsdk/frameworks'),'+configname=air','-load-config='+str(source/'air-config.xml'),'-source-path='+str(source),'-output='+str(source/'WallBlendMod.swf'),str(source/'WallBlendDoc.as')],check=True)
