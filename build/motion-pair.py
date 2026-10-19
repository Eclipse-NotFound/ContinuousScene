"""Reject comparisons with different terrain or local camera routes."""
from pathlib import Path
import json, sys

ROOT=Path(__file__).resolve().parent.parent/'knowledge/experiments/evidence'
names=sys.argv[1:]
assert len(names)==2
rows=[json.loads((ROOT/name/'storage/result.json').read_text('utf-8-sig')) for name in names]
policies=[json.loads((ROOT/name/'process-policy.json').read_text('utf-8-sig')) for name in names]
a,b=rows
def route(r):
    p=r['path']
    return (p['startX']%1920,p['endX']-p['startX'],p['y']%1000)
checks={'completed':all(r['ok'] for r in rows),
    'eligible':all(p['performanceEligible'] and not p['otherAirProcessIds'] for p in policies),
    'layoutSeed':a['world'].get('layoutSeed')==b['world'].get('layoutSeed') and 'layoutSeed' in a['world'],
    'entryTerrain':a['world'].get('entryRoomTiles')==b['world'].get('entryRoomTiles') and 'entryRoomTiles' in a['world'],
    'localRoute':route(a)==route(b),
    'effects':all(a['config'].get(key)==b['config'].get(key) for key in ('noLighting','noWall','vision'))}
print(json.dumps({'names':names,'checks':checks,'referenceComparable':all(checks.values()),
    'limits':'Entity randomness and ordinary/merged camera bounds still differ; this is not an identical-world causal experiment.'},indent=2))
if not all(checks.values()):sys.exit(1)
