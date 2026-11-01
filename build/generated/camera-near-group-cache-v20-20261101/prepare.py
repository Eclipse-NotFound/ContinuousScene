from pathlib import Path
import shutil
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'camera-static-groups-v15-20261101'
group=(OLD/'StaticObjectGroups.as').read_text('utf-8-sig')
group=group.replace('import flash.utils.Dictionary;', 'import flash.utils.Dictionary;\n    import flash.geom.Rectangle;')
group=group.replace('private var active:Boolean=false;', '''private var active:Boolean=false;
        public var cacheEnabled:Boolean=true;
        private var view:Rectangle,near:Rectangle;
        private var cachedGroups:int=0,cachedVisible:int=0,wrappedVisible:int=0,estimatedPixels:Number=0;''')
group=group.replace('active=true;', '''active=true;cachedGroups=cachedVisible=wrappedVisible=0;estimatedPixels=0;
            var scale:Number=w.cam.scaleV;
            view=new Rectangle(-w.cam.vx/scale,-w.cam.vy/scale,w.cam.screenX/scale,w.cam.screenY/scale);
            near=view.clone();near.inflate(512,512);''')
group=group.replace('if(children.length<2)return;', '''if(children.length<2)return;
            var bounds:Rectangle=null,visible:int=0;
            for each(var root:DisplayObject in children) {
                var rect:Rectangle=root.getBounds(layer);
                bounds=bounds?bounds.union(rect):rect;
                if(root.visible && root.alpha>0 && rect.intersects(view))++visible;
            }
            if(!near.intersects(bounds))return;''')
group=group.replace('for each(var child:DisplayObject in children){group.addChild(child);++moved;}', '''for each(var child:DisplayObject in children){group.addChild(child);++moved;}
            wrappedVisible+=visible;
            var width:int=Math.ceil(bounds.width)+256,height:int=Math.ceil(bounds.height)+256;
            var area:Number=Number(width)*height;
            if(cacheEnabled && width<=2048 && height<=2048 && estimatedPixels+area<=16777216) {
                group.cacheAsBitmap=true;estimatedPixels+=area;++cachedGroups;cachedVisible+=visible;
            }''')
group=group.replace('return {active:active,groups:', 'return {cacheEnabled:cacheEnabled,cachedGroups:cachedGroups,cachedVisible:cachedVisible,wrappedVisible:wrappedVisible,estimatedPixels:estimatedPixels,active:active,groups:')
(HERE/'StaticObjectGroups.as').write_text(group,'utf-8')
probe=(OLD/'ContinuousSceneMotionMod.as').read_text('utf-8-sig')
probe=probe.replace('camera-static-groups-15','camera-near-group-cache-20')
probe=probe.replace('["static","x","y"]','["x","y"]')
probe=probe.replace('["full","fill","fill","full"]','["full","group","fill","fill","group","full"]')
probe=probe.replace('frames:300','frames:240')
probe=probe.replace('fill.setEnabled(w,mode=="fill");drawing=mode;', '''if(drawing!=mode) {
                fill.clear();fill.cacheEnabled=mode=="fill";
                fill.setEnabled(w,mode!="full");drawing=mode;
            }''')
probe=probe.replace('if(mode=="fill")assertThat("fill-active-"+index,mark.fill.active && mark.fill.groups>0 && mark.fill.errors==0,mark.fill);', '''if(mode!="full")assertThat("group-active-"+index,mark.fill.active && mark.fill.wrappedVisible>0 && mark.fill.errors==0,mark.fill);
                        if(mode=="fill")assertThat("cache-covers-visible-"+index,mark.fill.cachedVisible>0 && mark.fill.cachedGroups>0,mark.fill);''')
probe=probe.replace('report.pixels=[];', 'report.pixels=[];report.nativeCacheStagePixelsVerified=false;')
a=probe.index('            for each(var offset:Array',probe.index('private static function pixelCheck()'))
b=probe.index('            assertThat("groups-balanced"',a)
probe=probe[:a]+'''            for each(var cache:Boolean in [false,true]) {
                fill.cacheEnabled=cache;
                for each(var offset:Array in [[0,0],[120,0],[-160,0],[0,96],[0,-96]]) {
                    cam.X=centerX+offset[0];cam.Y=centerY+offset[1];cam.calc(player);g.sceneTick();
                    var a:BitmapData=captureWorld();fill.setEnabled(w,true);
                    var b:BitmapData=captureWorld(),status:Object=fill.stats(),diff:Object=compareImages(a,b);
                    report.pixels.push({cache:cache,offset:offset,difference:diff,stats:status});a.dispose();b.dispose();
                    assertThat("near-pixels-exact-"+report.pixels.length,status.active && status.wrappedVisible>0 && diff.changed==0,diff);
                    if(cache)assertThat("near-cache-covers-view-"+report.pixels.length,status.cachedVisible>0,status);
                    a=captureWorld();fill.clear();b=captureWorld();diff=compareImages(a,b);a.dispose();b.dispose();
                    assertThat("near-restores-exactly-"+report.pixels.length,diff.changed==0,diff);
                }
            }
'''+probe[b:]
(HERE/'ContinuousSceneMotionMod.as').write_text(probe,'utf-8')
for name in ('work.py','CameraProbePlatform.as'):shutil.copy2(OLD/name,HERE/name)
print('Prepared near-view only grouping/cache, with nontransparent visible-child coverage assertions')
