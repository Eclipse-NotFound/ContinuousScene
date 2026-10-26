"""Read-only independent identity and outcome audit; never rewrite original results."""
from pathlib import Path
import hashlib
import json
import math
import statistics

HERE=Path(__file__).resolve().parent
MOD=HERE.parents[2]
ROOT=MOD.parents[1]
E=MOD/'knowledge/experiments/evidence'
NAMES=('camera-stage3d-wholeworld-20261027-r1','camera-stage3d-wholeworld-late-20261027-r1','camera-stage3d-wholeworld-nullslots-20261027-r1')
def read(path):return json.loads(path.read_text('utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest().upper()
def metric(values):
    s=sorted(values)
    return dict(n=len(s),mean=statistics.mean(s),median=statistics.median(s),p95=s[math.ceil(.95*len(s))-1],maximum=s[-1]) if s else None
def review(name):
    folder=E/name
    record=read(folder/'runner-inputs.json');build=read(folder/'probe-build.json')
    raw=read(folder/'storage/result.json');policy=read(folder/'process-policy.json')
    actual={k.replace('\\','/'):v for k,v in read(folder/'inputs.json').items()};loader=read(folder/'loader-check.json')
    assert len(record['baseline'])==526 and len(record['runtimeInputs'])==13
    for table in ('baseline','runtimeInputs'):
        for path,digest in record[table].items():assert sha(ROOT/path)==digest,(name,table,path)
    for table in ('runnerInputs','compilerInputs','fixtureInputs'):
        for path,digest in record[table].items():assert sha(Path(path))==digest,(name,table,path)
    source=Path(build['frozenSourcePath'])
    assert len(build['frozenSourceSHA256'])==86
    for path,digest in build['frozenSourceSHA256'].items():assert sha(source/path)==digest,(name,path)
    assert sha(Path(build['probePath']))==build['probeSHA256']==record['probeSHA256']
    assert sha(Path(build['sourceOrigin']))==build['sourceOriginSHA256']
    assert sha(Path(build['configPath']))==build['configSHA256']
    for key,digest in record['baseline'].items():
        if key not in ('application.xml','mods/loader-manifest.txt'):assert actual[key]==digest,(name,key)
    assert actual['mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf']==build['probeSHA256']
    assert len(loader['sessions'])==1 and all(loader['loaded'].values())
    assert policy['desktopPolicy']=='private' and not policy['performanceEligible']
    assert not policy.get('otherAirProcessIds') and not policy.get('memoryAbort') and not policy.get('runFailure')
    assert record['memoryBeforeAir']['availableCommit']>=4*1024**3 and record['memoryBeforeAir']['availablePhysical']>=2*1024**3
    t=raw['cameraRaster'];cleanup=raw['cameraRasterCleanup'];p=cleanup['presentation']
    assert cleanup==t['cleanup'] and cleanup['pendingOwnedBitmaps']==0
    assert t['pixelBitmapsCreated']==t['pixelBitmapsDisposed'] and not t['pixelDisposeErrors']
    assert p['texturesCreated']==p['texturesDisposed'] and p['allocated']==p['disposed']
    assert p['contextCreates']==p['contextDisposals']==1 and p['gpuBytes']==0 and not p['active'] and not p['ready']
    assert p['clipsStopped']==p['clipsResumed']
    if t['windows']:
        last=t['timingStartAtMs'];stamps=[];deltas=[]
        for row in t['windows']:
            for stamp,dt in zip(row['sampleAtMs'],row['framesMs']):
                assert stamp-last==dt;last=stamp;stamps.append(stamp);deltas.append(dt)
        assert deltas==t['framesMs'] and stamps==t['sampleAtMs']
    result=dict(name=name,resultSHA256=sha(folder/'storage/result.json'),probeSHA256=build['probeSHA256'],
        frozenSource=source.parent.name,pid=policy['pid'],formalFiles=526,runtimeFiles=13,sourceFiles=86,
        inputIntegrity=True,originalOK=raw['ok'],originalError=raw['error'],trialErrors=t['errors'],
        complete=t['complete'],passed=t['passed'],frames=len(t['framesMs']),warmups=len(t.get('nativeWarmups',[])),
        pixelChecks=len(t['pixels']),pixelBuffers=t['pixelBitmapsCreated'],pixelBuffersDisposed=t['pixelBitmapsDisposed'],
        pixels=t['pixels'],cleanup=cleanup,minimumAvailableCommit=policy['minimumAvailableCommit'],deployed=False)
    result['arms']={mode:metric([v for row in t['windows'] if row['mode']==mode for v in row['framesMs']])
        for mode in ('native-static','native-moving','gpu-static','gpu-moving')}
    return result
if __name__=='__main__':
    results=[review(name) for name in NAMES]
    dest=HERE/'runs-review.json';assert not dest.exists(),'Keep earlier independent reviews'
    dest.write_text(json.dumps(dict(runs=results,readOnlyReview=True,originalFailuresRetained=True),indent=2,ensure_ascii=False),'utf-8')
    print(json.dumps([dict(name=r['name'],frames=r['frames'],errors=r['trialErrors'],integrity=r['inputIntegrity']) for r in results],ensure_ascii=False))
