"""Prepare the exact 29AF native combat probe; never compile or launch AIR."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import uuid

HERE = Path(__file__).resolve().parent
MOD = HERE.parents[2]
SEED = MOD / 'knowledge/experiments/evidence/camera-atlas-paged-combat-20261025-r1/probe-build.json'
SEED_SHA = '983727AEB832BC586AF3767613B7C9D61564D92DC9D8E2435F972EEBF1D1D5EE'
SOURCE_PROBE = '29AF34571E7181139C682AA32A160E2C217C1B02B295E6DCBD6931D8DB7F94E5'
MAIN_RAW_SHA = '5087CBB3D6FA9E1F92E1F24D5D386D7CA48F7D5974F56352AB8DEC25CE856333'
CHANGED = ['ContinuousSceneMotionProbe.as', 'tests/SceneActivityRangeProbe.as']

EDITS = (
    ('    import tests.SceneActivityCensus;',
     '    import tests.SceneActivityCensus;\n    import tests.SceneActivityRangeProbe;'),
    ('        private static var continuousPreviousSampleAt:int=-1;',
     '        private static var continuousPreviousSampleAt:int=-1;\n'
     '        private static var activityRangeProbe:SceneActivityRangeProbe=new SceneActivityRangeProbe();'),
    ('            if(cfg.sleepingRootShort) {',
     '            if(cfg.drawControl!="rcnative" || cfg.benchmark!="scene" || !cfg.nativeInputMotion || !cfg.nativeSprint ||\n'
     '                !cfg.playerFire || !cfg.fixedEnemies || !cfg.combatRoute || !cfg.stableMotion || cfg.presentationCheck ||\n'
     '                cfg.sleepingRootShort || cfg.satsCheck || !cfg.noLighting || !cfg.noWall || cfg.vision)\n'
     '                throw new Error("Activity range requires exact native SMG fixture with visual mods off");\n'
     '            report.activityRange={version:"activity-camera-range-1",diagnosticOnly:true,performanceEligible:false,\n'
     '                order:[false,true,true,false],limits:"No real input or production gameplay qualification; all verification and switching costs retained."};\n'
     '            if(cfg.sleepingRootShort) {'),
    ('            row.sampleAtMs=[];row.continuousFramesMs=[];row.caseBeginAtMs=caseBegin;',
     '            row.sampleAtMs=[];row.continuousFramesMs=[];row.caseBeginAtMs=caseBegin;\n'
     '            row.activityRangeSwitch=activityRangeProbe.select(w,index);\n'
     '            row.activityRange=[];'),
    ('                    var now:int=getTimer();\n                    if(continuousPreviousSampleAt<0)',
     '                    row.activityRange.push(activityRangeProbe.sample(w));\n'
     '                    var now:int=getTimer();\n                    if(continuousPreviousSampleAt<0)'),
    ('            closeProbeTiming(true);',
     '            closeProbeTiming(true);\n'
     '            report.activityRangeCleanup=activityRangeProbe.clear();\n'
     '            if(!report.activityRangeCleanup.cleared || report.activityRangeCleanup.errors.length!=0)\n'
     '                error=(error?error+"\\n":"")+"Activity range mode cleanup failed";'),
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def tree(path):
    return {p.relative_to(path).as_posix(): sha(p) for p in sorted(path.rglob('*')) if p.is_file()}


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


def prepare(destination):
    assert not destination.exists(), 'Preserve existing prepared source'
    assert sha(SEED) == SEED_SHA
    seed = json.loads(SEED.read_text('utf-8-sig'))
    assert seed['probeSHA256'] == SOURCE_PROBE
    origin = Path(seed['frozenSourcePath'])
    before = tree(origin)
    assert before == seed['frozenSourceSHA256'] and len(before) == 85
    assert before['ContinuousSceneMotionProbe.as'] == MAIN_RAW_SHA
    shutil.copytree(origin, destination)
    main = destination / 'ContinuousSceneMotionProbe.as'
    main.write_text(transform(main.read_text('utf-8-sig')), 'utf-8')
    shutil.copy2(HERE / 'probe/SceneActivityRangeProbe.as', destination / 'tests/SceneActivityRangeProbe.as')
    after = tree(destination)
    changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    assert changed == CHANGED and len(after) == 86
    assert reverse(main.read_text('utf-8')) == (origin / 'ContinuousSceneMotionProbe.as').read_text('utf-8-sig')
    return dict(version='activity-camera-range-probe-1', seedReceipt=str(SEED), seedReceiptSHA256=SEED_SHA,
                sourceProbeSHA256=SOURCE_PROBE, originalSource=str(origin), originalSourceSHA256=before,
                preparedSource=str(destination), preparedSourceSHA256=after, changed=changed, reverseExact=True,
                sourceInputs={str(p): sha(p) for p in (Path(__file__), HERE / 'probe/SceneActivityRangeProbe.as')},
                compiled=False, gameStarted=False, performanceAccepted=False, deployed=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    folder = HERE / 'probe-prepared' / uuid.uuid4().hex
    evidence = prepare(folder / 'src')
    receipt = folder / 'source-proof.json'
    receipt.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), 'utf-8')
    print(json.dumps(dict(receipt=str(receipt), changed=evidence['changed'], sourceCount=86,
                          reverseExact=True, compiled=False, gameStarted=False), ensure_ascii=False))


if __name__ == '__main__':
    main()
