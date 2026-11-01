"""Summarize owned experiments without changing their raw evidence or acceptance."""
from pathlib import Path
import hashlib
import json
import statistics

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
REPO = ROOT / 'mods/ContinuousScene'
BASE = REPO / 'knowledge/experiments/evidence'
RUNS = [
    'camera-object-clip-large-r1-20261101',
    'camera-object-cache-guard-large-r1-20261101',
    'camera-object-cache-base-large-r1-20261101',
    'camera-scaled-fill-small-r1-20261101',
    'camera-terrain-cache-large-r1-20261101',
    'camera-phase-search-small-r1-20261101',
    'camera-screen-cache-small-r1-20261101',
    'camera-screen-cache-small-r2-20261101',
    'camera-screen-cache-large-r1-20261101',
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def stats(rows):
    values = sorted(row[1] for row in rows if row[1] >= 0)
    if not values:
        return {}
    return dict(n=len(values), mean=round(statistics.mean(values), 3),
                p95=values[int(.95 * (len(values)-1))],
                p99=values[int(.99 * (len(values)-1))],
                maximum=values[-1], over100=sum(v > 100 for v in values))


def main():
    summary = {'runs': [], 'missing': [], 'totalIntervals': 0,
               'diagnosticOnly': True, 'performanceDeploymentAccepted': False,
               'rawAcceptancePreserved': True}
    reference_mods = None
    for name in RUNS:
        directory = BASE / name
        path = directory / 'storage/result.json'
        if not path.exists():
            summary['missing'].append(name)
            continue
        raw = json.loads(path.read_text('utf-8'))
        inputs = json.loads((directory / 'inputs.json').read_text('utf-8'))
        review = json.loads((directory / 'review-inputs.json').read_text('utf-8'))
        policy = json.loads((directory / 'process-policy.json').read_text('utf-8'))
        mods = {k: v for k, v in inputs.items()
                if k.lower().endswith('mod.swf') and 'continuousscenemotion' not in k.lower()
                and 'continuoussceneprobe' not in k.lower()}
        if reference_mods is None:
            reference_mods = mods
        assert mods == reference_mods, (name, 'formal mod combination differs')
        assert inputs['pfe.swf'] == review['host'], (name, 'host receipt differs')
        groups = {}
        blocks = []
        for block in raw.get('blocks', []):
            if 'rows' not in block:
                continue
            rows = block['rows']
            groups.setdefault(block['settings']['mode'], []).extend(rows)
            delta = {k: block['endCounters'][k] - block['startCounters'][k]
                     for k in ['sceneWarmCount', 'sceneRedraws', 'sceneMisses', 'sceneEvictions']}
            assert not any(delta.values()), (name, block['index'], delta)
            blocks.append({'index': block['index'], **block['settings'], **stats(rows),
                           'worldChanges': delta})
        result = {'name': name, 'ok': raw['ok'], 'error': raw.get('error'),
                  'assertions': len(raw['assertions']),
                  'failedAssertions': [a for a in raw['assertions'] if not a['ok']],
                  'entry': {k: raw.get('entry', {}).get(k)
                            for k in ['units', 'scale', 'stageWidth', 'stageHeight']},
                  'host': inputs['pfe.swf'],
                  'groups': {k: stats(v) for k, v in groups.items()}, 'blocks': blocks,
                  'legacyHarnessPerformanceEligible': policy['performanceEligible'],
                  'otherAirProcessIds': policy['otherAirProcessIds'],
                  'minimumAvailableCommit': policy.get('minimumAvailableCommit'),
                  'nativeHiddenActor': raw.get('nativeHiddenActor'),
                  'rawSHA256': sha(path), 'recipeProbeSHA256': review['recipe']['probe']}
        assert not policy['otherAirProcessIds'], (name, 'AIR contention')
        if raw.get('nativeHiddenActor'):
            assert raw['nativeHiddenActor']['after'] is False
        summary['runs'].append(result)
        summary['totalIntervals'] += sum(g['n'] for g in result['groups'].values())
    summary['formalMods'] = reference_mods
    summary['currentRootHostSHA256'] = sha(ROOT / 'pfe.swf')
    summary['currentFormalModsMatch'] = all(sha(ROOT / k) == v for k, v in reference_mods.items())
    (HERE / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), 'utf-8')
    print(json.dumps({k: v for k, v in summary.items() if k not in ['runs', 'formalMods']}, ensure_ascii=False))
    for result in summary['runs']:
        print(json.dumps({k: result[k] for k in ['name', 'ok', 'assertions', 'groups']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
