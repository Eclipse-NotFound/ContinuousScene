from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'camera-static-groups-v15-20261101'
group=(OLD/'StaticObjectGroups.as').read_text('utf-8-sig')
group=group.replace('private var active:Boolean=false;', 'private var active:Boolean=false;\n        public var cellWidth:int=960,cellHeight:int=500;')
group=group.replace('owner.X/960','owner.X/cellWidth').replace('owner.Y/500','owner.Y/cellHeight')
group=group.replace('return {active:active,groups:', 'return {cellWidth:cellWidth,cellHeight:cellHeight,active:active,groups:')
(HERE/'StaticObjectGroups.as').write_text(group,'utf-8')
probe=(OLD/'ContinuousSceneMotionMod.as').read_text('utf-8-sig')
probe=probe.replace('camera-static-groups-15','camera-group-scale-18')
probe=probe.replace('["static","x","y"]','["x","y"]')
probe=probe.replace('["full","fill","fill","full"]','["full","fine","coarse","coarse","fine","full"]')
probe=probe.replace('frames:300','frames:240')
probe=probe.replace('fill.setEnabled(w,mode=="fill");drawing=mode;', '''if(drawing!=mode) {
                fill.clear();
                fill.cellWidth=mode=="fine"?480:3840;fill.cellHeight=mode=="fine"?250:2000;
                fill.setEnabled(w,mode!="full");drawing=mode;
            }''')
probe=probe.replace('if(mode=="fill")assertThat','if(mode!="full")assertThat')
a=probe.index('            for each(var offset:Array',probe.index('private static function pixelCheck()'))
b=probe.index('            assertThat("groups-balanced"',a)
probe=probe[:a]+'''            for each(var size:Array in [[480,250],[3840,2000]]) {
                fill.cellWidth=size[0];fill.cellHeight=size[1];
                for each(var offset:Array in [[0,0],[120,0],[-160,0],[0,96],[0,-96]]) {
                    cam.X=centerX+offset[0];cam.Y=centerY+offset[1];cam.calc(player);g.sceneTick();
                    var a:BitmapData=captureWorld();fill.setEnabled(w,true);
                    var b:BitmapData=captureWorld(),status:Object=fill.stats(),diff:Object=compareImages(a,b);
                    report.pixels.push({size:size,offset:offset,difference:diff,stats:status});a.dispose();b.dispose();
                    assertThat("group-pixels-exact-"+report.pixels.length,status.active && diff.changed==0,diff);
                    a=captureWorld();fill.clear();b=captureWorld();diff=compareImages(a,b);a.dispose();b.dispose();
                    assertThat("group-restores-exactly-"+report.pixels.length,diff.changed==0,diff);
                }
            }
'''+probe[b:]
(HERE/'ContinuousSceneMotionMod.as').write_text(probe,'utf-8')
for name in ('work.py','CameraProbePlatform.as'):shutil.copy2(OLD/name,HERE/name)
print('Prepared two neutral grouping scales; same native object order and effects')
