"""Compare the bullet-grid arms: frame intervals, CS phases and live grid density.

Usage: python analyze_grid.py bulletgrid-base-combat-r1 bulletgrid-grid-combat-r1
"""
from pathlib import Path
import json, sys

HERE = Path(__file__).resolve().parent
MOD = HERE.parents[2]
EVIDENCE = MOD / 'knowledge/experiments/evidence'
PHASES = [('tick', 'tickMs'), ('warm', 'warmMs'), ('sync', 'syncMs'), ('cull', 'cullMs'),
          ('mark', 'markMs'), ('step', 'stepMs'), ('beginWarm', 'beginWarmMs')]


def load(name):
    path = EVIDENCE / name / 'storage/result.json'
    if not path.exists():
        raise SystemExit('missing ' + str(path))
    return json.loads(path.read_text(encoding='utf-8'))


def pct(values, q):
    if not values:
        return float('nan')
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round(q * (len(ordered) - 1)))))
    return ordered[index]


def summarize(name):
    report = load(name)
    samples = report.get('samples') or []
    rows = []
    previous = None
    for sample in samples:
        chunk = sample.get('chunk') or {}
        if previous is not None:
            row = {'dt': sample['dtMs'], 'phase': sample.get('phase'), 'projectiles': sample.get('projectiles')}
            for label, key in PHASES:
                row[label] = max(0, int(chunk.get(key) or 0) - int(previous.get(key) or 0))
            rows.append(row)
        previous = chunk
    grid = [s.get('grid') for s in samples if s.get('grid')]
    active = [g for g in grid if g.get('active')]
    buckets = [g.get('bucket') for g in active if isinstance(g.get('bucket'), int)]
    units = [g.get('units') for g in active if isinstance(g.get('units'), int)]
    dense = [g.get('dense') for g in active if isinstance(g.get('dense'), int) and g.get('dense')]
    summary = {
        'name': name,
        'samples': len(samples),
        'intervals': len(rows),
        'checks': report.get('checks'),
        'errors': [c for c in (report.get('checks') or []) if not c.get('ok')] if isinstance(report.get('checks'), list) else None,
        'gridSamples': len(grid),
        'gridActive': len(active),
        'gridUnitsMean': round(sum(units) / len(units), 1) if units else None,
        'gridBucketMean': round(sum(buckets) / len(buckets), 2) if buckets else None,
        'gridBucketP95': pct(buckets, 0.95) if buckets else None,
        'gridBucketMax': max(buckets) if buckets else None,
        'gridDenseMean': round(sum(dense) / len(dense), 1) if dense else None,
        'gridError': next((g.get('error') for g in grid if g.get('error')), None),
    }
    if rows:
        dts = [r['dt'] for r in rows]
        summary['dtMean'] = round(sum(dts) / len(dts), 2)
        summary['dtP50'] = pct(dts, 0.5)
        summary['dtP95'] = pct(dts, 0.95)
        summary['dtMax'] = max(dts)
        summary['over100'] = sum(1 for d in dts if d >= 100)
        summary['over50'] = sum(1 for d in dts if d >= 50)
        for label, _ in PHASES:
            values = [r[label] for r in rows]
            summary[label + 'Mean'] = round(sum(values) / len(values), 3)
    projectiles = [r['projectiles'] for r in rows if isinstance(r.get('projectiles'), int)]
    summary['projectileMean'] = round(sum(projectiles) / len(projectiles), 2) if projectiles else None
    summary['projectileMax'] = max(projectiles) if projectiles else None
    return summary


def main(names):
    summaries = [summarize(name) for name in names]
    for summary in summaries:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    if len(summaries) == 2 and all('dtMean' in s for s in summaries):
        first, second = summaries
        print('delta dtMean: %+.2f ms (%+.1f%%)' % (
            second['dtMean'] - first['dtMean'],
            100.0 * (second['dtMean'] - first['dtMean']) / first['dtMean']))


if __name__ == '__main__':
    main(sys.argv[1:])
