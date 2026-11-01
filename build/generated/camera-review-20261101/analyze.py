from pathlib import Path
import json, statistics, sys
ROOT=Path(__file__).resolve().parents[5]
EVIDENCE=ROOT/'mods/ContinuousScene/knowledge/experiments/evidence'

def summary(name):
    file=EVIDENCE/name/'storage/result.json'
    r=json.loads(file.read_text('utf-8'))
    out={'run':name,'ok':r['ok'],'error':r.get('error'),'entry':{k:r.get('entry',{}).get(k) for k in ('x','y','width','height','units','stageWidth','stageHeight','scale','quality')},'menuBefore':r.get('menuBefore'),'menuAfter':r.get('menuAfter'),'nativeHiddenActor':r.get('nativeHiddenActor'),'blocks':[]}
    for b in r.get('blocks',[]):
        rows=b.get('rows',[]);valid=[x for x in rows if x[1]>=0];dt=sorted(x[1] for x in valid)
        if not dt:continue
        start,end=b['startCounters'],b['endCounters']
        out['blocks'].append({'index':b['index'],**b['settings'],'n':len(dt),'mean':round(statistics.mean(dt),3),'p95':dt[int(.95*(len(dt)-1))],'max':max(dt),'over50':sum(x>50 for x in dt),'over100':sum(x>100 for x in dt),'prePost':round(statistics.mean(x[2] for x in valid),3),'probePeak':max(x[13] for x in rows),'visualRangeX':max(x[5] for x in rows)-min(x[5] for x in rows),'visualRangeY':max(x[6] for x in rows)-min(x[6] for x in rows),'playerRangeX':max(x[7] for x in rows)-min(x[7] for x in rows),'playerRangeY':max(x[8] for x in rows)-min(x[8] for x in rows),'outsidePlayer':sum(not(0<=x[11]<r['entry']['stageWidth'] and 0<=x[12]<r['entry']['stageHeight']) for x in rows),'counterDeltas':{k:end[k]-start[k] for k in start}})
    target=EVIDENCE/name/'review-summary.json'
    if not target.exists():target.write_text(json.dumps(out,indent=2),'utf-8')
    print(json.dumps({k:v for k,v in out.items() if k!='blocks'},ensure_ascii=False))
    for b in out['blocks']:print(json.dumps(b,ensure_ascii=False))
    return out

if __name__=='__main__':
    for n in sys.argv[1:]:summary(n)
