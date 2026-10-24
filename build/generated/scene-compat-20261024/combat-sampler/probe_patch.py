"""Add bounded sampler windows to the exact B7ED/39A frozen dense probe.

No workload/actor/camera/host edits. Sampler windows exclude the final frame's
probe tick and later listeners. Every full-run frame is diagnostic, not FPS proof.
"""
from pathlib import Path
import shutil

VERSION = 'combat-sampler-1'
HELPER = Path(__file__).resolve().parent / 'tests/SceneCombatSampler.as'
CHANGED = ['ContinuousSceneMotionProbe.as', 'tests/SceneCombatSampler.as']
PATCHES = (
    ('    import tests.SceneDenseCombatMetrics;',
     '\n    import tests.SceneCombatSampler;'),
    ('        private static var denseMetrics:SceneDenseCombatMetrics=new SceneDenseCombatMetrics();',
     '\n        private static var combatSampler:SceneCombatSampler=new SceneCombatSampler();'),
    ('            if(cfg.drawControl=="objectgroups")cases=["all-object-layers-a","hide-box-layers","hide-unit-layer","all-object-layers-a-repeat"];',
     '\n            if(cases.length!=4 || cfg.drawControl!="rcnative" || !cfg.nativeInputMotion || !cfg.nativeSprint ||'
     '\n                !cfg.playerFire || !cfg.encounter || !cfg.fixedEnemies || cfg.sleepingRootShort || cfg.visual)'
     '\n                throw new Error("Combat sampler requires the unchanged four by 300 real dense-sprint fixture");'),
    ('function(e:Event):void {absoluteStart=getTimer();',
     'if(!done && phase==4)combatSampler.head(index,age,String(cases[index]));'),
    ('        private static function tick(e:Event):void {\n            if(done)return;',
     '\n            if(phase==4)combatSampler.beforeTick(index,age);'),
    ('                    row.caseEndAtMs=getTimer();',
     '\n                    row.combatSampler=combatSampler.complete(index);'),
    ('        private static function finish(error:String=null):void {\n            if(done)return;done=true;',
     '\n            report.combatSampler=combatSampler.finish();'
     '\n            report.diagnosticOnly=true;report.performanceEligible=false;'),
)
HEARTBEAT_OLD = 'if(getTimer()-lastProgress>5000) {lastProgress=getTimer();save("heartbeat.json",'
HEARTBEAT_NEW = 'if(!combatSampler.sampling && getTimer()-lastProgress>5000) {lastProgress=getTimer();save("heartbeat.json",'


def transform(source):
    assert 'combatSampler' not in source and 'SceneCombatSampler' not in source
    changed = source
    for anchor, insertion in PATCHES:
        assert changed.count(anchor) == 1, anchor
        changed = changed.replace(anchor, anchor + insertion)
    assert changed.count(HEARTBEAT_OLD) == 1
    changed = changed.replace(HEARTBEAT_OLD, HEARTBEAT_NEW)
    restored = changed.replace(HEARTBEAT_NEW, HEARTBEAT_OLD)
    for anchor, insertion in reversed(PATCHES):
        assert restored.count(anchor + insertion) == 1
        restored = restored.replace(anchor + insertion, anchor)
    assert restored == source, 'Sampler patch must reverse to the exact frozen workload'
    return changed


def prepare(source: Path, destination: Path):
    assert not destination.exists()
    assert not (source / 'tests/SceneCombatSampler.as').exists()
    shutil.copytree(source, destination)
    target = destination / 'ContinuousSceneMotionProbe.as'
    target.write_text(transform(target.read_text(encoding='utf-8-sig')), encoding='utf-8')
    shutil.copyfile(HELPER, destination / 'tests/SceneCombatSampler.as')
