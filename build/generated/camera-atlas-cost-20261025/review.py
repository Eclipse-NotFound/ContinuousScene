"""Summarize all raw intervals; never change a visual failure into acceptance."""
from pathlib import Path
import argparse
import hashlib
import json
import statistics


def stats(values):
    ordered = sorted(values)
    return dict(count=len(values), meanMs=statistics.mean(values), medianMs=statistics.median(values),
                p95Ms=ordered[int((len(ordered)-1)*.95)], maxMs=max(values), totalMs=sum(values))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence', type=Path)
    args = parser.parse_args()
    source = args.evidence / 'storage/result.json'
    result = json.loads(source.read_text('utf-8-sig'))
    trial = result['cameraRaster']
    assert trial['timingComplete'] and len(trial['framesMs']) == 960
    assert trial['cleanup']['restored'] and trial['cleanup']['errors'] == []
    groups = {}
    rows = []
    frames = []
    for row in trial['windows']:
        assert len(row['framesMs']) == 120
        groups.setdefault(row['mode'], []).extend(row['framesMs'])
        rows.append(dict(index=row['index'], mode=row['mode'], **stats(row['framesMs'])))
        frames.extend(row['framesMs'])
    assert frames == trial['framesMs'] and sum(frames) == trial['timingElapsedMs']
    merged = {mode: stats(values) for mode, values in groups.items()}
    assert all(value['count'] == 240 for value in merged.values())
    excess = {}
    for mode in ('native', 'atlas'):
        excess[mode] = merged[mode+'-moving']['meanMs'] - merged[mode+'-static']['meanMs']
    report = dict(resultSHA256=hashlib.sha256(source.read_bytes()).hexdigest().upper(),
        diagnosticOnly=True, performanceEligible=False, gameplayAcceptance=False, deployed=False,
        originalProbeOk=result['ok'], qualityAccepted=trial['qualityAccepted'], qualityErrors=trial['qualityErrors'],
        frames=960, elapsedMs=sum(frames), merged=merged, windows=rows,
        movementExtraMeanMs=excess,
        sequentialMovementExtraMeanMs=[rows[1]['meanMs']-rows[0]['meanMs'],
            rows[3]['meanMs']-rows[2]['meanMs'], rows[4]['meanMs']-rows[5]['meanMs'],
            rows[6]['meanMs']-rows[7]['meanMs']],
        note='All intervals retained; visual failures unchanged. Cost attribution only; no gameplay or release acceptance.')
    destination = args.evidence / 'aggregate-review.json'
    assert not destination.exists(), 'Preserve existing analysis'
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), 'utf-8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
