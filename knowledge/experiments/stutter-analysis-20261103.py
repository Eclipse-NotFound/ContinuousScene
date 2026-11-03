"""Recompute the 2026-11-03 diagnosis from retained raw evidence (no game launch)."""
from pathlib import Path
from collections import Counter
import json
import math
import statistics

EVIDENCE = Path(__file__).resolve().parent / 'evidence'


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def metrics(rows):
    values = sorted(r['dtMs'] for r in rows)
    if not values:
        return {'n': 0}
    return {'n': len(values), 'meanMs': statistics.mean(values),
            'p95Ms': values[math.ceil(.95 * len(values)) - 1],
            'p99Ms': values[math.ceil(.99 * len(values)) - 1],
            'maxMs': max(values), 'gt100': sum(t > 100 for t in values),
            'gt100PerMinute': 60000 * sum(t > 100 for t in values) / sum(values)}


def probe(name):
    directory = EVIDENCE / name
    data = load(directory / 'storage/result.json')
    rows = data['samples']
    previous = None
    for row in rows:
        row['memoryDropBytes'] = 0 if previous is None else max(0, previous['memoryBytes'] - row['memoryBytes'])
        for key in ('sceneWarmSlices', 'sceneWarmCount', 'sceneMisses', 'sceneWarmForced'):
            row['delta_' + key] = 0 if previous is None else row['scene'][key] - previous['scene'][key]
        previous = row
    result = {'name': name, 'ok': data['ok'], 'entry': data['entry'],
              'all': metrics(rows), 'insideOnly': metrics([r for r in rows if r['insideViewport']]),
              'allLmg': all(r['weapon'] == 'lmg' for r in rows),
              'playerShotFrames': sum(r['playerShot'] for r in rows),
              'fixtureEnemyShotFrames': sum(r['enemyShots'] for r in rows),
              'maxPositionDifference': {axis: max(abs(r['player' + axis] - r['vis' + axis]) for r in rows) for axis in ('X', 'Y')},
              'longFramesWithMemoryDropOver1MiB': sum(r['dtMs'] > 100 and r['memoryDropBytes'] > 1048576 for r in rows),
              'longFramesWithWarmSlice': sum(r['dtMs'] > 100 and r['delta_sceneWarmSlices'] > 0 for r in rows),
              'maxWakeTransitionsPerFrame': max(r['woke'] for r in rows),
              'maxSleepTransitionsPerFrame': max(r['slept'] for r in rows),
              'phaseOrWindow': []}
    group_field = 'window' if 'window' in rows[0] else 'phase'
    for group in sorted({r[group_field] for r in rows}):
        subset = [r for r in rows if r[group_field] == group]
        samples = [r['presentation'] for r in subset if 'presentation' in r]
        row = {group_field: group, 'phase': subset[0]['phase'], **metrics(subset),
               'withoutTransition': metrics([r for r in subset if not r['transition']]),
               'insideFraction': sum(r['insideViewport'] for r in subset) / len(subset),
               'playerShotFrames': sum(r['playerShot'] for r in subset),
               'fixtureEnemyShotFrames': sum(r['enemyShots'] for r in subset),
               'xRange': [min(r['playerX'] for r in subset), max(r['playerX'] for r in subset)],
               'yRange': [min(r['playerY'] for r in subset), max(r['playerY'] for r in subset)],
               'activityMeanMs': statistics.mean(r['activityMs'] for r in subset),
               'presenterFallbacks': dict(Counter(r['lastReason'] for r in samples)),
               'culling': subset[0].get('cullingEnabled'),
               'warmSlices': sum(r['delta_sceneWarmSlices'] for r in subset),
               'newBlocks': sum(r['delta_sceneWarmCount'] for r in subset),
               'misses': sum(r['delta_sceneMisses'] for r in subset),
               'forced': sum(r['delta_sceneWarmForced'] for r in subset),
               'memoryDrops': sum(r['memoryDropBytes'] > 1048576 for r in subset)}
        if 'continuousSceneHandlerMs' in subset[0]:
            row['continuousSceneHandlerMeanMs'] = statistics.mean(r['continuousSceneHandlerMs'] for r in subset)
        if samples:
            row['presenterClearsWithinSamples'] = samples[-1]['helper']['clears'] - samples[0]['helper']['clears']
        result['phaseOrWindow'].append(row)
    (directory / 'analysis-20261103.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    for name in ('stutter-lmg-current-20261103-r2', 'stutter-lmg-explore-20261103-r1', 'stutter-culling-abba-20261103-r1'):
        if not (EVIDENCE / name / 'storage/result.json').exists():
            continue
        result = probe(name)
        print(json.dumps({k: v for k, v in result.items() if k not in ('entry', 'phaseOrWindow')}, ensure_ascii=False))
        for row in result['phaseOrWindow']:
            print(json.dumps(row, ensure_ascii=False))
