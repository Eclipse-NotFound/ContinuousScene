"""Terminal turret timeline component on exact B7ED/39A frozen 85-source probe.

No shared source/host changes. The phase-2 early return avoids route relocation,
test actor creation, weapon changes and dense warmup. Only the next phase-3 call
runs the isolated synchronous component, then the inherited terminal cleanup.
"""
from pathlib import Path
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
HELPER = HERE / 'tests/SceneTurretTimelineChecks.as'
VERSION = 'turret-timeline-sync-1'
CHANGED = ['ContinuousSceneMotionProbe.as', 'tests/SceneTurretTimelineChecks.as']
SEED_RECEIPT_SHA = 'B7ED1EAB8BEE0DC1024D6EF0A56A965F311B97E8CED9A9F32A2BCDE35B35FF13'
SEED_MAIN_SHA = 'F87A95E684A88D508679853C2EA2E1377EFC30236DD9BC7097885F4E5756FEE1'
PATCHES = (
    ('    import tests.SceneEncounter;', '\n    import tests.SceneTurretTimelineChecks;'),
    ('                    check("actual-expected-native-map",cfg.benchmark=="normal"?(!w.grafon.sceneLarge && loc.spaceX==48):(w.grafon.sceneLarge && loc.spaceX>48));',
     '\n                    report.turretTimelineEntry={diagnosticOnly:true,terminalOnly:true,phase:2,densePreparationSkipped:true};'
     '\n                    age=0;phase=3;return;'),
    ('                }else if(phase==3) {',
     '\n                    report.diagnosticOnly=true;report.performanceEligible=false;'
     '\n                    report.turretTimeline=SceneTurretTimelineChecks.run(w);'
     '\n                    check("turret-timeline-synchronous-component",report.turretTimeline.passed,report.turretTimeline.restore);'
     '\n                    finish();return;'),
)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def transform(source):
    assert 'SceneTurretTimelineChecks' not in source
    changed = source
    for anchor, insertion in PATCHES:
        assert changed.count(anchor) == 1, ('Unique frozen anchor required', anchor[:100])
        changed = changed.replace(anchor, anchor + insertion, 1)
    restored = changed
    for anchor, insertion in reversed(PATCHES):
        assert restored.count(anchor + insertion) == 1
        restored = restored.replace(anchor + insertion, anchor, 1)
    assert restored == source, 'Component patch must reverse exactly'
    return changed


def prepare(source: Path, destination: Path):
    source, destination = Path(source), Path(destination)
    assert not destination.exists(), 'A fresh copied source directory is required'
    # Explicitly validate the complete immutable seed, not active HEAD.
    receipt = HERE.parents[3] / 'knowledge/experiments/evidence/vertical-camera-band-20261023-combat-candidate-r3/probe-build.json'
    assert digest(receipt) == SEED_RECEIPT_SHA
    doc = json.loads(receipt.read_text(encoding='utf-8-sig'))
    expected = doc['sharedSourceSnapshotSHA256']
    actual = {p.relative_to(source).as_posix(): digest(p) for p in source.rglob('*') if p.is_file()}
    assert len(actual) == len(expected) == 85 and actual == expected, 'Exact B7ED 85-source seed required'
    assert digest(source / 'ContinuousSceneMotionProbe.as') == SEED_MAIN_SHA
    shutil.copytree(source, destination)
    main = destination / 'ContinuousSceneMotionProbe.as'
    main.write_text(transform(main.read_text(encoding='utf-8-sig')), encoding='utf-8')
    shutil.copyfile(HELPER, destination / 'tests/SceneTurretTimelineChecks.as')
