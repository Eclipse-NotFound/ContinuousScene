"""Independent host-variant closure and allocation-count reconstruction."""
from pathlib import Path
import argparse,collections,importlib.util,json,hashlib
HERE=Path(__file__).resolve().parent;MOD=HERE.parents[2];ROOT=MOD.parents[1];E=MOD/'knowledge/experiments/evidence'
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def load(p):
    sp=importlib.util.spec_from_file_location('clamp_allocation_summary',p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
def totals(raw):
    groups={}
    for w in raw['cameraRaster']['cpuSampling']['windows']:
        counts=collections.Counter()
        for row in w['newObjectStacks']:
            names=row['names'];n=row['samples'];assert isinstance(n,int) and n>0
            counts[names[0] or '<anonymous>' if names else '<empty-stack>']+=n
        assert dict(counts)=={r['name']:r['samples'] for r in w['newObjectTop']}
        assert sum(counts.values())==w['counts']['newObject']
        groups.setdefault(w['name'],collections.Counter()).update(counts)
    return groups
def main():
    p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args();assert not args.out.exists()
    folder=E/args.name;r=read(folder/'runner-inputs.json');probe=read(folder/'probe-build.json');raw=read(folder/'storage/result.json')
    assert not (folder/'runner-failure.json').exists()
    for key in ['baseline','runtimeInputs']:
        for path,digest in r[key].items():assert sha(ROOT/path)==digest,(key,path)
    for key in ['runnerInputs','compilerInputs','fixtureInputs']:
        for path,digest in r[key].items():assert sha(Path(path))==digest,(key,path)
    assert len(r['baseline'])==526 and len(r['runtimeInputs'])==13 and len(probe['frozenSourceSHA256'])==87
    for path,digest in probe['frozenSourceSHA256'].items():assert sha(Path(probe['frozenSourcePath'])/path)==digest
    for path,key in [('sourceOrigin','sourceOriginSHA256'),('configPath','configSHA256')]:assert sha(Path(probe[path]))==probe[key]
    assert sha(Path(probe['probePath']))==probe['probeSHA256']==r['probeSHA256']
    actual={k.replace('\\','/'):v for k,v in read(folder/'inputs.json').items()}
    expected=r['expectedRuntime'];assert set(expected)==set(r['baseline'])
    changes=[k for k in expected if expected[k]!=r['baseline'][k]]
    assert changes==(['pfe.swf'] if r['hostVariant']=='clamp' else [])
    for path,digest in expected.items():
        if path not in ['application.xml','mods/loader-manifest.txt']:assert actual[path]==digest,path
    assert actual['mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf']==probe['probeSHA256']
    policy=read(folder/'process-policy.json');loader=read(folder/'loader-check.json')
    assert policy['desktopPolicy']=='private' and not policy['performanceEligible']
    assert not any(policy.get(k) for k in ['otherAirProcessIds','memoryAbort','runFailure'])
    assert len(loader['sessions'])==1 and all(loader['loaded'].values())
    assert r['memoryBeforeAir']['availableCommit']>=4*1024**3 and r['memoryBeforeAir']['availablePhysical']>=2*1024**3
    policies=r['startupResourcePolicies'];assert len(policies)==1 and policies[0]['pid']==policy['pid']
    applied=policies[0]['policy'];assert not applied['errors'] and not applied['after']['errors']
    assert applied['after']['cpuPriorityClass']==32 and applied['after']['memoryPriority']==5 and applied['after']['powerThrottling']['highQoS']
    recipe=HERE.parent/'camera-visible-allocation-stacks-20261027'
    summary=load(recipe/'summary.py').summarize(raw)
    summary.update(resultSHA256=sha(folder/'storage/result.json'),probeSHA256=probe['probeSHA256'],hostSHA256=expected['pfe.swf'],inputsUnchanged=True)
    assert summary==read(folder/'summary.json')
    baseline=E/'camera-visible-allocation-stacks-20261027-scene-r1'
    prior=read(baseline/'storage/result.json');review=read(recipe/'scene-review.json')
    assert sha(baseline/'storage/result.json')==review['run']['resultSHA256']
    assert probe['probeSHA256']==review['run']['probeSHA256']
    before,after=totals(prior),totals(raw)
    for a,b in zip(prior['cameraRaster']['windows'],raw['cameraRaster']['windows']):
        assert a['cameraX']==b['cameraX'] and a['cameraY']==b['cameraY'] and a['condition']==b['condition']
    comparison={k:dict(beforeNew=sum(before[k].values()),afterNew=sum(v.values()),
        beforeEnvironment=before[k]['fe.graph::Grafon/sceneNativeEnvironment'],afterEnvironment=v['fe.graph::Grafon/sceneNativeEnvironment'],
        afterTop=v.most_common(12)) for k,v in after.items()}
    result=dict(verified=True,name=args.name,pid=policy['pid'],hostSHA256=expected['pfe.swf'],
        probeSHA256=probe['probeSHA256'],resultSHA256=sha(folder/'storage/result.json'),
        all960CameraCoordinatesMatch=True,allocationComparison=comparison,deployed=False,performanceAcceptance=False,
        boundary='Same test program and camera route; random decorations and allocation observation still affect workload. Counts are not invocation counts, durations, byte volumes or frame-rate acceptance.')
    args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps(dict(verified=True,sha256=sha(args.out),comparison=comparison)),flush=True)
if __name__=='__main__':main()
