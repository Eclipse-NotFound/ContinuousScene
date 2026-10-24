"""Reversible terrain-only visibility attribution over the measured 29AF SMG fixture."""
from pathlib import Path
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
VERSION = 'terrain-layer-native-1'
SOURCE_PROBE = '29AF34571E7181139C682AA32A160E2C217C1B02B295E6DCBD6931D8DB7F94E5'
MAIN_RAW_SHA = '5087CBB3D6FA9E1F92E1F24D5D386D7CA48F7D5974F56352AB8DEC25CE856333'
CHANGED = ['ContinuousSceneMotionProbe.as', 'SceneTerrainLayerTrial.as']
MODE = '(cfg.drawControl=="terrainback" || cfg.drawControl=="terrainfront")'

EDITS = (
    ('private static var rasterPresentation:SceneRasterPresentation=new SceneRasterPresentation();',
     'private static var rasterPresentation:SceneRasterPresentation=new SceneRasterPresentation();\n'
     '        private static var terrainLayer:SceneTerrainLayerTrial=new SceneTerrainLayerTrial();'),
    ('if(cfg.drawControl)cases=["draw-baseline-a","draw-control-b","draw-control-b-repeat","draw-baseline-a-repeat"];',
     'if(cfg.drawControl)cases=["draw-baseline-a","draw-control-b","draw-control-b-repeat","draw-baseline-a-repeat"];\n'
     '            if'+MODE+' {\n'
     '                if(cfg.benchmark!="scene" || !cfg.nativeInputMotion || !cfg.nativeSprint || !cfg.playerFire ||\n'
     '                    !cfg.fixedEnemies || !cfg.combatRoute || !cfg.stableMotion || cfg.presentationCheck || cfg.sleepingRootShort)\n'
     '                    throw new Error("Terrain attribution requires four-window native-input SMG combat");\n'
     '                report.terrainLayer={version:"terrain-layer-native-1",mode:cfg.drawControl,order:[false,true,true,false],\n'
     '                    diagnosticOnly:true,performanceEligible:false,visualAcceptance:false,\n'
     '                    control:"Only native terrain bitmaps [0] or [1,2] are hidden; parent/object/water/fog layers stay unchanged.",\n'
     '                    intervalMeaning:"All continuous intervals retain switches and scan costs; previousApplied describes the prior presentation.",\n'
     '                    limits:"Rendering attribution only: terrain is intentionally missing in B. AI, physics, input and fire remain native; no gameplay or visual acceptance."};\n'
     '            }'),
    ('absoluteStart=getTimer();rasterPresentation.beginFrame();',
     'absoluteStart=getTimer();if'+MODE+'terrainLayer.beginFrame();rasterPresentation.beginFrame();'),
    ('            closeProbeTiming(true);\n            if(cfg.drawControl=="atlas") {',
     '            closeProbeTiming(true);\n'
     '            if'+MODE+' {\n'
     '                try {report.terrainLayerCleanup=terrainLayer.clear();\n'
     '                    if(!report.terrainLayerCleanup.restored)error=(error?error+"\\n":"")+"Terrain visibility cleanup failed";\n'
     '                } catch(terrainCleanupError:*) {error=(error?error+"\\n":"")+String(terrainCleanupError);}\n'
     '            }\n            if(cfg.drawControl=="atlas") {'),
    ('            row.combatWindows=[];row.denseFrames=denseMetrics.bucket();',
     '            row.combatWindows=[];row.denseFrames=denseMetrics.bucket();\n'
     '            if'+MODE+'row.terrainLayer={version:"terrain-layer-native-1",mode:cfg.drawControl,\n'
     '                start:terrainLayer.snapshot(),frames:[]};'),
    ('                        if(cfg.drawControl=="tilecrop")tilePresentation.update(w,altered);',
     '                        if'+MODE+'row.terrainLayer.frames.push(terrainLayer.update(w,cfg.drawControl,altered));\n'
     '                        if(cfg.drawControl=="tilecrop")tilePresentation.update(w,altered);'),
    ('                    if(cfg.drawControl=="tilecrop")row.presentation={copies:tilePresentation.copies,allocated:tilePresentation.allocated};',
     '                    if'+MODE+'row.terrainLayer.end=terrainLayer.snapshot();\n'
     '                    if(cfg.drawControl=="tilecrop")row.presentation={copies:tilePresentation.copies,allocated:tilePresentation.allocated};'),
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def reverse(source):
    for before, after in reversed(EDITS):
        assert source.count(after) == 1, after
        source = source.replace(after, before, 1)
    return source


def transform(source):
    original = source
    for before, after in EDITS:
        assert source.count(before) == 1, before
        source = source.replace(before, after, 1)
    assert reverse(source) == original
    return source


def prepare(source, destination):
    assert not destination.exists()
    assert sha(source / 'ContinuousSceneMotionProbe.as') == MAIN_RAW_SHA
    assert len([p for p in source.rglob('*') if p.is_file()]) == 85
    shutil.copytree(source, destination)
    (destination / 'ContinuousSceneMotionProbe.as').write_text(transform(
        (source / 'ContinuousSceneMotionProbe.as').read_text('utf-8-sig')), 'utf-8')
    shutil.copy2(HERE / 'SceneTerrainLayerTrial.as', destination / 'SceneTerrainLayerTrial.as')
