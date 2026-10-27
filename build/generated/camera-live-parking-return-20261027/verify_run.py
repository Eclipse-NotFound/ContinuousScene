"""Independent input/time/lifecycle review; failed evidence remains failed."""
from pathlib import Path
import hashlib,json,math,statistics,sys
HERE=Path(__file__).resolve().parent
MOD=HERE.parents[2];ROOT=MOD.parents[1];E=MOD/'knowledge/experiments/evidence'
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def metric(v):
    a=sorted(v);return dict(count=len(a),mean=statistics.mean(a),median=statistics.median(a),p95=a[math.ceil(.95*len(a))-1],maximum=a[-1])
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
    t=raw.get('farParking');clean=raw['farParkingCleanup'];rows=raw['samples']
    out=dict(name=name,inputIntegrity=True,formalFiles=526,runtimeFiles=13,sourceFiles=86,
        resultSHA256=sha(folder/'storage/result.json'),probeSHA256=build['probeSHA256'],frozenSource=source.parent.name,
        pid=policy['pid'],appId=policy['appId'],rawOK=raw['ok'],error=raw['error'],samples=len(rows),
        parking=t,cleanup=clean,verification=raw.get('farParkingVerification'),deployed=False,gameplayAccepted=False)
    if rows:
        clock=raw['continuousSampling']['startedAtMs'];begin=clock;deltas=[];windows=[]
        for i,row in enumerate(rows):
            on=i%4 in (1,2);states=row['farParking']
            assert len(row['frames'])==len(row['continuousFramesMs'])==len(row['sampleAtMs'])==len(states)==60
            assert row['empty']==0 and row['nativeInputMotion']['movementRequested']
            for stamp,dt,state in zip(row['sampleAtMs'],row['continuousFramesMs'],states):
                assert stamp-clock==dt and dt>=0;clock=stamp;deltas.append(dt)
                assert state['enabled'] is on and state['windowVisible']
                if not on:assert state['held']==0
            windows.append(dict(index=i,enabled=on,frame=metric(row['continuousFramesMs']),work=metric([s['workMs'] for s in states]),
                held=[min(s['held'] for s in states),max(s['held'] for s in states)],
                retired=[min(s['retired'] for s in states),max(s['retired'] for s in states)],
                xRange=[min(s['vx'] for s in states),max(s['vx'] for s in states)],
                yRange=[min(s['vy'] for s in states),max(s['vy'] for s in states)],
                playerShots=row['playerShotFrames'],enemyShots=row['enemyShotFrames']))
        assert sum(deltas)==clock-begin
        out.update(frames=len(deltas),elapsedMs=sum(deltas),rows=windows)
        if len(rows)==20:
            out['arms']={str(on):metric([dt for i,row in enumerate(rows) if (i%4 in (1,2)) is on for dt in row['continuousFramesMs']]) for on in (False,True)}
            out['pairs']=[dict(base=i+a,candidate=i+b,delta=windows[i+b]['frame']['mean']-windows[i+a]['frame']['mean']) for i in range(0,20,4) for a,b in [(0,1),(3,2)]]
    if raw['ok']:
        assert raw['error'] is None and len(rows)==20 and t['selected']>0 and t['maximumHeld']>0
        assert clean==t['cleanup'] and clean['restored'] and clean['pendingOwnedRoots']==0 and not clean['errors']
        v=raw['farParkingVerification'];assert v['afterTiming'] and v['restored']
        assert all(v['nativeRemoval'][k] for k in ['wasHeld','nativeRemoved','retired','notResurrected'])
        for k in ['changed','restored']:assert v['pixels'][k]['passed'] and v['pixels'][k]['maxRGB']<=2 and v['pixels'][k]['maxAlpha']==0
        assert all(a['ok'] for a in raw['assertions'])
    return out
if __name__=='__main__':
    name=sys.argv[1] if len(sys.argv)>1 else HERE.name+'-r1'
    result=review(name);out=HERE/'run-review.json';assert not out.exists()
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps(result,ensure_ascii=False))
