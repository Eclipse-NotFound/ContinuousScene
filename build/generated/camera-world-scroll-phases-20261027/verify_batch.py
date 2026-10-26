"""Read-only audit of three original failures; never rewrite their reports."""
from pathlib import Path
import hashlib
import importlib.util
import inspect
import json

HERE = Path(__file__).resolve().parent
MOD = HERE.parents[2]
GAME = MOD.parents[1]
EVIDENCE = MOD / 'knowledge/experiments/evidence'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def read(path):
    return json.loads(path.read_text('utf-8-sig'))


def audit(name):
    folder = EVIDENCE / (name + '-20261027-r1')
    rec = read(folder / 'runner-inputs.json')
    probe = read(folder / 'probe-build.json')
    raw = read(folder / 'storage/result.json')
    policy = read(folder / 'process-policy.json')
    failure = read(folder / 'runner-failure.json')
    t = raw['cameraRaster']
    assert len(rec['baseline']) == 526 and len(rec['runtimeInputs']) == 13
    for key, digest in rec['baseline'].items():
        assert sha(GAME / key) == digest, key
    for group in ('runnerInputs', 'compilerInputs', 'fixtureInputs'):
        for key, digest in rec[group].items():
            assert sha(Path(key)) == digest, (group, key)
    for key, digest in rec['runtimeInputs'].items():
        assert sha(GAME / key) == digest, key
    assert len(probe['frozenSourceSHA256']) == 86
    for key, digest in probe['frozenSourceSHA256'].items():
        assert sha(Path(probe['frozenSourcePath']) / key) == digest, key
    assert sha(Path(probe['probePath'])) == probe['probeSHA256']
    assert policy['desktopPolicy'] == 'private'
    assert not any(policy.get(k) for k in ('otherAirProcessIds', 'memoryAbort', 'runFailure'))
    assert t['cleanup']['restored'] and not t['cleanup']['errors']
    assert t['cleanup']['pendingOwnedBitmaps'] == 0
    assert t['pixelBitmapsCreated'] == t['pixelBitmapsDisposed']
    assert not failure['complete'] and not failure['deployed']
    return folder, raw, dict(
        name=name, pid=policy['pid'], resultSHA256=sha(folder / 'storage/result.json'),
        originalFailureSHA256=sha(folder / 'runner-failure.json'),
        originalFailure=failure['error'], originalFailureRetained=True,
        probeSHA256=probe['probeSHA256'], frozenSourceCount=86, inputsUnchanged=True,
        capturesDisposed=t['pixelBitmapsDisposed'], samples=len(t['framesMs']),
        errors=t['errors'], cleanup=t['cleanup'], deployed=False)


rows = []
folder, raw, row = audit('camera-world-scroll-routewarm')
t = raw['cameraRaster']
assert not raw['ok'] and not t['complete'] and not t['framesMs']
assert len(t['nativeWarmups']) == 1 and t['nativeWarmups'][0]['passed']
c = t['pixels'][0]['conditions'][0]
assert c['condition'] == 2 and c['changed']['maxRGB'] == 92 and c['changed']['maxAlpha'] == 0
assert c['restored']['equal'] and t['pixelBitmapsDisposed'] == 15
row['pixelFailure'] = c
rows.append(row)

folder, raw, row = audit('camera-world-scroll-cost')
t = raw['cameraRaster']
assert not raw['ok'] and not t['complete'] and len(t['framesMs']) == 121
assert not t['visualAccepted'] and len(t['qualityFailures']) == 5
assert t['errors'] == ['Terrain changed during rendered interval']
assert len(t['windows']) == 2 and [len(w['framesMs']) for w in t['windows']] == [120, 1]
assert t['pixelBitmapsDisposed'] == 75
row['limitation'] = 'Incomplete run. Its legacy error checks world display state, not terrain pixels. No paired timing result.'
rows.append(row)

folder, raw, row = audit('camera-world-scroll-phases')
spec = importlib.util.spec_from_file_location('scroll_phase_original_runner', HERE / 'run.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
# Re-evaluate the original full summary without editing the immutable runner.
# Only the unsupported exactly-one EXIT_FRAME assumption is replaced. All 480
# retained latest snapshots, timestamps, positions and prior visual failures
# remain checked. Unretained callbacks are explicitly outside this audit.
original = inspect.getsource(runner.summarize)
old = "phase['snapshots']==480"
assert original.count(old) == 1
revised = original.replace(old, "phase['snapshots']>=480")
scope = dict(vars(runner))
exec(compile(revised, '<read-only retained-snapshot review>', 'exec'), scope)
summary = scope['summarize'](raw)
assert raw['ok'] and summary['complete'] and not summary['visualAccepted']
assert summary['phaseObservation']['snapshots'] == 1281
assert summary['phaseObservation']['nativeEntryRepositions'] == 240
assert not summary['candidateAcceptance'] and not summary['performanceEligible']
row['retainedSnapshotReview'] = summary
row['reviewAdjustment'] = dict(
    original=old, checked="phase['snapshots']>=480",
    reason='The driver subscribes directly to ENTER_FRAME without a timer or measurement skip. EXIT_FRAME is not proven one-to-one with those entries.',
    limits='Only each interval\'s retained latest EXIT_FRAME state is available. Intermediate callbacks were overwritten; this is not a count of physical presentations.')
rows.append(row)

result = dict(complete=True, originalFailuresRetained=True, gameRuns=rows,
              candidateAcceptance=False, gameplayAcceptance=False, deployed=False)
target = HERE / 'batch-review.json'
assert not target.exists(), 'Preserve prior review'
target.write_text(json.dumps(result, ensure_ascii=False, indent=2), 'utf-8')
print(json.dumps(dict(review=str(target), runs=[dict(name=r['name'], samples=r['samples'], pid=r['pid']) for r in rows],
                     arms=summary['arms'], pairs=summary['pairs'], candidateAcceptance=False), ensure_ascii=False))
