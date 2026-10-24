"""Reversible B7ED/39A probe-only broad FocusManager diagnostic, four by 300."""
from pathlib import Path
import shutil

VERSION = 'focus-control-3'
HELPER = Path(__file__).resolve().parent / 'tests/SceneFocusControl.as'
CHANGED = ['ContinuousSceneMotionProbe.as', 'tests/SceneFocusControl.as']
PATCHES = (
    ('    import tests.SceneDenseCombatMetrics;', '\n    import tests.SceneFocusControl;'),
    ('        private static var denseMetrics:SceneDenseCombatMetrics=new SceneDenseCombatMetrics();',
     '\n        private static var focusControl:SceneFocusControl=new SceneFocusControl();'),
    ('            if(cfg.drawControl=="objectgroups")cases=["all-object-layers-a","hide-box-layers","hide-unit-layer","all-object-layers-a-repeat"];',
     '\n            if(cases.length!=4 || cfg.drawControl!="rcnative" || !cfg.nativeInputMotion || !cfg.nativeSprint ||'
     '\n                !cfg.playerFire || !cfg.encounter || !cfg.fixedEnemies || cfg.sleepingRootShort || cfg.visual)'
     '\n                throw new Error("Focus control requires unchanged four by 300 real dense-sprint fixture");'),
    ('            var rcSwitch:Object=null;', '\n            var focusWindow:Object=focusControl.begin(w,index);'),
    ('            row.sampleAtMs=[];row.continuousFramesMs=[];row.caseBeginAtMs=caseBegin;',
     '\n            row.focusControl=focusWindow;'),
    ('                }else if(phase==4) {', '\n                    focusControl.sample(w,index,age);'),
    ('                    row.caseEndAtMs=getTimer();', '\n                    focusControl.end(w,index);'),
    ('        private static function finish(error:String=null):void {\n            if(done)return;done=true;',
     '\n            report.focusControl=focusControl.clear(w);'
     '\n            report.diagnosticOnly=true;report.performanceEligible=false;'),
)


def transform(source):
    assert 'focusControl' not in source and 'SceneFocusControl' not in source
    changed = source
    for anchor, insertion in PATCHES:
        assert changed.count(anchor) == 1, anchor
        changed = changed.replace(anchor, anchor + insertion)
    restored = changed
    for anchor, insertion in reversed(PATCHES):
        assert restored.count(anchor + insertion) == 1
        restored = restored.replace(anchor + insertion, anchor)
    assert restored == source, 'Focus diagnostic must reverse to exact original workload'
    return changed


def prepare(source: Path, destination: Path):
    assert not destination.exists()
    assert not (source / 'tests/SceneFocusControl.as').exists()
    shutil.copytree(source, destination)
    target = destination / 'ContinuousSceneMotionProbe.as'
    target.write_text(transform(target.read_text(encoding='utf-8-sig')), encoding='utf-8')
    shutil.copyfile(HELPER, destination / 'tests/SceneFocusControl.as')
