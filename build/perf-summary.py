"""Summarize actual frame intervals (not fixed-step game time)."""
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]/'knowledge/experiments/evidence'

def stats(values):
    if not values:
        return {'count': 0}
    ordered = sorted(values)
    return dict(count=len(values), median=statistics.median(values),
                p95=ordered[min(len(values)-1,int(len(values)*.95))],
                p99=ordered[min(len(values)-1,int(len(values)*.99))],
                max=max(values), mean=round(statistics.mean(values),2))

for name in sys.argv[1:]:
    folder=ROOT/name
    result=json.loads((folder/'result.json').read_text(encoding='utf-8-sig'))
    policy=json.loads((folder/'process-policy.json').read_text(encoding='utf-8-sig'))
    print(json.dumps(dict(name=name,ok=result['ok'],entryMs=result.get('entryMs'),
        entryRedraws=result.get('entryRedraws'),entryMemoryMB=result.get('entryMemoryMB'),
        walking=stats(result.get('walkingFrameDeltas',[])),render=stats(result.get('walkingRenderFrames',[])),
        cached=stats(result.get('walkingCachedFrames',[])),
        script=stats(result.get('walkingScriptFrames',[])),
        peakAS3MB=max([result.get('memoryMB',0)]+[s['memMB'] for s in result.get('samples',[])]),
        finalRedraws=result.get('samples',[{}])[-1].get('redraws'),process=policy),ensure_ascii=False))
