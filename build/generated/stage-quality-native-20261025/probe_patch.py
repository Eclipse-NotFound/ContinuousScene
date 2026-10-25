"""Exact 29AF fixture plus frozen clock anchors and HIGH/LOW/LOW/HIGH only."""
from pathlib import Path
import hashlib
import importlib.util
import shutil

HERE = Path(__file__).resolve().parent
VERSION = 'stage-quality-native-1'
SOURCE_PROBE = '29AF34571E7181139C682AA32A160E2C217C1B02B295E6DCBD6931D8DB7F94E5'
MAIN_RAW_SHA = '5087CBB3D6FA9E1F92E1F24D5D386D7CA48F7D5974F56352AB8DEC25CE856333'
CLOCK_PATCH = HERE.parent / 'thread-cpu-native-20261025/probe_patch.py'
CLOCK_PATCH_SHA = 'A4C1F93AFDFC5555872B8E6E501DB341E5E621B3E52497D88F7B3EB7E06C2AE2'
CHANGED = ['ContinuousSceneMotionProbe.as', 'SceneStageQualityTrial.as']
EDITS = (
    ('private static var rasterPresentation:SceneRasterPresentation=new SceneRasterPresentation();',
     'private static var rasterPresentation:SceneRasterPresentation=new SceneRasterPresentation();\n'
     '        private static var qualityTrial:SceneStageQualityTrial=new SceneStageQualityTrial();'),
    ('if(cfg.drawControl)cases=["draw-baseline-a","draw-control-b","draw-control-b-repeat","draw-baseline-a-repeat"];',
     'if(cfg.drawControl)cases=["draw-baseline-a","draw-control-b","draw-control-b-repeat","draw-baseline-a-repeat"];\n'
     '            if(cfg.drawControl!="rcnative" || cfg.benchmark!="scene" || !cfg.nativeInputMotion || !cfg.nativeSprint ||\n'
     '                !cfg.playerFire || !cfg.fixedEnemies || !cfg.combatRoute || !cfg.stableMotion || cfg.presentationCheck || cfg.sleepingRootShort)\n'
     '                throw new Error("Quality diagnostic requires unchanged native-input SMG scene combat");\n'
     '            report.stageQuality=qualityTrial.report;'),
    ('            closeProbeTiming(true);\n            if(cfg.drawControl=="atlas") {',
     '            closeProbeTiming(true);\n'
     '            if(cfg.drawControl=="rcnative") {\n'
     '                try {report.stageQuality=qualityTrial.finish(w,error==null && report.samples.length==4);\n'
     '                    if(!report.stageQuality.complete || report.stageQuality.errors.length>0 || !report.stageQuality.cleanup.restored ||\n'
     '                        report.stageQuality.cleanup.pendingRestore!=0 || report.stageQuality.cleanup.errors.length>0)\n'
     '                        error=(error?error+"\\n":"")+"Stage quality diagnostic incomplete";\n'
     '                } catch(qualityError:*) {error=(error?error+"\\n":"")+String(qualityError);}\n'
     '                finally {try {report.stageQualityCleanup=qualityTrial.clear();}\n'
     '                    catch(qualityCleanup:*) {error=(error?error+"\\n":"")+String(qualityCleanup);}}\n'
     '            }\n            if(cfg.drawControl=="atlas") {'),
    ('            var rcSwitch:Object=null;',
     '            var qualitySwitch:Object=qualityTrial.switchCase(w,index,caseBegin);\n'
     '            var rcSwitch:Object=null;'),
    ('            if(rcSwitch)row.rcOffline=rcSwitch;',
     '            if(rcSwitch)row.rcOffline=rcSwitch;\n'
     '            row.stageQuality=qualitySwitch;'),
    ('                    var now:int=getTimer();',
     '                    row.stageQuality.frames.push(qualityTrial.observe(w,index,age));\n'
     '                    var now:int=getTimer();'),
)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()

def clock_patch():
    assert sha(CLOCK_PATCH) == CLOCK_PATCH_SHA
    spec = importlib.util.spec_from_file_location('quality_frozen_clock_patch', CLOCK_PATCH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def reverse(source):
    for old, new in reversed(EDITS):
        assert source.count(new) == 1, new
        source = source.replace(new, old, 1)
    for anchor, insertion in reversed(clock_patch().EDITS):
        assert source.count(anchor + insertion) == 1
        source = source.replace(anchor + insertion, anchor, 1)
    return source

def transform(source):
    original = source
    source = clock_patch().transform(source)
    for old, new in EDITS:
        assert source.count(old) == 1, old
        source = source.replace(old, new, 1)
    assert reverse(source) == original
    return source

def prepare(source, destination):
    assert not destination.exists()
    assert sha(source / 'ContinuousSceneMotionProbe.as') == MAIN_RAW_SHA
    assert len([p for p in source.rglob('*') if p.is_file()]) == 85
    shutil.copytree(source, destination)
    (destination / 'ContinuousSceneMotionProbe.as').write_text(transform(
        (source / 'ContinuousSceneMotionProbe.as').read_text('utf-8-sig')), 'utf-8')
    shutil.copy2(HERE / 'SceneStageQualityTrial.as', destination / 'SceneStageQualityTrial.as')
