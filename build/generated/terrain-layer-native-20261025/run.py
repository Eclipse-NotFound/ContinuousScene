"""Registered terrain-bitmap attribution: unchanged native SMG combat, 4 x 300 ABBA.

Only isolated probe/runtime outputs are written. B intentionally omits terrain;
these observations are neither a playable candidate nor product FPS acceptance.
"""
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
import uuid

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
VERSION = 'terrain-layer-native-1'
FIXTURE_VERSION = 'dense-sprint-smg10-1'
SEED_SHA = '983727AEB832BC586AF3767613B7C9D61564D92DC9D8E2435F972EEBF1D1D5EE'
PROBE_SHA = '29AF34571E7181139C682AA32A160E2C217C1B02B295E6DCBD6931D8DB7F94E5'
HELPER_SHA = '9EB7A9215F03BCDD6CB538E50BA24CEBDFAA4576F87F719E982C1230B52742EF'
PATCH_SHA = '1150197A929552A31A4A0A4AC7F74D1CE1E303DAFAE708FDBB68D650F44E0CB0'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


old = load('terrain_smg_build_support', HERE.parent / 'camera-atlas-paged-combat-20261025/run.py')
shared, control, dense, base, r, m, support = old.shared, old.control, old.dense, old.base, old.r, old.m, old.support
patch = load('terrain_native_patch', HERE / 'probe_patch.py')
HELPER = HERE / 'SceneTerrainLayerTrial.as'
SEED_RECEIPT = r.E / 'camera-atlas-paged-combat-20261025-r1/probe-build.json'
PINS = dict(old.PINS)
POLICY_BEFORE = "if getattr(args,'draw_control',None) in ('world','fog','objects','objectgroups','effects','sleepclips','implicitpause','mousetree','shortlayers','worldlayers','unitviewport','bulletblend'):"
POLICY_AFTER = POLICY_BEFORE[:-2] + ",'terrainback','terrainfront'):"


def policy_adapter():
    """Copy one function; the shared module and all execution/memory code stay intact."""
    original = inspect.getsource(m.run_owned)
    assert original.count(POLICY_BEFORE) == 1 and POLICY_AFTER not in original
    changed = original.replace(POLICY_BEFORE, POLICY_AFTER, 1)
    assert changed.replace(POLICY_AFTER, POLICY_BEFORE, 1) == original
    tree = ast.parse(changed)
    assert len(tree.body) == 1 and isinstance(tree.body[0], ast.FunctionDef)
    assert tree.body[0].name == 'run_owned'
    assert "current['availableCommit']<512*1024**2" in original
    assert 'HiddenProcess(' in original and 'record.child(process.pid)' in original
    namespace = dict(m.__dict__)
    exec(compile(tree, '<terrain-only-process-policy-adapter>', 'exec'), namespace)
    function = namespace['run_owned']
    assert function is not m.run_owned and function.__globals__ is not m.__dict__
    digest = lambda text: hashlib.sha256(text.encode('utf-8')).hexdigest().upper()
    return function, dict(version='terrain-only-policy-adapter-1', originalSHA256=digest(original),
        transformedSHA256=digest(changed), originalAnchor=POLICY_BEFORE, replacementAnchor=POLICY_AFTER,
        originalModule=str(Path(m.__file__).resolve()), originalModuleSHA256=r.sha(Path(m.__file__)),
        onlyChange='Add terrainback/terrainfront to intentionally-hidden rendering policy tuple',
        sourceRestoredExactly=True, sharedModuleModified=False, runGuardBytes=512*1024**2)


def seed():
    assert r.sha(SEED_RECEIPT) == SEED_SHA
    value = r.read(SEED_RECEIPT)
    assert value['version'] == 'native-input-combat-probe-1'
    assert value['motionAtlasCombatVersion'] == 'camera-atlas-paged-smg10-combat-1'
    assert value['denseFixture'] == FIXTURE_VERSION and value['observerFixtureSource'] == dense.VERSION
    assert value['probeSHA256'] == PROBE_SHA == patch.SOURCE_PROBE == r.sha(Path(value['probePath']))
    assert r.sha(Path(value['configPath'])) == value['configSHA256']
    assert r.sha(Path(value['sourceOrigin'])) == value['sourceOriginSHA256']
    assert len(value['frozenSourceSHA256']) == 85
    assert base.tree_hashes(Path(value['frozenSourcePath'])) == value['frozenSourceSHA256']
    return value


def runner_inputs():
    assert r.sha(HELPER) == HELPER_SHA and r.sha(HERE / 'probe_patch.py') == PATCH_SHA
    return dict(old.runner_inputs(), **{str(p): r.sha(p) for p in
        [Path(old.__file__), Path(shared.__file__), Path(m.__file__), HERE / 'run.py',
         HERE / 'probe_patch.py', HELPER, SEED_RECEIPT]})


def fixture_inputs():
    value = seed()
    return {str(p): r.sha(p) for p in [SEED_RECEIPT, Path(value['probePath']),
        Path(value['configPath']), Path(value['sourceOrigin']), HERE / 'probe_patch.py', HELPER,
        support.OUT / 'source-provenance.json']}


def compile_probe(lease, baseline, scripts, compiler, fixture):
    value = seed(); staging = HERE / 'source-staging' / uuid.uuid4().hex
    patch.prepare(Path(value['frozenSourcePath']), staging / 'src')
    after = base.tree_hashes(staging / 'src')
    changed = sorted(k for k in set(after) | set(value['frozenSourceSHA256'])
        if after.get(k) != value['frozenSourceSHA256'].get(k))
    assert changed == patch.CHANGED and len(after) == 86
    origin = staging / 'source-origin.json'
    r.save(origin, dict(version=VERSION, seedReceipt=str(SEED_RECEIPT), seedReceiptSHA256=SEED_SHA,
        seedProbeSHA256=PROBE_SHA, seedSourceSHA256=value['frozenSourceSHA256'],
        stagedSHA256=after, changed=changed, fixtureInputs=fixture))
    path = shared.compile_frozen(lease, staging / 'src', baseline, scripts, compiler, fixture)
    receipt = r.read(path)
    receipt.update(terrainLayerVersion=VERSION, denseFixture=FIXTURE_VERSION, observerFixtureSource=dense.VERSION,
        sourceOrigin=str(origin), sourceOriginSHA256=r.sha(origin))
    r.save(path, receipt); return path


def verify_probe(path, baseline, scripts, compiler, fixture):
    value = base.verify_probe(path, baseline, scripts, compiler, fixture)
    assert value['terrainLayerVersion'] == VERSION and value['denseFixture'] == FIXTURE_VERSION
    assert value['observerFixtureSource'] == dense.VERSION
    op = Path(value['sourceOrigin']); assert r.sha(op) == value['sourceOriginSHA256']
    origin, source = r.read(op), seed()
    assert origin['seedReceiptSHA256'] == SEED_SHA and origin['seedProbeSHA256'] == PROBE_SHA
    assert origin['seedSourceSHA256'] == source['frozenSourceSHA256'] and origin['changed'] == patch.CHANGED
    assert origin['stagedSHA256'] == value['frozenSourceSHA256'] and origin['fixtureInputs'] == fixture
    changed = sorted(k for k in set(value['frozenSourceSHA256']) | set(source['frozenSourceSHA256'])
        if value['frozenSourceSHA256'].get(k) != source['frozenSourceSHA256'].get(k))
    assert changed == patch.CHANGED and len(value['frozenSourceSHA256']) == 86
    frozen, original = Path(value['frozenSourcePath']), Path(source['frozenSourcePath'])
    assert (frozen / 'ContinuousSceneMotionProbe.as').read_text('utf-8-sig') == patch.transform(
        (original / 'ContinuousSceneMotionProbe.as').read_text('utf-8-sig'))
    assert r.sha(frozen / HELPER.name) == r.sha(HELPER)
    return value


def options(name):
    # New draw-control names are assigned only after the unchanged parser runs.
    return ['--name', name, '--high-qos', '--land', 'random_mane', '--encounter', '--fixed-enemies',
        '--benchmark', 'scene', '--short', '--stable-motion', '--native-input-motion', '--native-sprint',
        '--player-fire', '--combat-route', '--combat-route-length', '200', '--window-width', '2048',
        '--window-height', '1123', '--no-lighting', '--no-wall', '--expect-no-signs']


def snapshot(value):
    assert value['version'] == VERSION and value['errors'] == []
    for key in ('pendingRestore', 'updates', 'hides', 'restores', 'nodesScanned'):
        assert isinstance(value[key], int) and value[key] >= 0
    assert value['hides'] - value['restores'] == value['pendingRestore']
    assert value['applied'] is (value['pendingRestore'] > 0)
    for key in ('bindingsCreated','bindingsReleased','liveBindings'):
        assert isinstance(value[key], int) and value[key] >= 0
    assert value['bindingsCreated'] - value['bindingsReleased'] == value['liveBindings']


def terrain_frames(result, mode):
    report = result['terrainLayer']
    assert report['version'] == VERSION and report['mode'] == mode and report['order'] == [False, True, True, False]
    assert report['diagnosticOnly'] and not report['performanceEligible'] and not report['visualAcceptance']
    targets = (0,) if mode == 'terrainfront' else (1, 2)
    previous = None; totals = dict(updates=0, hides=0, nodesScanned=0)
    observations = []
    for index, row in enumerate(result['samples']):
        segment = row['terrainLayer']; enabled = index in (1, 2)
        assert segment['version'] == VERSION and segment['mode'] == mode and len(segment['frames']) == 300
        start = segment['start']; snapshot(start)
        if previous is not None:
            assert start == previous['snapshot']
        else:
            assert start['mode'] == '' and all(start[key] == 0 for key in totals)
        for j, frame in enumerate(segment['frames']):
            assert frame['version'] == VERSION and frame['mode'] == mode and frame['enabled'] is enabled
            assert frame['previousApplied'] is (previous['applied'] if previous else False)
            assert frame['identityParentDataPreserved'] and frame['nonTargetVisibilityPreserved'] and frame['watchedUnchanged']
            assert frame['watchedBefore'] == frame['watchedAfter']
            watched = {x['name']: x for x in frame['watchedBefore']}
            assert len(watched) == len(frame['watchedBefore']) and len(watched) >= 8
            assert {'world','frontParent','backParent','back2Parent','waterParent','fogParent','satsParent','objects0'} <= set(watched)
            assert watched['world']['effectiveVisible'] and not watched['satsParent']['visible']
            assert frame['surfaces'] > 0 and frame['nodes'] == 4 * frame['surfaces']
            assert frame['totalByLayer'] == [frame['surfaces']] * 4
            before, after = frame['beforeVisible'], frame['afterVisible']
            assert len(before) == len(after) == 4
            assert all(isinstance(v, int) and 0 <= v <= frame['surfaces'] for v in before + after)
            target = sum(before[k] for k in targets)
            assert frame['targetVisible'] == target and frame['hidden'] == (target if enabled else 0)
            assert frame['applied'] is (frame['hidden'] > 0)
            assert after == [0 if enabled and k in targets else before[k] for k in range(4)]
            camera = frame['camera']
            assert set(camera) == set(('vx','vy','scale','worldX','worldY','quakeX','quakeY','a','b','c','d','tx','ty'))
            assert all(base.finite(v) for v in camera.values()) and camera['scale'] > 0
            moving = previous is not None and any(camera[k] != previous['camera'][k] for k in ('vx','vy','scale','tx','ty'))
            assert frame['cameraMoving'] is moving
            counters = frame['nativeCounters']
            assert set(counters) == {'resident','warm','slices','forced','misses'}
            assert all(isinstance(v, int) and v >= 0 for v in counters.values())
            assert counters['resident'] == frame['surfaces']
            if previous:
                assert all(counters[k] >= previous['nativeCounters'][k] for k in counters)
                assert counters['warm'] - previous['nativeCounters']['warm'] == row['warm'][j]
            snap = frame['snapshot']; snapshot(snap)
            assert snap['mode'] == mode and snap['restores'] == totals['hides']
            totals['updates'] += 1; totals['hides'] += frame['hidden']; totals['nodesScanned'] += frame['nodes']
            assert all(snap[key] == value for key, value in totals.items())
            assert snap['pendingRestore'] == frame['hidden']
            assert snap['liveBindings'] == frame['nodes']
            previous = frame
        assert segment['end'] == previous['snapshot']
        end = previous['nativeCounters']
        assert end['resident'] == row['residentEnd'] and end['misses'] - row['missStart'] == row['misses']
        assert end['slices'] - row['slicesStart'] == row['slices'] and end['forced'] - row['forcedStart'] == row['forced']
        assert row['residentStart'] <= segment['frames'][0]['nativeCounters']['resident']
        hidden = sum(f['hidden'] for f in segment['frames'])
        assert hidden > 0 if enabled else hidden == 0
        observations.append(dict(enabled=enabled, appliedFrames=sum(f['applied'] for f in segment['frames']),
            priorAppliedFrames=sum(f['previousApplied'] for f in segment['frames']),
            movingFrames=sum(f['cameraMoving'] for f in segment['frames']), hidden=hidden,
            nodesScanned=sum(f['nodes'] for f in segment['frames']),
            residentStart=row['residentStart'], residentEnd=row['residentEnd'],
            nativeCounterStart=segment['frames'][0]['nativeCounters'], nativeCounterEnd=end,
            start=start, end=segment['end']))
    cleanup = result['terrainLayerCleanup']
    assert cleanup['restored'] and cleanup['errors'] == [] and cleanup['diagnosticOnly'] and not cleanup['performanceEligible']
    snapshot(cleanup['before']); snapshot(cleanup['after'])
    assert cleanup['before'] == previous['snapshot']
    final = cleanup['after']
    assert all(final[key] == value for key, value in totals.items()) and totals['updates'] == 1200
    assert final['restores'] == final['hides'] and final['pendingRestore'] == 0 and not final['applied']
    assert final['bindingsCreated'] == final['bindingsReleased'] and final['liveBindings'] == 0
    return observations, cleanup


def summarize(result, name, mode):
    cfg, motion = result['config'], result['nativeInputMotion']
    assert result['ok'] and not result['error'] and len(result['assertions']) == 26 and all(x['ok'] for x in result['assertions'])
    assert cfg['benchmark'] == 'scene' and cfg['drawControl'] == mode and not cfg['presentationCheck']
    assert cfg['nativeInputMotion'] and cfg['nativeSprint'] and cfg['stableMotion'] and cfg['playerFire']
    assert cfg['fixedEnemies'] and not cfg['localEnemies'] and cfg['noLighting'] and cfg['noWall'] and not cfg['vision']
    assert not any(cfg[k] for k in ('profile','bulletSegments','worldProfile','locationProfile','guiWeaponProfile','playerStepProfile','playerAnimateProfile'))
    assert result['denseFixture']['version'] == FIXTURE_VERSION and motion['version'] == 'native-input-dense-sprint-2'
    assert result['denseFixture']['enemyWeapon'] == 'smg10' and result['denseFixture']['actors'] == 6
    old.six_smg10(result['playerFireWarmup']['encounter'])
    assert result['observerPolicy'] == dict(version='dense-observer-lean-2', settingsDuringTiming=False,
        segmentProgressWrites=False, segmentCensus=False, finalCensus=True, heartbeatIntervalMs=5000,
        continuousFramesRetained=True)
    assert result['driver']['forcedPositionCalls'] == 0 and motion['spawn']['calls'] == 1
    assert motion['warmup']['ready'] and motion['warmup']['roundTrips'] >= 1 and motion['warmup']['groundContactRun'] >= 10
    assert motion['timingStart']['floorContact'] and motion['route']['terrainVerified']
    assert result['world']['layoutSeed'] == 20261019 and len(result['samples']) == 4
    assert result['viewport']['zoom'] == 1 and (result['world']['width'], result['world']['height']) == (240, 125)
    terrain, cleanup = terrain_frames(result, mode)
    rows = []
    for index, row in enumerate(result['samples']):
        assert row['name'] == ['draw-baseline-a','draw-control-b','draw-control-b-repeat','draw-baseline-a-repeat'][index]
        assert row['empty'] == row['misses'] == 0 and row['playerShotFrames'] > 0 and row['enemyShotFrames'] > 0
        old.six_smg10(row['encounter'])
        for observation in row['combatWindows']: old.six_smg10(observation['encounter'])
        assert 'activityCensus' not in row
        assert sum(row['probeTiming']['censusMs']) == sum(row['probeTiming']['progressSaveMs']) == 0
        bands = {key: base.metrics(row[key]) for key in ('nativeBand','wallBand','sceneBand','preBand','tailBand','totalScript','afterProbeBand')}
        rows.append(dict(index=index, mode='hidden' if index in (1,2) else 'native',
            continuous=base.metrics(row['continuousFramesMs']), withinSegment=base.metrics(row['frames']),
            bands=bands, playerShots=row['playerShotFrames'], enemyShots=row['enemyShotFrames'],
            combatWindows=base.combat_windows(row,300), workload=dense.workload(row,motion['route']),
            activity=row['activity'],activityEnd=row.get('activityEnd'),warmed=sum(row['warm']),
            slices=row['slices'],forced=row['forced'],probeWorkMs=base.metrics(row['probeTiming']['workMs']),
            terrainLayer=terrain[index]))
    census = result['finalActivityCensus']
    assert census['afterFinalSample'] and census['data']
    assert result['samples'][-1]['sampleAtMs'][-1] <= census['startedAtMs'] <= census['endedAtMs']
    qualification = dict(actualSprint=sum(x['workload']['aboveWalkSpeedFrames'] for x in rows) >= 30,
        concurrentFixtureBullets=any(v >= 3 for row in result['samples'] for v in row['denseFrames']['fixtureBullets']),
        observedNativePlayerBullets=any(v > 0 for row in result['samples'] for v in row['denseFrames']['playerBullets']),
        playerShotFrames=sum(x['playerShots'] for x in rows),enemyShotFrames=sum(x['enemyShots'] for x in rows))
    qualification['passed'] = all(qualification[k] for k in ('actualSprint','concurrentFixtureBullets','observedNativePlayerBullets'))
    grouped = {label:base.metrics([dt for i,row in enumerate(result['samples']) if (i in (1,2)) == hidden
        for dt in row['continuousFramesMs']]) for label,hidden in (('native',False),('hidden',True))}
    prior = {label:base.metrics([dt for row in result['samples'] for dt,frame in
        zip(row['continuousFramesMs'],row['terrainLayer']['frames']) if frame['previousApplied'] is hidden])
        for label,hidden in (('native',False),('hidden',True))}
    return dict(version=VERSION,name=name,layer=mode,complete=True,diagnosticOnly=True,performanceEligible=False,
        performanceAcceptance=False,gameplayAcceptance=False,visualAcceptance=False,deployed=False,
        qualification=qualification,fixtureVersion=FIXTURE_VERSION,observerFixtureSource=dense.VERSION,
        continuous=dense.continuous(result),rows=rows,grouped=grouped,byPriorPresentation=prior,cleanup=cleanup,
        weaponStats=[a['weaponStats'] for a in result['samples'][0]['encounter']['actors']],
        limitations=['Terrain is intentionally hidden in B; no visual/gameplay acceptance or production optimization.',
            'Only native terrain Bitmap children [0] or [1,2] change. Parent/object/water/fog layers remain unchanged.',
            'A and B scan the same four layers and retain observer work, visibility setters, restores and transitions in all 1200 intervals.',
            'Primary ABBA groups follow the requested window; byPriorPresentation also groups all intervals by the actual preceding presentation. No boundary frames are removed.',
            'Probe work includes the terrain observer but does not isolate its CPU cost. Frame/script residual is not GPU time.',
            'Native SMG10/ASSR fire, AI, physics, Shift input and knockback remain active; unseeded population/fire and prewarm may differ between windows.',
            'Lighting, vision and WallBlend are off. Shared helpers and sampler/profile flags are not enabled to alter process classification.'])


def main():
    assert __debug__
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name',required=True); parser.add_argument('--layer',choices=['back','front'],required=True)
    parser.add_argument('--registry-wait',type=int,default=600)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--compile-probe',action='store_true'); group.add_argument('--probe-build',type=Path)
    args=parser.parse_args()
    assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
    folder=r.E/args.name; assert not folder.exists(),'Preserve prior evidence'
    mode='terrain'+args.layer
    run_owned, adapter=policy_adapter()
    record=dict(version=VERSION,diagnosticOnly=True,performanceEligible=False,gameplayAcceptance=False,
        fixtureVersion=FIXTURE_VERSION,observerFixtureSource=dense.VERSION,options=options(args.name),
        drawControlAssignment=mode,processPolicyAdapter=adapter)
    with m.Registration(owner='ContinuousScene / native terrain attribution / 01a13816',purpose=args.name,
                        run_dir=m.RUNTIME,evidence=folder,resource='game',wait=args.registry_wait) as lease:
        try:
            assert not m.air_pids(),'Other AIR remains untouched'
            memory=control.memory_gate()
            baseline,scripts,compiler,fixture=r.baseline(),runner_inputs(),support.compiler_inputs(),fixture_inputs()
            rv=r.read(old.RV_RECEIPT)
            assert rv['result']=='PASS' and rv['new'].upper()==old.RV_CURRENT and rv['before']['pfe.swf'].upper()==control.HOST
            for key,digest in PINS.items(): assert baseline[key]==digest,key
            record.update(baseline=baseline,runnerInputs=scripts,compilerInputs=compiler,fixtureInputs=fixture,
                          memoryBefore=memory,hostSHA256=control.HOST)
            path=compile_probe(lease,baseline,scripts,compiler,fixture) if args.compile_probe else args.probe_build.resolve()
            probe=verify_probe(path,baseline,scripts,compiler,fixture)
            m.prepare(); shutil.copy2(probe['probePath'],m.RUNTIME/base.PROBE_PATH)
            for key,digest in baseline.items():
                if key not in ('application.xml','mods/loader-manifest.txt'): assert r.sha(m.RUNTIME/key)==digest,key
            assert baseline==r.baseline() and scripts==runner_inputs()
            launch=m.parse_args(record['options']); assert launch.draw_control is None
            launch.draw_control=mode
            assert not launch.profile and not launch.presentation_check
            record.update(probeBuildPath=str(path),probeSHA256=probe['probeSHA256'],memoryBeforeAir=control.memory_gate())
            try: run_owned(launch,lease)
            finally:
                if folder.exists():
                    r.save(folder/'probe-build.json',probe); r.save(folder/'runner-inputs.json',record)
            assert baseline==r.baseline() and scripts==runner_inputs() and fixture==fixture_inputs()
            assert compiler==support.compiler_inputs() and policy_adapter()[1]==adapter
            verify_probe(path,baseline,scripts,compiler,fixture)
            result,actual=r.result(args.name)
            for key,digest in baseline.items():
                if key not in ('application.xml','mods/loader-manifest.txt'): assert actual[key]==digest,key
            assert actual[base.PROBE_PATH]==probe['probeSHA256']
            policy=r.read(folder/'process-policy.json')
            assert policy['desktopPolicy']=='private' and not policy['performanceEligible']
            assert policy['diagnosticOnly']=='Rendering intentionally hidden for attribution'
            assert not policy.get('runFailure') and not policy.get('memoryAbort') and not policy.get('otherAirProcessIds')
            summary=summarize(result,args.name,mode)
            summary.update(probeSHA256=probe['probeSHA256'],resultSHA256=r.sha(folder/'storage/result.json'),
                           inputsUnchanged=True,checks=len(result['assertions']),processPolicyAdapter=adapter)
            r.save(folder/'summary.json',summary)
            assert summary['qualification']['passed'],'Native sprint/fire qualification failed; retained'
            lease.outcome='passed';lease.note='1200-frame native terrain-only attribution; intentionally hidden, no deployment'
            print(json.dumps({k:summary[k] for k in ('name','layer','continuous','grouped','qualification','checks')},ensure_ascii=False),flush=True)
        except BaseException as error:
            lease.outcome='failed';lease.note=repr(error)
            folder.mkdir(parents=True,exist_ok=True)
            r.save(folder/'runner-failure.json',dict(record,error=repr(error),complete=False,deployed=False))
            raise


shared.HERE,shared.VERSION=HERE,VERSION
shared.runner_inputs,shared.fixture_inputs=runner_inputs,fixture_inputs
base.OUT=HERE/'probe-builds'
base.runner_inputs,base.candidate_inputs=runner_inputs,fixture_inputs
if __name__=='__main__':main()
