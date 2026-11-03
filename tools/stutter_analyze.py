"""Analyze all retained intervals, separately identifying warmup and transitions."""
from pathlib import Path
import json,math,statistics,sys
MOD=Path(__file__).resolve().parents[1]

def stats(rows):
    if not rows:return {'n':0}
    t=sorted(r['dtMs'] for r in rows)
    return {'n':len(t),'meanMs':statistics.mean(t),'p95Ms':t[math.ceil(.95*len(t))-1],
        'p99Ms':t[math.ceil(.99*len(t))-1],'maxMs':max(t),'gt100':sum(v>100 for v in t),
        'gt100PerMinute':60000*sum(v>100 for v in t)/sum(t),
        'csMeanMs':statistics.mean(r['continuousSceneHandlerMs'] for r in rows),
        'inside':sum(r['insideViewport'] for r in rows),'shotFrames':sum(r['playerShot'] for r in rows),
        'xRange':[min(r['playerX'] for r in rows),max(r['playerX'] for r in rows)],
        'yRange':[min(r['playerY'] for r in rows),max(r['playerY'] for r in rows)]}

def analyze(name):
    folder=MOD/'knowledge/experiments/evidence'/name
    data=json.loads((folder/'storage/result.json').read_text(encoding='utf-8-sig'))
    rows=data['samples'];steady=[r for r in rows if not r.get('warmup')]
    result={'name':name,'ok':data['ok'],'error':data.get('error'),'checks':data.get('cullingChecks'),
        'pixels':data.get('pixelEquivalence'),'all':stats(rows),'measured':{},'windows':[]}
    for mode in [False,True]:
        group=[r for r in steady if r['candidate']==mode]
        result['measured']['candidate' if mode else 'legacy']={
            'all':stats(group),'withoutTransitions':stats([r for r in group if not r['transition']]),
            'right':stats([r for r in group if r['phase']==47]),'left':stats([r for r in group if r['phase']==48])}
    for window in sorted({r['window'] for r in rows}):
        part=[r for r in rows if r['window']==window]
        result['windows'].append({'window':window,'candidate':part[0]['candidate'],'warmup':part[0]['warmup'],
            **stats(part),'newBlocks':part[-1]['scene']['sceneWarmCount']-part[0]['scene']['sceneWarmCount'],
            'force':part[-1]['scene']['sceneWarmForced']-part[0]['scene']['sceneWarmForced']})
    (folder/'comparison.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))

if __name__=='__main__':
    for name in sys.argv[1:]:analyze(name)
