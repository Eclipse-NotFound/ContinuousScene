"""Exact 29AF SMG fixture: read-only leaf stability, then terminal pixels."""
from pathlib import Path
import hashlib
import shutil

HERE = Path(__file__).resolve().parent
VERSION = 'player-leaf-cache-1'
SOURCE_PROBE = '29AF34571E7181139C682AA32A160E2C217C1B02B295E6DCBD6931D8DB7F94E5'
MAIN_RAW_SHA = '5087CBB3D6FA9E1F92E1F24D5D386D7CA48F7D5974F56352AB8DEC25CE856333'
CHANGED = ['ContinuousSceneMotionProbe.as', 'SceneLeafCacheTrial.as']
EDITS = (
    ('private static var rasterPresentation:SceneRasterPresentation=new SceneRasterPresentation();',
     'private static var rasterPresentation:SceneRasterPresentation=new SceneRasterPresentation();\n'
     '        private static var leafCache:SceneLeafCacheTrial=new SceneLeafCacheTrial();'),
    ('if(cfg.drawControl)cases=["draw-baseline-a","draw-control-b","draw-control-b-repeat","draw-baseline-a-repeat"];',
     'if(cfg.drawControl)cases=["draw-baseline-a","draw-control-b","draw-control-b-repeat","draw-baseline-a-repeat"];\n'
     '            if(cfg.drawControl=="playerleaf") {\n'
     '                if(cfg.benchmark!="scene" || !cfg.nativeInputMotion || !cfg.nativeSprint || !cfg.playerFire ||\n'
     '                    !cfg.fixedEnemies || !cfg.combatRoute || !cfg.stableMotion || cfg.presentationCheck || cfg.sleepingRootShort)\n'
     '                    throw new Error("Leaf diagnostic requires the unchanged four-window native-input SMG fixture");\n'
     '                cases=["leaf-observation-0","leaf-observation-1","leaf-observation-2","leaf-observation-3"];\n'
     '                report.leafCache=leafCache.report;\n'
     '            }'),
    ('            closeProbeTiming(true);\n            if(cfg.drawControl=="atlas") {',
     '            closeProbeTiming(true);\n'
     '            if(cfg.drawControl=="playerleaf") {\n'
     '                try {report.leafCache=leafCache.finish(w,error==null && report.samples.length==4);\n'
     '                    if(!report.leafCache.passed)error=(error?error+"\\n":"")+"Leaf diagnostic did not qualify";\n'
     '                } catch(leafError:*) {error=(error?error+"\\n":"")+String(leafError);}\n'
     '                finally {try {report.leafCacheCleanup=leafCache.clear();}\n'
     '                    catch(leafCleanup:*) {error=(error?error+"\\n":"")+String(leafCleanup);}}\n'
     '            }\n            if(cfg.drawControl=="atlas") {'),
    ('            row.combatWindows=[];row.denseFrames=denseMetrics.bucket();',
     '            row.combatWindows=[];row.denseFrames=denseMetrics.bucket();\n'
     '            if(cfg.drawControl=="playerleaf")row.leafCache={start:leafCache.snapshot(),frames:[]};'),
    ('                    report.lastWarm=w.grafon.sceneWarmCount;report.lastDraw=w.grafon.sceneDrawMs;startCase();\n                }else if(phase==96) {',
     '                    if(cfg.drawControl=="playerleaf") {\n'
     '                        var leafReady:Boolean=leafCache.begin(w);\n'
     '                        save("leaf-inventory.json",leafCache.report);\n'
     '                        if(!leafReady){finish("Exact leaf preflight inconclusive");return;}\n'
     '                    }\n'
     '                    report.lastWarm=w.grafon.sceneWarmCount;report.lastDraw=w.grafon.sceneDrawMs;startCase();\n                }else if(phase==96) {'),
    ('                        if(cfg.drawControl=="tilecrop")tilePresentation.update(w,altered);',
     '                        if(cfg.drawControl=="playerleaf")row.leafCache.frames.push(leafCache.observe(w,index,age));\n'
     '                        if(cfg.drawControl=="tilecrop")tilePresentation.update(w,altered);'),
    ('                    if(cfg.drawControl=="tilecrop")row.presentation={copies:tilePresentation.copies,allocated:tilePresentation.allocated};',
     '                    if(cfg.drawControl=="playerleaf")row.leafCache.end=leafCache.snapshot();\n'
     '                    if(cfg.drawControl=="tilecrop")row.presentation={copies:tilePresentation.copies,allocated:tilePresentation.allocated};'),
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
    shutil.copy2(HERE / 'SceneLeafCacheTrial.as', destination / 'SceneLeafCacheTrial.as')
