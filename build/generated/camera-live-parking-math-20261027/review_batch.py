"""Independently preserve compile/runtime failures and validate successful timing."""
from pathlib import Path
import hashlib,importlib.util,json,sys
HERE=Path(__file__).resolve().parent;MOD=HERE.parents[2];ROOT=MOD.parents[1]
E=MOD/'knowledge/experiments/evidence'
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def inputs(rec):
    assert len(rec['baseline'])==526 and len(rec['runtimeInputs'])==13
    for group in ['baseline','runtimeInputs']:
        for name,digest in rec[group].items():assert sha(ROOT/name)==digest,(group,name)
    for group in ['runnerInputs','compilerInputs','fixtureInputs']:
        for name,digest in rec[group].items():assert sha(Path(name))==digest,(group,name)
def review(name):
    folder=E/name;recipe=MOD/'build/generated'/name.rsplit('-r',1)[0]
    if not (folder/'runner-inputs.json').exists():
        rec=read(folder/'runner-failure.json');inputs(rec)
        origins=list((recipe/'source-staging').glob('*/source-origin.json'));assert len(origins)==1
        origin=read(origins[0]);staged=origins[0].parent/'src'
        assert len(origin['stagedSHA256'])==86
        for path,digest in origin['stagedSHA256'].items():assert sha(staged/path)==digest,path
        frozen=list((recipe/'probe-builds/probe-source').glob('*/src'));assert len(frozen)==1
        for path,digest in origin['stagedSHA256'].items():assert sha(frozen[0]/path)==digest,path
        logs=list((recipe/'probe-builds/probe-source').glob('*/compile.log'));assert len(logs)==1
        assert '函数没有返回值' in logs[0].read_text('utf-8-sig')
        assert not list((recipe/'probe-builds/probe-source').glob('*/probe-build.json'))
        return dict(name=name,inputIntegrity=True,formalFiles=526,runtimeFiles=13,sourceFiles=86,
            outcome='compile-failed',error=rec['error'],compileLogSHA256=sha(logs[0]),launchedAir=False,deployed=False)
    rec=read(folder/'runner-inputs.json');inputs(rec)
    build=read(folder/'probe-build.json');src=Path(build['frozenSourcePath'])
    assert len(build['frozenSourceSHA256'])==86
    for p,d in build['frozenSourceSHA256'].items():assert sha(src/p)==d,p
    assert sha(Path(build['probePath']))==rec['probeSHA256']==build['probeSHA256']
    for p,d in [('sourceOrigin','sourceOriginSHA256'),('configPath','configSHA256')]:assert sha(Path(build[p]))==build[d]
    actual={k.replace('\\','/'):v for k,v in read(folder/'inputs.json').items()}
    for p,d in rec['baseline'].items():
        if p not in ('application.xml','mods/loader-manifest.txt'):assert actual[p]==d,p
    assert actual['mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf']==build['probeSHA256']
    policy=read(folder/'process-policy.json');assert policy['desktopPolicy']=='private' and not policy['performanceEligible']
    assert not policy.get('otherAirProcessIds')
    assert rec['memoryBeforeAir']['availableCommit']>=4*1024**3 and rec['memoryBeforeAir']['availablePhysical']>=2*1024**3
    samples=policy['ownedProcessCpuSamples'];gaps=[]
    for a,b in zip(samples,samples[1:]):
        dt=b['elapsed']-a['elapsed']
        if dt>10:gaps.append(dict(gapSeconds=dt,cpuMs=(b['kernelMs']+b['userMs'])-(a['kernelMs']+a['userMs'])))
    out=dict(name=name,inputIntegrity=True,formalFiles=526,runtimeFiles=13,sourceFiles=86,
        probeSHA256=build['probeSHA256'],frozenSource=src.parent.name,pid=policy['pid'],appId=policy['appId'],
        monitorGaps=gaps,deployed=False,gameplayAccepted=False)
    if not (folder/'storage/result.json').exists():
        failure=read(folder/'runner-failure.json');assert policy['runFailure']
        if policy.get('memoryAbort'):
            assert 'Memory pressure' in failure['error'] and policy['memoryAbort']['availableCommit']<512*1024**2
            kind='memory-abort-no-result'
        else:
            assert 'TimeoutError' in failure['error'];kind='timed-out-no-result'
        out.update(outcome=kind,error=failure['error'],heartbeat=read(folder/'storage/heartbeat.json'),cleanupVerified=False,memoryBefore=policy['memoryBefore'],memoryAbort=policy.get('memoryAbort'))
        return out
    raw=read(folder/'storage/result.json');loader=read(folder/'loader-check.json')
    assert len(loader['sessions'])==1 and all(loader['loaded'].values()) and not policy.get('runFailure')
    t=raw['farParking'];clean=raw['farParkingCleanup']
    out.update(outcome='completed' if raw['ok'] else 'runtime-failed',rawOK=raw['ok'],error=raw['error'],
        resultSHA256=sha(folder/'storage/result.json'),parking=t,cleanup=clean,samples=len(raw['samples']),
        nativeWindowEvents=raw.get('nativeWindowEvents'),nativeWindowRestored=raw.get('nativeWindowRestored'))
    if raw['ok']:
        if 'math-' in t['version']:
            assert all(t[k]['passed'] and t[k]['checks']>0 and t[k]['maxError']<0.00001 for k in ['boundsAuditParked','boundsAuditNative'])
        spec=importlib.util.spec_from_file_location('parking_independent',HERE.parent/'camera-live-parking-return-20261027/verify_run.py')
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        independent=m.review(name);out.update(arms=independent['arms'],pairs=independent['pairs'],rows=independent['rows'],frames=independent['frames'],elapsedMs=independent['elapsedMs'],verification=independent['verification'])
        assert raw['nativeWindowRestored'] and not [x for x in raw['nativeWindowEvents'] if x['phase']==4]
    return out
if __name__=='__main__':
    for name in sys.argv[1:]:
        result=review(name);out=HERE/(name+'-review.json');assert not out.exists()
        out.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
        print(json.dumps({k:v for k,v in result.items() if k not in ['rows','parking','verification']},ensure_ascii=False))
