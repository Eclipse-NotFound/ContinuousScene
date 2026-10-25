"""Exact 29AF native SMG: one genuine mouse handshake and existing mousetree ABBA."""
from pathlib import Path
import hashlib
import shutil

HERE=Path(__file__).resolve().parent
SOURCE_PROBE='29AF34571E7181139C682AA32A160E2C217C1B02B295E6DCBD6931D8DB7F94E5'
MAIN_RAW_SHA='5087CBB3D6FA9E1F92E1F24D5D386D7CA48F7D5974F56352AB8DEC25CE856333'
CHANGED=['ContinuousSceneMotionProbe.as','tests/SceneWorldMouseProbe.as']

EDITS=(
    ('    import tests.SceneActivityCensus;','    import tests.SceneActivityCensus;\n    import tests.SceneWorldMouseProbe;'),
    ('        private static var continuousPreviousSampleAt:int=-1;',
     '        private static var continuousPreviousSampleAt:int=-1;\n        private static var worldMouse:SceneWorldMouseProbe=new SceneWorldMouseProbe();'),
    ('            if(cfg.sleepingRootShort) {',
     '            if(cfg.drawControl!="mousetree" || cfg.benchmark!="scene" || !cfg.nativeInputMotion || !cfg.nativeSprint ||\n'
     '                !cfg.playerFire || !cfg.fixedEnemies || !cfg.combatRoute || !cfg.stableMotion || cfg.presentationCheck ||\n'
     '                cfg.sleepingRootShort || cfg.satsCheck || !cfg.noLighting || !cfg.noWall || cfg.vision)\n'
     '                throw new Error("Real mouse trial requires unchanged native SMG and three visual mods off");\n'
     '            report.worldMouse={version:"mouse-world-native-2",diagnosticOnly:true,performanceEligible:false,order:[false,true,true,false]};\n'
     '            if(cfg.sleepingRootShort) {'),
    ('                }else if(phase==3) {\n                    if(cfg.nativeInputMotion) {',
     '                }else if(phase==3) {\n                    if(!worldMouse.gate(w))return;\n                    worldMouse.warm(w);\n                    if(cfg.nativeInputMotion) {'),
    ('            row.sampleAtMs=[];row.continuousFramesMs=[];row.caseBeginAtMs=caseBegin;',
     '            row.sampleAtMs=[];row.continuousFramesMs=[];row.caseBeginAtMs=caseBegin;\n            row.worldMouse=[];'),
    ('                    var now:int=getTimer();\n                    if(continuousPreviousSampleAt<0)',
     '                    row.worldMouse.push(worldMouse.sample(w));\n                    var now:int=getTimer();\n                    if(continuousPreviousSampleAt<0)'),
    ('            if(cfg.drawControl=="rcnative")last=caseBegin;',
     '            if(cfg.drawControl=="rcnative" || cfg.drawControl=="mousetree")last=caseBegin;'),
    ('            try {implicitFreeze.clear();}',
     '            try {\n                report.worldMouseCleanup=worldMouse.clear();\n'
     '                report.worldMouseTreeRestored=mouseTreeOriginal && w && w.visual===mouseTreeOriginal.root &&\n'
     '                    w.visual.mouseChildren===mouseTreeOriginal.children && w.visual.mouseEnabled===mouseTreeOriginal.enabled;\n'
     '                if(!report.worldMouseCleanup.cleared || !report.worldMouseCleanup.titleRestored || !report.worldMouseCleanup.visibilityRestored ||\n'
     '                    report.worldMouseCleanup.errors.length>0 || !report.worldMouseTreeRestored)\n'
     '                    error=(error?error+"\\n":"")+"World mouse cleanup failed";\n'
     '            } catch(mouseCleanup:*) {error=(error?error+"\\n":"")+String(mouseCleanup);}\n'
     '            try {implicitFreeze.clear();}'),
)

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest().upper()

def reverse(source):
    for old,new in reversed(EDITS):
        assert source.count(new)==1,new
        source=source.replace(new,old,1)
    return source

def transform(source):
    original=source
    for old,new in EDITS:
        assert source.count(old)==1,old
        source=source.replace(old,new,1)
    assert reverse(source)==original
    return source

def prepare(source,destination):
    assert not destination.exists()
    assert sha(source/'ContinuousSceneMotionProbe.as')==MAIN_RAW_SHA
    assert len([p for p in source.rglob('*') if p.is_file()])==85
    shutil.copytree(source,destination)
    (destination/'ContinuousSceneMotionProbe.as').write_text(transform((source/'ContinuousSceneMotionProbe.as').read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HERE/'SceneWorldMouseProbe.as',destination/'tests/SceneWorldMouseProbe.as')
