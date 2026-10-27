"""Independent review of the three actor-cache experiments, including failed pixels."""
from pathlib import Path
import argparse,hashlib,json,math,statistics
HERE=Path(__file__).resolve().parent;MOD=HERE.parents[2];ROOT=MOD.parents[1]
NAMES=('camera-actor-sprites-20261027-r1','camera-actor-direct-20261027-r1','camera-actor-frames-20261027-r1',
       'camera-actor-frames-checked-20261027-r1','camera-actor-frames-scan-20261027-r1',
       'camera-actor-atlas-20261027-r1','camera-actor-atlas-checks-20261027-r1')

def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def metric(v):
    v=sorted(v)
    return dict(count=len(v),mean=statistics.mean(v),median=statistics.median(v),p95=v[math.ceil(.95*len(v))-1],maximum=v[-1]) if v else None

def review(name):
    folder=MOD/'knowledge/experiments/evidence'/name
    rec=read(folder/'runner-inputs.json');build=read(folder/'probe-build.json');raw=read(folder/'storage/result.json')
    policy=read(folder/'process-policy.json');loader=read(folder/'loader-check.json')
    inputs={k.replace('\\','/'):v for k,v in read(folder/'inputs.json').items()}
    assert len(rec['baseline'])==526 and len(rec['runtimeInputs'])==13
    for key in ('baseline','runtimeInputs'):
        for path,digest in rec[key].items():assert sha(ROOT/path)==digest,(key,path)
    for key in ('runnerInputs','compilerInputs','fixtureInputs'):
        for path,digest in rec[key].items():assert sha(Path(path))==digest,(key,path)
    source=Path(build['frozenSourcePath']);assert len(build['frozenSourceSHA256'])==86
    for path,digest in build['frozenSourceSHA256'].items():assert sha(source/path)==digest,path
    assert sha(Path(build['probePath']))==build['probeSHA256']==rec['probeSHA256']
    for key in ('sourceOrigin','configPath'):
        assert sha(Path(build[key]))==build['sourceOriginSHA256' if key=='sourceOrigin' else 'configSHA256']
    for path,digest in rec['baseline'].items():
        if path not in ('application.xml','mods/loader-manifest.txt'):assert inputs[path]==digest,path
    assert inputs['mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf']==build['probeSHA256']
    assert len(loader['sessions'])==1 and all(loader['loaded'].values())
    assert policy['desktopPolicy']=='private' and not policy['performanceEligible']
    assert not policy.get('otherAirProcessIds') and not policy.get('memoryAbort') and not policy.get('runFailure')
    assert rec['memoryBeforeAir']['availableCommit']>=4*1024**3 and rec['memoryBeforeAir']['availablePhysical']>=2*1024**3
    t=raw['cameraRaster'];clean=raw['cameraRasterCleanup'];p=clean['presentation']
    assert t['cleanup']==clean and clean['pendingOwnedBitmaps']==0 and not t['pixelDisposeErrors']
    assert t['pixelBitmapsCreated']==t['pixelBitmapsDisposed']
    assert p['allocated']==p['disposed'] and p['texturesCreated']==p['texturesDisposed']
    assert p['gpuBytes']==p['liveCPUBytes']==0 and p['contextCreates']==p['contextDisposals']==1
    assert not p['active'] and not p['ready'] and p['liveAnimation'] and p['clipsStopped']==p['clipsResumed']==0
    assert p['layerWrites']==p['layerRestores'] and p['actorVisibilityWrites']==p['actorVisibilityRestores']
    assert p['peakCPUBytes']<=128*1024**2 and p['peakGPUBytes']<=128*1024**2
    text=(source/'SceneTilePresentation.as').read_text('utf-8-sig')
    assert '.stop(' not in text and '.play(' not in text and '.gotoAnd' not in text
    out=dict(name=name,formalFiles=526,runtimeFiles=13,sourceFiles=86,inputIntegrity=True,
        probeSHA256=build['probeSHA256'],frozenSource=source.parent.name,pid=policy['pid'],
        resultSHA256=sha(folder/'storage/result.json'),originalOK=raw['ok'],originalError=raw['error'],
        complete=t['complete'],passed=t['passed'],errors=t['errors'],cleanup=clean,
        frames=len(t['framesMs']),pixels=t['pixels'],visualAccepted=t.get('visualAccepted'),
        animationOracle=p['oracleChecks'],deployed=False,gameplayAcceptance=False)
    check_trial=name==NAMES[-1]
    modes=('native-static','native-moving','gpu-static','gpu-moving')+ (('gpu-fast-static','gpu-fast-moving') if check_trial else ())
    out['arms']={mode:metric([dt for row in t['windows'] if row['mode']==mode for dt in row['framesMs']]) for mode in modes}
    if t['complete']:
        assert raw['ok'] and t['passed'] and not t['errors'] and clean['restored']
        post=name.startswith('camera-actor-frames') or name.startswith('camera-actor-atlas');count=18 if post else 13
        assert t['visualAccepted']==t['pixelsValid']==all(x['visualAccepted'] for x in t['pixels'])
        assert len(t['pixels'])==count and len(t['nativeWarmups'])==count+5
        assert t['pixelBitmapsCreated']==(335 if post else 260)
        assert p['captures']==p['oracleCalls']==count and len(p['oracleChecks'])==count
        assert all(x['passed'] and len(x['checks'])==3 and all(y['pixels']['equal'] for y in x['checks']) for x in t['nativeWarmups'])
        for pixel in t['pixels']:
            assert pixel['restore']['equal'] and pixel['restore']['differentPixels']==0
            assert pixel['visualAccepted']==(pixel['candidate']['maxRGB']<=2 and pixel['candidate']['maxAlpha']==0)
        for oracle in p['oracleChecks']:
            assert oracle['accepted']==(oracle['maxRGB']<=2 and oracle['maxAlpha']==0)
            assert oracle['equal']==(oracle['differentPixels']==0)
        assert t['zeroRasterWork'] and all(v==0 for v in t['timingRasterDelta'].values())
        order=(0,1,2,3,4,5,5,4,3,2,1,0) if check_trial else (0,1,2,3,3,2,1,0)
        rows=t['windows'];assert len(rows)==len(order) and len(t['framesMs'])==120*len(order)
        previous=t['timingStartAtMs'];stamps=[];deltas=[]
        for row,c in zip(rows,order):
            assert row['condition']==c and row['mode']==modes[c] and len(row['framesMs'])==120 and row['startAtMs']==previous
            assert all(v is (c<2) for v in row['worldVisible']) and all(row['windowVisible'])
            positions=len(set(zip(row['vx'],row['vy'])));assert positions>100 if c%2 else positions==1
            assert all(pose==t['timingStart']['gg'] for pose in row['gg'])
            for stamp,dt in zip(row['sampleAtMs'],row['framesMs']):
                assert stamp-previous==dt and dt>=0;previous=stamp;stamps.append(stamp);deltas.append(dt)
            assert row['endAtMs']==previous
            for sample in row['presentation']:
                assert sample['captures']==13 and sample['liveAnimation'] and sample['clipsStopped']==sample['clipsResumed']==0
                assert sample['active'] is (c>=2) and sample['parents']==(2 if c>=2 else 0)
                assert sample['actorVisibilityWrites']==sample['actorVisibilityRestores']
                if check_trial:assert sample['errorChecking'] is (c<4) and row['checked'] is (c<4)
        assert deltas==t['framesMs'] and stamps==t['sampleAtMs'] and sum(deltas)==t['timingElapsedMs']
        assert previous==t['timingEndAtMs'] and previous-t['timingStartAtMs']==sum(deltas)
        pairs=((1,3),(10,8),(1,5),(10,6),(3,5),(8,6)) if check_trial else ((1,3),(6,4))
        out['pairs']=[dict(native=a,gpu=b,delta=statistics.mean(rows[b]['framesMs'])-statistics.mean(rows[a]['framesMs'])) for a,b in pairs]
        first=rows[0]['presentation'][0];last=rows[-1]['presentation'][-1]
        keys=('layerRasterCalls','layerRasterMs','layerUploadMs','actorRasterCalls','actorRasterMs','actorRefreshMs',
              'actorUploadMs','actorRasterPixels','directBitmapUploads','animationChanges','watchReads','watchMs',
              'uploads','allocated','disposed','actorVisibilityWrites','actorVisibilityRestores','actorDirectCalls',
              'actorDirectMs','actorParentCalls','actorParentMs','poseHits','poseMisses','poseEvictions','poseSkipped',
              'atlasPasses','atlasRoots','atlasDrawMs','atlasCopyMs','actorTransformWrites','actorTransformRestores')
        out['timedCache']={key:last[key]-first[key] for key in keys if key in first}
        out['rows']=[dict(mode=row['mode'],frame=metric(row['framesMs']),workMs=metric(row['workMs'])) for row in rows]
        if post:
            assert p['poseBytes']==0 and p['poseEntries']==0 and p['posePeak']<=24*1024**2
            assert [x['index'] for x in t['pixels'][-5:]]==list(range(1000,1005))
        if name.startswith('camera-actor-atlas'):
            assert p['actorTransformWrites']==p['actorTransformRestores'] and p['atlasPasses']>0 and p['poseHits']==0
            assert all(s['actorTransformWrites']==s['actorTransformRestores'] for row in rows for s in row['presentation'])
    return out

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--name',choices=NAMES,required=True);args=parser.parse_args()
    out=review(args.name);dest=HERE.parent/args.name.removesuffix('-r1')/'run-review.json'
    assert not dest.exists(),'Preserve prior review'
    dest.write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps({key:out.get(key) for key in ('name','complete','frames','errors','arms','pairs','timedCache','visualAccepted')}))
