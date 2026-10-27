"""Validate immutable input closure and full clocks, including the rejected site."""
from pathlib import Path
import hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent;MOD=HERE.parents[2];ROOT=MOD.parents[1];E=MOD/'knowledge/experiments/evidence'
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def load(name,p):
    sp=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
def verify(name,recipe,failed=False,source_count=86):
    folder=E/name;r=read(folder/'runner-inputs.json');b=read(folder/'probe-build.json');raw=read(folder/'storage/result.json')
    assert len(r['baseline'])==526 and len(r['runtimeInputs'])==13
    for key in ['baseline','runtimeInputs']:
        for p,d in r[key].items():assert sha(ROOT/p)==d,(name,p)
    for key in ['runnerInputs','fixtureInputs','compilerInputs']:
        for p,d in r[key].items():assert sha(Path(p))==d,(name,p)
    assert len(b['frozenSourceSHA256'])==source_count
    for p,d in b['frozenSourceSHA256'].items():assert sha(Path(b['frozenSourcePath'])/p)==d,(name,p)
    assert sha(Path(b['probePath']))==b['probeSHA256']==r['probeSHA256']
    for p,k in [('sourceOrigin','sourceOriginSHA256'),('configPath','configSHA256')]:assert sha(Path(b[p]))==b[k]
    actual={p.replace('\\','/'):d for p,d in read(folder/'inputs.json').items()}
    for p,d in r['baseline'].items():
        if p not in ['application.xml','mods/loader-manifest.txt']:assert actual[p]==d,(name,p)
    assert actual['mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf']==b['probeSHA256']
    policy=read(folder/'process-policy.json');loader=read(folder/'loader-check.json')
    assert policy['desktopPolicy']=='private' and not policy['performanceEligible']
    assert not any(policy.get(k) for k in ['otherAirProcessIds','memoryAbort','runFailure'])
    assert len(loader['sessions'])==1 and all(loader['loaded'].values())
    assert r['memoryBeforeAir']['availableCommit']>=4*1024**3 and r['memoryBeforeAir']['availablePhysical']>=2*1024**3
    if failed:
        assert (folder/'runner-failure.json').exists() and not raw['ok']
        assert not raw['cameraRaster']['windows'] and raw['cameraRaster']['errors']==['No verified visible reference platform in room 2,3']
        summary=None
    else:
        assert not (folder/'runner-failure.json').exists()
        summary=load(name,recipe/'summary.py').summarize(raw)
        summary.update(resultSHA256=sha(folder/'storage/result.json'),probeSHA256=b['probeSHA256'],inputsUnchanged=True,runtimeInputsUnchanged=True)
        assert summary==read(folder/'summary.json')
    return dict(name=name,originalRunPassed=not failed,closureVerified=True,probeSHA256=b['probeSHA256'],
        resultSHA256=sha(folder/'storage/result.json'),frozen=Path(b['frozenSourcePath']).parent.name,pid=policy['pid'],
        sourceCount=source_count,summary=summary,rawErrors=raw['cameraRaster']['errors']),raw
def main():
    result=dict(runs=[],deployed=False,gameplayAcceptance=False)
    old=HERE.parent/'camera-visible-room-reference-20261027'
    rec,_=verify(old.name+'-normal-r1',old,True);result['runs'].append(rec)
    raws={}
    for mode in ['scene','normal']:
        rec,raw=verify(HERE.name+'-'+mode+'-r1',HERE);result['runs'].append(rec);raws[mode]=raw
    a=raws['normal']['cameraRaster'];b=raws['scene']['cameraRaster'];sa=a['referenceSite'];sb=b['referenceSite']
    assert sa['tileHash']==sb['tileHash']==3026506315
    assert sa['roomX']==sb['roomX']==sa['roomY']==sb['roomY']==3
    assert result['runs'][1]['probeSHA256']==result['runs'][2]['probeSHA256']
    for x,y in zip(a['windows'],b['windows']):
        assert x['condition']==y['condition'] and len(x['vx'])==len(y['vx'])==120
        assert [v-5760 for v in y['cameraX']]==x['cameraX'] and [v-3000 for v in y['cameraY']]==x['cameraY']
        assert [v+5760 for v in y['vx']]==x['vx'] and [v+3000 for v in y['vy']]==x['vy']
    result['matchedReference']=dict(tileHash=sa['tileHash'],all960CameraCoordinates=True,offset=[5760,3000],
        sameProbe=True,imagesInspected=['normal/reference-0.png','scene/reference-0.png'],
        limitation='Both contain the actual player and room. Decorations and native exploration mask differ; images are not pixel-identical. Native stage band and between-stage timing are not exclusive CPU/GPU timings.')
    out=HERE/'review.json';assert not out.exists();out.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps(dict(verifiedRuns=len(result['runs']),sha256=sha(out),matched=result['matchedReference'])))
if __name__=='__main__':main()
