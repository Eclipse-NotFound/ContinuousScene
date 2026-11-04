"""Recalculate run-03 observations without treating frames as independent trials."""
from pathlib import Path
import argparse, json, math, statistics

DEFAULT = Path('D:/活/AI/测试运行/remains-proof-strategy-20261104/run-03')

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def distribution(values):
    values = sorted(values)
    if not values:
        return None
    return {'n':len(values), 'mean':statistics.mean(values), 'min':values[0],
            'median':statistics.median(values),
            'p95':values[max(0,math.ceil(.95*len(values))-1)],
            'p99':values[max(0,math.ceil(.99*len(values))-1)], 'max':values[-1]}

def trial(path):
    result = read(path/'ProofActivity.json')
    meta = read(path/'meta.json')
    validity = read(path/'validity.json') if (path/'validity.json').exists() else {}
    rows = result['samples']
    if not rows:
        return {'name':path.name,'ok':False,'error':result.get('error'),'frames':0}
    frame = [r[0] for r in rows]
    elapsed = sum(frame)/1000
    objects = result['objects']
    loader=result.get('loader',{})
    init_order=[name for _,name in sorted((int(value.rsplit('@',1)[-1]),key[3:]) for key,value in loader.items() if key.startswith('ok_'))]
    local = distribution([r[1] for r in rows])
    local['totalMsFromProduct'] = result['activity'].get('totalMs')
    local['sumFrameObservations'] = sum(r[1] for r in rows)
    local['allCallsOnePerFrame'] = all(r[4]==1 for r in rows)
    return {'name':path.name,'ok':result['ok'],'error':result.get('error'),
            'scenario':result['config']['scenario'],'arm':result['config']['arm'],
            'diagnostic':result['config']['diagnostic'],'productSha256':meta['productSha256'],
            'probeSha256':meta['probeSha256'],'registration':meta['registration'],
            'initOrder':init_order,
            'frames':len(rows),'elapsedSeconds':elapsed,'frameMs':distribution(frame),
            'activityMs':local,'over50PerMinute':sum(x>50 for x in frame)*60/elapsed,
            'over100PerMinute':sum(x>100 for x in frame)*60/elapsed,
            'q':distribution([r[2] for r in rows]),'q0Fraction':sum(r[2]==0 for r in rows)/len(rows),
            'builds':sum(r[3] for r in rows),'calls':sum(r[4] for r in rows),
            'N':distribution([r['N'] for r in objects]),'T':distribution([r['T'] for r in objects]),
            'units':distribution([r['units'] for r in objects]),
            'awake':distribution([r[5] for r in rows]),'asleep':distribution([r[6] for r in rows]),
            'leashed':distribution([r[7] for r in rows]),'shots':result['shots'],
            'damageEvents':result['damageEvents'],'maxMove':result['maxMove'],'maxAim':result['maxAim'],
            'netMemoryChange':result['memoryAfter']-result['memoryBefore'],
            'initial':result['initial'],'checks':result['checks'],'activity':result['activity'],
            'measuredInitial':result.get('measuredInitial'),
            'validity':validity,'metaFailure':meta['failure']}

def pair(record, trials):
    names = [r['name'] for r in record.get('runs',[])]
    reasons = []
    if len(names)!=2 or not record.get('completed'):
        return {'name':record['name'],'valid':False,'reasons':[record.get('error','Pair incomplete')], 'runs':names}
    x,y = [trials[name] for name in names]
    if record['order']=='BA':
        a,b=y,x
    else:
        a,b=x,y
    for r in [a,b]:
        if not r['ok']:reasons.append(r['name']+': behavior invalid')
        if not r['validity'].get('environment',{}).get('performanceEligible'):
            reasons.append(r['name']+': environment invalid')
        if not r['activityMs']['allCallsOnePerFrame']:reasons.append(r['name']+': call/frame mismatch')
        if not any(c['name']=='main-menu-display-detached' and c['ok'] for c in r['checks']):
            reasons.append(r['name']+': main menu display detachment not checked')
    if a['probeSha256']!=b['probeSha256']:reasons.append('Probe bytes differ')
    if a['initOrder']!=b['initOrder']:reasons.append('Asynchronous module initialization order differs')
    if a['frames']!=b['frames']:reasons.append('Frame window differs')
    for field in ['land','stage','seed','limX','limY','width','height','frameRate','quality','scaleV','csVersion','units']:
        if a['initial'][field]!=b['initial'][field]:reasons.append('Initial '+field+' differs')
    if a.get('measuredInitial')!=b.get('measuredInitial') or a.get('measuredInitial') is None:
        reasons.append('Measured-start world state differs or was not captured')
    workload = {}
    for key in ['q','N','T','units']:
        aa,bb=a[key]['mean'],b[key]['mean']
        relative=abs(bb-aa)/max(abs(aa),abs(bb),1)
        workload[key]={'a':aa,'b':bb,'relativeDifference':relative}
        if relative>.05:reasons.append(key+' workload differs >5%')
    if abs(a['shots']-b['shots'])/max(a['shots'],b['shots'],1)>.02:reasons.append('Shots differ >2%')
    def difference(aa,bb):
        return {'a':aa,'b':bb,'bMinusA':bb-aa,'percent':100*(bb-aa)/aa if aa else None}
    deltas = {}
    for metric in ['activityMs','frameMs']:
        deltas[metric]={key:difference(a[metric][key],b[metric][key]) for key in ['mean','median','p95','p99','max']}
    for metric in ['over50PerMinute','over100PerMinute']:
        deltas[metric]=difference(a[metric],b[metric])
    return {'name':record['name'],'scenario':record['scenario'],'order':record['order'],
            'valid':not reasons,'reasons':reasons,'a':a['name'],'b':b['name'],
            'sameProductBytes':a['productSha256']==b['productSha256'],
            'workload':workload,'differences':deltas}

def analyze(root):
    trials={}
    for path in sorted((root/'data').iterdir()):
        if (path/'ProofActivity.json').exists():
            trials[path.name]=trial(path)
        elif (path/'meta.json').exists():
            meta=read(path/'meta.json')
            trials[path.name]={'name':path.name,'ok':False,'frames':0,'error':meta.get('failure') or 'Process exited without result JSON',
                               'exitCode':meta.get('exitCode'),'meta':meta}
        else:
            trials[path.name]={'name':path.name,'ok':False,'frames':0,'error':'No game result; reservation/preflight only',
                               'environmentBefore':read(path/'environment-before.json') if (path/'environment-before.json').exists() else None}
    pairs=[pair(read(p),trials) for p in sorted((root/'pairs').glob('*.json'))] if (root/'pairs').exists() else []
    return {'method':'Each pair is one repeat; nearest-rank p95/p99; negative B-A means lower time. No frame-level confidence interval.',
            'trials':trials,'pairs':pairs}

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=DEFAULT)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    result=analyze(args.root)
    if args.output:args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'trials':[{k:r.get(k) for k in ['name','ok','frames','elapsedSeconds','q0Fraction','builds','shots','error']} for r in result['trials'].values()], 'pairs':result['pairs']},ensure_ascii=False,indent=2))
