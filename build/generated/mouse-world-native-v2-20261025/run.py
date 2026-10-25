"""Real native center pointer plus existing world mousetree ABBA. Diagnostic only."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
import traceback
import uuid

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
VERSION='mouse-world-native-2'
MODE='mousetree'
FIXTURE='dense-sprint-smg10-1'
HELPER_SHA='88CB531E1836B9B4BD430AFD862272C0F5FE166A2899621AB5C6239BFF7B93D4'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

reference=load('world_mouse_window_support',HERE.parent/'window-visibility-native-20261025/run.py')
old=reference.old
shared,control,dense,base,r,m,support=(reference.shared,reference.control,reference.dense,reference.base,reference.r,reference.m,reference.support)
patch=load('world_mouse_patch',HERE/'probe_patch.py')
owned=load('world_mouse_owned_input',HERE/'owned_mouse.py')
HELPER=HERE/'SceneWorldMouseProbe.as'
SEED=reference.SEED
SEED_SHA,PROBE_SHA=reference.SEED_SHA,reference.PROBE_SHA
PINS=dict(reference.PINS)

def seed():
    value=reference.seed()
    assert value['probeSHA256']==PROBE_SHA==patch.SOURCE_PROBE and len(value['frozenSourceSHA256'])==85
    return value

def runner_inputs():
    assert len(HELPER_SHA)==64 and r.sha(HELPER)==HELPER_SHA,'Mouse helper not frozen'
    return dict(reference.runner_inputs(),**{str(p):r.sha(p) for p in
        (Path(reference.__file__),HERE/'run.py',HERE/'probe_patch.py',HERE/'owned_mouse.py',HERE/'README.md',HELPER,owned.CAPABILITY)})

def fixture_inputs():
    return dict(reference.fixture_inputs(),**{str(p):r.sha(p) for p in (HERE/'probe_patch.py',HERE/'owned_mouse.py',HELPER)})

def runtime_inputs():return reference.runtime_inputs()

def compile_probe(lease,baseline,scripts,compiler,fixture):
    value=seed();staging=HERE/'source-staging'/uuid.uuid4().hex
    patch.prepare(Path(value['frozenSourcePath']),staging/'src')
    after=base.tree_hashes(staging/'src')
    changed=sorted(k for k in set(after)|set(value['frozenSourceSHA256']) if after.get(k)!=value['frozenSourceSHA256'].get(k))
    assert changed==patch.CHANGED and len(after)==86
    origin=staging/'source-origin.json'
    r.save(origin,dict(version=VERSION,seedReceiptSHA256=SEED_SHA,seedProbeSHA256=PROBE_SHA,
        seedSourceSHA256=value['frozenSourceSHA256'],stagedSHA256=after,changed=changed,fixtureInputs=fixture))
    path=shared.compile_frozen(lease,staging/'src',baseline,scripts,compiler,fixture)
    receipt=r.read(path);receipt.update(worldMouseVersion=VERSION,denseFixture=FIXTURE,
        observerFixtureSource=dense.VERSION,sourceOrigin=str(origin),sourceOriginSHA256=r.sha(origin))
    r.save(path,receipt);return path

def verify_probe(path,baseline,scripts,compiler,fixture):
    raw=r.read(path);assert path.resolve()==(Path(raw['probePath']).parent/'probe-build.json').resolve()
    value=base.verify_probe(path,baseline,scripts,compiler,fixture);source=seed()
    assert value['worldMouseVersion']==VERSION and value['denseFixture']==FIXTURE and value['observerFixtureSource']==dense.VERSION
    op=Path(value['sourceOrigin']);assert r.sha(op)==value['sourceOriginSHA256'];origin=r.read(op)
    assert origin['seedReceiptSHA256']==SEED_SHA and origin['seedProbeSHA256']==PROBE_SHA
    assert origin['seedSourceSHA256']==source['frozenSourceSHA256'] and origin['changed']==patch.CHANGED
    assert origin['stagedSHA256']==value['frozenSourceSHA256'] and origin['fixtureInputs']==fixture
    changed=sorted(k for k in set(value['frozenSourceSHA256'])|set(source['frozenSourceSHA256'])
        if value['frozenSourceSHA256'].get(k)!=source['frozenSourceSHA256'].get(k))
    assert changed==patch.CHANGED and len(value['frozenSourceSHA256'])==86
    frozen,source_root=Path(value['frozenSourcePath']),Path(source['frozenSourcePath'])
    assert (frozen/'ContinuousSceneMotionProbe.as').read_text('utf-8-sig')==patch.transform((source_root/'ContinuousSceneMotionProbe.as').read_text('utf-8-sig'))
    assert r.sha(frozen/'tests/SceneWorldMouseProbe.as')==HELPER_SHA
    return value

def options(name):return reference.options(name)+['--draw-control',MODE]

def summarize(result,policy,name):
    cfg,motion=result['config'],result['nativeInputMotion']
    assert result['ok'] and result['error'] is None and len(result['samples'])==4
    assert len(result['assertions'])==30 and all(item['ok'] for item in result['assertions'])
    assert cfg['benchmark']=='scene' and cfg['drawControl']==MODE and not cfg['presentationCheck']
    assert cfg['nativeInputMotion'] and cfg['nativeSprint'] and cfg['stableMotion'] and cfg['playerFire']
    assert cfg['fixedEnemies'] and cfg['combatRoute'] and not cfg['localEnemies']
    assert cfg['noLighting'] and cfg['noWall'] and not cfg['vision'] and not cfg['satsCheck']
    assert not any(cfg[k] for k in ('profile','culling','sleepingRootShort','bulletSegments','worldProfile',
        'locationProfile','guiWeaponProfile','playerStepProfile','playerAnimateProfile','impactABBA','fogABBA','fogTypedABBA'))
    assert result['denseFixture']['version']==FIXTURE and result['denseFixture']['enemyWeapon']=='smg10'
    assert result['denseFixture']['actors']==6 and motion['version']=='native-input-dense-sprint-2'
    assert result['driver']['forcedPositionCalls']==0 and motion['spawn']['calls']==1
    assert motion['warmup']['ready'] and motion['warmup']['roundTrips']>=1 and motion['warmup']['groundContactRun']>=10
    assert motion['timingStart']['floorContact'] and motion['route']['terrainVerified']
    assert result['world']['layoutSeed']==20261019 and result['viewport']['zoom']==1
    assert (result['world']['width'],result['world']['height'])==(240,125)
    assert result['observerPolicy']==dict(version='dense-observer-lean-2',settingsDuringTiming=False,
        segmentProgressWrites=False,segmentCensus=False,finalCensus=True,heartbeatIntervalMs=5000,continuousFramesRetained=True)
    input_proof=policy['worldMouseInput'];end=result['worldMouseCleanup']
    assert input_proof['complete'] and input_proof['attempts']==1 and not input_proof['errors'] and input_proof['post']['accepted']
    assert end['accepted'] and end['cleared'] and end['titleRestored'] and end['visibilityRestored'] and not end['errors'] and end['sampled']==1200
    assert result['worldMouseTreeRestored'] and end['proof']==input_proof['proof'] and end['ready']==input_proof['ready']
    assert end['released']['nativeWorldContinued'] and not end['released']['probeWarmupStarted']
    assert end['released']['allStat']==1 and not end['released']['onPause'] and end['released']['gateTicks']>=1
    ready=end['ready'];x,y=ready['targetX'],ready['targetY']
    continuous=dense.continuous(result);rows=[];count=0
    old.six_smg10(result['playerFireWarmup']['encounter'])
    for index,row in enumerate(result['samples']):
        assert len(row['continuousFramesMs'])==len(row['worldMouse'])==300 and row['empty']==row['misses']==0
        assert row['playerShotFrames']>0 and row['enemyShotFrames']>0
        old.six_smg10(row['encounter'])
        for item in row['combatWindows']:old.six_smg10(item['encounter'])
        assert 'activityCensus' not in row and sum(row['probeTiming']['censusMs'])==sum(row['probeTiming']['progressSaveMs'])==0
        enabled=index not in (1,2)
        assert row['mouseTree']['children'] is enabled and row['mouseTree']['enabled'] is enabled
        for frame in row['worldMouse']:
            count+=1
            assert frame['sample']==count and frame['appId']==ready['appId']
            assert (frame['stageWidth'],frame['stageHeight'])==(ready['stageWidth'],ready['stageHeight'])
            assert frame['mouseChildren'] is enabled and frame['mouseEnabled'] is enabled
            assert owned.cap.near(frame['stageMouseX'],x) and owned.cap.near(frame['stageMouseY'],y)
        rows.append(dict(index=index,mouseTreeEnabled=enabled,continuous=base.metrics(row['continuousFramesMs']),
            playerShots=row['playerShotFrames'],enemyShots=row['enemyShotFrames'],warmed=sum(row['warm']),slices=row['slices'],
            workload=dense.workload(row,motion['route'])))
    assert end['released']['atMs']<=result['samples'][0]['caseBeginAtMs']
    qualification=dict(actualSprint=sum(row['workload']['aboveWalkSpeedFrames'] for row in rows)>=30,
        concurrentFixtureBullets=any(v>=3 for row in result['samples'] for v in row['denseFrames']['fixtureBullets']),
        observedNativePlayerBullets=any(v>0 for row in result['samples'] for v in row['denseFrames']['playerBullets']))
    qualification['passed']=all(qualification.values())
    return dict(version=VERSION,name=name,passed=qualification['passed'],complete=True,diagnosticOnly=True,
        performanceEligible=False,performanceAcceptance=False,gameplayAcceptance=False,deployed=False,
        qualification=qualification,continuous=continuous,rows=rows,inputProof=input_proof,mouseCleanup=end,
        limits=['One posted native mouse message and real event/Timer proof before warmup; no physical cursor or general input compatibility claim.',
            'Phase3 wait stops only probe warmup/input driving. Native AI, physics and prewarming continue; wait/release state is retained.',
            'The existing 29AF SMG camera aim and attack driver is byte-preserved in all arms; it is not evidence of real pointer input.',
            'Private window visible=true throughout; no activation or global cursor change. All 1200 intervals include switching and per-frame mouse observation.',
            'This diagnostic disables world hit testing in B and cannot be deployed as gameplay-compatible optimization.'])

def main():
    assert __debug__
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name',required=True);parser.add_argument('--registry-wait',type=int,default=600)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--compile-probe',action='store_true');group.add_argument('--probe-build',type=Path)
    args=parser.parse_args();assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
    folder=r.E/args.name;assert not folder.exists(),'Preserve old evidence'
    execute,adapter,handshake=owned.policy_adapter(m)
    record=dict(version=VERSION,options=options(args.name),processPolicyAdapter=adapter,diagnosticOnly=True,performanceEligible=False)
    with m.Registration(owner='ContinuousScene / real world mouse / 01a13816',purpose=args.name,
                        run_dir=m.RUNTIME,evidence=folder,resource='game',wait=args.registry_wait) as lease:
        try:
            assert not m.air_pids(),'Other AIR remains untouched'
            memory=control.memory_gate()
            baseline,scripts,compiler,fixture=r.baseline(),runner_inputs(),support.compiler_inputs(),fixture_inputs()
            runtime=runtime_inputs();assert len(baseline)==526 and len(runtime)==13
            for key,digest in PINS.items():assert baseline[key]==digest,key
            rv=r.read(old.RV_RECEIPT)
            assert rv['result']=='PASS' and rv['new'].upper()==old.RV_CURRENT and rv['before']['pfe.swf'].upper()==control.HOST
            record.update(baseline=baseline,runnerInputs=scripts,compilerInputs=compiler,fixtureInputs=fixture,runtimeInputs=runtime,memoryBefore=memory)
            path=compile_probe(lease,baseline,scripts,compiler,fixture) if args.compile_probe else args.probe_build.resolve()
            probe=verify_probe(path,baseline,scripts,compiler,fixture)
            m.prepare();shutil.copy2(probe['probePath'],m.RUNTIME/base.PROBE_PATH)
            for key,digest in baseline.items():
                if key not in ('application.xml','mods/loader-manifest.txt'):assert r.sha(m.RUNTIME/key)==digest,key
            launch=m.parse_args(record['options']);assert launch.draw_control==MODE and not launch.sats_check
            assert baseline==r.baseline() and scripts==runner_inputs() and runtime==runtime_inputs()
            record.update(probeBuildPath=str(path),probeSHA256=probe['probeSHA256'],memoryBeforeAir=control.memory_gate())
            run_error=None
            try:execute(launch,lease)
            except BaseException as error:
                run_error=error;record.update(executionError=repr(error),executionTraceback=traceback.format_exc())
            finally:
                if folder.exists():
                    r.save(folder/'probe-build.json',probe);r.save(folder/'runner-inputs.json',record)
                    r.save(folder/'world-mouse-input.json',handshake.report)
            assert baseline==r.baseline() and scripts==runner_inputs() and fixture==fixture_inputs()
            assert compiler==support.compiler_inputs() and runtime==runtime_inputs() and owned.policy_adapter(m)[1]==adapter
            verify_probe(path,baseline,scripts,compiler,fixture)
            result,actual=reference.read_retained_result(folder)
            for key,digest in baseline.items():
                if key not in ('application.xml','mods/loader-manifest.txt'):assert actual[key]==digest,key
            assert actual[base.PROBE_PATH]==probe['probeSHA256']
            policy=r.read(folder/'process-policy.json')
            assert policy['desktopPolicy']=='private' and not policy['performanceEligible'] and policy['diagnosticOnly']==owned.POLICY_REASON
            assert not policy.get('runFailure') and not policy.get('memoryAbort') and not policy.get('otherAirProcessIds')
            try:summary=summarize(result,policy,args.name)
            except Exception as error:
                summary=dict(version=VERSION,name=args.name,passed=False,complete=False,error=repr(error),
                    rawOK=result.get('ok'),rawError=result.get('error'),worldMouseCleanup=result.get('worldMouseCleanup'),
                    retainedSampleCount=len(result.get('samples',[])),diagnosticOnly=True,performanceEligible=False,deployed=False)
            summary.update(probeSHA256=probe['probeSHA256'],resultSHA256=r.sha(folder/'storage/result.json'),
                inputsUnchanged=True,runtimeInputsUnchanged=True,checks=len(result['assertions']),processPolicyAdapter=adapter)
            r.save(folder/'summary.json',summary)
            if run_error:raise run_error
            assert summary['passed'],'Real mouse ABBA incomplete; evidence retained'
            lease.outcome='passed';lease.note='One native pointer proof and 1200 world mouse-tree ABBA frames; diagnostic only'
            print(json.dumps({k:summary[k] for k in ('name','passed','complete','checks','qualification')}),flush=True)
        except BaseException as error:
            lease.outcome='failed';lease.note=repr(error);folder.mkdir(parents=True,exist_ok=True)
            r.save(folder/'runner-failure.json',dict(record,error=repr(error),worldMouseInput=handshake.report,complete=False,deployed=False));raise

shared.HERE,shared.VERSION=HERE,VERSION
shared.runner_inputs,shared.fixture_inputs=runner_inputs,fixture_inputs
base.OUT=HERE/'probe-builds'
base.runner_inputs,base.candidate_inputs=runner_inputs,fixture_inputs
if __name__=='__main__':main()
