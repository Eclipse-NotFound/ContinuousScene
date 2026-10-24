"""Add camera-only control to an already-frozen dense-sprint-2 source tree."""
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
HELPER = 'tests/SceneCombatCameraHoldProbe.as'


def transform(text):
    edits = [
        ('    import tests.SceneDenseCombatMetrics;', '    import tests.SceneDenseCombatMetrics;\n    import tests.SceneCombatCameraHoldProbe;'),
        ('        private static var denseMetrics:SceneDenseCombatMetrics=new SceneDenseCombatMetrics();',
         '        private static var denseMetrics:SceneDenseCombatMetrics=new SceneDenseCombatMetrics();\n        private static var combatCamera:SceneCombatCameraHoldProbe=new SceneCombatCameraHoldProbe();'),
        ('                    if(cfg.encounter){encounter=new SceneEncounter(w);',
         '                    if(encounter)throw new Error("Camera preparation must precede fixture creation");\n                    report.cameraPrewarm={};SceneCombatCameraHoldProbe.prepareCache(w,nativeInputRoute,report.cameraPrewarm);\n                    if(cfg.encounter){encounter=new SceneEncounter(w);'),
        ('            row.combatWindows=[];row.denseFrames=denseMetrics.bucket();',
         '            row.combatWindows=[];row.denseFrames=denseMetrics.bucket();\n            if(index==0)combatCamera.start(w,encounter.actorUnits(),nativeInputRoute);\n            combatCamera.beginWindow(index);report.cameraHold=combatCamera.snapshot();'),
        ('                    row.frames.push(now-last);last=now;',
         '                    row.frames.push(now-last);last=now;\n                    combatCamera.sample(index,age,now,row.continuousFramesMs[row.continuousFramesMs.length-1]);'),
        ('            closeProbeTiming(true);',
         '''            closeProbeTiming(true);
            try {combatCamera.clear(error==null&&report.samples.length==4);}
            catch(cameraCleanup:*) {error=(error?error+"\\n":"")+"Camera cleanup: "+String(cameraCleanup);}
            finally {report.cameraHold=combatCamera.snapshot();}''')]
    for old, new in edits:
        assert text.count(old) == 1, ('Non-unique frozen dense anchor', old, text.count(old))
        text = text.replace(old, new, 1)
    return text


def prepare(source, target):
    assert not target.exists(), 'Preserve frozen source'
    shutil.copytree(source, target)
    main = target / 'ContinuousSceneMotionProbe.as'
    main.write_text(transform(main.read_text('utf-8-sig')), 'utf-8')
    shutil.copy2(HERE / HELPER, target / HELPER)
