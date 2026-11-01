"""Freeze a new diagnostic from v24; never modify a completed experiment."""
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
source = BASE / 'camera-native-combat-v24-20261101'
target = BASE / 'combat-cost-v26-20261101'
target.mkdir()
for name in ['work.py', 'ScreenPresenter.as']:
    shutil.copy2(source / name, target / name)
shutil.copytree(source / 'tests', target / 'tests')
shutil.copy2(BASE / 'camera-review-v6-20261101/FrameCostProbe.as', target / 'FrameCostProbe.as')
code = (source / 'ContinuousSceneMotionMod.as').read_text('utf-8')
def replace(old, new):
    global code
    assert code.count(old) == 1, old
    code = code.replace(old, new)
replace('version:"camera-native-combat-24"', 'version:"combat-cost-26"')
replace('private static var encounter:SceneEncounter;', 'private static var encounter:SceneEncounter;\n        private static var sampleSequence:int=0;')
replace('main.stage.frameRate=120;phase=10;', 'FrameCostProbe.prepare();report.allocationDiagnostic=true;\n            main.stage.frameRate=120;phase=10;')
begin = code.index('        private static function makeSchedule():void {')
end = code.index('        private static function enterBlock():void {', begin)
code = code[:begin] + '''        private static function makeSchedule():void {
            main.stage.quality="high";
            for each(var axis:String in ["static","x","y","y","x","static"])
                schedule.push({fps:120,axis:axis,mode:"full",frames:90});
            report.schedule=schedule;index=0;enterBlock();
        }
''' + code[end:]
replace('previousAt=now;\n                    if(++age>=block.frames)', '''FrameCostProbe.observe({sequence:sampleSequence++,mode:route,condition:mode,layerCondition:"real-six-enemy-fire",stageBandMs:now-preAt});
                    previousAt=now;
                    if(++age>=block.frames)''')
replace('report.elapsedMs=getTimer()-started;', 'report.elapsedMs=getTimer()-started;report.frameCost=FrameCostProbe.finish();')
(target / 'ContinuousSceneMotionMod.as').write_text(code, 'utf-8')
print(target)
