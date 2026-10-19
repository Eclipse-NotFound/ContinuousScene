"""Compact observed frame timings; event bands are not exclusive CPU time."""
from pathlib import Path
import json, math, statistics, sys

ROOT=Path(__file__).resolve().parent.parent/'knowledge/experiments/evidence'

def stats(values):
    if not values:return None
    ordered=sorted(values)
    return {'n':len(values),'median':statistics.median(values),
            'p95':ordered[math.ceil(len(values)*.95)-1],
            'mean':round(statistics.mean(values),2),'max':max(values),
            'over100':sum(x>100 for x in values)}

for name in sys.argv[1:]:
    root=ROOT/name
    result=json.loads((root/'storage/result.json').read_text('utf-8-sig'))
    policy=json.loads((root/'process-policy.json').read_text('utf-8-sig'))
    report={key:result.get(key) for key in ('ok','error','entryMs','world','path','internalSigns')}
    report.update(name=name,performanceEligible=policy['performanceEligible'],
                  checks=len(result.get('assertions',[])),samples=[])
    for sample in result.get('samples',[]):
        row={key:sample.get(key) for key in ('name','misses','forced','slices','empty','warmMaxMs','shots','activity')}
        for key in ('frames','nativeBand','defaultBand','wallBand','sceneBand'):
            row[key]=stats(sample.get(key,[]))
        row['warm']=sum(sample.get('warm',[]))
        report['samples'].append(row)
    print(json.dumps(report,ensure_ascii=False))
