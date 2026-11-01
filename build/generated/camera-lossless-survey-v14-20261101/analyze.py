"""Summarize complete blocks; never convert a failed/partial run into a pass."""
from pathlib import Path
import argparse,collections,hashlib,json,statistics
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def metrics(rows):
    values=[r[1] for r in rows if r[1]>=0]
    ordered=sorted(values)
    if not values:return {'n':0}
    return {'n':len(values),'mean':statistics.mean(values),'p50':statistics.median(values),
            'p95':ordered[int(.95*(len(values)-1))],'p99':ordered[int(.99*(len(values)-1))],
            'max':max(values),'over100':sum(x>100 for x in values),
            'updateBandMean':statistics.mean(r[2] for r in rows if r[1]>=0),
            'tdfcMean':statistics.mean(r[15] for r in rows if r[1]>=0) if rows and len(rows[0])>15 else None,
            'reuseMean':statistics.mean(r[18] for r in rows if r[1]>=0) if rows and len(rows[0])>18 else None}
def main():
    p=argparse.ArgumentParser();p.add_argument('name');a=p.parse_args()
    folder=ROOT/'mods/ContinuousScene/knowledge/experiments/evidence'/a.name
    result=json.loads((folder/'storage/result.json').read_text('utf-8-sig'))
    policy=json.loads((folder/'process-policy.json').read_text('utf-8-sig'))
    out={'name':a.name,'ok':result['ok'],'error':result.get('error'),
         'diagnosticOnly':True,'policyPerformanceEligible':policy['performanceEligible'],
         'assertions':len(result['assertions']),'failedChecks':[c for c in result['assertions'] if not c['ok']],
         'runFailure':policy.get('runFailure'),'otherAIR':policy.get('otherAirProcessIds'),
         'blocks':[],'aggregate':{},'byAxis':{},'inputs':{}}
    for name in ('storage/result.json','process-policy.json','review-inputs.json','loader-check.json','inputs.json'):
        if (folder/name).is_file():out['inputs'][name]=sha(folder/name)
    combined=collections.defaultdict(list);axes=collections.defaultdict(lambda:collections.defaultdict(list))
    for block in result['blocks']:
        rows=block.get('rows',[]);settings=block['settings'];complete=len(rows)==settings['frames']
        delta={k:block.get('endCounters',{}).get(k,0)-v for k,v in block['startCounters'].items()}
        item={'settings':settings,'complete':complete,'delta':delta,'metrics':metrics(rows)}
        if rows:
            # Do not bridge separate blocks to count heap drops.
            item['heapDropsOver4MiB']=sum(b[14]<a[14]-4*1024**2 for a,b in zip(rows,rows[1:]))
        for key in ('tdfc','fill','gc'):
            if key in block:item[key]=block[key]
        if 'gc' in block and rows:
            item['lastFrameProbePostMs']=rows[-1][13]
        out['blocks'].append(item)
        if complete:
            combined[settings['mode']].extend(rows);axes[settings['axis']][settings['mode']].extend(rows)
    out['aggregate']={mode:metrics(rows) for mode,rows in combined.items()}
    out['byAxis']={axis:{mode:metrics(rows) for mode,rows in modes.items()} for axis,modes in axes.items()}
    out['functionalOnly']={k:result.get(k) for k in ('snapshotChecks','environmentSurvey','auxiliarySurvey','pixels') if k in result}
    with (folder/'analysis.json').open('x',encoding='utf-8') as f:json.dump(out,f,ensure_ascii=False,indent=2)
    print(json.dumps({k:out[k] for k in ('name','ok','error','assertions','runFailure','aggregate','byAxis')},ensure_ascii=False))
if __name__=='__main__':main()
