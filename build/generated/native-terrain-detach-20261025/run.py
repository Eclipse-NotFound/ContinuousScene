"""Registered native-invisible terrain detach ABBA, exact 29AF native SMG fixture.

Source preparation only until reviewed/frozen. No native IP/thread observer and
no production deployment. All 1200 intervals retain the complete helper cost.
"""
from pathlib import Path
import argparse
import ast
import hashlib
import importlib.util
import inspect
import json
import shutil
import sys
import traceback
import uuid

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
VERSION = 'native-terrain-detach-probe-1'
MODE = 'rcnative'
FIXTURE = 'dense-sprint-smg10-1'
HELPER_SHA = 'D1CD27ABC31DD44B24DB0FEDDF7BB62F0AFAE9C9BE3B341ACBE3A68AD774CB50'
POLICY_REASON = 'Native-invisible terrain Bitmap detach ABBA; diagnostic only, full switching and helper costs retained'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


reference = load('terrain_detach_window_support', HERE.parent / 'window-visibility-native-20261025/run.py')
old = reference.old
shared, control, dense, base, r, m, support = (reference.shared, reference.control, reference.dense,
                                            reference.base, reference.r, reference.m, reference.support)
patch = load('terrain_detach_patch', HERE / 'probe_patch.py')
HELPER = HERE / 'SceneNativeTerrainDetach.as'
SEED = reference.SEED
SEED_SHA, PROBE_SHA = reference.SEED_SHA, reference.PROBE_SHA
PINS = dict(reference.PINS)
ORDER = (False, True, True, False)
NAMES = ('terrain-native-a', 'terrain-detach-b', 'terrain-detach-b-repeat', 'terrain-native-a-repeat')


def seed():
    value = reference.seed()
    assert value['probeSHA256'] == PROBE_SHA == patch.SOURCE_PROBE
    assert len(value['frozenSourceSHA256']) == 85
    return value


def runner_inputs():
    assert len(HELPER_SHA) == 64 and r.sha(HELPER) == HELPER_SHA, 'Helper not finally frozen'
    values = dict(reference.runner_inputs(), **{str(p): r.sha(p) for p in
        [Path(reference.__file__), HERE / 'run.py', HERE / 'probe_patch.py', HERE / 'README.md', HELPER]})
    assert not any('owned-native-stack' in name or 'air-ip-only' in name for name in values)
    return values


def fixture_inputs():
    values = reference.fixture_inputs()
    values.update({str(p): r.sha(p) for p in [HERE / 'probe_patch.py', HELPER]})
    return values


def runtime_inputs():
    return reference.runtime_inputs()


def policy_adapter():
    original = inspect.getsource(m.run_owned)
    anchor = "policy['diagnosticOnly']='Independent RC binary comparison with native input and continuous timing; noop control, no RC probe API'"
    replacement = "policy['diagnosticOnly']=" + repr(POLICY_REASON)
    assert original.count(anchor) == 1
    changed = original.replace(anchor, replacement, 1)
    assert changed.replace(replacement, anchor, 1) == original
    assert "current['availableCommit']<512*1024**2" in changed
    assert 'HiddenProcess(' in changed and 'record.child(process.pid)' in changed
    tree = ast.parse(changed)
    scope = dict(m.__dict__); exec(compile(tree, '<terrain-detach-policy-only>', 'exec'), scope)
    digest = lambda text: hashlib.sha256(text.encode('utf-8')).hexdigest().upper()
    return scope['run_owned'], dict(originalSHA256=digest(original), transformedSHA256=digest(changed),
        reverseExact=True, sharedModuleModified=False, onlyChange='Replace rcnative diagnostic description',
        runGuardBytes=512*1024**2, threadOrIPObserver=False)


def source_qualification(value):
    source = Path(value['frozenSourcePath']) / 'ContinuousSceneMotionProbe.as'
    assert r.sha(source) == patch.MAIN_RAW_SHA
    raw = source.read_text('utf-8-sig')
    transformed = patch.transform(raw)
    assert patch.reverse(transformed) == raw
    # Same Stage dispatcher; before-native guard at highest priority and the
    # existing phase4 update at -1000 before the unchanged wall-clock sample.
    assert 'main.stage.addEventListener(Event.ENTER_FRAME,tick,false,-1000)' in raw
    assert 'terrainBeforeNative();rasterPresentation.beginFrame()' in transformed
    update_at = transformed.index('var terrainFrame:Object=terrainDetach.update(')
    sample_at = transformed.index('                    var now:int=getTimer();\n                    if(continuousPreviousSampleAt<0)')
    observe_at = transformed.index('                    if(encounter)encounter.sample();', sample_at)
    assert update_at < sample_at < observe_at
    begin_at = transformed.index('terrainReady=terrainDetach.begin(w);')
    assert transformed.index('continuousPreviousSampleAt=caseBegin;') < begin_at
    assert 'setting("realisticvision","enabled",Boolean(cfg.vision))' in raw
    assert 'setting("light-and-darkness","enabled",!cfg.noLighting)' in raw
    assert 'setting("wallblend","enabled",!cfg.noWall)' in raw
    return dict(reverseExact=True, changedSources=patch.CHANGED, seedFiles=85, preparedFiles=86,
        sameStageDispatcher=True, beforeNativePriority=2147483647, nativePriority=0,
        continuousScenePriority=-200, afterNativeUpdatePriority=-1000,
        updateBeforeWallSample=True, updateBeforeCombatObservation=True,
        beginAfterContinuousStart=True, threeVisualSettingsDisabled=True, satsForbidden=True,
        mainBeforeSHA256=patch.MAIN_RAW_SHA,
        mainAfterSHA256=hashlib.sha256(transformed.encode('utf-8')).hexdigest().upper(),
        hookEvidence=['game-reference/decompiled/1.02/src102/scripts/fe/MainMenu.as:85,842 (Stage priority 0 to World.step)',
            'game-reference/decompiled/1.02/src102/scripts/fe/World.as:1316 (Camera.calc in World.step)',
            'mods/ContinuousScene/build/prepare.py:177 (Camera calls sceneTick)',
            'mods/ContinuousScene/src/patches/GrafonChunks.as.inc:214 (sceneTick calls sceneCullSurfaces)',
            'mods/ContinuousScene/src/ContinuousSceneMod.as:46 (same Stage priority -200)'])


def compile_probe(lease, baseline, scripts, compiler, fixture):
    value = seed(); qualification = source_qualification(value)
    staging = HERE / 'source-staging' / uuid.uuid4().hex
    patch.prepare(Path(value['frozenSourcePath']), staging / 'src')
    after = base.tree_hashes(staging / 'src')
    changed = sorted(k for k in set(after) | set(value['frozenSourceSHA256'])
        if after.get(k) != value['frozenSourceSHA256'].get(k))
    assert changed == patch.CHANGED and len(after) == 86
    origin = staging / 'source-origin.json'
    r.save(origin, dict(version=VERSION, seedReceiptSHA256=SEED_SHA, seedProbeSHA256=PROBE_SHA,
        seedSourceSHA256=value['frozenSourceSHA256'], stagedSHA256=after, changed=changed,
        fixtureInputs=fixture, sourceQualification=qualification))
    path = shared.compile_frozen(lease, staging / 'src', baseline, scripts, compiler, fixture)
    receipt = r.read(path)
    receipt.update(nativeTerrainDetachVersion=VERSION, denseFixture=FIXTURE, observerFixtureSource=dense.VERSION,
                   sourceOrigin=str(origin), sourceOriginSHA256=r.sha(origin))
    r.save(path, receipt)
    return path


def verify_probe(path, baseline, scripts, compiler, fixture):
    raw = r.read(path)
    original = Path(raw['probePath']).parent / 'probe-build.json'
    assert path.resolve() == original.resolve(), 'Use original build receipt beside compile.log'
    value = base.verify_probe(path, baseline, scripts, compiler, fixture)
    assert value['nativeTerrainDetachVersion'] == VERSION and value['denseFixture'] == FIXTURE
    assert value['observerFixtureSource'] == dense.VERSION
    origin_path = Path(value['sourceOrigin']); assert r.sha(origin_path) == value['sourceOriginSHA256']
    origin, source = r.read(origin_path), seed()
    assert origin['seedReceiptSHA256'] == SEED_SHA and origin['seedProbeSHA256'] == PROBE_SHA
    assert origin['seedSourceSHA256'] == source['frozenSourceSHA256'] and origin['changed'] == patch.CHANGED
    assert origin['stagedSHA256'] == value['frozenSourceSHA256'] and origin['fixtureInputs'] == fixture
    assert origin['sourceQualification'] == source_qualification(source)
    changed = sorted(k for k in set(value['frozenSourceSHA256']) | set(source['frozenSourceSHA256'])
        if value['frozenSourceSHA256'].get(k) != source['frozenSourceSHA256'].get(k))
    assert changed == patch.CHANGED and len(value['frozenSourceSHA256']) == 86
    frozen, source_root = Path(value['frozenSourcePath']), Path(source['frozenSourcePath'])
    assert (frozen / 'ContinuousSceneMotionProbe.as').read_text('utf-8-sig') == patch.transform(
        (source_root / 'ContinuousSceneMotionProbe.as').read_text('utf-8-sig'))
    assert r.sha(frozen / 'tests/SceneNativeTerrainDetach.as') == HELPER_SHA
    return value


def options(name):
    return reference.options(name) + ['--draw-control', MODE]


def state_check(state, cleared=False):
    assert state['version'] == 'native-terrain-detach-1' and state['valid']
    assert state['cleared'] is cleared and state['initialized'] is (not cleared)
    assert state['diagnosticOnly'] and not state['performanceEligible'] and state['errors'] == []
    assert state['droppedSkipped'] == 0 and state['detaches'] - state['restores'] == state['held']
    assert state['pendingRestore'] == state['held'] and state['applied'] is (state['held'] > 0)
    assert state['nodes'] == state['surfaces'] * 4
    assert state['surfaces'] == 0 if cleared else state['surfaces'] > 0


def summarize(result, name):
    cfg, motion = result['config'], result['nativeInputMotion']
    assert result['ok'] and result['error'] is None
    assert len(result['assertions']) == 26 and all(item['ok'] for item in result['assertions'])
    assert cfg['benchmark'] == 'scene' and cfg['drawControl'] == MODE and not cfg['presentationCheck']
    assert cfg['nativeInputMotion'] and cfg['nativeSprint'] and cfg['stableMotion'] and cfg['playerFire']
    assert cfg['fixedEnemies'] and cfg['combatRoute'] and not cfg['localEnemies']
    assert cfg['noLighting'] and cfg['noWall'] and not cfg['vision'] and not cfg['satsCheck']
    assert not any(cfg[k] for k in ('profile','culling','sleepingRootShort','bulletSegments','worldProfile',
        'locationProfile','guiWeaponProfile','playerStepProfile','playerAnimateProfile','impactABBA','fogABBA','fogTypedABBA'))
    assert not any(k in result for k in ('rcOfflineInitial','rcOfflineCleanup','atlasMotion','windowVisibility','atlasMotionCleanup'))
    assert result['denseFixture']['version'] == FIXTURE and result['denseFixture']['enemyWeapon'] == 'smg10'
    assert result['denseFixture']['actors'] == 6 and motion['version'] == 'native-input-dense-sprint-2'
    assert result['driver']['forcedPositionCalls'] == 0 and motion['spawn']['calls'] == 1
    assert motion['warmup']['ready'] and motion['warmup']['roundTrips'] >= 1 and motion['warmup']['groundContactRun'] >= 10
    assert motion['timingStart']['floorContact'] and motion['route']['terrainVerified']
    assert result['world']['layoutSeed'] == 20261019 and result['viewport']['zoom'] == 1
    assert (result['world']['width'], result['world']['height']) == (240,125)
    assert result['observerPolicy'] == dict(version='dense-observer-lean-2', settingsDuringTiming=False,
        segmentProgressWrites=False, segmentCensus=False, finalCensus=True, heartbeatIntervalMs=5000, continuousFramesRetained=True)
    trial = result['nativeTerrainDetach']
    assert trial['version'] == VERSION and trial['order'] == list(ORDER)
    assert trial['diagnosticOnly'] and not trial['performanceEligible'] and not trial['visualAcceptance']
    begin = trial['begin']; state_check(begin['state'])
    assert begin['state']['held'] == begin['state']['updates'] == begin['state']['headChecks'] == 0
    old.six_smg10(result['playerFireWarmup']['encounter'])
    continuous = dense.continuous(result)
    assert len(result['samples']) == 4
    rows, all_states, previous, observed_updates = [], [], False, 0
    assert result['samples'][0]['caseBeginAtMs'] <= begin['startedAtMs'] <= begin['endedAtMs'] <= result['samples'][0]['sampleAtMs'][0]
    for index, row in enumerate(result['samples']):
        assert row['name'] == NAMES[index] and len(row['continuousFramesMs']) == 300
        assert row['empty'] == row['misses'] == 0 and row['playerShotFrames'] > 0 and row['enemyShotFrames'] > 0
        old.six_smg10(row['encounter'])
        for window in row['combatWindows']: old.six_smg10(window['encounter'])
        assert 'activityCensus' not in row and sum(row['probeTiming']['censusMs']) == sum(row['probeTiming']['progressSaveMs']) == 0
        segment = row['nativeTerrainDetach']; assert segment['enabled'] is ORDER[index] and len(segment['frames']) == 300
        state_check(segment['start']); state_check(segment['end'])
        for age, frame in enumerate(segment['frames']):
            data, state = frame['data'], frame['data']['snapshot']; state_check(state)
            assert frame['index'] == index and frame['frame'] == age
            assert data['version'] == 'native-terrain-detach-1' and data['valid'] and data['enabled'] is ORDER[index]
            assert data['previousApplied'] is previous and data['applied'] is state['applied']
            previous = data['applied']; observed_updates += 1
            assert state['updates'] == state['headChecks'] == observed_updates and not state['cleared']
            assert data['surfaces'] == state['surfaces'] == begin['state']['surfaces']
            assert all(len(data[key]) == 4 for key in ('nativeVisible','nativeInvisible','heldByLayer'))
            for layer in range(4):
                visible, invisible, held = (data[key][layer] for key in ('nativeVisible','nativeInvisible','heldByLayer'))
                assert all(type(v) is int and v >= 0 for v in (visible,invisible,held))
                assert visible + invisible == data['surfaces'] and held == (invisible if ORDER[index] else 0)
            assert sum(data['heldByLayer']) == state['held']
            assert all(base.finite(v) and v >= 0 for v in (data['ownMs'], frame['headMs']))
            assert frame['updateStartedAtMs'] <= frame['updateEndedAtMs'] <= row['sampleAtMs'][age]
            all_states.append(data)
        rows.append(dict(index=index, enabled=ORDER[index], continuous=base.metrics(row['continuousFramesMs']),
            playerShots=row['playerShotFrames'], enemyShots=row['enemyShotFrames'],
            workload=dense.workload(row,motion['route']), warmed=sum(row['warm']), slices=row['slices'],
            helperOwnMs=base.metrics([f['data']['ownMs'] for f in segment['frames']]),
            headGuardMs=base.metrics([f['headMs'] for f in segment['frames']]),
            held=base.metrics([f['data']['snapshot']['held'] for f in segment['frames']])))
    cleanup = result['nativeTerrainDetachCleanup']; assert cleanup['restored'] and cleanup['errors'] == []
    assert cleanup['result']['restored'] and cleanup['result']['pendingRestore'] == 0 and cleanup['result']['errors'] == []
    state_check(cleanup['before']); state_check(cleanup['after'], cleared=True)
    assert cleanup['before']['updates'] == cleanup['before']['headChecks'] == 1200 and cleanup['before']['held'] == 0
    pixels = result['nativeTerrainDetachPixels']; data = pixels['data']
    assert pixels['afterFinalSample'] and pixels['diagnosticOnly'] and not pixels['performanceEligible']
    assert result['samples'][-1]['sampleAtMs'][-1] <= pixels['startedAtMs'] <= pixels['endedAtMs']
    assert all(data[k] for k in ('valid','equal','restored','heldPositive','nonemptyNative'))
    assert data['errors'] == [] and data['samples'] == 3 and data['bitmapsCreated'] == data['bitmapsDisposed'] == 3
    assert len(data['cases']) == 2 and [v['name'] for v in data['cases']] == ['native-vs-detached','native-vs-restored']
    assert all(v['exactEqual'] and v['diffCount'] == v['maxRGB'] == v['maxAlpha'] == 0 for v in data['cases'])
    state_check(data['before']); state_check(data['after'])
    # checkPixels performs exactly one validate before recording its own before.
    # That validate scans each recorded node and checks the parent sequence once.
    expected_pixel_before = dict(cleanup['before'])
    expected_pixel_before['scannedNodes'] += cleanup['before']['nodes']
    expected_pixel_before['structureChecks'] += 1
    assert data['before'] == expected_pixel_before and data['before']['held'] == data['after']['held'] == 0
    assert data['before']['updates'] == 1200 and data['after']['updates'] == 1202
    assert data['before']['headChecks'] == data['after']['headChecks'] == 1200
    final = cleanup['after']; assert final['held'] == 0 and final['updates'] == 1202 and final['headChecks'] == 1200
    qualification = dict(actualSprint=sum(row['workload']['aboveWalkSpeedFrames'] for row in rows) >= 30,
        concurrentFixtureBullets=any(v >= 3 for row in result['samples'] for v in row['denseFrames']['fixtureBullets']),
        observedNativePlayerBullets=any(v > 0 for row in result['samples'] for v in row['denseFrames']['playerBullets']),
        actuallyDetached=any(state['newlyDetached'] > 0 for state in all_states),
        naturallyVisibleRestored=any(state['enteredRestored'] > 0 for state in all_states),
        lastNativeArmRestored=not previous)
    qualification['passed'] = all(qualification.values())
    arms = {label: base.metrics([v for i,row in enumerate(result['samples']) if ORDER[i] is enabled
        for v in row['continuousFramesMs']]) for label,enabled in (('nativeA',False),('detachedB',True))}
    return dict(version=VERSION, name=name, passed=qualification['passed'], complete=True, diagnosticOnly=True,
        performanceEligible=False, performanceAcceptance=False, gameplayAcceptance=False,
        visualAcceptance=False, deployed=False, qualification=qualification, continuous=continuous,
        rows=rows, arms=arms, begin=begin, cleanup=cleanup, terminalPixels=pixels,
        limits=['A/B/B/A retains all 1200 intervals, switches, guard scans, allocations and native workload; ownMs is never subtracted.',
            'The static resident and complete parent-sequence guard must hold throughout. Guard failure is retained, not repaired or skipped.',
            'Terminal same-frame pixels are outside the 1200 intervals and require exact equality; they do not prove full-route visuals, SATS, map-change or deployment acceptance.',
            'Only an isolated exploratory comparison; varying combat/warm workload and sequence effects can confound arm averages.',
            'No IP, thread-context or thread-CPU observer is added. Default process CPU accounting remains unchanged.'])


def main():
    assert __debug__
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    parser.add_argument('--registry-wait', type=int, default=600)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--compile-probe', action='store_true')
    group.add_argument('--probe-build', type=Path)
    args = parser.parse_args()
    assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
    folder = r.E / args.name
    assert not folder.exists(), 'Preserve previous evidence'
    execute, adapter = policy_adapter()
    record = dict(version=VERSION, diagnosticOnly=True, performanceEligible=False,
                  options=options(args.name), processPolicyAdapter=adapter)
    with m.Registration(owner='ContinuousScene / native terrain detach / 01a13816', purpose=args.name,
                        run_dir=m.RUNTIME, evidence=folder, resource='game', wait=args.registry_wait) as lease:
        try:
            assert not m.air_pids(), 'Other AIR remains untouched'
            memory = control.memory_gate()
            baseline, scripts, compiler, fixture = r.baseline(), runner_inputs(), support.compiler_inputs(), fixture_inputs()
            runtime = runtime_inputs()
            assert len(baseline) == 526 and len(runtime) == 13
            for key, digest in PINS.items(): assert baseline[key] == digest, key
            rv = r.read(old.RV_RECEIPT)
            assert rv['result'] == 'PASS' and rv['new'].upper() == old.RV_CURRENT and rv['before']['pfe.swf'].upper() == control.HOST
            record.update(baseline=baseline, runnerInputs=scripts, compilerInputs=compiler,
                          fixtureInputs=fixture, runtimeInputs=runtime, memoryBefore=memory,
                          sourceQualification=source_qualification(seed()))
            path = compile_probe(lease,baseline,scripts,compiler,fixture) if args.compile_probe else args.probe_build.resolve()
            probe = verify_probe(path,baseline,scripts,compiler,fixture)
            m.prepare(); shutil.copy2(probe['probePath'], m.RUNTIME / base.PROBE_PATH)
            for key, digest in baseline.items():
                if key not in ('application.xml','mods/loader-manifest.txt'): assert r.sha(m.RUNTIME/key) == digest, key
            assert baseline == r.baseline() and scripts == runner_inputs() and runtime == runtime_inputs()
            launch = m.parse_args(record['options'])
            assert launch.draw_control == MODE and not launch.profile and not launch.presentation_check and not launch.sats_check
            record.update(probeBuildPath=str(path), probeSHA256=probe['probeSHA256'], memoryBeforeAir=control.memory_gate())
            run_error = None
            try: execute(launch,lease)
            except BaseException as error:
                run_error = error
                record['executionError'] = repr(error)
                record['executionTraceback'] = traceback.format_exc()
            finally:
                if folder.exists():
                    r.save(folder/'probe-build.json',probe); r.save(folder/'runner-inputs.json',record)
                    if (folder/'storage/result.json').exists():
                        raw = r.read(folder/'storage/result.json')
                        r.save(folder/'component-status.json', dict(rawOK=raw.get('ok'), rawError=raw.get('error'),
                            nativeTerrainDetach=raw.get('nativeTerrainDetach'), cleanup=raw.get('nativeTerrainDetachCleanup'),
                            terminalPixels=raw.get('nativeTerrainDetachPixels'),
                            executionError=repr(run_error) if run_error else None))
            assert baseline == r.baseline() and scripts == runner_inputs() and fixture == fixture_inputs()
            assert compiler == support.compiler_inputs() and runtime == runtime_inputs() and policy_adapter()[1] == adapter
            verify_probe(path,baseline,scripts,compiler,fixture)
            result, actual = reference.read_retained_result(folder)
            for key, digest in baseline.items():
                if key not in ('application.xml','mods/loader-manifest.txt'): assert actual[key] == digest, key
            assert actual[base.PROBE_PATH] == probe['probeSHA256']
            policy = r.read(folder/'process-policy.json')
            assert policy['desktopPolicy'] == 'private' and not policy['performanceEligible'] and policy['diagnosticOnly'] == POLICY_REASON
            assert not policy.get('runFailure') and not policy.get('memoryAbort') and not policy.get('otherAirProcessIds')
            try: summary = summarize(result,args.name)
            except Exception as validation_error:
                summary = dict(version=VERSION,name=args.name,passed=False,complete=False,diagnosticOnly=True,
                    performanceEligible=False,performanceAcceptance=False,deployed=False,rawOK=result.get('ok'),
                    rawError=result.get('error'),error=repr(validation_error),nativeTerrainDetach=result.get('nativeTerrainDetach'),
                    cleanup=result.get('nativeTerrainDetachCleanup'),terminalPixels=result.get('nativeTerrainDetachPixels'),
                    retainedSampleCount=len(result.get('samples',[])))
            summary.update(probeSHA256=probe['probeSHA256'],resultSHA256=r.sha(folder/'storage/result.json'),
                inputsUnchanged=True,runtimeInputsUnchanged=True,checks=len(result['assertions']),processPolicyAdapter=adapter)
            r.save(folder/'summary.json',summary)
            if run_error: raise run_error
            assert summary['passed'], 'Terrain detach qualification incomplete; original evidence retained'
            lease.outcome='passed'; lease.note='1200 native SMG intervals and terrain parentage restoration; diagnostic, no visual/SATS/deployment acceptance'
            print(json.dumps({k:summary[k] for k in ('name','passed','complete','checks','qualification')}),flush=True)
        except BaseException as error:
            lease.outcome='failed'; lease.note=repr(error); folder.mkdir(parents=True,exist_ok=True)
            r.save(folder/'runner-failure.json',dict(record,error=repr(error),complete=False,deployed=False)); raise


shared.HERE, shared.VERSION = HERE, VERSION
shared.runner_inputs, shared.fixture_inputs = runner_inputs, fixture_inputs
base.OUT = HERE / 'probe-builds'
base.runner_inputs, base.candidate_inputs = runner_inputs, fixture_inputs
if __name__ == '__main__': main()
