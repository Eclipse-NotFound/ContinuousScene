"""Independent closure and exact-summary replay for the repeated combat run."""
from pathlib import Path
import hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent;MOD=HERE.parents[2];ROOT=MOD.parents[1]
F=MOD/'knowledge/experiments/evidence/camera-persistent-repeated-20261027-r1'
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def verify(folder,recipe):
    r=read(folder/'runner-inputs.json');b=read(folder/'probe-build.json');raw=read(folder/'storage/result.json')
    assert not (folder/'runner-failure.json').exists()
    assert len(r['baseline'])==526 and len(r['runtimeInputs'])==13
    for key in ['baseline','runtimeInputs']:
        for p,d in r[key].items():assert sha(ROOT/p)==d,p
    for key in ['runnerInputs','fixtureInputs','compilerInputs']:
        for p,d in r[key].items():assert sha(Path(p))==d,p
    assert len(b['frozenSourceSHA256'])==86
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
    sp=importlib.util.spec_from_file_location('persistent_combat_independent_summary',recipe/'summary.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
    summary=m.summarize(raw)
    summary.update(resultSHA256=sha(folder/'storage/result.json'),probeSHA256=b['probeSHA256'],inputsUnchanged=True,runtimeInputsUnchanged=True)
    assert summary==read(folder/'summary.json'),'Recorded summary differs from exact replay'
    return dict(checksPassed=True,sourceCount=86,frozen=Path(b['frozenSourcePath']).parent.name,
        probeSHA256=b['probeSHA256'],resultSHA256=sha(folder/'storage/result.json'),pid=policy['pid'],
        summary=summary,deployed=False,gameplayAcceptance=False)
def main():
    result=verify(F,HERE);out=HERE/'review.json';assert not out.exists(),'Preserve previous audit'
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps(dict(sha256=sha(out),checksPassed=True,probeSHA256=result['probeSHA256'],
        resultSHA256=result['resultSHA256'],pid=result['pid'],grouped=result['summary']['grouped']),ensure_ascii=False))
if __name__=='__main__':main()
