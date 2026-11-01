"""Archive exact diagnostic inputs and qualify evidence without promoting it."""
from pathlib import Path
import hashlib, json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
REPO = ROOT / 'mods/ContinuousScene'
BASE = REPO / 'knowledge/experiments/evidence'
RUNS = [
    'camera-soft-dense-v21-20261101-r1',
    'camera-soft-dense-v22-20261101-r1',
    'camera-soft-sparse-v22-20261101-r1',
    'camera-native-quality-dense-v23-20261101-r1',
    'camera-native-gpu-v23-20261101-r1',
    'camera-native-combat-v24-20261101-r1',
    'camera-soft-terrain-v25-20261101-r1',
    'combat-cost-visible-v27-20261101-r1',
    'camera-temporal-present-v28-20261101-r1',
    'combat-cost-target-v29-20261101-r1',
    'camera-temporal-target-v30-20261101-r1',
]
GENERATORS = [
    'camera-soft-present-v21-20261101',
    'camera-soft-present-v22-20261101',
    'camera-native-quality-v23-20261101',
    'camera-native-combat-v24-20261101',
    'camera-soft-terrain-v25-20261101',
    'combat-cost-v26-20261101',
    'combat-cost-visible-v27-20261101',
    'camera-temporal-present-v28-20261101',
    'combat-cost-target-v29-20261101',
    'camera-temporal-target-v30-20261101',
]

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest().upper()
def read(path): return json.loads(path.read_text('utf-8-sig'))
def write(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)

def main():
    expected = read(HERE.parent / 'lossless-cut-survey-20261101/summary.json')
    formal = expected['formalMods']
    out = dict(diagnosticOnly=True, performanceDeploymentAccepted=False,
               performanceTargetAchieved=False, deployment=None,
               formalMods=formal, host=expected['host'], runs=[], totalIntervals=0,
               onscreenDiagnosticIntervals=0,
               failedAndPartialEvidencePreserved=True,
               acceptanceBoundary='Legacy harness performanceEligible=false and 120-fps capacity diagnostics are not production acceptance.')
    archive = {}
    for name in RUNS:
        folder = BASE / name
        policy = read(folder / 'process-policy.json')
        inputs = read(folder / 'inputs.json')
        review = read(folder / 'review-inputs.json')
        assert all(inputs[k] == v for k, v in formal.items()), name
        assert inputs['pfe.swf'] == review['host'] == out['host'], name
        rawfile = folder / 'storage/result.json'
        raw = read(rawfile) if rawfile.exists() else {}
        item = dict(name=name, ok=raw.get('ok', False), error=raw.get('error') or policy.get('runFailure'),
                    assertions=len(raw.get('assertions', [])), probe=review['recipe']['probe'],
                    legacyHarnessPerformanceEligible=policy['performanceEligible'],
                    otherAirProcessIds=policy.get('otherAirProcessIds'),
                    minimumAvailableCommit=policy.get('minimumAvailableCommit'),
                    rawSHA256=sha(rawfile) if rawfile.exists() else None)
        if raw:
            assert raw['nativeHiddenActor']['after'] is False, name
            item['failedChecks'] = [a for a in raw['assertions'] if not a['ok']]
            item['entry'] = {k: raw['entry'].get(k) for k in ('units','scale','stageWidth','stageHeight','x','y')}
            item['qualityCapability'] = raw.get('qualityCapability')
            item['pixels'] = raw.get('pixels')
            item['fixedTarget'] = raw.get('fixtureFixedTarget')
            item['fixtureActualEnd'] = raw.get('fixtureActualEnd')
            item['visibleQualifications'] = [b.get('visibleQualification') for b in raw.get('blocks',[])]
            if raw.get('allocationDiagnostic'):
                item['allocationDiagnostic'] = True
                item['frameCostWindows'] = len(raw.get('frameCost', {}).get('windows', []))
            analysisfile = folder / 'quality-analysis.json'
            if analysisfile.exists():
                analysis = read(analysisfile)
                assert analysis['rawSHA256'] == sha(rawfile)
                item['byAxis'] = analysis['byAxis']
                if item['ok'] and not raw.get('allocationDiagnostic'):
                    out['totalIntervals'] += sum(m['n'] for axis in analysis['byAxis'].values() for m in axis.values())
                item['timedCounterChanges'] = [b['counters'] for b in analysis['blocks'] if b['complete'] and any(b['counters'].values())]
                item['combatDeltas'] = [b['combat'] for b in analysis['blocks'] if b.get('combat')]
            rows = [row for b in raw.get('blocks', []) for row in b.get('rows', [])]
            if rows:
                item['motionRanges'] = {raw['columns'][i]:[min(r[i] for r in rows),max(r[i] for r in rows)] for i in (3,4,5,6,7,8,11,12)}
                ranges = item['motionRanges']
                item['playerRemainedOnscreen'] = (ranges['screenPlayerX'][0]>=0 and ranges['screenPlayerX'][1]<raw['entry']['stageWidth'] and ranges['screenPlayerY'][0]>=0 and ranges['screenPlayerY'][1]<raw['entry']['stageHeight'])
                if item['ok'] and item['playerRemainedOnscreen'] and not raw.get('allocationDiagnostic'):
                    out['onscreenDiagnosticIntervals'] += sum(r[1]>=0 for r in rows)
        out['runs'].append(item)
        for path in folder.rglob('*'):
            if not path.is_file(): continue
            if path.name == 'partial.json' and item['ok']: continue
            if path.suffix.lower() in ('.json','.log','.png'):
                archive[path.relative_to(REPO).as_posix()] = sha(path)
    for name in GENERATORS:
        folder = HERE.parent / name
        if (folder / 'build.json').exists():
            receipt = read(folder / 'build.json')
            assert all(sha(folder / p) == v for p, v in receipt['sources'].items()), name
            assert sha(folder / 'ContinuousSceneMotionMod.swf') == receipt['probe'], name
        else:
            assert name == 'combat-cost-v26-20261101'
            out.setdefault('notLaunched', []).append(name+': compiler registry wait timed out; superseded by v27, no Java or AIR started')
        paths = [p for p in folder.iterdir() if p.is_file()]
        paths += list((folder / 'tests').rglob('*')) if (folder / 'tests').exists() else []
        for path in paths:
            if path.is_file() and path.suffix.lower() in ('.as','.py','.xml','.json','.log','.swf'):
                archive[path.relative_to(REPO).as_posix()] = sha(path)
    # Snapshot the corrected shared fact as evidence, not a second maintained copy.
    fact = ROOT / 'shared-knowledge/rendering/facts/desktop-stage-quality-limit.md'
    out['sharedFact'] = {'path':str(fact), 'SHA256':sha(fact)}
    out['formalDescriptor'] = {'SHA256':sha(ROOT/'application.xml'), 'allowLowQuality':False}
    assert '<allowLowQuality>' not in (ROOT/'application.xml').read_text('utf-8-sig')
    out['formalUnchanged'] = sha(ROOT/'pfe.swf') == out['host'] and all(sha(ROOT/p)==h for p,h in formal.items())
    out['foreignSourceUnchanged'] = sha(REPO/'src/tests/SceneRenderChecks.as') == '41DF71EE976EAD95CFFC1989CD9EF70A7C2FF0C24D541C4A3AD78A9F5B050983'
    assert out['formalUnchanged'] and out['foreignSourceUnchanged']
    write(HERE/'archive.json', archive)
    write(HERE/'summary.json', out)
    print(json.dumps({k:v for k,v in out.items() if k not in ('runs','formalMods')},ensure_ascii=False))
    print(json.dumps({'frozenFiles':len(archive),'runs':len(out['runs']),'successful':sum(r['ok'] for r in out['runs'])}))

if __name__ == '__main__': main()
