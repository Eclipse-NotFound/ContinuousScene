"""Retain successful and failed probes; independently verify exact input closure."""
from pathlib import Path
import hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent;MOD=HERE.parents[2];ROOT=MOD.parents[1]
SPECS=[('camera-persistent-repeated-20261027',86,True),('camera-persistent-jump-20261027',86,False),
       ('camera-persistent-jump-steer-20261027',86,False),('camera-persistent-pagesize-20261027',89,True),
       ('camera-persistent-readers-20261027',92,True)]
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def verify(name,count,passed):
    folder=MOD/'knowledge/experiments/evidence'/(name+'-r1');recipe=HERE.parent/name
    r=read(folder/'runner-inputs.json');b=read(folder/'probe-build.json');raw=read(folder/'storage/result.json')
    assert len(r['baseline'])==526 and len(r['runtimeInputs'])==13
    for key in ['baseline','runtimeInputs']:
        for p,d in r[key].items():assert sha(ROOT/p)==d,p
    for key in ['runnerInputs','fixtureInputs','compilerInputs']:
        for p,d in r[key].items():assert sha(Path(p))==d,p
    assert len(b['frozenSourceSHA256'])==count
    for p,d in b['frozenSourceSHA256'].items():assert sha(Path(b['frozenSourcePath'])/p)==d,p
    assert sha(Path(b['probePath']))==b['probeSHA256']==r['probeSHA256']
    for p,k in [('sourceOrigin','sourceOriginSHA256'),('configPath','configSHA256')]:assert sha(Path(b[p]))==b[k]
    actual={p.replace('\\','/'):d for p,d in read(folder/'inputs.json').items()}
    for p,d in r['baseline'].items():
        if p not in ['application.xml','mods/loader-manifest.txt']:assert actual[p]==d,p
    assert actual['mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf']==b['probeSHA256']
    policy=read(folder/'process-policy.json');loader=read(folder/'loader-check.json')
    assert policy['desktopPolicy']=='private' and not policy['performanceEligible']
    assert not any(policy.get(k) for k in ['otherAirProcessIds','memoryAbort','runFailure'])
    assert len(loader['sessions'])==1 and all(loader['loaded'].values())
    assert r['memoryBeforeAir']['availableCommit']>=4*1024**3 and r['memoryBeforeAir']['availablePhysical']>=2*1024**3
    result=dict(name=name,sourceCount=count,inputClosurePassed=True,originalRunPassed=passed,
        frozen=Path(b['frozenSourcePath']).parent.name,probeSHA256=b['probeSHA256'],resultSHA256=sha(folder/'storage/result.json'),pid=policy['pid'])
    if passed:
        assert not (folder/'runner-failure.json').exists()
        sp=importlib.util.spec_from_file_location('independent_'+name.replace('-','_'),recipe/'summary.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
        summary=m.summarize(raw);summary.update(resultSHA256=result['resultSHA256'],probeSHA256=b['probeSHA256'],inputsUnchanged=True,runtimeInputsUnchanged=True)
        assert summary==read(folder/'summary.json'),'Recorded summary differs from exact replay'
        result['summary']=summary
    else:
        assert not raw['ok'] and 'Native input left the verified full platform' in raw['error']
        failed=read(folder/'runner-failure.json');assert not failed['complete'] and not (folder/'summary.json').exists()
        result.update(failurePreserved=True,completedWindows=len(raw['samples']),error=raw['error'],measurementAccepted=False)
    return result
def main():
    out=HERE/'batch-review.json';assert not out.exists(),'Preserve prior audit'
    rows=[verify(*spec) for spec in SPECS]
    out.write_text(json.dumps(dict(rows=rows,deployed=False,goalComplete=False),ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps(dict(sha256=sha(out),runs=[{k:r[k] for k in ['name','sourceCount','originalRunPassed','pid','probeSHA256','resultSHA256']} for r in rows]),ensure_ascii=False))
if __name__=='__main__':main()
