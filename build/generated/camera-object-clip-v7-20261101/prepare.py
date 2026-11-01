"""Prepare a distinct, immutable diagnostic from the reviewed v5 fixture."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'camera-review-v5-20261101'
source=(OLD/'ContinuousSceneMotionMod.as').read_text('utf-8')
source=source.replace('version:"camera-review-5"','version:"camera-object-clip-7"')
source=source.replace('private static var lightVisible:Boolean;', 'private static var lightVisible:Boolean;\n        private static var viewport:ObjectViewportProbe;')
source=source.replace('layers=[g.visFront', 'assertThat("native-hidden-preserved",report.nativeHiddenActor.after===false);\n            viewport=new ObjectViewportProbe(g);\n            layers=[g.visFront')
a=source.index('            var order:Array=',source.index('private static function makeSchedule'))
b=source.index('            report.schedule=schedule',a)
source=source[:a]+'''            for each(var draw:String in ["objectClip","objectMask","objectMask","objectClip"])
                for each(var axis:String in ["x","y"]) {
                    schedule.push({fps:120,axis:axis,mode:"full",frames:180});
                    schedule.push({fps:120,axis:axis,mode:draw,frames:180});
                }
'''+source[b:]
a=source.index('            var value:Boolean=',source.index('private static function drawPolicy'))
b=source.index('        private static function after',a)
source=source[:a]+'''            viewport.apply(mode,cam);
        }
'''+source[b:]
source=source.replace('if(done)return;done=true;', 'if(done)return;done=true;\n            if(viewport)viewport.restore();')
(HERE/'ContinuousSceneMotionMod.as').write_text(source,'utf-8')
work=(OLD/'work.py').read_text('utf-8')
work=work.replace('camera review','object viewport optimization')
work=work.replace("if args.host=='a80':shutil.copy2(ROOT/'pfe_before_visualneutral_budget_20261031-121918.swf',runtime/'pfe.swf')", "candidate=ROOT/'pfe_before_unitvis_20261101-004531.swf'\n        assert sha(candidate)=='9D8662F6CF80E0AD20741EC2A4E7BEAD68446269EBB0ADB641C876DB68698B1D'\n        shutil.copy2(candidate,runtime/'pfe.swf')")
(HERE/'work.py').write_text(work,'utf-8')
print('Prepared object viewport candidate; production unchanged.')
