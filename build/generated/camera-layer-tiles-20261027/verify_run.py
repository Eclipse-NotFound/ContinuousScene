"""Independent input, resource, interval and timeline-layer evidence review."""
from pathlib import Path
import hashlib,json,math,statistics
HERE=Path(__file__).resolve().parent;MOD=HERE.parents[2];ROOT=MOD.parents[1]
NAME='camera-layer-tiles-20261027-r1';F=MOD/'knowledge/experiments/evidence'/NAME
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def metric(v):
    s=sorted(v)
    return dict(n=len(s),mean=statistics.mean(s),median=statistics.median(s),p95=s[math.ceil(.95*len(s))-1],maximum=s[-1]) if s else None


def main():
    rec=read(F/'runner-inputs.json');build=read(F/'probe-build.json');raw=read(F/'storage/result.json')
    policy=read(F/'process-policy.json');loader=read(F/'loader-check.json')
    actual={k.replace('\\','/'):v for k,v in read(F/'inputs.json').items()}
    assert len(rec['baseline'])==526 and len(rec['runtimeInputs'])==13
    for group in ('baseline','runtimeInputs'):
        for path,digest in rec[group].items():assert sha(ROOT/path)==digest,(group,path)
    for group in ('runnerInputs','compilerInputs','fixtureInputs'):
        for path,digest in rec[group].items():assert sha(Path(path))==digest,(group,path)
    source=Path(build['frozenSourcePath']);assert len(build['frozenSourceSHA256'])==86
    for path,digest in build['frozenSourceSHA256'].items():assert sha(source/path)==digest,path
    assert sha(Path(build['probePath']))==build['probeSHA256']==rec['probeSHA256']
    for field in ('sourceOrigin','configPath'):
        assert sha(Path(build[field]))==build['sourceOriginSHA256' if field=='sourceOrigin' else 'configSHA256']
    for key,digest in rec['baseline'].items():
        if key not in ('application.xml','mods/loader-manifest.txt'):assert actual[key]==digest,key
    assert actual['mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf']==build['probeSHA256']
    assert len(loader['sessions'])==1 and all(loader['loaded'].values())
    assert policy['desktopPolicy']=='private' and not policy['performanceEligible']
    assert not policy.get('otherAirProcessIds') and not policy.get('memoryAbort') and not policy.get('runFailure')
    assert rec['memoryBeforeAir']['availableCommit']>=4*1024**3 and rec['memoryBeforeAir']['availablePhysical']>=2*1024**3
    t=raw['cameraRaster'];clean=raw['cameraRasterCleanup'];p=clean['presentation']
    assert clean==t['cleanup'] and clean['pendingOwnedBitmaps']==0 and not t['pixelDisposeErrors']
    assert t['pixelBitmapsCreated']==t['pixelBitmapsDisposed']
    assert p['texturesCreated']==p['texturesDisposed'] and p['allocated']==p['disposed'] and p['gpuBytes']==p['liveCPUBytes']==0
    assert p['contextCreates']==p['contextDisposals']==1 and not p['active'] and not p['ready']
    assert p['clipsStopped']==p['clipsResumed']==0 and p['liveAnimation']
    assert p['layerWrites']==p['layerRestores']
    assert p['peakCPUBytes']<=128*1024**2 and p['peakGPUBytes']<=128*1024**2
    text=(source/'SceneTilePresentation.as').read_text('utf-8-sig')
    assert '.stop(' not in text and '.play(' not in text and '.gotoAnd' not in text
    result=dict(name=NAME,inputIntegrity=True,formalFiles=526,runtimeFiles=13,sourceFiles=86,
        resultSHA256=sha(F/'storage/result.json'),probeSHA256=build['probeSHA256'],frozenSource=source.parent.name,pid=policy['pid'],
        originalOK=raw['ok'],originalError=raw['error'],trialErrors=t['errors'],complete=t['complete'],passed=t['passed'],
        frames=len(t['framesMs']),pixelChecks=len(t['pixels']),pixelBuffers=t['pixelBitmapsCreated'],
        cleanup=clean,visualAccepted=t.get('visualAccepted'),deployed=False)
    result['arms']={m:metric([v for row in t['windows'] if row['mode']==m for v in row['framesMs']])
        for m in ('native-static','native-moving','gpu-static','gpu-moving')}
    if t['complete']:
        assert raw['ok'] and t['passed'] and not t['errors'] and clean['restored']
        assert t['attributionOnlyWithRejectedPixels'] and t['visualAccepted']==t['pixelsValid']==all(x['visualAccepted'] for x in t['pixels'])
        assert len(t['pixels'])==13 and len(t['nativeWarmups'])==18 and t['pixelBitmapsCreated']==260
        assert all(x['passed'] and len(x['checks'])==3 and all(y['pixels']['equal'] for y in x['checks']) for x in t['nativeWarmups'])
        assert all(x['restore']['equal'] and x['restore']['differentPixels']==0 for x in t['pixels'])
        assert t['zeroRasterWork'] and all(v==0 for v in t['timingRasterDelta'].values())
        assert p['captures']==13 and p['animationChanges']>0
        rows=t['windows'];assert len(rows)==8 and len(t['framesMs'])==960
        previous=t['timingStartAtMs'];stamps=[];deltas=[]
        for row,c in zip(rows,(0,1,2,3,3,2,1,0)):
            assert row['condition']==c and len(row['framesMs'])==120 and row['startAtMs']==previous
            assert all(v is (c<2) for v in row['worldVisible']) and all(row['windowVisible'])
            unique=len(set(zip(row['vx'],row['vy'])));assert unique>100 if c%2 else unique==1
            assert all(pose==t['timingStart']['gg'] for pose in row['gg'])
            for stamp,dt in zip(row['sampleAtMs'],row['framesMs']):
                assert stamp-previous==dt and dt>=0;previous=stamp;stamps.append(stamp);deltas.append(dt)
            for s in row['presentation']:
                assert s['layerWrites']==s['layerRestores'] and s['clipsStopped']==s['clipsResumed']==0
        assert deltas==t['framesMs'] and stamps==t['sampleAtMs'] and sum(deltas)==t['timingElapsedMs']
        assert previous==t['timingEndAtMs'] and previous-t['timingStartAtMs']==sum(deltas)
        result['pairs']=[dict(native=a,gpu=b,delta=statistics.mean(rows[b]['framesMs'])-statistics.mean(rows[a]['framesMs'])) for a,b in ((1,3),(6,4))]
        first=rows[0]['presentation'][0];last=rows[-1]['presentation'][-1]
        result['timedCache']={k:last[k]-first[k] for k in ('layerRasterCalls','layerRasterMs','layerUploadMs','animationChanges','watchReads','watchMs','uploads','allocated','disposed','tileRefreshes','tileRefreshMs','tileUploadMs','tileSkipChanges','dirtyOwnerReads')}
        assert result['timedCache']['animationChanges']>0 and result['timedCache']['tileRefreshes']>0
        assert p['oracleCalls']==13 and len(p['oracleChecks'])==13 and all(x['equal'] for x in p['oracleChecks'])
        result['timedCache']['perGPUIntervalInclusiveMs']=(result['timedCache']['layerRasterMs']+result['timedCache']['tileRefreshMs'])/480
    dest=HERE/'run-review.json';assert not dest.exists()
    dest.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps({k:result.get(k) for k in ('complete','frames','trialErrors','arms','pairs','timedCache','visualAccepted')}))


if __name__=='__main__':main()
