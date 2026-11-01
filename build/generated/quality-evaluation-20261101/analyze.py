from pathlib import Path
import argparse, collections, hashlib, json, statistics

ROOT=Path(__file__).resolve().parents[5]
BASE=ROOT/'mods/ContinuousScene/knowledge/experiments/evidence'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def metrics(rows):
    rows=[r for r in rows if r[1]>=0]
    if not rows:return {'n':0}
    a=sorted(r[1] for r in rows)
    return dict(n=len(a),mean=statistics.mean(a),median=statistics.median(a),p95=a[int(.95*(len(a)-1))],
        p99=a[int(.99*(len(a)-1))],max=max(a),over50=sum(v>50 for v in a),over100=sum(v>100 for v in a),
        updateBand=statistics.mean(r[2] for r in rows),probePost=statistics.mean(r[13] for r in rows))
def analyze(name):
    folder=BASE/name
    raw=folder/'storage/result.json'
    policy=json.loads((folder/'process-policy.json').read_text('utf-8-sig'))
    if not raw.exists():
        return {'name':name,'ok':False,'error':policy.get('runFailure'),'noFinalResult':True}
    d=json.loads(raw.read_text('utf-8-sig'))
    axes=collections.defaultdict(lambda:collections.defaultdict(list))
    blocks=[]
    for b in d.get('blocks',[]):
        s=b['settings'];rows=b.get('rows',[])
        complete=len(rows)==s['frames']
        row={'settings':s,'complete':complete,'metrics':metrics(rows),
             'counters':{k:b.get('endCounters',{}).get(k,0)-v for k,v in b['startCounters'].items()},
             'quality':b.get('quality')}
        start=b.get('combatStart');end=b.get('combatEnd')
        if start and end:
            row['combat']={k:end[k]-start[k] for k in ['actualShotFrames','shots','movingFrames','targetFrames']}
            row['combat']['aliveStart']=start['alive'];row['combat']['aliveEnd']=end['alive']
            row['combat']['targetingEnd']=end['targeting']
        if 'fill' in b and 'presenterStart' in b:
            row['presenter']={k:b['fill'][k]-b['presenterStart'][k] for k in ['captures','drawMs','restored']}
        if complete:axes[s['axis']][s['mode']].extend(rows)
        blocks.append(row)
    result={'name':name,'ok':d['ok'],'error':d.get('error'),'rawSHA256':sha(raw),
        'diagnosticOnly':True,'legacyPerformanceEligible':policy['performanceEligible'],
        'environment':{k:policy.get(k) for k in ['otherAirProcessIds','runFailure','minimumAvailableCommit']},
        'assertions':len(d['assertions']),'failedChecks':[c for c in d['assertions'] if not c['ok']],
        'entry':{k:d.get('entry',{}).get(k) for k in ['units','scale','stageWidth','stageHeight','x','y']},
        'qualityCapability':d.get('qualityCapability'),'qualityRestored':d.get('qualityRestored'),
        'nativeRepeat':d.get('nativeRepeat'),'pixels':d.get('pixels'),
        'byAxis':{axis:{mode:metrics(rows) for mode,rows in modes.items()} for axis,modes in axes.items()},'blocks':blocks}
    with (folder/'quality-analysis.json').open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('name');a=p.parse_args();d=analyze(a.name)
    print(json.dumps({k:v for k,v in d.items() if k not in ['blocks','pixels','failedChecks']},ensure_ascii=False))
    print(json.dumps({'blocks':[{k:b.get(k) for k in ['settings','metrics','combat','presenter','counters']} for b in d.get('blocks',[])]},ensure_ascii=False))
