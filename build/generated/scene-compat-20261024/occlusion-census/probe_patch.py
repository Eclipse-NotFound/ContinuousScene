"""Read-only fog coverage at four starts and each 30-frame end; reversible B7ED patch."""
from pathlib import Path
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
HELPER = HERE / 'tests/SceneOcclusionCensus.as'
VERSION = 'occlusion-census-1'
CHANGED = ['ContinuousSceneMotionProbe.as', 'tests/SceneOcclusionCensus.as']
SEED_RECEIPT_SHA = 'B7ED1EAB8BEE0DC1024D6EF0A56A965F311B97E8CED9A9F32A2BCDE35B35FF13'
SEED_MAIN_SHA = 'F87A95E684A88D508679853C2EA2E1377EFC30236DD9BC7097885F4E5756FEE1'
PATCHES = (
    ('    import tests.SceneEncounter;', '\n    import tests.SceneOcclusionCensus;'),
    ('            row.sampleAtMs=[];row.continuousFramesMs=[];row.caseBeginAtMs=caseBegin;',
     '\n            row.occlusionCensus=[SceneOcclusionCensus.capture(w,index,-1)];'),
    ('                    if(age%30==0) {row.camera.push({x:w.cam.vx,y:w.cam.vy});row.activity.push(main.getChildByName("ContinuousSceneCarrier")["nativeAPI"].activityStats());}',
     '\n                    if(age%30==29)row.occlusionCensus.push(SceneOcclusionCensus.capture(w,index,age));'),
    ('                    check("actual-expected-native-map",cfg.benchmark=="normal"?(!w.grafon.sceneLarge && loc.spaceX==48):(w.grafon.sceneLarge && loc.spaceX>48));',
     '\n                    if(cfg.benchmark!="scene")throw new Error("Occlusion census requires scene mode");'
     '\n                    report.occlusionCensus={version:"occlusion-census-1",readOnly:true,diagnosticOnly:true,performanceEligible:false,measurementAffected:true};'),
)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def transform(source):
    assert 'SceneOcclusionCensus' not in source
    changed = source
    for anchor, insertion in PATCHES:
        assert changed.count(anchor) == 1, anchor
        changed = changed.replace(anchor, anchor + insertion, 1)
    restored = changed
    for anchor, insertion in reversed(PATCHES):
        restored = restored.replace(anchor + insertion, anchor, 1)
    assert restored == source
    return changed


def prepare(source, destination):
    source, destination = Path(source), Path(destination)
    assert not destination.exists()
    receipt = HERE.parents[3] / 'knowledge/experiments/evidence/vertical-camera-band-20261023-combat-candidate-r3/probe-build.json'
    assert digest(receipt) == SEED_RECEIPT_SHA
    doc = json.loads(receipt.read_text('utf-8-sig'))
    actual = {p.relative_to(source).as_posix(): digest(p) for p in source.rglob('*') if p.is_file()}
    assert len(actual) == 85 and actual == doc['frozenSourceSHA256']
    assert digest(source / 'ContinuousSceneMotionProbe.as') == SEED_MAIN_SHA
    shutil.copytree(source, destination)
    main = destination / 'ContinuousSceneMotionProbe.as'
    main.write_text(transform(main.read_text('utf-8-sig')), 'utf-8')
    shutil.copyfile(HELPER, destination / 'tests/SceneOcclusionCensus.as')
