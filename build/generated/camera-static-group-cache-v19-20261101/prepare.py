from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'camera-static-groups-v15-20261101'
group=(OLD/'StaticObjectGroups.as').read_text('utf-8-sig')
group=group.replace('import flash.utils.Dictionary;', 'import flash.utils.Dictionary;\n    import flash.geom.Rectangle;')
group=group.replace('private var active:Boolean=false;', 'private var active:Boolean=false;\n        private var cachedGroups:int=0,estimatedPixels:Number=0;')
group=group.replace('active=true;', 'active=true;cachedGroups=0;estimatedPixels=0;')
group=group.replace('for each(var child:DisplayObject in children){group.addChild(child);++moved;}', '''for each(var child:DisplayObject in children){group.addChild(child);++moved;}
            // Bounded native cache. Native child mutations still invalidate it.
            // Bounds are only a conservative allocation estimate, not measured memory.
            var bounds:Rectangle=group.getBounds(group);
            var width:int=Math.ceil(bounds.width)+256,height:int=Math.ceil(bounds.height)+256;
            var area:Number=Number(width)*height;
            if(width<=2048 && height<=2048 && estimatedPixels+area<=16777216) {
                group.cacheAsBitmap=true;estimatedPixels+=area;++cachedGroups;
            }''')
group=group.replace('return {active:active,groups:', 'return {cachedGroups:cachedGroups,estimatedPixels:estimatedPixels,active:active,groups:')
(HERE/'StaticObjectGroups.as').write_text(group,'utf-8')
probe=(OLD/'ContinuousSceneMotionMod.as').read_text('utf-8-sig')
probe=probe.replace('camera-static-groups-15','camera-static-group-cache-19')
probe=probe.replace('["static","x","y"]','["x","y"]')
probe=probe.replace('mark.fill.groups>0','mark.fill.groups>0 && mark.fill.cachedGroups>0')
probe=probe.replace('report.pixels=[];', '''report.pixels=[];
            // BitmapData.draw equivalence is necessary, but does not prove a native
            // cached Stage has identical pixels. No deployment on these checks alone.
            report.nativeCacheStagePixelsVerified=false;''')
(HERE/'ContinuousSceneMotionMod.as').write_text(probe,'utf-8')
for name in ('work.py','CameraProbePlatform.as'):shutil.copy2(OLD/name,HERE/name)
print('Prepared bounded native group cache; stage visual gate explicitly pending')
