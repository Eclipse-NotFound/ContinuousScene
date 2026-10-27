"""Independently reconstruct timing and input identity; keep failed evidence failed."""
from pathlib import Path
import hashlib,json,math,statistics,sys
HERE=Path(__file__).resolve().parent
MOD=HERE.parents[2];ROOT=MOD.parents[1];E=MOD/'knowledge/experiments/evidence'
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def metric(v):
    a=sorted(v)
    return dict(count=len(a),mean=statistics.mean(a),median=statistics.median(a),p95=a[math.ceil(.95*len(a))-1],maximum=a[-1])
def review(name):
    folder=E/name;rec=read(folder/'runner-inputs.json');build=read(folder/'probe-build.json')
    raw=read(folder/'storage/result.json');policy=read(folder/'process-policy.json');loader=read(folder/'loader-check.json')
    actual={k.replace('\\','/'):v for k,v in read(folder/'inputs.json').items()}
    assert len(rec['baseline'])==526 and len(rec['runtimeInputs'])==13
    for group in ['baseline','runtimeInputs']:
        for path,digest in rec[group].items():assert sha(ROOT/path)==digest,(group,path)
    for group in ['runnerInputs','compilerInputs','fixtureInputs']:
        for path,digest in rec[group].items():assert sha(Path(path))==digest,(group,path)
    source=Path(build['frozenSourcePath']);assert len(build['frozenSourceSHA256'])==86
    for path,digest in build['frozenSourceSHA256'].items():assert sha(source/path)==digest,path
    assert sha(Path(build['probePath']))==build['probeSHA256']==rec['probeSHA256']
    for path,expected in [('sourceOrigin','sourceOriginSHA256'),('configPath','configSHA256')]:assert sha(Path(build[path]))==build[expected]
    for key,digest in rec['baseline'].items():
        if key not in ('application.xml','mods/loader-manifest.txt'):assert actual[key]==digest,key
    assert actual['mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf']==build['probeSHA256']
    assert len(loader['sessions'])==1 and all(loader['loaded'].values())
    assert policy['desktopPolicy']=='private' and not policy['performanceEligible']
    assert not policy.get('otherAirProcessIds') and not policy.get('memoryAbort') and not policy.get('runFailure')
    assert rec['memoryBeforeAir']['availableCommit']>=4*1024**3 and rec['memoryBeforeAir']['availablePhysical']>=2*1024**3
    t=raw['cameraRaster'];clean=raw['cameraRasterCleanup']
    assert clean==t['cleanup'] and clean['pendingOwnedBitmaps']==0 and not t['pixelDisposeErrors']
    assert t['pixelBitmapsCreated']==t['pixelBitmapsDisposed']
    result=dict(name=name,inputIntegrity=True,formalFiles=526,runtimeFiles=13,sourceFiles=86,resultSHA256=sha(folder/'storage/result.json'),
        probeSHA256=build['probeSHA256'],frozenSource=source.parent.name,pid=policy['pid'],appId=policy['appId'],
        stage=t['stage'],complete=t['complete'],passed=t['passed'],errors=t['errors'],cleanup=clean,frames=len(t['framesMs']),
        pixelChecks=len(t['pixels']),pixelBuffers=t['pixelBitmapsCreated'],rootSelection=t.get('rootSelection'),
        gameplayAccepted=False,windowPixelsNotCaptured=True,deployed=False)
    if not t['complete']:
        assert not raw['ok'] and not t['passed'] and t['errors']
        return result
    assert raw['ok'] and raw['error'] is None and t['passed'] and not t['errors'] and clean['restored'] and not clean['errors']
    assert t['pixelBitmapsCreated']==150 and len(t['pixels'])==len(t['nativeWarmups'])==10
    for warm in t['nativeWarmups']:
        assert warm['passed'] and len(warm['checks'])==3
        for check in warm['checks']:
            v=check['pixels'];assert v['equal'] and v['differentPixels']==v['maxRGB']==v['maxAlpha']==0
    for pixel in t['pixels']:
        assert pixel['passed'] and len(pixel['conditions'])==1
        for key in ['restored']:
            v=pixel['conditions'][0][key];assert v['equal'] and v['differentPixels']==v['maxRGB']==v['maxAlpha']==0
    roots=t['rootSelection'];assert roots['selected']>0 and 0<roots['estimatedBytes']<=32*1024**2
    assert roots['scanned']==roots['selected']+sum(roots['skips'].values())
    assert roots['selected']==sum(roots['byLayer'])==sum(roots['classes'].values())
    assert roots['perFrameFullScans']==0 and roots['transitionWrites']==roots['selected']*22 and roots['audits']>=25
    assert t['visualAccepted']==all(p['conditions'][0]['changed']['maxRGB']<=2 and p['conditions'][0]['changed']['maxAlpha']==0 for p in t['pixels']);result['visualAccepted']=t['visualAccepted'];result['candidatePixels']=[p['conditions'][0]['changed'] for p in t['pixels']]
    assert t['zeroRasterWork'] and all(x==0 for x in t['timingRasterDelta'].values())
    clock=t['timingStartAtMs'];stamps=[];deltas=[];names=['native-static','native-moving','native-cache-static','native-cache-moving']
    rows=t['windows'];assert len(rows)==8 and len(t['framesMs'])==960
    keys=('sceneRedraws','sceneDrawMs','sceneResident','sceneEvictions','sceneMisses','sceneWarmCount','sceneWarmSlices','sceneWarmForced')
    for i,(row,condition) in enumerate(zip(rows,[0,1,2,3,3,2,1,0])):
        assert row['index']==i and row['condition']==condition and row['mode']==names[condition] and row['startAtMs']==clock
        assert len(row['framesMs'])==len(row['sampleAtMs'])==120 and all(row['worldVisible']) and all(row['windowVisible'])
        assert row['moving'] is (condition%2==1) and row['hidden'] is False
        assert (len(set(row['vx']))>1)==row['moving'] and (len(set(row['vy']))>1)==row['moving']
        assert all(v==[condition//2,roots['selected']] for v in row['terrain'])
        assert all(v==t['timingStart']['gg'] for v in row['gg'])
        assert row['copiesStart']==row['copiesEnd']==row['allocatedStart']==row['allocatedEnd']==0
        for scene in row['scene']:assert all(scene[k]==t['timingStart']['scene'][k] for k in keys)
        for stamp,dt in zip(row['sampleAtMs'],row['framesMs']):
            assert stamp-clock==dt and dt>=0;clock=stamp;stamps.append(stamp);deltas.append(dt)
        assert row['endAtMs']==clock
    assert deltas==t['framesMs'] and stamps==t['sampleAtMs'] and sum(deltas)==t['timingElapsedMs']==clock-t['timingStartAtMs']
    assert clock==t['timingEndAtMs']
    for i in [3,4,6]:assert rows[i]['vx']==rows[1]['vx'] and rows[i]['vy']==rows[1]['vy']
    result['arms']={name:metric([v for row in rows if row['mode']==name for v in row['framesMs']]) for name in names}
    result['pairs']=[dict(base=a,candidate=b,delta=statistics.mean(rows[b]['framesMs'])-statistics.mean(rows[a]['framesMs'])) for a,b in [(1,3),(6,4),(0,2),(7,5)]]
    return result
if __name__=='__main__':
    name=sys.argv[1] if len(sys.argv)>1 else HERE.name+'-r1'
    result=review(name);out=HERE/'run-review.json'
    assert not out.exists(),'Preserve previous review'
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps(result,ensure_ascii=False))
