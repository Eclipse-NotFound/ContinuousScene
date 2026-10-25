"""Reversible exact 29AF SMG fixture: native-invisible terrain detach ABBA."""
from pathlib import Path
import hashlib
import shutil

HERE = Path(__file__).resolve().parent
VERSION = 'native-terrain-detach-probe-1'
SOURCE_PROBE = '29AF34571E7181139C682AA32A160E2C217C1B02B295E6DCBD6931D8DB7F94E5'
MAIN_RAW_SHA = '5087CBB3D6FA9E1F92E1F24D5D386D7CA48F7D5974F56352AB8DEC25CE856333'
CHANGED = ['ContinuousSceneMotionProbe.as', 'tests/SceneNativeTerrainDetach.as']

GUARD = '''            if(cfg.drawControl!="rcnative" || cfg.benchmark!="scene" || !cfg.nativeInputMotion || !cfg.nativeSprint ||
                !cfg.playerFire || !cfg.fixedEnemies || !cfg.combatRoute || !cfg.stableMotion || cfg.presentationCheck ||
                cfg.sleepingRootShort || cfg.satsCheck || !cfg.noLighting || !cfg.noWall || cfg.vision)
                throw new Error("Terrain detach requires unchanged native SMG, idle SATS and three visual mods disabled");
            cases=["terrain-native-a","terrain-detach-b","terrain-detach-b-repeat","terrain-native-a-repeat"];
            report.nativeTerrainDetach={version:"native-terrain-detach-probe-1",order:[false,true,true,false],
                diagnosticOnly:true,performanceEligible:false,visualAcceptance:false,
                intervalMeaning:"All 1200 continuous intervals retain initialization, previous presentation, native updates, guards, detach/restore, observation and switching costs; no subtraction or trimming",
                hookOrder:{dispatcher:"main.stage",beforeNativePriority:2147483647,nativePriority:0,continuousScenePriority:-200,updatePriority:-1000},
                satsPolicy:"No SATS input; helper rejects keySats/active/visible overlay before and after native update"};
'''

HEAD = '''        private static function terrainBeforeNative():void {
            terrainHeadMs=0;
            if(done || !terrainReady || phase!=4)return;
            var began:int=getTimer();
            try {
                terrainDetach.beginFrame(w);
                if(!terrainDetach.snapshot().valid)throw new Error("Terrain head guard failed");
            } catch(terrainHeadError:*) {finish("Terrain head: "+String(terrainHeadError));}
            finally {terrainHeadMs=getTimer()-began;}
        }
'''

BEGIN = '''            if(!terrainStarted) {
                terrainStarted=true;
                report.nativeTerrainDetach.begin={startedAtMs:getTimer()};
                terrainReady=terrainDetach.begin(w);
                report.nativeTerrainDetach.begin.endedAtMs=getTimer();
                report.nativeTerrainDetach.begin.state=terrainDetach.snapshot();
                if(!terrainReady)throw new Error("Terrain detach initialization rejected");
            }
'''

UPDATE = '''                    if(!terrainReady)throw new Error("Terrain detach not initialized");
                    var terrainUpdateAt:int=getTimer();
                    var terrainFrame:Object=terrainDetach.update(w,index==1 || index==2);
                    row.nativeTerrainDetach.frames.push({index:index,frame:age,headMs:terrainHeadMs,
                        updateStartedAtMs:terrainUpdateAt,updateEndedAtMs:getTimer(),data:terrainFrame});
                    if(!terrainFrame.valid)throw new Error("Terrain detach update rejected");
'''

CLEANUP = '''            if(terrainStarted) {
                report.nativeTerrainDetachCleanup={before:null,result:null,after:null,errors:[],restored:false};
                try {
                    report.nativeTerrainDetachCleanup.before=terrainDetach.snapshot();
                    if(error==null && report.samples.length==4) {
                        report.nativeTerrainDetachPixels={startedAtMs:getTimer(),afterFinalSample:true,diagnosticOnly:true,performanceEligible:false};
                        report.nativeTerrainDetachPixels.data=terrainDetach.checkPixels(w);
                        report.nativeTerrainDetachPixels.endedAtMs=getTimer();
                        var terrainPixels:Object=report.nativeTerrainDetachPixels.data;
                        if(!terrainPixels.valid || !terrainPixels.equal || !terrainPixels.restored || !terrainPixels.heldPositive ||
                            terrainPixels.errors.length>0 || terrainPixels.bitmapsCreated!=terrainPixels.bitmapsDisposed)
                            throw new Error("Terrain terminal pixel check failed");
                    }
                }
                catch(terrainBeforeError:*) {report.nativeTerrainDetachCleanup.errors.push(String(terrainBeforeError));}
                finally {
                    try {report.nativeTerrainDetachCleanup.result=terrainDetach.clear();}
                    catch(terrainClearError:*) {report.nativeTerrainDetachCleanup.errors.push(String(terrainClearError));}
                    terrainReady=false;
                }
                try {report.nativeTerrainDetachCleanup.after=terrainDetach.snapshot();}
                catch(terrainAfterError:*) {report.nativeTerrainDetachCleanup.errors.push(String(terrainAfterError));}
                var terrainClean:Object=report.nativeTerrainDetachCleanup;
                terrainClean.restored=terrainClean.errors.length==0 && terrainClean.result && terrainClean.result.restored &&
                    terrainClean.after && terrainClean.after.valid && terrainClean.after.cleared &&
                    terrainClean.after.held==0 && terrainClean.after.pendingRestore==0 && terrainClean.after.droppedSkipped==0 &&
                    terrainClean.after.errors.length==0;
                if(!terrainClean.restored)error=(error?error+"\\n":"")+"Terrain detach cleanup failed";
            }
'''

EDITS = (
    ('    import tests.SceneActivityCensus;', '    import tests.SceneActivityCensus;\n    import tests.SceneNativeTerrainDetach;'),
    ('        private static var continuousPreviousSampleAt:int=-1;',
     '        private static var continuousPreviousSampleAt:int=-1;\n'
     '        private static var terrainDetach:SceneNativeTerrainDetach=new SceneNativeTerrainDetach();\n'
     '        private static var terrainStarted:Boolean=false,terrainReady:Boolean=false;\n'
     '        private static var terrainHeadMs:int=0;'),
    ('            main.stage.addEventListener(Event.ENTER_FRAME,function(e:Event):void {absoluteStart=getTimer();',
     GUARD + '            main.stage.addEventListener(Event.ENTER_FRAME,function(e:Event):void {absoluteStart=getTimer();terrainBeforeNative();'),
    ('        private static function finish(error:String=null):void {', HEAD + '        private static function finish(error:String=null):void {'),
    ('            closeProbeTiming(true);\n            if(cfg.drawControl=="atlas") {',
     '            closeProbeTiming(true);\n' + CLEANUP + '            if(cfg.drawControl=="atlas") {'),
    ('            var rcSwitch:Object=null;', BEGIN + '            var rcSwitch:Object=null;'),
    ('            row.sampleAtMs=[];row.continuousFramesMs=[];row.caseBeginAtMs=caseBegin;',
     '            row.sampleAtMs=[];row.continuousFramesMs=[];row.caseBeginAtMs=caseBegin;\n'
     '            row.nativeTerrainDetach={enabled:index==1 || index==2,frames:[],start:terrainDetach.snapshot()};'),
    ('                    if(cfg.culling)objectCulling.update(w,index%2==1);',
     UPDATE + '                    if(cfg.culling)objectCulling.update(w,index%2==1);'),
    ('                    row.caseEndAtMs=getTimer();',
     '                    row.nativeTerrainDetach.end=terrainDetach.snapshot();\n                    row.caseEndAtMs=getTimer();'),
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
    shutil.copy2(HERE / 'SceneNativeTerrainDetach.as', destination / 'tests/SceneNativeTerrainDetach.as')
