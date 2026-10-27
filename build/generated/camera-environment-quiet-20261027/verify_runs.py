"""Verify native environment behavior, frozen inputs and full unfiltered clocks."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,statistics,math
HERE=Path(__file__).resolve().parent;MOD=HERE.parents[2];ROOT=MOD.parents[1];E=MOD/'knowledge/experiments/evidence'
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def load(p):
    s=importlib.util.spec_from_file_location('quiet_review_summary',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def metric(values):
    ordered=sorted(values);assert values and all(isinstance(v,int) and v>=0 for v in values)
    return dict(count=len(values),mean=statistics.mean(values),median=statistics.median(values),p95=ordered[math.ceil(.95*len(values))-1],maximum=max(values),
        over33=sum(v>33 for v in values),over50=sum(v>50 for v in values),over100=sum(v>100 for v in values))
def verify(name):
    folder=E/name;r=read(folder/'runner-inputs.json');b=read(folder/'probe-build.json');raw=read(folder/'storage/result.json');assert not (folder/'runner-failure.json').exists()
    assert len(r['baseline'])==526 and len(r['runtimeInputs'])==13 and len(b['frozenSourceSHA256'])==86
    for key in ['baseline','runtimeInputs']:
        for p,d in r[key].items():assert sha(ROOT/p)==d,(key,p)
    for key in ['runnerInputs','compilerInputs','fixtureInputs']:
        for p,d in r[key].items():assert sha(Path(p))==d,(key,p)
    for p,d in b['frozenSourceSHA256'].items():assert sha(Path(b['frozenSourcePath'])/p)==d
    for p,k in [('sourceOrigin','sourceOriginSHA256'),('configPath','configSHA256')]:assert sha(Path(b[p]))==b[k]
    assert sha(Path(b['probePath']))==b['probeSHA256']==r['probeSHA256']
    expected=r.get('expectedRuntime',r['baseline']);kind=r.get('hostVariant','base')
    differences=[k for k in expected if expected[k]!=r['baseline'][k]]
    assert differences==(['pfe.swf'] if kind=='cache' else [])
    actual={k.replace('\\','/'):v for k,v in read(folder/'inputs.json').items()}
    for p,d in expected.items():
        if p not in ['application.xml','mods/loader-manifest.txt']:assert actual[p]==d,p
    assert actual['mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf']==b['probeSHA256']
    if kind=='cache':
        candidate=r['candidateBuild'];assert candidate['candidate']==expected['pfe.swf'] and candidate['base']==r['baseline']['pfe.swf']
        assert candidate['audit']==sha(HERE.parent/'camera-environment-keycache-20261027/audit-proof.json')
    policy=read(folder/'process-policy.json');loader=read(folder/'loader-check.json')
    assert policy['desktopPolicy']=='private' and not policy['performanceEligible']
    assert not any(policy.get(k) for k in ['otherAirProcessIds','memoryAbort','runFailure'])
    assert len(loader['sessions'])==1 and all(loader['loaded'].values())
    assert r['memoryBeforeAir']['availableCommit']>=4*1024**3 and r['memoryBeforeAir']['availablePhysical']>=2*1024**3
    startup=r['startupResourcePolicies'];assert len(startup)==1 and startup[0]['pid']==policy['pid']
    applied=startup[0]['policy'];assert not applied['errors'] and not applied['after']['errors']
    assert applied['after']['cpuPriorityClass']==32 and applied['after']['memoryPriority']==5 and applied['after']['powerThrottling']['highQoS']
    summary=load(HERE/'summary.py').summarize(raw)
    summary.update(resultSHA256=sha(folder/'storage/result.json'),probeSHA256=b['probeSHA256'],inputsUnchanged=True)
    if 'expectedRuntime' in r:summary['hostSHA256']=expected['pfe.swf']
    else:summary['runtimeInputsUnchanged']=True
    assert summary==read(folder/'summary.json')
    checks=summary['environmentChecks'];assert checks['sceneLarge'] and checks['cachePresent']==(kind=='cache')
    moving=[v for w in raw['cameraRaster']['windows'] if w['condition']!=0 for v in w['framesMs']]
    static=[v for w in raw['cameraRaster']['windows'] if w['condition']==0 for v in w['framesMs']]
    return dict(name=name,kind=kind,pid=policy['pid'],probeSHA256=b['probeSHA256'],hostSHA256=expected['pfe.swf'],
        resultSHA256=sha(folder/'storage/result.json'),environmentCases=len(checks['cases']),environmentFieldsChecked=checks['fieldsChecked'],restored=True,
        moving=metric(moving),static=metric(static),arms=summary['arms']),raw
def main():
    p=argparse.ArgumentParser();p.add_argument('--names',nargs='+',required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args();assert not args.out.exists()
    results=[];raws=[]
    for name in args.names:
        rec,raw=verify(name);results.append(rec);raws.append(raw)
    assert len(set(r['probeSHA256'] for r in results))==1
    for raw in raws[1:]:
        for a,b in zip(raws[0]['cameraRaster']['windows'],raw['cameraRaster']['windows']):
            assert a['condition']==b['condition'] and a['cameraX']==b['cameraX'] and a['cameraY']==b['cameraY']
    grouped={}
    for kind in ['base','cache']:
        values=[v for rec,raw in zip(results,raws) if rec['kind']==kind for w in raw['cameraRaster']['windows'] if w['condition']!=0 for v in w['framesMs']]
        if values:grouped[kind]=metric(values)
    report=dict(verified=True,runs=results,moving=grouped,all960CameraCoordinatesMatch=True,deployed=False,
        limitation='All intervals retained; private-desktop camera diagnostics with live quiet simulation, not actual monitor FPS or combat acceptance. Random decorations, order and background load remain limitations.')
    if set(grouped)=={'base','cache'}:report['movingMeanChangePercent']=(grouped['cache']['mean']/grouped['base']['mean']-1)*100
    args.out.write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps(dict(verified=True,sha256=sha(args.out),moving=grouped,changePercent=report.get('movingMeanChangePercent'),environmentCases=[r['environmentCases'] for r in results])),flush=True)
if __name__=='__main__':main()
