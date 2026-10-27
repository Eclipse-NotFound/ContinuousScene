"""Independent frozen-input, window-state and interval audit; preserve failures."""
from pathlib import Path
import hashlib,json,math,statistics,sys
HERE=Path(__file__).resolve().parent
MOD=HERE.parents[2];ROOT=MOD.parents[1];E=MOD/'knowledge/experiments/evidence'
NAMES=['camera-native-window-switch-20261027-r1','camera-native-window-audit-20261027-r1']
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
    assert [x['renderer'] for x in t['nativeWindows']]==['direct','direct','auto']
    assert t['stage']==dict(width=2032,height=1084,quality='HIGH') and t['windowPixelsNotCaptured']
    result=dict(name=name,inputIntegrity=True,formalFiles=526,runtimeFiles=13,sourceFiles=86,resultSHA256=sha(folder/'storage/result.json'),
        probeSHA256=build['probeSHA256'],frozenSource=source.parent.name,pid=policy['pid'],appId=policy['appId'],
        complete=t['complete'],passed=t['passed'],errors=t['errors'],cleanup=clean,frames=len(t['framesMs']),
        pixelChecks=len(t['pixels']),pixelBuffers=t['pixelBitmapsCreated'],pixels=t['pixels'],stageSwitchCount=len(t['stageSwitches']),
        gameplayAccepted=False,windowPixelsNotCaptured=True,deployed=False)
    if not t['complete']:
        assert not raw['ok'] and not t['passed'] and t['errors']
        return result
    assert raw['ok'] and raw['error'] is None and t['passed'] and not t['errors'] and clean['restored'] and not clean['errors']
    assert clean['ownedWindowsCreated']==clean['ownedWindowsClosed']==2 and len(t['framesMs'])==1440 and len(t['windows'])==12
    assert t['pixelBitmapsCreated']==75 and len(t['pixels'])==5
    for pixel in t['pixels']:
        assert pixel['passed'] and len(pixel['roundtrips'])==3
        for trip in pixel['roundtrips']:
            for key in ['nativeRepeat','newDirect','newAuto','restored']:
                v=trip[key];assert v['equal'] and v['differentPixels']==v['maxRGB']==v['maxAlpha']==0
    assert t['zeroRasterWork'] and all(x==0 for x in t['timingRasterDelta'].values())
    clock=t['timingStartAtMs'];stamps=[];deltas=[];names=['original-static','original-moving','direct-static','direct-moving','auto-static','auto-moving']
    rows=t['windows']
    for i,(row,condition) in enumerate(zip(rows,[0,1,2,3,4,5,5,4,3,2,1,0])):
        assert row['index']==i and row['condition']==condition and row['mode']==names[condition] and row['startAtMs']==clock
        assert len(row['framesMs'])==len(row['sampleAtMs'])==120 and all(row['worldVisible']) and all(row['windowVisible'])
        assert set(row['nativeMode'])=={condition//2} and set(row['renderer'])=={'auto' if condition>=4 else 'direct'}
        assert row['moving'] is (condition%2==1) and row['hidden'] is False
        assert (len(set(row['vx']))>1)==row['moving'] and (len(set(row['vy']))>1)==row['moving']
        assert all(v==t['timingStart']['gg'] for v in row['gg'])
        for stamp,dt in zip(row['sampleAtMs'],row['framesMs']):
            assert stamp-clock==dt and dt>=0;clock=stamp;stamps.append(stamp);deltas.append(dt)
        assert row['endAtMs']==clock
    assert deltas==t['framesMs'] and stamps==t['sampleAtMs'] and sum(deltas)==t['timingElapsedMs']==clock-t['timingStartAtMs']
    assert clock==t['timingEndAtMs']
    for i in [3,5,6,8,10]:assert rows[i]['vx']==rows[1]['vx'] and rows[i]['vy']==rows[1]['vy']
    result['arms']={name:metric([v for row in rows if row['mode']==name for v in row['framesMs']]) for name in names}
    result['pairs']=[dict(base=a,candidate=b,delta=statistics.mean(rows[b]['framesMs'])-statistics.mean(rows[a]['framesMs'])) for a,b in [(1,3),(1,5),(10,8),(10,6),(3,5),(8,6)]]
    return result
if __name__=='__main__':
    names=sys.argv[1:] or NAMES
    for name in names:
        result=review(name);out=HERE.parent/name.removesuffix('-r1')/'run-review.json'
        assert not out.exists(),'Preserve previous review'
        out.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
        print(json.dumps({k:v for k,v in result.items() if k not in ['pixels','cleanup']},ensure_ascii=False))
