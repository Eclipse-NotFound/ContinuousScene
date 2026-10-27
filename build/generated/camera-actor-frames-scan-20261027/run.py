"""Native layer caching with live Flash timelines; not gameplay acceptance."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import math
import shutil
import statistics
import sys
import traceback
import uuid

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
VERSION = 'camera-actor-frames-scan-1'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


reference = load('camera_world_reference', HERE.parent/'window-visibility-native-20261025/run.py')
old, shared, control, dense, base, r, m, support = (reference.old, reference.shared, reference.control,
    reference.dense, reference.base, reference.r, reference.m, reference.support)
patch = load('camera_world_patch', HERE/'probe_patch.py')
PINS = dict(reference.PINS)
RC_RECEIPT=HERE.parents[4]/'mods/RConnect/build/m52/a-live-animation-deploy-01/verified.json'
RC_CURRENT='2C49DFD05D524085EA43FB8FFA537D1A9359FEBD52FB13D6A19FAAE6E2563621'
PINS['mods/Rconnect/release/RConnectMod.swf']=RC_CURRENT
LINEAGE=HERE.parent/'camera-terrain-layers-20261025/lineage.py'
lineage=load('backdrop_registry_lineage',LINEAGE)


def runner_inputs():
    assert r.sha(RC_RECEIPT)=='5446D95AAA1552622CF1E691BBDE5C962875897014CF5C06A452A95037ACBC3B'
    assert patch.HELPER.read_text('utf-8-sig') == patch.helper_source()
    return dict(reference.runner_inputs(), **{str(p): r.sha(p) for p in
        (Path(reference.__file__), HERE/'run.py', HERE/'README.md', HERE/'probe_patch.py', LINEAGE, RC_RECEIPT,
         patch.HELPER, patch.ORIGINAL, patch.PATCH_SOURCE, *patch.EXTRA_INPUTS)})


def fixture_inputs():
    return dict(lineage.fixture_inputs(reference), **{str(p): r.sha(p) for p in
        (HERE/'probe_patch.py', LINEAGE, patch.HELPER, patch.ORIGINAL, patch.PATCH_SOURCE, *patch.EXTRA_INPUTS)})


def compile_probe(lease, baseline, scripts, compiler, fixture):
    seed = lineage.read_seed(reference)
    staging = HERE/'source-staging'/uuid.uuid4().hex
    patch.prepare(Path(seed['frozenSourcePath']), staging/'src')
    after = base.tree_hashes(staging/'src')
    changed = sorted(k for k in set(after)|set(seed['frozenSourceSHA256']) if after.get(k)!=seed['frozenSourceSHA256'].get(k))
    assert changed == patch.CHANGED and len(after) == 86
    origin = staging/'source-origin.json'
    r.save(origin, dict(version=VERSION, seedReceiptSHA256=reference.SEED_SHA,
        seedProbeSHA256=reference.PROBE_SHA, seedSourceSHA256=seed['frozenSourceSHA256'],
        stagedSHA256=after, changed=changed, fixtureInputs=fixture))
    path = shared.compile_frozen(lease, staging/'src', baseline, scripts, compiler, fixture)
    value = r.read(path)
    value.update(cameraWorldVersion=VERSION, sourceOrigin=str(origin), sourceOriginSHA256=r.sha(origin))
    r.save(path, value)
    return path


def verify_probe(path, baseline, scripts, compiler, fixture):
    value = base.verify_probe(path, baseline, scripts, compiler, fixture)
    assert value['cameraWorldVersion'] == VERSION
    seed = lineage.read_seed(reference)
    origin_path = Path(value['sourceOrigin'])
    assert r.sha(origin_path) == value['sourceOriginSHA256']
    origin = r.read(origin_path)
    assert origin['seedReceiptSHA256'] == reference.SEED_SHA and origin['seedProbeSHA256'] == reference.PROBE_SHA
    assert origin['seedSourceSHA256'] == seed['frozenSourceSHA256'] and origin['changed'] == patch.CHANGED
    assert origin['fixtureInputs'] == fixture and origin['stagedSHA256'] == value['frozenSourceSHA256']
    changed = sorted(k for k in set(value['frozenSourceSHA256'])|set(seed['frozenSourceSHA256'])
        if value['frozenSourceSHA256'].get(k) != seed['frozenSourceSHA256'].get(k))
    assert changed == patch.CHANGED and len(value['frozenSourceSHA256']) == 86
    frozen, source = Path(value['frozenSourcePath']), Path(seed['frozenSourcePath'])
    assert (frozen/'ContinuousSceneMotionProbe.as').read_text('utf-8-sig') == patch.transform((source/'ContinuousSceneMotionProbe.as').read_text('utf-8-sig'))
    assert r.sha(frozen/'tests/SceneCameraRasterTrial.as') == r.sha(patch.HELPER)
    assert r.sha(frozen/'SceneTilePresentation.as') == r.sha(patch.PRESENTER)
    return value


def options(name):
    return reference.options(name)+['--draw-control','tilecrop','--presentation-check']


def metric(values):
    ordered = sorted(values)
    return dict(count=len(values), mean=statistics.mean(values), median=statistics.median(values),
                p95=ordered[math.ceil(len(ordered)*.95)-1], maximum=max(values))


def summarize(raw):
    assert raw['ok'] and raw['error'] is None and not raw['samples']
    cfg=raw['config'];assert cfg['drawControl']=='tilecrop' and cfg['presentationCheck']
    assert cfg['noLighting'] and cfg['noWall'] and not cfg['vision']
    trial,cleanup=raw['cameraRaster'],raw['cameraRasterCleanup']
    assert trial['version']==VERSION and trial['complete'] and trial['passed'] and not trial['errors']
    assert trial['nativeMenuChildren'] and all(x['className']!='visMainMenu' for x in trial['nativeMenuChildren'])
    assert cleanup==trial['cleanup'] and cleanup['restored'] and not cleanup['errors'] and cleanup['pendingOwnedBitmaps']==0
    end=cleanup['presentation'];assert not end['active'] and end['parents']==0
    assert end['enables']==end['restores'] and end['allocated']==end['disposed']
    assert end['texturesCreated']==end['texturesDisposed']>1
    assert end['contextCreates']==end['contextDisposals']==1 and end['gpuBytes']==end['liveCPUBytes']==0 and not end['ready'] and not end['error']
    assert end['liveAnimation'] and end['clipsStopped']==end['clipsResumed']==0
    assert end['timelinesRestored'] and end['worldPrepared'] and end['captureCullRestored']
    assert end['layerWrites']==end['layerRestores'] and end['animationChanges']>0 and end['actorRasterCalls']>0
    assert end['poseBytes']==0 and end['poseEntries']==0
    assert end['actorVisibilityWrites']==end['actorVisibilityRestores']
    assert end['oracleCalls']==18 and len(end['oracleChecks'])==18 
    assert 'software' not in end['initial']['driverInfo'].lower()
    assert end['captures']==18 and trial['pixelBitmapsCreated']==trial['pixelBitmapsDisposed']==335
    assert trial['attributionOnlyWithRejectedPixels']
    assert trial['pixelsValid']==trial['visualAccepted']==all(p['visualAccepted'] for p in trial['pixels'])
    assert len(trial['pixels'])==18 and len(trial['nativeWarmups'])==23
    for warm in trial['nativeWarmups']:
        assert warm['passed'] and len(warm['preparationReturns'])==3 and len(warm['checks'])==3
        assert all(x['pixels']['equal'] and x['pixels']['differentPixels']==0 for x in warm['checks'])
    for pixel in trial['pixels']:
        assert pixel['visualAccepted']==(pixel['candidate']['maxRGB']<=2 and pixel['candidate']['maxAlpha']==0)
        assert pixel['passed']==pixel['visualAccepted'] # Restore is independently exact below.
        assert pixel['restore']['equal'] and pixel['restore']['differentPixels']==0
        assert pixel['presentation']['active'] and pixel['presentation']['parents']==2
    assert trial['testFrameRate']==120 and trial['stabilizationFrames']==12
    assert 1<=len(trial['preparePasses'])<=12 and trial['preparePasses'][-1]['quiet']
    assert all(v==0 for v in trial['preparePasses'][-1]['delta'].values())
    assert trial['zeroRasterWork'] and all(v==0 for v in trial['timingRasterDelta'].values())
    assert len(trial['windows'])==8 and len(trial['framesMs'])==len(trial['sampleAtMs'])==960
    keys=('sceneRedraws','sceneDrawMs','sceneResident','sceneEvictions','sceneMisses','sceneWarmCount','sceneWarmSlices','sceneWarmForced')
    initial=trial['timingStart'];previous=trial['timingStartAtMs'];intervals=[];stamps=[];rows=[]
    modes=('native-static','native-moving','gpu-static','gpu-moving')
    first=trial['windows'][0]['presentation'][0]
    for i,(row,condition) in enumerate(zip(trial['windows'],(0,1,2,3,3,2,1,0))):
        cached=condition>=2
        assert row['index']==i and row['condition']==condition and row['mode']==modes[condition]
        assert row['cached'] is cached and row['moving'] is (condition%2==1) and row['startAtMs']==previous
        for key in ('framesMs','sampleAtMs','vx','vy','cameraX','cameraY','gg','scene','workMs','worldVisible','windowVisible','presentation'):
            assert len(row[key])==120,key
        assert all(v is (not cached) for v in row['worldVisible']) and all(v is True for v in row['windowVisible'])
        positions=set(zip(row['vx'],row['vy']));assert (len(positions)>1) if row['moving'] else len(positions)==1
        assert all(x==initial['gg'] for x in row['gg'])
        for scene in row['scene']:
            assert all(scene[k]==initial['scene'][k] for k in keys)
        for p in row['presentation']:
            assert p['active'] is cached and p['parents']==(2 if cached else 0) and p['actualCache'] is cached
            assert p['liveAnimation'] and p['clipsStopped']==p['clipsResumed']==0
            assert p['layerWrites']==p['layerRestores'] and 0<=p['liveCPUBytes']<=128*1024*1024
            assert p['captures']==13 and p['contextCreates']==1 and p['contextDisposals']==0 and p['clipsResumed']==0
        for stamp,dt in zip(row['sampleAtMs'],row['framesMs']):
            assert stamp-previous==dt and dt>=0;previous=stamp
        assert row['endAtMs']==previous and row['copiesEnd']>=row['copiesStart']
        assert row['allocatedEnd']>=row['allocatedStart']
        intervals.extend(row['framesMs']);stamps.extend(row['sampleAtMs'])
        rows.append(dict(index=i,condition=condition,mode=row['mode'],frame=metric(row['framesMs']),workMs=sum(row['workMs'])))
    assert intervals==trial['framesMs'] and stamps==trial['sampleAtMs']
    assert previous==trial['timingEndAtMs'] and sum(intervals)==trial['timingElapsedMs']==previous-trial['timingStartAtMs']
    arms={name:metric([v for row in trial['windows'] if row['mode']==name for v in row['framesMs']]) for name in modes}
    pairs=[dict(nativeIndex=a,gpuIndex=b,meanDeltaMs=rows[b]['frame']['mean']-rows[a]['frame']['mean']) for a,b in ((1,3),(6,4))]
    return dict(version=VERSION,complete=True,diagnosticOnly=True,performanceEligible=False,gameplayAcceptance=False,deployed=False,
        rows=rows,arms=arms,pairs=pairs,elapsedMs=sum(intervals),zeroNativeRasterWork=True,pixels=trial['pixels'],cleanup=cleanup,visualAccepted=trial['visualAccepted'],
        limits=['Candidate pixels may fail RGB2 and remain explicitly rejected; this is only a fixed-picture cost upper bound.',
                'Layer cache with live Flash timelines; simulation paused, no gameplay/combat claim; mutation tracking incomplete.',
                'Direct ENTER_FRAME intervals, not physical presents; all spikes and boundary work retained.',
                'GPU readback plus native Stage.draw, no actual OS-window presentation acceptance.'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name',required=True);parser.add_argument('--registry-wait',type=int,default=300)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--compile-probe',action='store_true');group.add_argument('--probe-build',type=Path)
    args=parser.parse_args()
    assert __debug__ and args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
    folder=r.E/args.name;assert not folder.exists(),'Keep prior evidence'
    record=dict(version=VERSION,options=options(args.name),diagnosticOnly=True,deployed=False)
    with m.Registration(owner='ContinuousScene / camera ordered actor sprites / 01a13816',purpose=args.name,
            run_dir=m.RUNTIME,evidence=folder,resource='game',wait=args.registry_wait) as lease:
        try:
            assert not m.air_pids(),'Other AIR remains untouched'
            memory=control.memory_gate()
            baseline,scripts,compiler,fixture=r.baseline(),runner_inputs(),support.compiler_inputs(),fixture_inputs()
            runtime=reference.runtime_inputs();assert len(baseline)==526 and len(runtime)==13
            for key,digest in PINS.items():assert baseline[key]==digest,key
            record.update(baseline=baseline,runnerInputs=scripts,compilerInputs=compiler,fixtureInputs=fixture,runtimeInputs=runtime,memoryBefore=memory)
            path=compile_probe(lease,baseline,scripts,compiler,fixture) if args.compile_probe else args.probe_build.resolve()
            probe=verify_probe(path,baseline,scripts,compiler,fixture)
            m.prepare();shutil.copy2(probe['probePath'],m.RUNTIME/base.PROBE_PATH)
            for key,digest in baseline.items():
                if key not in ('application.xml','mods/loader-manifest.txt'):assert r.sha(m.RUNTIME/key)==digest,key
            assert baseline==r.baseline() and scripts==runner_inputs() and runtime==reference.runtime_inputs()
            record.update(probeBuildPath=str(path),probeSHA256=probe['probeSHA256'],memoryBeforeAir=control.memory_gate())
            run_error=None
            try:m.run_owned(m.parse_args(record['options']),lease)
            except BaseException as error:
                run_error=error;record.update(executionError=repr(error),executionTraceback=traceback.format_exc())
            finally:
                if folder.exists():
                    r.save(folder/'probe-build.json',probe);r.save(folder/'runner-inputs.json',record)
            assert baseline==r.baseline() and scripts==runner_inputs() and compiler==support.compiler_inputs()
            assert fixture==fixture_inputs() and runtime==reference.runtime_inputs()
            verify_probe(path,baseline,scripts,compiler,fixture)
            if not (folder/'storage/result.json').is_file():
                if run_error:raise run_error
                raise RuntimeError('No retained result; original process evidence preserved')
            raw,actual=reference.read_retained_result(folder)
            for key,digest in baseline.items():
                if key not in ('application.xml','mods/loader-manifest.txt'):assert actual[key]==digest,key
            assert actual[base.PROBE_PATH]==probe['probeSHA256']
            policy=r.read(folder/'process-policy.json')
            assert policy['desktopPolicy']=='private' and not policy['performanceEligible']
            assert not policy.get('otherAirProcessIds') and not policy.get('memoryAbort') and not policy.get('runFailure')
            summary=summarize(raw)
            summary.update(resultSHA256=r.sha(folder/'storage/result.json'),probeSHA256=probe['probeSHA256'],inputsUnchanged=True,runtimeInputsUnchanged=True)
            r.save(folder/'summary.json',summary)
            if run_error:raise run_error
            lease.outcome='passed';lease.note='960 native versus live timeline layer-cache intervals; simulation paused, no deployment'
            print(json.dumps(dict(name=args.name,complete=True,arms=summary['arms'],pairs=summary['pairs'])),flush=True)
        except BaseException as error:
            folder.mkdir(parents=True,exist_ok=True)
            r.save(folder/'runner-failure.json',dict(record,error=repr(error),traceback=traceback.format_exc(),complete=False,deployed=False))
            lease.outcome='failed';lease.note=repr(error);raise


shared.HERE,shared.VERSION=HERE,VERSION
shared.runner_inputs,shared.fixture_inputs=runner_inputs,fixture_inputs
base.OUT=HERE/'probe-builds'
base.runner_inputs,base.candidate_inputs=runner_inputs,fixture_inputs
if __name__=='__main__':main()
