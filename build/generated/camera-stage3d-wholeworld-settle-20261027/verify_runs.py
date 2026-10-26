"""Independent immutable-file review for the whole-world diagnostic sequence."""
from pathlib import Path
import hashlib
import json
import math
import statistics
HERE=Path(__file__).resolve().parent;MOD=HERE.parents[2];ROOT=MOD.parents[1];E=MOD/'knowledge/experiments/evidence'
NAMES=('camera-stage3d-wholeworld-20261027-r1',*[f'camera-stage3d-wholeworld-{s}-20261027-r1' for s in ('late','nullslots','observed','cost','settle')])
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def metric(values):
    s=sorted(values)
    return dict(n=len(s),mean=statistics.mean(s),median=statistics.median(s),p95=s[math.ceil(.95*len(s))-1],maximum=s[-1]) if s else None
def review(name):
    folder=E/name;rec=read(folder/'runner-inputs.json');build=read(folder/'probe-build.json')
    raw=read(folder/'storage/result.json');policy=read(folder/'process-policy.json');loader=read(folder/'loader-check.json')
    actual={k.replace('\\','/'):v for k,v in read(folder/'inputs.json').items()}
    assert len(rec['baseline'])==526 and len(rec['runtimeInputs'])==13
    for group in ('baseline','runtimeInputs'):
        for path,digest in rec[group].items():assert sha(ROOT/path)==digest,(name,group,path)
    for group in ('runnerInputs','compilerInputs','fixtureInputs'):
        for path,digest in rec[group].items():assert sha(Path(path))==digest,(name,group,path)
    source=Path(build['frozenSourcePath']);assert len(build['frozenSourceSHA256'])==86
    for path,digest in build['frozenSourceSHA256'].items():assert sha(source/path)==digest,(name,path)
    assert sha(Path(build['probePath']))==build['probeSHA256']==rec['probeSHA256']
    assert sha(Path(build['sourceOrigin']))==build['sourceOriginSHA256'] and sha(Path(build['configPath']))==build['configSHA256']
    for key,digest in rec['baseline'].items():
        if key not in ('application.xml','mods/loader-manifest.txt'):assert actual[key]==digest,(name,key)
    assert actual['mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf']==build['probeSHA256']
    assert len(loader['sessions'])==1 and all(loader['loaded'].values())
    assert policy['desktopPolicy']=='private' and not policy['performanceEligible']
    assert not policy.get('otherAirProcessIds') and not policy.get('memoryAbort') and not policy.get('runFailure')
    assert rec['memoryBeforeAir']['availableCommit']>=4*1024**3 and rec['memoryBeforeAir']['availablePhysical']>=2*1024**3
    t=raw['cameraRaster'];clean=raw['cameraRasterCleanup'];p=clean['presentation']
    assert clean==t['cleanup'] and clean['pendingOwnedBitmaps']==0 and not t['pixelDisposeErrors']
    assert t['pixelBitmapsCreated']==t['pixelBitmapsDisposed']
    assert p['texturesCreated']==p['texturesDisposed'] and p['allocated']==p['disposed'] and p['gpuBytes']==0
    assert p['contextCreates']==p['contextDisposals']==1 and not p['active'] and not p['ready']
    # Do not erase the two externally restarted clips in the failed cost run.
    if name==NAMES[4]:
        assert (p['clipsStopped'],p['clipsResumed'])==(47,45) and not clean['restored']
        assert len(p['timelineChanges'])==2 and all(x['className']=='pfe_fla::bloat_bulk_896' and x['beforeFrame']==55 for x in p['timelineChanges'])
    else:assert p['clipsStopped']==p['clipsResumed']
    result=dict(name=name,inputIntegrity=True,formalFiles=526,runtimeFiles=13,sourceFiles=86,
        resultSHA256=sha(folder/'storage/result.json'),probeSHA256=build['probeSHA256'],frozenSource=source.parent.name,pid=policy['pid'],
        originalOK=raw['ok'],originalError=raw['error'],trialErrors=t['errors'],complete=t['complete'],passed=t['passed'],
        frames=len(t['framesMs']),pixelChecks=len(t['pixels']),pixelBuffers=t['pixelBitmapsCreated'],
        cleanup=clean,visualAccepted=t.get('visualAccepted'),deployed=False)
    result['arms']={mode:metric([v for row in t['windows'] if row['mode']==mode for v in row['framesMs']])
        for mode in ('native-static','native-moving','gpu-static','gpu-moving')}
    if t['complete']:
        assert raw['ok'] and t['passed'] and not t['errors'] and clean['restored']
        assert t['attributionOnlyWithRejectedPixels'] and t['visualAccepted']==t['pixelsValid']==all(x['visualAccepted'] for x in t['pixels'])
        assert len(t['pixels'])==13 and len(t['nativeWarmups'])==18 and t['pixelBitmapsCreated']==260
        assert all(x['passed'] and len(x['checks'])==3 and all(y['pixels']['equal'] for y in x['checks']) for x in t['nativeWarmups'])
        assert all(x['restore']['equal'] and x['restore']['differentPixels']==0 for x in t['pixels'])
        assert t['zeroRasterWork'] and all(v==0 for v in t['timingRasterDelta'].values())
        assert p['captures']==13 and p['observationSteps']==8 and p['implicitStopped']>0 and not p['timelineChanges'] and p['frameScriptDrainDone']
        rows=t['windows'];assert len(rows)==8 and len(t['framesMs'])==960
        previous=t['timingStartAtMs'];stamps=[];deltas=[]
        for row,c in zip(rows,(0,1,2,3,3,2,1,0)):
            assert row['condition']==c and len(row['framesMs'])==120 and row['startAtMs']==previous
            assert all(v is (c<2) for v in row['worldVisible']) and all(row['windowVisible'])
            unique=len(set(zip(row['vx'],row['vy'])));assert unique>100 if c%2 else unique==1
            assert all(pose==t['timingStart']['gg'] for pose in row['gg'])
            for stamp,dt in zip(row['sampleAtMs'],row['framesMs']):
                assert stamp-previous==dt and dt>=0;previous=stamp;stamps.append(stamp);deltas.append(dt)
        assert deltas==t['framesMs'] and stamps==t['sampleAtMs'] and sum(deltas)==t['timingElapsedMs']
        assert previous==t['timingEndAtMs'] and previous-t['timingStartAtMs']==sum(deltas)
        result['pairs']=[dict(native=a,gpu=b,delta=statistics.mean(rows[b]['framesMs'])-statistics.mean(rows[a]['framesMs'])) for a,b in ((1,3),(6,4))]
    return result
if __name__=='__main__':
    runs=[review(n) for n in NAMES];assert all(r['frames']==0 for r in runs[:5])
    dest=HERE/'runs-review.json';assert not dest.exists(),'Do not overwrite prior review'
    dest.write_text(json.dumps(dict(readOnlyReview=True,originalFailuresRetained=True,runs=runs),ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps([dict(name=r['name'],frames=r['frames'],errors=r['trialErrors'],arms=r['arms']) for r in runs],ensure_ascii=False))
