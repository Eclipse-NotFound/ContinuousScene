"""Registered read-only player-leaf observations, then terminal cache pixels.

No cache change occurs in the 1200 native combat intervals. This is a component
qualification and window-state observation, never a candidate FPS benchmark.
"""
from pathlib import Path
import argparse
import ast
import hashlib
import importlib.util
import inspect
import json
import re
import shutil
import sys
import uuid

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
VERSION = 'player-leaf-cache-1'
MODE = 'playerleaf'
FIXTURE = 'dense-sprint-smg10-1'
SEED_SHA = '983727AEB832BC586AF3767613B7C9D61564D92DC9D8E2435F972EEBF1D1D5EE'
PROBE_SHA = '29AF34571E7181139C682AA32A160E2C217C1B02B295E6DCBD6931D8DB7F94E5'
HELPER_SHA = 'C6BEFB17B0779B7699A8C87B8A34CA2D89E08A45BCCEEC3174F22AF401A4500D'
PATCH_SHA = 'F3B5FB63DB230B0DA264026D6ED7810B36FE601BB77610FF8CF884F457E9F6FA'
POLICY_REASON = 'Read-only player leaf/window observations and terminal cache pixels; no performance acceptance'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


old = load('leaf_smg_support', HERE.parent / 'camera-atlas-paged-combat-20261025/run.py')
shared, control, dense, base, r, m, support = old.shared, old.control, old.dense, old.base, old.r, old.m, old.support
patch = load('leaf_component_patch', HERE / 'probe_patch.py')
HELPER = HERE / 'SceneLeafCacheTrial.as'
SEED = r.E / 'camera-atlas-paged-combat-20261025-r1/probe-build.json'
PINS = dict(old.PINS)


def seed():
    assert r.sha(SEED) == SEED_SHA
    value = r.read(SEED)
    original = Path(value['probePath']).parent / 'probe-build.json'
    assert r.sha(original) == SEED_SHA and r.read(original) == value
    for field in ('runnerInputs', 'compilerInputs', 'candidateInputs'):
        for path, digest in value[field].items(): assert r.sha(Path(path)) == digest, (field, path)
    checked = old.verify_probe(original, value['productionSHA256'], value['runnerInputs'],
        value['compilerInputs'], value['candidateInputs'])
    assert checked == value and value['probeSHA256'] == PROBE_SHA == patch.SOURCE_PROBE
    assert len(value['frozenSourceSHA256']) == 85 and value['denseFixture'] == FIXTURE
    return value


def runner_inputs():
    assert HELPER_SHA and PATCH_SHA, 'The new component sources are not frozen'
    assert r.sha(HELPER) == HELPER_SHA and r.sha(HERE / 'probe_patch.py') == PATCH_SHA
    return dict(old.runner_inputs(), **{str(p): r.sha(p) for p in
        [Path(old.__file__), Path(shared.__file__), Path(m.__file__), HERE / 'run.py',
         HERE / 'probe_patch.py', HERE / 'README.md', HELPER, SEED]})


def fixture_inputs():
    value = seed()
    return {str(p): r.sha(p) for p in [SEED, Path(value['probePath']), Path(value['configPath']),
        Path(value['sourceOrigin']), Path(value['probePath']).parent / 'probe-build.json',
        HERE / 'probe_patch.py', HELPER, support.OUT / 'source-provenance.json']}


def policy_adapter():
    original = inspect.getsource(m.run_owned)
    anchor = "    if getattr(args,'draw_control',None)=='rcnative':"
    inserted = ("    if getattr(args,'draw_control',None)=='playerleaf':\n"
        "        policy['performanceEligible']=False\n"
        "        policy['diagnosticOnly']=" + repr(POLICY_REASON) + "\n" + anchor)
    assert original.count(anchor) == 1 and inserted not in original
    changed = original.replace(anchor, inserted, 1)
    assert changed.replace(inserted, anchor, 1) == original
    assert "current['availableCommit']<512*1024**2" in changed
    assert 'HiddenProcess(' in changed and 'record.child(process.pid)' in changed
    tree = ast.parse(changed)
    assert len(tree.body) == 1 and isinstance(tree.body[0], ast.FunctionDef) and tree.body[0].name == 'run_owned'
    scope = dict(m.__dict__); exec(compile(tree, '<leaf-component-policy-only>', 'exec'), scope)
    assert scope['run_owned'] is not m.run_owned and scope['run_owned'].__globals__ is not m.__dict__
    digest = lambda text: hashlib.sha256(text.encode('utf-8')).hexdigest().upper()
    return scope['run_owned'], dict(originalSHA256=digest(original), transformedSHA256=digest(changed),
        reverseExact=True, sharedModuleModified=False, onlyChange='Add diagnostic policy classification',
        runGuardBytes=512*1024**2)


def compile_probe(lease, baseline, scripts, compiler, fixture):
    value = seed(); staging = HERE / 'source-staging' / uuid.uuid4().hex
    patch.prepare(Path(value['frozenSourcePath']), staging / 'src')
    after = base.tree_hashes(staging / 'src')
    changed = sorted(k for k in set(after) | set(value['frozenSourceSHA256'])
        if after.get(k) != value['frozenSourceSHA256'].get(k))
    assert changed == patch.CHANGED and len(after) == 86
    origin = staging / 'source-origin.json'
    r.save(origin, dict(version=VERSION, seedReceiptSHA256=SEED_SHA, seedProbeSHA256=PROBE_SHA,
        seedSourceSHA256=value['frozenSourceSHA256'], stagedSHA256=after, changed=changed, fixtureInputs=fixture))
    path = shared.compile_frozen(lease, staging / 'src', baseline, scripts, compiler, fixture)
    receipt = r.read(path)
    receipt.update(playerLeafVersion=VERSION, denseFixture=FIXTURE, observerFixtureSource=dense.VERSION,
        sourceOrigin=str(origin), sourceOriginSHA256=r.sha(origin))
    r.save(path, receipt); return path


def verify_probe(path, baseline, scripts, compiler, fixture):
    raw = r.read(path)
    original = Path(raw['probePath']).parent / 'probe-build.json'
    assert path.resolve() == original.resolve(), 'Pass original build receipt beside compile.log: ' + str(original)
    value = base.verify_probe(path, baseline, scripts, compiler, fixture)
    assert value['playerLeafVersion'] == VERSION and value['denseFixture'] == FIXTURE
    assert value['observerFixtureSource'] == dense.VERSION
    op = Path(value['sourceOrigin']); assert r.sha(op) == value['sourceOriginSHA256']
    origin, source = r.read(op), seed()
    assert origin['seedReceiptSHA256'] == SEED_SHA and origin['seedProbeSHA256'] == PROBE_SHA
    assert origin['seedSourceSHA256'] == source['frozenSourceSHA256'] and origin['changed'] == patch.CHANGED
    assert origin['stagedSHA256'] == value['frozenSourceSHA256'] and origin['fixtureInputs'] == fixture
    changed = sorted(k for k in set(value['frozenSourceSHA256']) | set(source['frozenSourceSHA256'])
        if value['frozenSourceSHA256'].get(k) != source['frozenSourceSHA256'].get(k))
    assert changed == patch.CHANGED and len(value['frozenSourceSHA256']) == 86
    frozen, original_source = Path(value['frozenSourcePath']), Path(source['frozenSourcePath'])
    assert (frozen / 'ContinuousSceneMotionProbe.as').read_text('utf-8-sig') == patch.transform(
        (original_source / 'ContinuousSceneMotionProbe.as').read_text('utf-8-sig'))
    assert r.sha(frozen / HELPER.name) == HELPER_SHA
    return value


def options(name):
    args = old.options(name)
    assert args[-2:] == ['--draw-control', 'atlas']
    return args[:-2]


CONTENT = ('id','parent','shape','frame','totalFrames','isPlaying','children','cache','filters','mask',
    'blendMode','visible','alpha','shapeVisible','shapeAlpha','shapeCache','shapeFilters','shapeMask','shapeBlendMode',
    'matrix','color','shapeMatrix','shapeColor')


def window_observation(value):
    assert isinstance(value.get('errors'), list)
    if value['errors']: return False
    stage, window = value['stage'], value['nativeWindow']
    assert all(k in stage for k in ('displayState','frameRate','quality','stageWidth','stageHeight'))
    assert all(k in window for k in ('visible','active','closed','displayState','renderMode','bounds','applicationActiveWindowMatches'))
    assert all(type(window[k]) is bool for k in ('visible','active','closed','applicationActiveWindowMatches'))
    assert all(base.finite(stage[k]) for k in ('frameRate','stageWidth','stageHeight'))
    assert stage['frameRate'] > 0 and stage['stageWidth'] > 0 and stage['stageHeight'] > 0
    assert all(base.finite(window['bounds'][k]) for k in ('x','y','width','height'))
    return not window['closed']


def leaf_review(result):
    report = result['leafCache']; assert report['version'] == VERSION
    assert report['target'] == 'pfe_fla::sleg20_53' and report['diagnosticOnly'] and not report['performanceEligible']
    assert report['policy'] == dict(minimumStableRunFrames=120,maximumTopologyChangesPer120Frames=1,
        pixelMaxRGB=2,pixelMaxAlpha=0,restoreExact=True)
    frames = [f for row in result['samples'] for f in row.get('leafCache',{}).get('frames',[])]
    if len(frames) == 1200:
        samples=present=eligible=changes=topology=run=maximum=scan_ms=0; prior=None; previous=None
        for index,row in enumerate(result['samples']):
            segment=row['leafCache']; assert len(segment['frames']) == 300
            if previous is not None: assert segment['start'] == previous
            else:
                assert segment['start']['samples'] == 0 and segment['start']['scanNodes'] > 0
                nodes=segment['start']['scanNodes']
            for age,f in enumerate(segment['frames']):
                assert f['window'] == index and f['frame'] == age
                leaf=f['leaf']; assert (leaf is not None) == (f['matches'] == 1)
                samples+=1; present+=int(leaf is not None); eligible+=int(leaf is not None and leaf['eligible'])
                if prior and (not leaf or any(leaf[k] != prior[k] for k in ('id','parent','shape'))): topology+=1
                if leaf and leaf['eligible'] and prior and all(leaf[k] == prior[k] for k in CONTENT): run+=1
                else:
                    if prior: changes+=1
                    run=1 if leaf and leaf['eligible'] else 0
                maximum=max(maximum,run)
                assert f['stableRun'] == run and isinstance(f['scanMs'],int) and f['scanMs'] >= 0
                assert isinstance(f['scanNodes'],int) and f['scanNodes'] > 0
                scan_ms+=f['scanMs']; nodes+=f['scanNodes']; prior=leaf
                if leaf:
                    assert leaf['className'] == report['target']
                    if leaf['eligible']:
                        assert leaf['cache'] is False and not leaf['isPlaying']
                        assert leaf['frame']==leaf['totalFrames']==leaf['children']==1
                        assert leaf['filters']==leaf['mask']==leaf['shapeFilters']==leaf['shapeMask']==0
                        assert not leaf['shapeCache'] and leaf['blendMode']==leaf['shapeBlendMode']=='normal'
            expected=dict(samples=samples,present=present,eligible=eligible,contentChanges=changes,
                topologyChanges=topology,currentStableRun=run,maxStableRun=maximum,scanMs=scan_ms,
                scanNodes=nodes,pendingRestore=0,created=0,disposed=0)
            assert segment['end'] == expected
            previous=expected
        assert report['observation'] == previous
        assert report['frequentReplacement'] is (topology > samples//120)
        assert report['stabilityAccepted'] is (report['complete'] and present==samples and eligible==samples and run>=120 and topology<=samples//120)
    else:
        assert not report['complete'] and not report['passed'] and not report['pixels']['attempted']
    cleanup=report['cleanup']; assert result['leafCacheCleanup'] == cleanup
    assert cleanup['restored'] and cleanup['pendingRestore']==0 and cleanup['created']==cleanup['disposed'] and cleanup['errors']==[]
    pixels=report['pixels']
    if pixels['attempted']:
        assert len(frames)==1200 and report['stabilityAccepted'] and pixels['afterFinalTimingSample']
        assert 0<=cleanup['created']<=3
        if pixels['errors']:
            assert not pixels['passed']  # A failed terminal eligibility check need not allocate images.
        else:
            assert cleanup['created']==cleanup['disposed']==3
            visibility=pixels['visibility'];bounds=visibility['bounds'];stage=report['finalWindow']['stage']
            assert all(visibility[k] for k in ('onStage','ancestryReachesStage','effectiveVisible','finiteBounds','intersectsStage'))
            assert base.finite(visibility['effectiveAlpha']) and visibility['effectiveAlpha']>0
            assert all(base.finite(bounds[k]) for k in ('x','y','width','height'))
            assert bounds['width']>0 and bounds['height']>0
            assert bounds['x']<stage['stageWidth'] and bounds['y']<stage['stageHeight']
            assert bounds['x']+bounds['width']>0 and bounds['y']+bounds['height']>0
            assert pixels['stateRestored'] and pixels['restored']['exactEqual']
            for key in ('cached','restored'):
                p=pixels[key]
                assert p['exactEqual'] is (p['changedPixels']==0)
                assert p['withinTolerance'] is (p['maxRGB']<=2 and p['maxAlpha']==0)
            assert pixels['restored']['changedPixels']==pixels['restored']['maxRGB']==pixels['restored']['maxAlpha']==0
            assert pixels['passed'] is (pixels['cached']['withinTolerance'] and pixels['stateRestored'])
    else: assert cleanup['created']==0 and not report['passed']
    windows=dict(initial=window_observation(report['initialWindow']),final=window_observation(report['finalWindow']))
    expected_pass=report['stabilityAccepted'] and pixels.get('passed') is True and report['errors']==[] and cleanup['restored']
    assert report['passed'] is expected_pass
    reasons=[]; observed=report['observation']
    if not report.get('preflightPassed'):reasons.append('Exact initial native leaf/equipment qualification failed')
    if not report['complete']:reasons.append('The full 1200 native observations did not complete')
    if observed['present']!=observed['samples']:reasons.append('The exact leaf was missing or ambiguous during motion')
    if observed['eligible']!=observed['samples']:reasons.append('The exact leaf became ineligible during motion')
    if observed['currentStableRun']<120:reasons.append('Final content/identity stability was shorter than 120 frames')
    if report['frequentReplacement']:reasons.append('Topology transitions exceeded one per 120 observed frames')
    if pixels['attempted'] and not pixels['passed']:reasons.append('Terminal current-pose pixel comparison failed')
    if not all(windows.values()):reasons.append('Actual window state was not fully readable/open')
    return dict(observedFrames=len(frames),complete=report['complete'],componentPassed=report['passed'],
        outcome=report['outcome'],initialWindow=report['initialWindow'],finalWindow=report['finalWindow'],
        windowObservationValid=all(windows.values()),windowChecks=windows,observation=report['observation'],
        pixels=pixels,cleanup=cleanup,qualificationReasons=reasons,screenPresentationVerified=False)


def summarize(result, name):
    component=leaf_review(result); rows=[]; qualification={'passed':False}
    complete=len(result['samples'])==4 and component['observedFrames']==1200
    census_status=dict(present='finalActivityCensus' in result,requiredForSuccessfulRaw=True,absenceReason=None)
    if complete:
        cfg,motion=result['config'],result['nativeInputMotion']
        assert len(result['assertions'])==26 and all(x['ok'] for x in result['assertions'])
        assert cfg['benchmark']=='scene' and cfg['drawControl']==MODE and not cfg['presentationCheck']
        assert cfg['nativeInputMotion'] and cfg['nativeSprint'] and cfg['stableMotion'] and cfg['playerFire']
        assert cfg['fixedEnemies'] and not cfg['localEnemies'] and cfg['noLighting'] and cfg['noWall'] and not cfg['vision']
        assert not any(cfg[k] for k in ('profile','culling','sleepingRootShort','bulletSegments','worldProfile',
            'locationProfile','guiWeaponProfile','playerStepProfile','playerAnimateProfile','impactABBA','fogABBA','fogTypedABBA'))
        assert result['denseFixture']['version']==FIXTURE and result['denseFixture']['enemyWeapon']=='smg10'
        assert result['denseFixture']['actors']==6 and motion['version']=='native-input-dense-sprint-2'
        assert result['driver']['forcedPositionCalls']==0 and motion['spawn']['calls']==1
        assert motion['warmup']['ready'] and motion['warmup']['roundTrips']>=1 and motion['warmup']['groundContactRun']>=10
        assert motion['timingStart']['floorContact'] and motion['route']['terrainVerified']
        assert result['observerPolicy']==dict(version='dense-observer-lean-2',settingsDuringTiming=False,
            segmentProgressWrites=False,segmentCensus=False,finalCensus=True,heartbeatIntervalMs=5000,continuousFramesRetained=True)
        old.six_smg10(result['playerFireWarmup']['encounter'])
        for index,row in enumerate(result['samples']):
            assert row['name']=='leaf-observation-'+str(index) and row['empty']==row['misses']==0
            assert row['playerShotFrames']>0 and row['enemyShotFrames']>0
            old.six_smg10(row['encounter'])
            for item in row['combatWindows']:old.six_smg10(item['encounter'])
            assert 'activityCensus' not in row and sum(row['probeTiming']['censusMs'])==sum(row['probeTiming']['progressSaveMs'])==0
            rows.append(dict(index=index,continuous=base.metrics(row['continuousFramesMs']),
                playerShots=row['playerShotFrames'],enemyShots=row['enemyShotFrames'],
                combatWindows=base.combat_windows(row,300),workload=dense.workload(row,motion['route']),
                observationScanMs=sum(f['scanMs'] for f in row['leafCache']['frames'])))
        census=result.get('finalActivityCensus')
        if result['ok'] and not result['error']:assert census is not None,'Successful raw requires final census'
        if census is not None:
            assert census['afterFinalSample'] and census['data']
            assert result['samples'][-1]['sampleAtMs'][-1]<=census['startedAtMs']<=census['endedAtMs']
        else:
            assert not result['ok'] or result['error']
            census_status['absenceReason']='Original finish skips the final census after a component/raw error; observations retained as non-passing'
        qualification=dict(actualSprint=sum(x['workload']['aboveWalkSpeedFrames'] for x in rows)>=30,
            concurrentFixtureBullets=any(v>=3 for row in result['samples'] for v in row['denseFrames']['fixtureBullets']),
            observedNativePlayerBullets=any(v>0 for row in result['samples'] for v in row['denseFrames']['playerBullets']))
        qualification['passed']=all(qualification.values())
    passed=bool(result['ok'] and not result['error'] and complete and qualification['passed'] and component['componentPassed'] and component['windowObservationValid'])
    return dict(version=VERSION,name=name,complete=complete,passed=passed,outcome=component['outcome'],
        rawOK=result['ok'],rawError=result['error'],diagnosticOnly=True,performanceEligible=False,
        performanceAcceptance=False,gameplayAcceptance=False,deployed=False,qualification=qualification,
        continuous=dense.continuous(result) if complete else None,rows=rows,component=component,finalActivityCensus=census_status,
        limits=['All 1200 frames observe the unchanged native leaf; caching is terminal only, so there is no candidate FPS arm.',
            'A single final-pose Stage comparison does not prove animation/zoom/OS presentation equivalence.',
            'Window properties are read without show/activate/focus. Hidden or inactive status is recorded, not interpreted as a leaf failure.',
            'Missing/unstable target remains inconclusive/not-qualified; source and failed results remain unchanged.'])


def read_retained_result(folder):
    # Shared r.result rejects raw.ok=false before a component's inconclusive
    # outcome can be reviewed. Keep its independent loader/log/input checks,
    # but preserve that raw outcome for summarize and the final pass gate.
    result=r.read(folder/'storage/result.json');policy=r.read(folder/'process-policy.json')
    assert not policy['otherAirProcessIds'] and not policy.get('memoryAbort')
    loader=r.read(folder/'loader-check.json')
    assert len(loader['sessions'])==1 and len(loader['loaded'])==15 and all(loader['loaded'].values())
    log=(folder/'storage/tdfc.log').read_text('utf-8-sig')
    assert not re.search(r'\[(?:error|ui-error)\]',log),'TDFC runtime error'
    return result,{k.replace('\\','/'):v for k,v in r.read(folder/'inputs.json').items()}


def main():
    assert __debug__
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--name',required=True)
    parser.add_argument('--registry-wait',type=int,default=600)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--compile-probe',action='store_true');group.add_argument('--probe-build',type=Path)
    args=parser.parse_args();assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
    folder=r.E/args.name;assert not folder.exists(),'Preserve prior evidence'
    execute,adapter=policy_adapter()
    record=dict(version=VERSION,diagnosticOnly=True,performanceEligible=False,options=options(args.name),
        drawControlAssignment=MODE,processPolicyAdapter=adapter)
    with m.Registration(owner='ContinuousScene / player leaf component / 01a13816',purpose=args.name,
                        run_dir=m.RUNTIME,evidence=folder,resource='game',wait=args.registry_wait) as lease:
        try:
            assert not m.air_pids(),'Other AIR remains untouched'
            memory=control.memory_gate()
            baseline,scripts,compiler,fixture=r.baseline(),runner_inputs(),support.compiler_inputs(),fixture_inputs()
            assert len(baseline)==526
            for key,digest in PINS.items():assert baseline[key]==digest,key
            rv=r.read(old.RV_RECEIPT)
            assert rv['result']=='PASS' and rv['new'].upper()==old.RV_CURRENT and rv['before']['pfe.swf'].upper()==control.HOST
            record.update(baseline=baseline,runnerInputs=scripts,compilerInputs=compiler,fixtureInputs=fixture,memoryBefore=memory)
            path=compile_probe(lease,baseline,scripts,compiler,fixture) if args.compile_probe else args.probe_build.resolve()
            probe=verify_probe(path,baseline,scripts,compiler,fixture)
            m.prepare();shutil.copy2(probe['probePath'],m.RUNTIME/base.PROBE_PATH)
            for key,digest in baseline.items():
                if key not in ('application.xml','mods/loader-manifest.txt'):assert r.sha(m.RUNTIME/key)==digest,key
            assert baseline==r.baseline() and scripts==runner_inputs()
            launch=m.parse_args(record['options']);assert launch.draw_control is None
            launch.draw_control=MODE;assert not launch.profile and not launch.presentation_check
            record.update(probeBuildPath=str(path),probeSHA256=probe['probeSHA256'],memoryBeforeAir=control.memory_gate())
            run_error=None
            try:execute(launch,lease)
            except Exception as error:run_error=error
            finally:
                if folder.exists():
                    r.save(folder/'probe-build.json',probe);r.save(folder/'runner-inputs.json',record)
                    raw_path=folder/'storage/result.json'
                    if raw_path.exists():
                        raw=r.read(raw_path)
                        r.save(folder/'component-status.json',dict(rawOK=raw.get('ok'),rawError=raw.get('error'),
                            leafCache=raw.get('leafCache'),leafCacheCleanup=raw.get('leafCacheCleanup'),
                            executionError=repr(run_error) if run_error else None))
            assert baseline==r.baseline() and scripts==runner_inputs() and fixture==fixture_inputs()
            assert compiler==support.compiler_inputs() and policy_adapter()[1]==adapter
            verify_probe(path,baseline,scripts,compiler,fixture)
            result,actual=read_retained_result(folder)
            for key,digest in baseline.items():
                if key not in ('application.xml','mods/loader-manifest.txt'):assert actual[key]==digest,key
            assert actual[base.PROBE_PATH]==probe['probeSHA256']
            policy=r.read(folder/'process-policy.json')
            assert policy['desktopPolicy']=='private' and not policy['performanceEligible'] and policy['diagnosticOnly']==POLICY_REASON
            assert not policy.get('runFailure') and not policy.get('memoryAbort') and not policy.get('otherAirProcessIds')
            inventory_path=folder/'storage/leaf-inventory.json'
            inventory=r.read(inventory_path)
            assert inventory['version']==VERSION and inventory['initialWindow']==result['leafCache']['initialWindow']
            assert inventory['inventory']==result['leafCache']['inventory'] and inventory['equipment']==result['leafCache']['equipment']
            assert not inventory['complete'] and inventory['outcome'] in ('observing','inconclusive-initial-target')
            summary=summarize(result,args.name)
            summary.update(probeSHA256=probe['probeSHA256'],resultSHA256=r.sha(folder/'storage/result.json'),
                inventorySHA256=r.sha(inventory_path),inputsUnchanged=True,checks=len(result['assertions']),processPolicyAdapter=adapter)
            r.save(folder/'summary.json',summary)
            if run_error:raise run_error
            assert summary['passed'],'Leaf component inconclusive/not qualified; original outcome retained'
            lease.outcome='passed';lease.note='Read-only native leaf observations and terminal pixels passed; no performance or deployment acceptance'
            print(json.dumps({k:summary[k] for k in ('name','passed','outcome','complete','checks')},ensure_ascii=False),flush=True)
        except BaseException as error:
            lease.outcome='failed';lease.note=repr(error);folder.mkdir(parents=True,exist_ok=True)
            r.save(folder/'runner-failure.json',dict(record,error=repr(error),complete=False,deployed=False));raise


shared.HERE,shared.VERSION=HERE,VERSION
shared.runner_inputs,shared.fixture_inputs=runner_inputs,fixture_inputs
base.OUT=HERE/'probe-builds'
base.runner_inputs,base.candidate_inputs=runner_inputs,fixture_inputs
if __name__=='__main__':main()
