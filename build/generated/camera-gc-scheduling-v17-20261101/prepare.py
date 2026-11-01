from pathlib import Path
import shutil
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'camera-screen-cache-v13-20261101'
probe=(OLD/'ContinuousSceneMotionMod.as').read_text('utf-8-sig')
probe=probe.replace('private static var fill:ScreenTerrainCache=new ScreenTerrainCache(7);','private static var gcCalls:int=0,gcElapsed:int=0,gcMax:int=0;')
probe=probe.replace('camera-screen-cache-13','camera-gc-scheduling-17')
a=probe.index('        private static function makeSchedule()')
b=probe.index('        private static function enterBlock()',a)
probe=probe[:a]+'''        private static function makeSchedule():void {
            for each(var axis:String in ["x","y"])
                for each(var draw:String in ["full","gc95","full","gc75","gc75","full","gc95","full"])
                    schedule.push({fps:120,axis:axis,mode:draw,frames:240});
            report.schedule=schedule;index=0;enterBlock();
        }
'''+probe[b:]
probe=probe.replace('age=0;previousAt=0;rows=[];phase=20;', 'age=0;previousAt=0;rows=[];phase=20;gcCalls=gcElapsed=gcMax=0;')
a=probe.index('        private static function drawPolicy()')
b=probe.index('        private static function after(',a)
probe=probe[:a]+'''        private static function drawPolicy():void {
            if(mode=="full")return;
            var start:int=getTimer();
            System.pauseForGCIfCollectionImminent(mode=="gc95"?.95:.75);
            var delta:int=getTimer()-start;++gcCalls;gcElapsed+=delta;gcMax=Math.max(gcMax,delta);
        }
'''+probe[b:]
probe=probe.replace('mark.rows=rows;mark.fill=fill.stats();','mark.rows=rows;mark.gc={calls:gcCalls,ms:gcElapsed,max:gcMax};')
a=probe.index('                        if(mode=="fill")')
b=probe.index('                        mark.actualFrameRate',a)
probe=probe[:a]+probe[b:]
a=probe.index('        private static function captureWorld()')
b=probe.index('        private static function finish(',a)
probe=probe[:a]+probe[b:]
probe=probe.replace('            fill.clear();','')
(HERE/'ContinuousSceneMotionMod.as').write_text(probe,'utf-8')
shutil.copy2(OLD/'work.py',HERE/'work.py')
shutil.copy2(OLD/'CameraProbePlatform.as',HERE/'CameraProbePlatform.as')
print('Prepared bounded garbage-collection scheduling comparison')
