"""Independent frozen-input, window-state and interval audit; preserve failures."""
from pathlib import Path
import hashlib,json,math,statistics,sys
HERE=Path(__file__).resolve().parent
MOD=HERE.parents[2];ROOT=MOD.parents[1];E=MOD/'knowledge/experiments/evidence'
NAMES=['camera-native-quality-20261027-r1']
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def metric(v):
    a=sorted(v)
    return dict(count=len(a),mean=statistics.mean(a),median=statistics.median(a),p95=a[math.ceil(.95*len(a))-1],maximum=a[-1]) if a else None
def review(name):
    folder=E/name;rec=read(folder/'runner-inputs.json');build=read(folder/'probe-build.json')
    raw=read(folder/'storage/result.json');policy=read(folder/'process-policy.json');loader=read(folder/'loader-check.json')
    actual={k.replace('\\','/'):v for k,v in read(folder/'inputs.json').items()}
    assert len(rec['baseline'])==526 and len(rec['runtimeInputs'])==13
    for group in ['baseline','runtimeInputs']:
        for path,digest in rec[group].items():assert sha(ROOT/path)==digest,(name,group,path)
    for group in ['runnerInputs','compilerInputs','fixtureInputs']:
        for path,digest in rec[group].items():assert sha(Path(path))==digest,(name,group,path)
    source=Path(build['frozenSourcePath']);assert len(build['frozenSourceSHA256'])==86
    for path,digest in build['frozenSourceSHA256'].items():assert sha(source/path)==digest,path
    assert sha(Path(build['probePath']))==build['probeSHA256']==rec['probeSHA256']
    for path,expected in [('sourceOrigin','sourceOriginSHA256'),('configPath','configSHA256')]:assert sha(Path(build[path]))==build[expected]
    for key,digest in rec['baseline'].items():
        if key not in ('application.xml','mods/loader-manifest.txt'):assert actual[key]==digest,key
    assert actual['mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf']==build['probeSHA256']
    assert rec['runtimeDescriptor']['restored']
    assert actual['application.xml']==rec['runtimeDescriptor']['duringSHA256']==rec['runtimeDescriptor']['beforeSHA256']==sha(MOD/'build/runtime/application.xml')
    assert len(loader['sessions'])==1 and all(loader['loaded'].values())
    assert policy['desktopPolicy']=='private' and not policy['performanceEligible']
    assert not policy.get('otherAirProcessIds') and not policy.get('memoryAbort') and not policy.get('runFailure')
    assert rec['memoryBeforeAir']['availableCommit']>=4*1024**3 and rec['memoryBeforeAir']['availablePhysical']>=2*1024**3
    t=raw['cameraRaster'];clean=raw['cameraRasterCleanup']
    assert clean==t['cleanup'] and clean['pendingOwnedBitmaps']==0 and not t['pixelDisposeErrors']
    assert t['pixelBitmapsCreated']==t['pixelBitmapsDisposed']
    assert raw['ok'] and raw['error'] is None and t['complete'] and t['passed'] and not t['errors']
    assert clean['restored'] and not clean['errors'] and t['pixelBitmapsCreated']==25
    assert len(t['pixels'])==5 and all(p['passed'] for p in t['pixels'])
    for p in t['pixels']:
        for key in ['nativeRepeat','medium','low','restored']:
            assert p[key]['equal'] and p[key]['differentPixels']==p[key]['maxRGB']==p[key]['maxAlpha']==0
    assert t['stage']==dict(width=2032,height=1084,quality='HIGH')
    assert t['zeroRasterWork'] and all(x==0 for x in t['timingRasterDelta'].values())
    assert len(t['framesMs'])==1440 and len(t['windows'])==12
    clock=t['timingStartAtMs'];deltas=[];stamps=[]
    for row,c in zip(t['windows'],[0,1,2,3,4,5,5,4,3,2,1,0]):
        assert row['condition']==c and row['startAtMs']==clock and len(row['framesMs'])==120
        assert row['quality']==['HIGH']*120, 'Desktop runtime retained HIGH; these are not lower-quality arms'
        assert all(row['worldVisible']) and all(row['windowVisible']) and not row['hidden']
        assert (len(set(row['vx']))>1)==bool(c%2) and (len(set(row['vy']))>1)==bool(c%2)
        assert all(p==t['timingStart']['gg'] for p in row['gg'])
        for stamp,dt in zip(row['sampleAtMs'],row['framesMs']):
            assert stamp-clock==dt and dt>=0;clock=stamp;stamps.append(stamp);deltas.append(dt)
        assert row['endAtMs']==clock
    assert deltas==t['framesMs'] and stamps==t['sampleAtMs'] and sum(deltas)==t['timingElapsedMs']==clock-t['timingStartAtMs']
    assert clock==t['timingEndAtMs']
    assert 'AssertionError' in read(folder/'runner-failure.json')['traceback']
    return dict(name=name,inputIntegrity=True,formalFiles=526,runtimeFiles=13,sourceFiles=86,
        resultSHA256=sha(folder/'storage/result.json'),probeSHA256=build['probeSHA256'],frozenSource=source.parent.name,
        pid=policy['pid'],frames=1440,actualQuality='HIGH in all 1440 intervals',qualityComparisonValid=False,
        originalDriverOK=True,summaryRejected=True,cleanup=clean,deployed=False,
        originalHighStatic=metric([v for row in t['windows'] if row['mode']=='high-static' for v in row['framesMs']]),
        originalHighMoving=metric([v for row in t['windows'] if row['mode']=='high-moving' for v in row['framesMs']]),
        source='https://airsdk.dev/reference/actionscript/3.0/flash/display/Stage.html#quality',
        limits=['Desktop AIR only accepts HIGH/BEST; MEDIUM/LOW are ignored. No lower-quality performance or image claim.'])
if __name__=='__main__':
    result=review(NAMES[0]);out=HERE/'run-review.json';assert not out.exists()
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8');print(json.dumps(result,ensure_ascii=False))
