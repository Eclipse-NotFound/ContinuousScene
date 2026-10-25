"""Registered terminal static-Box census, exact native SMG fixture, no optimization arm."""
from pathlib import Path
import argparse
import ast
import hashlib
import importlib.util
import inspect
import json
import math
import shutil
import sys
import traceback
import uuid

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
VERSION = 'static-box-census-runner-1'
MODE = 'rcnative'
FIXTURE = 'dense-sprint-smg10-1'
HELPER_SHA = 'E2653F4431A6242C23F67D1444FDC4346F3AE58CE9401100B84A1AEB497C5AE7'
POLICY_REASON = 'Read-only terminal static Box census with per-frame actual viewport union; diagnostic, not performance acceptance'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


reference = load('static_box_window_support', HERE.parent / 'window-visibility-native-20261025/run.py')
old = reference.old
shared, control, dense, base, r, m, support = (reference.shared, reference.control, reference.dense,
                                            reference.base, reference.r, reference.m, reference.support)
patch = load('static_box_patch', HERE / 'probe_patch.py')
HELPER = HERE / 'SceneStaticBoxCensus.as'
SEED = reference.SEED
SEED_SHA, PROBE_SHA = reference.SEED_SHA, reference.PROBE_SHA
PINS = dict(reference.PINS)


def seed():
    value = reference.seed()
    assert value['probeSHA256'] == PROBE_SHA == patch.SOURCE_PROBE
    assert len(value['frozenSourceSHA256']) == 85
    return value


def runner_inputs():
    assert len(HELPER_SHA) == 64 and r.sha(HELPER) == HELPER_SHA, 'Helper not finally frozen'
    values = dict(reference.runner_inputs(), **{str(p): r.sha(p) for p in
        [Path(reference.__file__), HERE / 'run.py', HERE / 'probe_patch.py', HERE / 'README.md', HELPER]})
    assert not any('owned-native-stack' in name or 'air-ip-only' in name for name in values), 'No native observer imports'
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
    scope = dict(m.__dict__); exec(compile(tree, '<static-box-policy-only>', 'exec'), scope)
    digest = lambda text: hashlib.sha256(text.encode('utf-8')).hexdigest().upper()
    return scope['run_owned'], dict(originalSHA256=digest(original), transformedSHA256=digest(changed),
        reverseExact=True, sharedModuleModified=False, onlyChange='Replace rcnative diagnostic description',
        runGuardBytes=512*1024**2, threadOrIPObserver=False)


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
    receipt.update(staticBoxCensusVersion=VERSION, denseFixture=FIXTURE, observerFixtureSource=dense.VERSION,
                   sourceOrigin=str(origin), sourceOriginSHA256=r.sha(origin))
    r.save(path, receipt)
    return path


def verify_probe(path, baseline, scripts, compiler, fixture):
    raw = r.read(path)
    original = Path(raw['probePath']).parent / 'probe-build.json'
    assert path.resolve() == original.resolve(), 'Use original build receipt beside compile.log'
    value = base.verify_probe(path, baseline, scripts, compiler, fixture)
    assert value['staticBoxCensusVersion'] == VERSION and value['denseFixture'] == FIXTURE
    assert value['observerFixtureSource'] == dense.VERSION
    origin_path = Path(value['sourceOrigin']); assert r.sha(origin_path) == value['sourceOriginSHA256']
    origin, source = r.read(origin_path), seed()
    assert origin['seedReceiptSHA256'] == SEED_SHA and origin['seedProbeSHA256'] == PROBE_SHA
    assert origin['seedSourceSHA256'] == source['frozenSourceSHA256'] and origin['changed'] == patch.CHANGED
    assert origin['stagedSHA256'] == value['frozenSourceSHA256'] and origin['fixtureInputs'] == fixture
    changed = sorted(k for k in set(value['frozenSourceSHA256']) | set(source['frozenSourceSHA256'])
        if value['frozenSourceSHA256'].get(k) != source['frozenSourceSHA256'].get(k))
    assert changed == patch.CHANGED and len(value['frozenSourceSHA256']) == 86
    frozen, source_root = Path(value['frozenSourcePath']), Path(source['frozenSourcePath'])
    assert (frozen / 'ContinuousSceneMotionProbe.as').read_text('utf-8-sig') == patch.transform(
        (source_root / 'ContinuousSceneMotionProbe.as').read_text('utf-8-sig'))
    assert r.sha(frozen / 'tests/SceneStaticBoxCensus.as') == HELPER_SHA
    return value


def options(name):
    return reference.options(name) + ['--draw-control', MODE]


def viewport_review(result):
    views, observer_ms = [], []
    for row in result['samples']:
        assert len(row['staticBoxViewports']) == len(row['staticBoxViewportMs']) == 300
        views.append(row['staticBoxViewportBoundary'])
        views.extend(row['staticBoxViewports'])
        observer_ms.append(row['staticBoxViewportBoundaryMs'])
        observer_ms.extend(row['staticBoxViewportMs'])
    assert len(views) == len(observer_ms) == 1204
    for view in views:
        assert len(view) == 12 and all(base.finite(v) for v in view)
        sw, sh, a, b, c, d, tx, ty, left, top, right, bottom = view
        assert sw > 0 and sh > 0 and a*d-b*c != 0 and right > left and bottom > top
        xs = (tx, a*sw+tx, c*sh+tx, a*sw+c*sh+tx)
        ys = (ty, b*sw+ty, d*sh+ty, b*sw+d*sh+ty)
        assert all(abs(actual-expected) < 1e-6 for actual, expected in
                   zip((left, top, right, bottom), (min(xs), min(ys), max(xs), max(ys))))
    assert all(base.finite(ms) and ms >= 0 for ms in observer_ms)
    left, top = min(v[8] for v in views), min(v[9] for v in views)
    right, bottom = max(v[10] for v in views), max(v[11] for v in views)
    expected = dict(x=left, y=top, width=right-left, height=bottom-top)
    terminal = result['staticBoxCensus']
    assert terminal['viewportObservations'] == 1204 and terminal['routeSamples'] == 1200 and terminal['segmentBoundaries'] == 4
    assert terminal['afterFinalSample'] and terminal['coordinateSpace'] == 'w.visual'
    assert terminal['diagnosticOnly'] and not terminal['performanceEligible']
    assert all(abs(terminal['viewportUnion'][k] - expected[k]) < 1e-6 for k in expected)
    data = terminal['data']
    assert data['version'] == 'static-box-census-2' and data['arrayEnded'] and data['chainEnded']
    membership = data['membership']
    assert membership['arrayOnly'] + membership['both'] == membership['arrayUniqueBoxes']
    assert membership['chainOnly'] + membership['both'] == membership['chainUniqueBoxes']
    assert data['funnel']['arrayEntries'] == sum(membership[k] for k in
        ('arrayUniqueBoxes','arrayDuplicateEntries','arrayNullEntries','arrayOtherEntries'))
    assert data['funnel']['exactBox'] == data['eligibleStructural'] + sum(data['exclusions'].values())
    assert all(sum(counts.values()) == membership['arrayUniqueBoxes'] for counts in data['fieldTypes'].values())
    assert all(abs(data['viewport'][k] - expected[k]) < 1e-6 for k in expected)
    assert data['margin'] == 320
    expanded = dict(x=left-320, y=top-320, width=right-left+640, height=bottom-top+640)
    assert all(abs(data['excludedViewport'][k] - expanded[k]) < 1e-6 for k in expanded)
    last = result['samples'][-1]['sampleAtMs'][-1]
    assert last <= terminal['startedAtMs'] <= terminal['endedAtMs']
    assert data['complete'] and not data['truncated'] and not data['errors'] and data['contextUnchanged']
    assert data['readOnly'] and data['structuralOnly'] and data['diagnosticOnly']
    assert not data['performanceEligible'] and not data['detachEligible']
    return dict(observations=1204, samplingObservations=1200, boundaryObservations=4,
                coordinateSpace='w.visual', unpaddedUnion=expected, expandedUnion=expanded,
                observationMs=base.metrics(observer_ms), terminalStartedAtMs=terminal['startedAtMs'],
                terminalEndedAtMs=terminal['endedAtMs'], terminalOutside1200Intervals=True)


def summarize(result, name):
    cfg, motion = result['config'], result['nativeInputMotion']
    assert result['ok'] and result['error'] is None
    assert len(result['assertions']) == 26 and all(item['ok'] for item in result['assertions'])
    assert cfg['benchmark'] == 'scene' and cfg['drawControl'] == MODE and not cfg['presentationCheck']
    assert cfg['nativeInputMotion'] and cfg['nativeSprint'] and cfg['stableMotion'] and cfg['playerFire']
    assert cfg['fixedEnemies'] and cfg['combatRoute'] and not cfg['localEnemies']
    assert cfg['noLighting'] and cfg['noWall'] and not cfg['vision']
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
    old.six_smg10(result['playerFireWarmup']['encounter'])
    continuous = dense.continuous(result)
    assert len(result['samples']) == 4
    rows = []
    for index, row in enumerate(result['samples']):
        assert len(row['continuousFramesMs']) == 300 and row['empty'] == row['misses'] == 0
        assert row['playerShotFrames'] > 0 and row['enemyShotFrames'] > 0
        old.six_smg10(row['encounter'])
        for window in row['combatWindows']: old.six_smg10(window['encounter'])
        assert 'activityCensus' not in row and sum(row['probeTiming']['censusMs']) == sum(row['probeTiming']['progressSaveMs']) == 0
        rows.append(dict(index=index, continuous=base.metrics(row['continuousFramesMs']),
            playerShots=row['playerShotFrames'], enemyShots=row['enemyShotFrames'],
            workload=dense.workload(row,motion['route']), warmed=sum(row['warm']), slices=row['slices'],
            viewportObserverMs=base.metrics(row['staticBoxViewportMs'])))
    qualification = dict(actualSprint=sum(row['workload']['aboveWalkSpeedFrames'] for row in rows) >= 30,
        concurrentFixtureBullets=any(v >= 3 for row in result['samples'] for v in row['denseFrames']['fixtureBullets']),
        observedNativePlayerBullets=any(v > 0 for row in result['samples'] for v in row['denseFrames']['playerBullets']))
    qualification['passed'] = all(qualification.values())
    review = viewport_review(result)
    assert qualification['passed']
    return dict(version=VERSION, name=name, passed=True, complete=True, diagnosticOnly=True,
        performanceEligible=False, performanceAcceptance=False, gameplayAcceptance=False,
        visualAcceptance=False, detachEligible=False, deployed=False, qualification=qualification,
        continuous=continuous, rows=rows, viewportReview=review, staticBoxCensus=result['staticBoxCensus'],
        limits=['One terminal structural snapshot cannot prove immobility, future safety or detach eligibility.',
            'Per-frame inverse-transform observations and allocation remain in all 1200 continuous intervals; no production timing claim.',
            'Four segment-start viewports conservatively cover boundary display states; inverse full-stage AABBs include shake and ancestry.',
            'The helper expands the complete route union once by 320 pixels. No camera, physics, AI, visibility or display-tree mutation is added.',
            'No IP, thread-context or thread-CPU observer is imported or installed. Default process CPU accounting is unchanged.'])


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
    with m.Registration(owner='ContinuousScene / static Box census / 01a13816', purpose=args.name,
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
                          fixtureInputs=fixture, runtimeInputs=runtime, memoryBefore=memory)
            path = compile_probe(lease,baseline,scripts,compiler,fixture) if args.compile_probe else args.probe_build.resolve()
            probe = verify_probe(path,baseline,scripts,compiler,fixture)
            m.prepare(); shutil.copy2(probe['probePath'], m.RUNTIME / base.PROBE_PATH)
            for key, digest in baseline.items():
                if key not in ('application.xml','mods/loader-manifest.txt'): assert r.sha(m.RUNTIME/key) == digest, key
            assert baseline == r.baseline() and scripts == runner_inputs() and runtime == runtime_inputs()
            launch = m.parse_args(record['options'])
            assert launch.draw_control == MODE and not launch.profile and not launch.presentation_check
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
                            staticBoxCensus=raw.get('staticBoxCensus'), executionError=repr(run_error) if run_error else None))
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
                    performanceEligible=False,performanceAcceptance=False,detachEligible=False,deployed=False,
                    rawOK=result.get('ok'),rawError=result.get('error'),error=repr(validation_error),
                    staticBoxCensus=result.get('staticBoxCensus'),retainedSampleCount=len(result.get('samples',[])))
            summary.update(probeSHA256=probe['probeSHA256'],resultSHA256=r.sha(folder/'storage/result.json'),
                inputsUnchanged=True,runtimeInputsUnchanged=True,checks=len(result['assertions']),processPolicyAdapter=adapter)
            r.save(folder/'summary.json',summary)
            if run_error: raise run_error
            assert summary['passed'], 'Static Box census incomplete; original evidence retained'
            lease.outcome='passed'; lease.note='1200 unchanged native combat intervals and terminal Box structural census; no performance or detach acceptance'
            print(json.dumps({k:summary[k] for k in ('name','passed','complete','checks','detachEligible')}),flush=True)
        except BaseException as error:
            lease.outcome='failed'; lease.note=repr(error); folder.mkdir(parents=True,exist_ok=True)
            r.save(folder/'runner-failure.json',dict(record,error=repr(error),complete=False,deployed=False)); raise


shared.HERE, shared.VERSION = HERE, VERSION
shared.runner_inputs, shared.fixture_inputs = runner_inputs, fixture_inputs
base.OUT = HERE / 'probe-builds'
base.runner_inputs, base.candidate_inputs = runner_inputs, fixture_inputs
if __name__ == '__main__': main()
