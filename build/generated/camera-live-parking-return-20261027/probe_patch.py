"""One frozen live-world fixture, chain-owned Box/Bonus parking ABBA."""
from pathlib import Path
import hashlib, shutil
HERE=Path(__file__).resolve().parent
VERSION='camera-live-parking-return-1'
HELPER=HERE/'tests/SceneFarParkingTrial.as'
ORIGINAL=HERE.parent/'camera-far-live-detach-20261027/run.py'
PATCH_SOURCE=HERE/'probe_patch.py'
EXTRA_INPUTS=(HERE/'prepare.py',HERE/'summary.py',HERE.parent/'camera-live-parking-20261027/tests/SceneFarParkingTrial.as',HERE.parent/'camera-live-parking-20261027/probe_patch.py',HERE.parent/'camera-live-parking-20261027/summary.py',HERE.parent/'camera-live-parking-20261027/README.md',HERE.parent/'camera-live-parking-20261027/run.py')
CHANGED=['ContinuousSceneMotionProbe.as','tests/SceneFarParkingTrial.as']

def helper_source():return HELPER.read_text('utf-8-sig')
def one(s,a,b):
    assert s.count(a)==1,(a,s.count(a))
    return s.replace(a,b,1)

EDITS=(
('    import tests.SceneFogChecks;', '    import tests.SceneFarParkingTrial;\n    import tests.SceneFogChecks;'),
('private static var rasterPresentation:SceneRasterPresentation=new SceneRasterPresentation();',
 'private static var rasterPresentation:SceneRasterPresentation=new SceneRasterPresentation();\n        private static var farParking:SceneFarParkingTrial=new SceneFarParkingTrial();'),
('for(var rcCase:int=0;rcCase<4;++rcCase)', 'for(var rcCase:int=0;rcCase<20;++rcCase)'),
('w.mm.active=false;w.newGame(-1,"Scene Motion",{propusk:true});phase=1;',
 'w.mm.mainMenuOff();if(w.mm.active)throw new Error("Native menu shutdown failed");w.newGame(-1,"Scene Motion",{propusk:true});phase=1;'),
('            var caseTimed:Boolean=probeTimingRow!=null,caseBegin:int=getTimer();',
 '            farParking.prepare(w);report.farParking=farParking.report;\n            var caseTimed:Boolean=probeTimingRow!=null,caseBegin:int=getTimer();'),
('            row.sampleAtMs=[];row.continuousFramesMs=[];row.caseBeginAtMs=caseBegin;',
 '            row.sampleAtMs=[];row.continuousFramesMs=[];row.caseBeginAtMs=caseBegin;\n            row.farParking=[];'),
('                    var now:int=getTimer();',
 '                    row.farParking.push(farParking.update(w,index%4==1 || index%4==2));\n                    var now:int=getTimer();'),
('if(age<(cfg.sleepingRootShort || cfg.drawControl=="rcoffline"?60:300))return;',
 'if(age<(cfg.sleepingRootShort || cfg.drawControl=="rcoffline" || cfg.drawControl=="rcnative"?60:300))return;'),
('            closeProbeTiming(true);\n            if(cfg.drawControl=="atlas") {',
 '''            closeProbeTiming(true);
            try {
                if(error==null && report.samples.length==20) {
                    report.farParkingVerification=farParking.verify(w);
                    check("parking-pixels",report.farParkingVerification.pixels.changed.passed && report.farParkingVerification.pixels.restored.passed,report.farParkingVerification);
                    check("parking-native-removal",report.farParkingVerification.nativeRemoval.notResurrected,report.farParkingVerification);
                }
            } catch(parkingError:*) {error=(error?error+"\\n":"")+"Parking verification: "+String(parkingError);}
            finally {report.farParkingCleanup=farParking.clear();if(!report.farParkingCleanup.restored)error=(error?error+"\\n":"")+"Parking cleanup failed";}
            if(cfg.drawControl=="atlas") {'''),
('if(error==null && report.samples.length==4 && w && w.grafon.sceneLarge)',
 'if(error==null && report.samples.length==20 && w && w.grafon.sceneLarge)'),
)
def transform(s):
    original=s
    for a,b in EDITS:s=one(s,a,b)
    check=s
    for a,b in reversed(EDITS):check=one(check,b,a)
    assert check==original
    return s

def prepare(source,destination):
    assert not destination.exists()
    assert hashlib.sha256((source/'ContinuousSceneMotionProbe.as').read_bytes()).hexdigest().upper()=='5087CBB3D6FA9E1F92E1F24D5D386D7CA48F7D5974F56352AB8DEC25CE856333'
    assert len([p for p in source.rglob('*') if p.is_file()])==85
    shutil.copytree(source,destination)
    main=destination/'ContinuousSceneMotionProbe.as';main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/'tests/SceneFarParkingTrial.as')
