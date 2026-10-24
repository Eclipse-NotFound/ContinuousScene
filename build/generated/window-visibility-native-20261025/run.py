"""Registered private-desktop NativeWindow visibility ABBA; unchanged SMG combat.

All 1200 intervals include switching and observation costs. This is environment
sensitivity only: no product FPS, visual acceptance or foreground presentation.
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
VERSION = 'window-visibility-native-1'
MODE = 'windowvisibility'
FIXTURE = 'dense-sprint-smg10-1'
SEED_SHA = '983727AEB832BC586AF3767613B7C9D61564D92DC9D8E2435F972EEBF1D1D5EE'
PROBE_SHA = '29AF34571E7181139C682AA32A160E2C217C1B02B295E6DCBD6931D8DB7F94E5'
HELPER_SHA = '6BC5D98059B25DCCAF612328ACF514AAEF63FC695717457DA8048FBC25C47CC9'
PATCH_SHA = '28719F0EB5AA53D5877A90079C12B0A04D1D8E11DA38E1D829931A7CD515E8E2'
POLICY_REASON = 'Private-desktop native window visibility ABBA; environment sensitivity, not product performance'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


old = load('window_visibility_smg_support', HERE.parent / 'camera-atlas-paged-combat-20261025/run.py')
shared, control, dense, base, r, m, support = old.shared, old.control, old.dense, old.base, old.r, old.m, old.support
patch = load('window_visibility_patch', HERE / 'probe_patch.py')
HELPER = HERE / 'SceneWindowVisibilityTrial.as'
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
    values = dict(old.runner_inputs(), **{str(p): r.sha(p) for p in
        [Path(old.__file__), Path(shared.__file__), Path(m.__file__), HERE / 'run.py',
         HERE / 'probe_patch.py', HERE / 'README.md', HELPER, SEED]})
    values.update({str(r.ROOT / p): digest for p,digest in runtime_inputs().items()})
    return values


def fixture_inputs():
    value = seed()
    return {str(p): r.sha(p) for p in [SEED, Path(value['probePath']), Path(value['configPath']),
        Path(value['sourceOrigin']), Path(value['probePath']).parent / 'probe-build.json',
        HERE / 'probe_patch.py', HELPER, support.OUT / 'source-provenance.json']}


def policy_adapter():
    original = inspect.getsource(m.run_owned)
    anchor = "    if getattr(args,'draw_control',None)=='rcnative':"
    inserted = ("    if getattr(args,'draw_control',None)=='windowvisibility':\n"
        "        policy['performanceEligible']=False\n"
        "        policy['diagnosticOnly']=" + repr(POLICY_REASON) + "\n" + anchor)
    assert original.count(anchor) == 1 and inserted not in original
    changed = original.replace(anchor, inserted, 1)
    assert changed.replace(inserted, anchor, 1) == original
    assert "current['availableCommit']<512*1024**2" in changed
    assert 'HiddenProcess(' in changed and 'record.child(process.pid)' in changed
    tree = ast.parse(changed)
    assert len(tree.body) == 1 and isinstance(tree.body[0], ast.FunctionDef) and tree.body[0].name == 'run_owned'
    scope = dict(m.__dict__); exec(compile(tree, '<window-visibility-policy-only>', 'exec'), scope)
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
    receipt.update(windowVisibilityVersion=VERSION, denseFixture=FIXTURE, observerFixtureSource=dense.VERSION,
        sourceOrigin=str(origin), sourceOriginSHA256=r.sha(origin))
    r.save(path, receipt); return path


def verify_probe(path, baseline, scripts, compiler, fixture):
    raw = r.read(path)
    original = Path(raw['probePath']).parent / 'probe-build.json'
    assert path.resolve() == original.resolve(), 'Pass original build receipt beside compile.log: ' + str(original)
    value = base.verify_probe(path, baseline, scripts, compiler, fixture)
    assert value['windowVisibilityVersion'] == VERSION and value['denseFixture'] == FIXTURE
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


def runtime_inputs():
    runtime = r.ROOT / 'runtimes/air/win64'
    files = [r.ROOT / 'adl64.exe'] + sorted(p for p in runtime.rglob('*') if p.is_file())
    assert len(files) == 13 and all(p.is_file() for p in files), 'Runtime closure changed'
    return {p.relative_to(r.ROOT).as_posix(): r.sha(p) for p in files}


ORDER = (False, True, True, False)
NAMES = ('window-hidden-0','window-visible-1','window-visible-2','window-hidden-3')
STATE_KEYS = ('active','applicationActiveWindowMatches','onPause','stageWidth','stageHeight',
    'quality','frameRate','displayState','stageDisplayState','renderMode','bounds')


def state_check(value):
    assert all(type(value[k]) is bool for k in ('visible','active','applicationActiveWindowMatches','onPause'))
    assert all(base.finite(value[k]) and value[k] > 0 for k in ('stageWidth','stageHeight','frameRate'))
    assert all(isinstance(value[k],str) and value[k] for k in ('quality','displayState','stageDisplayState','renderMode'))
    assert all(base.finite(value['bounds'][k]) for k in ('x','y','width','height'))
    assert value['bounds']['width'] > 0 and value['bounds']['height'] > 0


def window_review(result):
    report=result['windowVisibility']; assert report['version']==VERSION
    assert report['diagnosticOnly'] and not report['performanceEligible']
    cleanup=report['cleanup']; assert cleanup==result['windowVisibilityCleanup']
    initial=report.get('initial'); observations=[]; confounds={}; reasons=[]
    def compare(label,state):
        state_check(state)
        if initial is not None:
            for key in STATE_KEYS:
                if state[key]!=initial[key]:
                    entry=confounds.setdefault(key,dict(initial=initial[key],count=0,examples=[]))
                    entry['count']+=1
                    if len(entry['examples'])<8:entry['examples'].append(dict(at=label,value=state[key]))
    if initial is not None:
        state_check(initial); assert initial['visible'] is False
    switches=report.get('switches',[]); assert len(switches)<=4
    for index,row in enumerate(result['samples']):
        segment=row['windowVisibility']; assert row['name']==NAMES[index]
        assert segment['index']==index and segment['expectedVisible'] is ORDER[index]
        assert segment['caseBeginAtMs']==row['caseBeginAtMs']
        assert segment['caseBeginAtMs']<=segment['switchBeginAtMs']<=segment['switchEndAtMs']<=row['sampleAtMs'][0]
        assert segment['switchMs']==segment['switchEndAtMs']-segment['switchBeginAtMs']
        assert {k:v for k,v in segment.items() if k!='frames'}==switches[index]
        assert len(segment['frames'])==300
        for age,frame in enumerate(segment['frames']):
            assert frame['index']==index and frame['frame']==age and frame['visible'] is ORDER[index]
            assert isinstance(frame['elapsedMs'],int) and frame['elapsedMs']>=0
            compare('case%d/frame%d'%(index,age),frame)
        observations.append(dict(index=index,expectedVisible=ORDER[index],frames=300,
            switchMs=segment['switchMs'],before=segment['before'],after=segment['after'],
            observationMs=base.metrics([f['elapsedMs'] for f in segment['frames']])))
    for index,switch in enumerate(switches):
        assert switch['index']==index and switch['expectedVisible'] is ORDER[index]
        compare('switch%d/before'%index,switch['before']);compare('switch%d/after'%index,switch['after'])
        assert switch['before']['visible'] is (ORDER[index-1] if index else False)
        assert switch['after']['visible'] is ORDER[index]
    for key in ('finalBeforeRestore','finalAfterRestore'):
        if key in report:compare(key,report[key])
    count=sum(x['frames'] for x in observations)
    assert isinstance(report['observations'],int) and report['observations']>=count
    if report['complete']:
        assert count==report['observations']==1200 and len(switches)==4
        assert report['finalBeforeRestore']['visible'] is False
    if cleanup['initialized']:
        assert cleanup['originalVisible'] is initial['visible']
        if cleanup['restored']:assert report['finalAfterRestore']['visible'] is initial['visible']
    if not report['complete']:reasons.append('All 1200 window observations did not complete')
    if not cleanup['initialized']:reasons.append('The owned native window was not initialized')
    if report['errors']:reasons.append('Window observer reported errors: '+repr(report['errors']))
    if not cleanup['restored'] or cleanup['pendingRestore']!=0 or cleanup['errors']:
        reasons.append('Original visibility was not fully restored: '+repr(cleanup))
    return dict(complete=report['complete'],observedFrames=report['observations'],retainedFrames=count,
        initial=initial,finalBeforeRestore=report.get('finalBeforeRestore'),
        finalAfterRestore=report.get('finalAfterRestore'),switches=switches,rows=observations,
        errors=report['errors'],cleanup=cleanup,qualificationReasons=reasons,confounds=confounds,
        stateStableExceptVisibility=not confounds,windowStateQualification=not reasons and not confounds,
        screenPresentationVerified=False)


def summarize(result,name):
    review=window_review(result);rows=[];qualification={'passed':False}
    complete=len(result['samples'])==4 and review['complete'] and review['retainedFrames']==1200
    census_status=dict(present='finalActivityCensus' in result,requiredForSuccessfulRaw=True,absenceReason=None)
    continuous=None;pairs=[];arms={}
    if complete:
        cfg,motion=result['config'],result['nativeInputMotion']
        assert len(result['assertions'])==26 and all(x['ok'] for x in result['assertions'])
        assert cfg['benchmark']=='scene' and cfg['drawControl']==MODE and not cfg['presentationCheck']
        assert cfg['nativeInputMotion'] and cfg['nativeSprint'] and cfg['stableMotion'] and cfg['playerFire']
        assert cfg['fixedEnemies'] and cfg['combatRoute'] and not cfg['localEnemies']
        assert cfg['noLighting'] and cfg['noWall'] and not cfg['vision']
        assert not any(cfg[k] for k in ('profile','culling','sleepingRootShort','bulletSegments','worldProfile',
            'locationProfile','guiWeaponProfile','playerStepProfile','playerAnimateProfile','impactABBA','fogABBA','fogTypedABBA'))
        assert not any(k in result for k in ('rcOfflineInitial','rcOfflineCleanup','atlasMotion','atlasMotionCleanup','terrainLayer','leafCache'))
        assert result['denseFixture']['version']==FIXTURE and result['denseFixture']['enemyWeapon']=='smg10'
        assert result['denseFixture']['actors']==6 and motion['version']=='native-input-dense-sprint-2'
        assert result['driver']['forcedPositionCalls']==0 and motion['spawn']['calls']==1
        assert motion['warmup']['ready'] and motion['warmup']['roundTrips']>=1 and motion['warmup']['groundContactRun']>=10
        assert motion['timingStart']['floorContact'] and motion['route']['terrainVerified']
        assert result['world']['layoutSeed']==20261019 and result['viewport']['zoom']==1
        assert (result['world']['width'],result['world']['height'])==(240,125)
        assert result['observerPolicy']==dict(version='dense-observer-lean-2',settingsDuringTiming=False,
            segmentProgressWrites=False,segmentCensus=False,finalCensus=True,heartbeatIntervalMs=5000,continuousFramesRetained=True)
        old.six_smg10(result['playerFireWarmup']['encounter'])
        continuous=dense.continuous(result)
        assert result['samples'][0]['windowVisibility']['caseBeginAtMs']==continuous['startedAtMs']
        for index,row in enumerate(result['samples']):
            assert row['empty']==row['misses']==0 and row['playerShotFrames']>0 and row['enemyShotFrames']>0
            old.six_smg10(row['encounter'])
            for item in row['combatWindows']:old.six_smg10(item['encounter'])
            assert 'activityCensus' not in row and sum(row['probeTiming']['censusMs'])==sum(row['probeTiming']['progressSaveMs'])==0
            rows.append(dict(index=index,visible=ORDER[index],continuous=base.metrics(row['continuousFramesMs']),
                withinSegment=base.metrics(row['frames']),playerShots=row['playerShotFrames'],enemyShots=row['enemyShotFrames'],
                combatWindows=base.combat_windows(row,300),workload=dense.workload(row,motion['route']),
                bands={k:base.metrics(row[k]) for k in ('nativeBand','wallBand','sceneBand','preBand','tailBand','totalScript','afterProbeBand')},
                activity=row['activity'],activityEnd=row.get('activityEnd'),warmed=sum(row['warm']),slices=row['slices'],
                forced=row['forced'],residentStart=row['residentStart'],residentEnd=row['residentEnd'],
                probeWorkMs=base.metrics(row['probeTiming']['workMs']),windowObservation=review['rows'][index]))
        census=result.get('finalActivityCensus')
        if result['ok'] and not result['error']:assert census is not None,'Successful raw requires final census'
        if census is not None:
            assert census['afterFinalSample'] and census['data']
            assert result['samples'][-1]['sampleAtMs'][-1]<=census['startedAtMs']<=census['endedAtMs']
        else:census_status['absenceReason']='Original finish skips census after a raw/component error; non-passing result retained'
        qualification=dict(actualSprint=sum(x['workload']['aboveWalkSpeedFrames'] for x in rows)>=30,
            concurrentFixtureBullets=any(v>=3 for row in result['samples'] for v in row['denseFrames']['fixtureBullets']),
            observedNativePlayerBullets=any(v>0 for row in result['samples'] for v in row['denseFrames']['playerBullets']))
        qualification['passed']=all(qualification.values())
        for label,indices in (('hidden',(0,3)),('visible',(1,2))):
            frames=[dt for i in indices for dt in result['samples'][i]['continuousFramesMs']]
            arms[label]=dict(indices=list(indices),continuous=base.metrics(frames),
                playerShots=sum(rows[i]['playerShots'] for i in indices),enemyShots=sum(rows[i]['enemyShots'] for i in indices),
                warmed=sum(rows[i]['warmed'] for i in indices),slices=sum(rows[i]['slices'] for i in indices),
                switchMs=sum(rows[i]['windowObservation']['switchMs'] for i in indices))
        for ai,bi in ((0,1),(3,2)):
            pairs.append(dict(hiddenIndex=ai,visibleIndex=bi,hidden=rows[ai]['continuous'],visible=rows[bi]['continuous'],
                visibleMinusHiddenMeanMs=rows[bi]['continuous']['mean']-rows[ai]['continuous']['mean']))
    reasons=list(review['qualificationReasons'])
    if not result['ok'] or result['error']:reasons.append('Original raw did not pass: '+str(result['error']))
    if not qualification['passed']:reasons.append('Full native movement/fire qualification was not established')
    passed=bool(complete and result['ok'] and not result['error'] and qualification['passed'] and not review['qualificationReasons'])
    return dict(version=VERSION,name=name,complete=complete,passed=passed,rawOK=result['ok'],rawError=result['error'],
        diagnosticOnly=True,performanceEligible=False,performanceAcceptance=False,visualAcceptance=False,
        gameplayAcceptance=False,deployed=False,qualification=qualification,qualificationReasons=reasons,
        stateStableExceptVisibility=review['stateStableExceptVisibility'],
        visibilityOnlyAttributionEligible=passed and review['stateStableExceptVisibility'],
        continuous=continuous,rows=rows,arms=arms,pairs=pairs,windowVisibility=review,finalActivityCensus=census_status,
        limits=['Visible=true is confined to an owned private Windows desktop; no SwitchDesktop/activate/focus call is added.',
            'This does not establish presentation on the user desktop, user FPS, a rendering backend, or GPU time.',
            'Every switching and observation interval is retained; no boundary, warm or long frame is removed.',
            'Active-window, pause, size, frame rate, quality, display state, render mode or bounds changes disqualify visibility-only attribution.',
            'Natural AI, bullet density and prewarm evolve across ABBA; workload and order remain confounders even when window properties are stable.',
            'No gameplay, display-object, atlas, leaf-cache or RC API alteration is introduced. No pixel comparison is performed.'])


def read_retained_result(folder):
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
    with m.Registration(owner='ContinuousScene / window visibility diagnostic / 01a13816',purpose=args.name,
                        run_dir=m.RUNTIME,evidence=folder,resource='game',wait=args.registry_wait) as lease:
        try:
            assert not m.air_pids(),'Other AIR remains untouched'
            memory=control.memory_gate()
            baseline,scripts,compiler,fixture=r.baseline(),runner_inputs(),support.compiler_inputs(),fixture_inputs()
            runtime=runtime_inputs();assert len(baseline)==526
            for key,digest in PINS.items():assert baseline[key]==digest,key
            rv=r.read(old.RV_RECEIPT)
            assert rv['result']=='PASS' and rv['new'].upper()==old.RV_CURRENT and rv['before']['pfe.swf'].upper()==control.HOST
            record.update(baseline=baseline,runnerInputs=scripts,compilerInputs=compiler,fixtureInputs=fixture,
                runtimeInputs=runtime,memoryBefore=memory)
            path=compile_probe(lease,baseline,scripts,compiler,fixture) if args.compile_probe else args.probe_build.resolve()
            probe=verify_probe(path,baseline,scripts,compiler,fixture)
            m.prepare();shutil.copy2(probe['probePath'],m.RUNTIME/base.PROBE_PATH)
            for key,digest in baseline.items():
                if key not in ('application.xml','mods/loader-manifest.txt'):assert r.sha(m.RUNTIME/key)==digest,key
            assert baseline==r.baseline() and scripts==runner_inputs() and runtime==runtime_inputs()
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
                            windowVisibility=raw.get('windowVisibility'),windowVisibilityCleanup=raw.get('windowVisibilityCleanup'),
                            executionError=repr(run_error) if run_error else None))
            assert baseline==r.baseline() and scripts==runner_inputs() and fixture==fixture_inputs()
            assert compiler==support.compiler_inputs() and runtime==runtime_inputs() and policy_adapter()[1]==adapter
            verify_probe(path,baseline,scripts,compiler,fixture)
            result,actual=read_retained_result(folder)
            for key,digest in baseline.items():
                if key not in ('application.xml','mods/loader-manifest.txt'):assert actual[key]==digest,key
            assert actual[base.PROBE_PATH]==probe['probeSHA256']
            policy=r.read(folder/'process-policy.json')
            assert policy['desktopPolicy']=='private' and not policy['performanceEligible'] and policy['diagnosticOnly']==POLICY_REASON
            assert not policy.get('runFailure') and not policy.get('memoryAbort') and not policy.get('otherAirProcessIds')
            try:summary=summarize(result,args.name)
            except Exception as validation_error:
                summary=dict(version=VERSION,name=args.name,passed=False,complete=False,diagnosticOnly=True,
                    performanceEligible=False,performanceAcceptance=False,visualAcceptance=False,deployed=False,
                    rawOK=result.get('ok'),rawError=result.get('error'),qualificationReasons=[repr(validation_error)],
                    windowVisibility=result.get('windowVisibility'),visibilityOnlyAttributionEligible=False,
                    retainedSampleCount=len(result.get('samples',[])))
            summary.update(probeSHA256=probe['probeSHA256'],resultSHA256=r.sha(folder/'storage/result.json'),
                inputsUnchanged=True,runtimeInputsUnchanged=True,checks=len(result['assertions']),processPolicyAdapter=adapter)
            r.save(folder/'summary.json',summary)
            if run_error:raise run_error
            assert summary['passed'],'Window diagnostic incomplete/invalid; full original evidence retained'
            lease.outcome='passed';lease.note='1200 native combat intervals and owned window visibility/restoration checked; environment sensitivity only'
            print(json.dumps({k:summary[k] for k in ('name','passed','complete','checks','visibilityOnlyAttributionEligible')},ensure_ascii=False),flush=True)
        except BaseException as error:
            lease.outcome='failed';lease.note=repr(error);folder.mkdir(parents=True,exist_ok=True)
            r.save(folder/'runner-failure.json',dict(record,error=repr(error),complete=False,deployed=False));raise


shared.HERE,shared.VERSION=HERE,VERSION
shared.runner_inputs,shared.fixture_inputs=runner_inputs,fixture_inputs
base.OUT=HERE/'probe-builds'
base.runner_inputs,base.candidate_inputs=runner_inputs,fixture_inputs
if __name__=='__main__':main()
