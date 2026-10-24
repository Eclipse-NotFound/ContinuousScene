"""Exact 29AF fixture; change only owned NativeWindow visibility in ABBA."""
from pathlib import Path
import hashlib
import shutil

HERE = Path(__file__).resolve().parent
VERSION = 'window-visibility-native-1'
SOURCE_PROBE = '29AF34571E7181139C682AA32A160E2C217C1B02B295E6DCBD6931D8DB7F94E5'
MAIN_RAW_SHA = '5087CBB3D6FA9E1F92E1F24D5D386D7CA48F7D5974F56352AB8DEC25CE856333'
CHANGED = ['ContinuousSceneMotionProbe.as', 'SceneWindowVisibilityTrial.as']
EDITS = (
    ('private static var rasterPresentation:SceneRasterPresentation=new SceneRasterPresentation();',
     'private static var rasterPresentation:SceneRasterPresentation=new SceneRasterPresentation();\n'
     '        private static var windowTrial:SceneWindowVisibilityTrial=new SceneWindowVisibilityTrial();'),
    ('if(cfg.drawControl)cases=["draw-baseline-a","draw-control-b","draw-control-b-repeat","draw-baseline-a-repeat"];',
     'if(cfg.drawControl)cases=["draw-baseline-a","draw-control-b","draw-control-b-repeat","draw-baseline-a-repeat"];\n'
     '            if(cfg.drawControl=="windowvisibility") {\n'
     '                if(cfg.benchmark!="scene" || !cfg.nativeInputMotion || !cfg.nativeSprint || !cfg.playerFire ||\n'
     '                    !cfg.fixedEnemies || !cfg.combatRoute || !cfg.stableMotion || cfg.presentationCheck || cfg.sleepingRootShort)\n'
     '                    throw new Error("Visibility trial requires unchanged native-input SMG combat fixture");\n'
     '                cases=["window-hidden-0","window-visible-1","window-visible-2","window-hidden-3"];\n'
     '                report.windowVisibility=windowTrial.report;\n'
     '            }'),
    ('            closeProbeTiming(true);\n            if(cfg.drawControl=="atlas") {',
     '            closeProbeTiming(true);\n'
     '            if(cfg.drawControl=="windowvisibility") {\n'
     '                try {report.windowVisibility=windowTrial.finish(w,error==null && report.samples.length==4);\n'
     '                    if(!report.windowVisibility.complete || report.windowVisibility.errors.length>0 || !report.windowVisibility.cleanup.restored)\n'
     '                        error=(error?error+"\\n":"")+"Window visibility diagnostic incomplete";\n'
     '                } catch(windowError:*) {error=(error?error+"\\n":"")+String(windowError);}\n'
     '                finally {try {report.windowVisibilityCleanup=windowTrial.clear();}\n'
     '                    catch(windowCleanup:*) {error=(error?error+"\\n":"")+String(windowCleanup);}}\n'
     '            }\n            if(cfg.drawControl=="atlas") {'),
    ('            var rcSwitch:Object=null;',
     '            var windowSwitch:Object=null;\n'
     '            if(cfg.drawControl=="windowvisibility")windowSwitch=windowTrial.switchCase(w,index,caseBegin);\n'
     '            var rcSwitch:Object=null;'),
    ('            if(rcSwitch)row.rcOffline=rcSwitch;',
     '            if(rcSwitch)row.rcOffline=rcSwitch;\n'
     '            if(windowSwitch)row.windowVisibility=windowSwitch;'),
    ('            if(cfg.drawControl=="rcnative")last=caseBegin;',
     '            if(cfg.drawControl=="rcnative" || cfg.drawControl=="windowvisibility")last=caseBegin;'),
    ('                        if(cfg.drawControl=="tilecrop")tilePresentation.update(w,altered);',
     '                        if(cfg.drawControl=="windowvisibility")row.windowVisibility.frames.push(windowTrial.observe(w,index,age));\n'
     '                        if(cfg.drawControl=="tilecrop")tilePresentation.update(w,altered);'),
)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()

def reverse(source):
    for old, new in reversed(EDITS):
        assert source.count(new) == 1, new
        source = source.replace(new, old, 1)
    return source

def transform(source):
    original = source
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
    shutil.copy2(HERE / 'SceneWindowVisibilityTrial.as', destination / 'SceneWindowVisibilityTrial.as')
