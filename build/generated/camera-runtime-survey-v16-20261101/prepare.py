from pathlib import Path
import shutil
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'camera-screen-cache-v13-20261101'
probe=(OLD/'ContinuousSceneMotionMod.as').read_text('utf-8-sig')
probe=probe.replace('private static var fill:ScreenTerrainCache=new ScreenTerrainCache(7);','private static var fill:StaticObjectGroups=new StaticObjectGroups();')
probe=probe.replace('camera-screen-cache-13','camera-static-groups-15')
probe=probe.replace('["x","y","y","x"]','["static","x","y"]')
probe=probe.replace('["full","fill"]','["full","fill","fill","full"]')
probe=probe.replace('frames:270','frames:300')
a=probe.index('            var api:*',probe.index('        private static function drawPolicy()'))
b=probe.index('        private static function after(',a)
probe=probe[:a]+'''            fill.setEnabled(w,mode=="fill");drawing=mode;
        }
'''+probe[b:]
probe=probe.replace('mark.fill.presented && mark.fill.internalErrors==0 && mark.fill.cleanupErrors==0,mark.fill.lastFallback','mark.fill.active && mark.fill.groups>0 && mark.fill.errors==0,mark.fill')
a=probe.index('        private static function pixelCheck()')
b=probe.index('        private static function finish(',a)
probe=probe[:a]+'''        private static function pixelCheck():void {
            report.pixels=[];
            var savedX:Number=cam.X,savedY:Number=cam.Y;
            for each(var offset:Array in [[0,0],[120,0],[-160,0],[0,96],[0,-96]]) {
                cam.X=centerX+offset[0];cam.Y=centerY+offset[1];cam.calc(player);g.sceneTick();
                var a:BitmapData=captureWorld();fill.setEnabled(w,true);
                var b:BitmapData=captureWorld(),status:Object=fill.stats(),diff:Object=compareImages(a,b);
                report.pixels.push({offset:offset,difference:diff,stats:status});a.dispose();b.dispose();
                assertThat("group-pixels-exact-"+report.pixels.length,status.active && diff.changed==0,diff);
                a=captureWorld();fill.clear();b=captureWorld();diff=compareImages(a,b);a.dispose();b.dispose();
                assertThat("group-restores-exactly-"+report.pixels.length,diff.changed==0,diff);
            }
            assertThat("groups-balanced",fill.stats().moved==fill.stats().restored && fill.stats().errors==0,fill.stats());
            cam.X=savedX;cam.Y=savedY;cam.calc(player);g.sceneTick();
        }
'''+probe[b:]
(HERE/'ContinuousSceneMotionMod.as').write_text(probe,'utf-8')
shutil.copy2(OLD/'work.py',HERE/'work.py')
shutil.copy2(OLD/'CameraProbePlatform.as',HERE/'CameraProbePlatform.as')
print('Prepared identity-parent groups; isolated files only')
