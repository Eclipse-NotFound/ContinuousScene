from pathlib import Path
import json,statistics,sys
ROOT=Path(__file__).resolve().parents[5]
BASE=ROOT/'mods/ContinuousScene/knowledge/experiments/evidence'
for name in sys.argv[1:]:
    directory=BASE/name
    result=json.loads((directory/'storage/result.json').read_text('utf-8'))
    out={'analysisVersion':2,'run':name,'ok':result['ok'],'error':result.get('error'),'hidden':result.get('nativeHiddenActor'),'entry':{k:result.get('entry',{}).get(k) for k in ['units','scale','stageWidth','stageHeight']},'warmPasses':len(result.get('warm',[])),'blocks':[],'groups':{},'unitCensus':result.get('unitCensus'),'objectCensus':result.get('objectCensus'),'pixels':result.get('pixels')}
    grouped={}
    def stats(rows):
        values=sorted(x[1] for x in rows if x[1]>=0)
        if not values:return {}
        # Grouped modes are non-contiguous blocks. Never join their heaps across a gap.
        adjacent=[(a,b) for a,b in zip(rows,rows[1:]) if b[0]==a[0]+1 and b[1]>=0]
        drops=[(b[1],a[14]-b[14]) for a,b in adjacent if b[14]<a[14]-4*1024**2]
        growth=[b[14]-a[14] for a,b in adjacent if b[14]>=a[14]]
        return {'n':len(values),'mean':round(statistics.mean(values),3),'median':statistics.median(values),'p95':values[int(.95*(len(values)-1))],'p99':values[int(.99*(len(values)-1))],'max':values[-1],'over50':sum(x>50 for x in values),'over100':sum(x>100 for x in values),'prePostMean':round(statistics.mean(x[2] for x in rows if x[1]>=0),3),'memoryDrops':len(drops),'dropOver100':sum(dt>100 for dt,size in drops),'growthMiBPerPositiveInterval':round(statistics.mean(growth)/1024**2,3) if growth else None}
    for block in result.get('blocks',[]):
        if 'rows' not in block:continue
        key=block['settings']['mode']
        grouped.setdefault(key,[]).extend(block['rows'])
        change={k:block['endCounters'][k]-block['startCounters'][k] for k in ['sceneWarmCount','sceneRedraws','sceneMisses','sceneEvictions']}
        out['blocks'].append({'index':block['index'],**block['settings'],**stats(block['rows']),'worldChanges':change,'activity':block.get('activity')})
    out['groups']={k:stats(v) for k,v in grouped.items()}
    target=directory/'optimization-summary.json'
    target.write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps({k:v for k,v in out.items() if k not in ['blocks','objectCensus']},ensure_ascii=False))
    for i in range(0,len(out['blocks'])-1,2):
        a,b=out['blocks'][i:i+2]
        print(json.dumps({'pair':i//2,'axis':a['axis'],'mode':b['mode'],'mean':[a['mean'],b['mean']],'p95':[a['p95'],b['p95']],'over100':[a['over100'],b['over100']],'warm':[a['worldChanges'],b['worldChanges']]},ensure_ascii=False))
