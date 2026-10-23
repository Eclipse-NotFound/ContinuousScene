"""Isolated normal/scene dense native-input comparison; no deployment.

One frozen probe uses real movement keys, six native LMG enemies, and native
assault-rifle player fire. Four 300-frame windows retain continuous wall time.
This v2 variant requests sprint, never jump or forced per-frame movement.
It retains every interval while avoiding repeated settings and full-report IO.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import math
import shutil
import sys
import uuid

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
BUILD = HERE.parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base = load('dense_native_base', BUILD / 'native-input-combat-run.py')
patcher = load('dense_native_patch', HERE / 'probe_patch.py')
r, m, support = base.r, base.m, base.support
ORIGINAL_INPUTS = base.runner_inputs
CORE_RUNNER_PATHS = tuple(ORIGINAL_INPUTS())
RC = 'mods/Rconnect/release/RConnectMod.swf'
FORMAL_RC = 'EB3653533CFB305BCCA0B0CFE5E81BC306EA28FA400AAE751AB7B5AE1CFA5FEE'
VERSION = 'dense-sprint-2'


def fixture_inputs():
    return {str(p): r.sha(p) for p in (HERE / 'probe_patch.py', HERE / 'SceneDenseCombatMetrics.as')}


def runner_inputs():
    values = {path: r.sha(Path(path)) for path in CORE_RUNNER_PATHS}
    values[str(Path(__file__))] = r.sha(Path(__file__))
    values[str(BUILD / 'native-input-combat-run.py')] = r.sha(BUILD / 'native-input-combat-run.py')
    return values


base.OUT = HERE / 'probe-builds'
base.runner_inputs = runner_inputs
base.candidate_inputs = fixture_inputs


def compile_probe(lease, baseline, scripts, compiler, fixture):
    shared = BUILD.parent / 'src'
    before = base.tree_hashes(shared)
    staging = HERE / 'source-staging' / uuid.uuid4().hex
    patcher.prepare(shared, staging / 'src')
    assert before == base.tree_hashes(shared), 'Shared source changed during capture'
    after = base.tree_hashes(staging / 'src')
    changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    assert changed == ['ContinuousSceneMotionProbe.as', 'tests/SceneDenseCombatMetrics.as', 'tests/SceneEncounter.as']
    origin = staging / 'source-origin.json'
    r.save(origin, dict(version=VERSION, sharedSource=str(shared), sharedSHA256=before,
                        stagedSource=str(staging / 'src'), stagedSHA256=after, changed=changed, fixtureInputs=fixture))
    # Reuse the reviewed compiler/registry implementation against our copied tree.
    # This does not redirect any file under the shared production source path.
    base.B = staging / 'build'
    path = base.compile_frozen_probe(lease, baseline, scripts, compiler, fixture)
    receipt = r.read(path)
    receipt.update(denseFixture=VERSION, sourceOrigin=str(origin), sourceOriginSHA256=r.sha(origin))
    r.save(path, receipt)
    return path


def verify_probe(path, baseline, scripts, compiler, fixture):
    probe = base.verify_probe(path, baseline, scripts, compiler, fixture)
    assert probe['denseFixture'] == VERSION
    origin_path = Path(probe['sourceOrigin'])
    assert r.sha(origin_path) == probe['sourceOriginSHA256']
    origin = r.read(origin_path)
    assert origin['fixtureInputs'] == fixture and origin['stagedSHA256'] == probe['frozenSourceSHA256']
    return probe


def continuous(result):
    previous = result['continuousSampling']['startedAtMs']
    started = previous
    intervals = []
    for row in result['samples']:
        assert len(row['frames']) == len(row['sampleAtMs']) == len(row['continuousFramesMs']) == 300
        assert previous <= row['caseBeginAtMs'] <= row['sampleAtMs'][0]
        for i, (stamp, dt) in enumerate(zip(row['sampleAtMs'], row['continuousFramesMs'])):
            assert isinstance(stamp, int) and isinstance(dt, int) and dt == stamp - previous and dt >= 0
            assert dt >= row['frames'][i]
            if i:
                assert dt == row['frames'][i]
            intervals.append(dt)
            previous = stamp
        assert row['caseEndAtMs'] >= previous
    assert len(intervals) == 1200 and sum(intervals) == previous - started
    return dict(startedAtMs=started, endedAtMs=previous, count=len(intervals), totalMs=sum(intervals), metrics=base.metrics(intervals))


def workload(row, route):
    data = row['denseFrames']
    assert data['version'] == 'dense-workload-1' and data['samples'] == 300
    arrays = {k: v for k, v in data.items() if isinstance(v, list)}
    assert all(len(v) == 300 for v in arrays.values())
    bounds = route['safeCenterRange']
    fast = ground_run = airborne = 0
    for i in range(300):
        assert all(isinstance(data[k][i], (int, float)) and math.isfinite(data[k][i])
                   for k in ('x', 'y', 'dx', 'dy', 'walkSpeed', 'runSpeed', 'maxSpeed', 'stamina'))
        assert bounds['left'] <= data['x'][i] <= bounds['right']
        assert data['left'][i] != data['right'][i] and data['runKey'][i] and not data['jumpKey'][i]
        assert data['attackKey'][i]
        assert data['liveBullets'][i] == data['fixtureBullets'][i] + data['playerBullets'][i] + data['otherBullets'][i]
        assert data['chainBullets'][i] >= data['liveBullets'][i]
        if data['floorContact'][i]:
            assert data['stay'][i] and abs(data['y'][i] - route['floorY']) < .01 and abs(data['dy'][i]) < .01
        direction = 1 if data['right'][i] else -1
        # Only same-direction, grounded, actual native run frames establish sprint speed.
        # Knockback and airtime remain measured but do not qualify as sprint evidence.
        if data['stay'][i] and data['isRun'][i]:
            ground_run += 1
            if direction * data['dx'][i] > 1.1 * data['walkSpeed'][i]:
                fast += 1
        if not data['stay'][i]:
            airborne += 1
    assert max(data['x']) - min(data['x']) > 1 and any(data['floorContact'])
    return dict(groundedNativeRunFrames=ground_run, aboveWalkSpeedFrames=fast, airborneFrames=airborne,
        absoluteDx=base.metrics([abs(x) for x in data['dx']]),
        liveBullets=base.metrics(data['liveBullets']), fixtureBullets=base.metrics(data['fixtureBullets']),
        playerBullets=base.metrics(data['playerBullets']), observedNewBullets=sum(data['observedNewBullets']),
        scanMs=base.metrics(data['scanMs']), scanTotalMs=sum(data['scanMs']),
        objectsScanned=base.metrics(data['objectsScanned']), staminaMin=min(data['stamina']), staminaMax=max(data['stamina']))


def summarize(result, args):
    cfg, motion = result['config'], result['nativeInputMotion']
    assert cfg['benchmark'] == args.mode and cfg['drawControl'] == 'rcnative'
    assert cfg['nativeInputMotion'] and cfg['nativeSprint'] and cfg['stableMotion'] and cfg['playerFire']
    assert cfg['fixedEnemies'] and not cfg['localEnemies'] and cfg['noLighting'] and cfg['noWall'] and not cfg['vision']
    assert result['denseFixture']['version'] == VERSION and motion['version'] == 'native-input-dense-sprint-2'
    assert result['observerPolicy'] == dict(version='dense-observer-lean-2', settingsDuringTiming=False,
        segmentProgressWrites=False, segmentCensus=False, finalCensus=True, heartbeatIntervalMs=5000,
        continuousFramesRetained=True)
    assert result['driver']['forcedPositionCalls'] == 0 and motion['spawn']['calls'] == 1
    assert motion['warmup']['ready'] and motion['warmup']['roundTrips'] >= 1 and motion['warmup']['groundContactRun'] >= 10
    assert motion['timingStart']['floorContact'] and motion['route']['terrainVerified']
    assert result['world']['layoutSeed'] == 20261019 and len(result['samples']) == 4
    assert result['viewport']['zoom'] == 1
    assert (result['world']['width'], result['world']['height']) == ((48, 25) if args.mode == 'normal' else (240, 125))
    if args.mode == 'normal':
        assert (result['nativeRoom']['x'], result['nativeRoom']['y']) == (2, 4)
    rows = []
    for index, row in enumerate(result['samples']):
        assert row['name'] == 'dense-native-' + str(index) and row['empty'] == row['misses'] == 0
        assert row['playerShotFrames'] > 0 and row['enemyShotFrames'] > 0
        base.six_armed(row['encounter'])
        assert all(u['weapon']['id'] == 'lmg' for u in row['encounter']['actors'])
        assert 'activityCensus' not in row
        assert sum(row['probeTiming']['censusMs']) == sum(row['probeTiming']['progressSaveMs']) == 0
        rows.append(dict(index=index, continuous=base.metrics(row['continuousFramesMs']),
            withinSegment=base.metrics(row['frames']), nativeBand=base.metrics(row['nativeBand']),
            playerShots=row['playerShotFrames'], enemyShots=row['enemyShotFrames'],
            combatWindows=base.combat_windows(row, 300), workload=workload(row, motion['route']),
            activity=row['activity'], activityEnd=row.get('activityEnd'), warmed=sum(row['warm']),
            censusMs=sum(row['probeTiming']['censusMs']), saveMs=sum(row['probeTiming']['saveMs']),
            heartbeatSaveMs=sum(row['probeTiming']['heartbeatSaveMs']),
            probeWorkMs=base.metrics(row['probeTiming']['workMs']),
            startCaseMs=base.metrics(row['probeTiming']['startCaseMs'])))
    final_census = result.get('finalActivityCensus')
    if args.mode == 'scene':
        assert final_census and final_census['afterFinalSample']
        assert result['samples'][-1]['sampleAtMs'][-1] <= final_census['startedAtMs'] <= final_census['endedAtMs']
        assert final_census['data']
    else:
        assert final_census is None
    # Report insufficient sprint or density as fixture qualification failure,
    # never redefine a slow/empty run as the intended stress workload.
    qualification = dict(actualSprint=sum(x['workload']['aboveWalkSpeedFrames'] for x in rows) >= 30,
        concurrentFixtureBullets=any(v >= 3 for row in result['samples'] for v in row['denseFrames']['fixtureBullets']),
        observedNativePlayerBullets=any(v > 0 for row in result['samples'] for v in row['denseFrames']['playerBullets']),
        playerShotFrames=sum(x['playerShots'] for x in rows), enemyShotFrames=sum(x['enemyShots'] for x in rows))
    qualification['passed'] = all(qualification[k] for k in
        ('actualSprint', 'concurrentFixtureBullets', 'observedNativePlayerBullets'))
    room = result['selectedCombatRoom']
    offset_x, offset_y = room['x'] * 1920, room['y'] * 1000
    route = motion['route']
    return dict(version=VERSION, name=args.name, mode=args.mode, diagnosticOnly=True,
        performanceEligible=False, performanceAcceptance=False, deployed=False,
        continuous=continuous(result), samples=rows, qualification=qualification,
        normalizedRoute=dict(x=route['playerX'] - offset_x, endX=route['endX'] - offset_x,
            floorY=route['floorY'] - offset_y,
            enemies=[dict(x=e['x'] - offset_x, y=e['y'] - offset_y) for e in route['enemies']]),
        nativeRouteHash=dict(hash=route['hash'], cells=route['cells']),
        selectedCombatCorridorTiles=result['selectedCombatCorridorTiles'], viewport=result['viewport'],
        fixture=result['denseFixture'], world=result['world'], initialEncounter=result['encounter'],
        observerPolicy=result['observerPolicy'], finalActivityCensus=final_census,
        limitations=['Real input, acceleration, knockback and stamina; no jumps requested in this variant.',
            'Six native LMG enemies, not twelve; verify observed concurrency instead of inferring density from weapon names.',
            'Inherited durable enemies/damage2 and player ammo/durability refill/godMode make this a diagnostic sustained-fire fixture.',
            'All continuous intervals and per-frame scan costs are retained; no subtraction or outlier removal.',
            'Display settings apply once before warmup; only a short heartbeat is written during the four windows.',
            'Full activity census runs once after the final sampled timestamp, outside the timing series.',
            'The final sample ends the wall-time series; work after that final timestamp and terminal cleanup are outside it.',
            'Original room camera bounds and offscreen population differ from a continuous map; paired times are experience comparison, not pure scheduler causality.',
            'AI decisions and encounter population are not fully seeded. Compare fire, activity and windows, not pooled time alone.',
            'This fixture uses scale1 with lighting/vision/WallBlend off; no all-effects or multiplayer performance claim.'])


def main():
    if not __debug__:
        raise RuntimeError('Do not disable assertions')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    parser.add_argument('--mode', choices=['normal', 'scene'], required=True)
    parser.add_argument('--paired-evidence', help='Completed other mode; must reuse its exact probe')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--compile-probe', action='store_true')
    group.add_argument('--probe-build', type=Path)
    parser.add_argument('--registry-wait', type=int, default=600)
    args = parser.parse_args()
    assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
    folder = r.E / args.name
    assert not folder.exists(), 'Preserve existing evidence'
    assert not args.paired_evidence or args.probe_build
    with m.Registration(owner='ContinuousScene / dense native fixture / 01a13816', purpose=args.name,
                        run_dir=m.RUNTIME, evidence=folder, wait=args.registry_wait) as lease:
        assert not m.air_pids(), 'Other AIR remains untouched'
        baseline, scripts, compiler, fixture = r.baseline(), runner_inputs(), support.compiler_inputs(), fixture_inputs()
        assert baseline['pfe.swf'] == base.FORMAL_HOST and baseline[base.CS_PATH] == base.FORMAL_CS
        assert baseline[RC] == FORMAL_RC
        path = compile_probe(lease, baseline, scripts, compiler, fixture) if args.compile_probe else args.probe_build.resolve()
        probe = verify_probe(path, baseline, scripts, compiler, fixture)
        reference = None
        if args.paired_evidence:
            assert all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.paired_evidence)
            r.result(args.paired_evidence)
            old = r.E / args.paired_evidence
            reference = r.read(old / 'summary.json')
            assert reference['version'] == VERSION and reference['mode'] != args.mode
            assert r.read(old / 'probe-build.json')['probeSHA256'] == probe['probeSHA256']
            assert r.read(old / 'runner-inputs.json')['baseline'] == baseline
        m.prepare()
        shutil.copy2(probe['probePath'], m.RUNTIME / base.PROBE_PATH)
        for key in ('pfe.swf', base.CS_PATH, RC):
            assert r.sha(m.RUNTIME / key) == baseline[key]
        options = ['--name', args.name, '--high-qos', '--land', 'random_mane', '--encounter', '--fixed-enemies',
            '--benchmark', args.mode, '--short', '--stable-motion', '--native-input-motion', '--native-sprint',
            '--player-fire', '--combat-route', '--combat-route-length', '200', '--window-width', '2048',
            '--window-height', '1123', '--no-lighting', '--no-wall', '--draw-control', 'rcnative']
        if args.mode == 'normal':
            options += ['--native-room-x', '2', '--native-room-y', '4', '--native-route-x', '480', '--native-route-y', '119']
        else:
            options += ['--expect-no-signs']
        try:
            m.run_owned(m.parse_args(options), lease)
        finally:
            if folder.exists():
                r.save(folder / 'probe-build.json', probe)
                r.save(folder / 'runner-inputs.json', dict(options=options, baseline=baseline, runnerInputs=scripts,
                    compilerInputs=compiler, fixtureInputs=fixture, probeBuildPath=str(path), pairedEvidence=args.paired_evidence))
        assert baseline == r.baseline() and scripts == runner_inputs() and fixture == fixture_inputs()
        verify_probe(path, baseline, scripts, compiler, fixture)
        result, inputs = r.result(args.name)
        for key, digest in baseline.items():
            if key not in ('application.xml', 'mods/loader-manifest.txt'):
                assert inputs[key] == digest, key
        assert inputs[base.PROBE_PATH] == probe['probeSHA256']
        policy = r.read(folder / 'process-policy.json')
        assert policy['performanceEligible'] is False and not policy.get('runFailure')
        assert not policy.get('memoryAbort') and not policy.get('otherAirProcessIds')
        summary = summarize(result, args)
        if reference:
            matched = all(summary[k] == reference[k] for k in
                ('normalizedRoute', 'nativeRouteHash', 'selectedCombatCorridorTiles', 'viewport'))
            summary['pairedComparison'] = dict(evidence=args.paired_evidence, matchedTerrainAndProbe=matched,
                previous=reference['continuous'], current=summary['continuous'], exactCausalAcceptance=False)
        r.save(folder / 'summary.json', summary)
        print(json.dumps({k: summary[k] for k in ('name', 'mode', 'continuous', 'qualification')}, ensure_ascii=False), flush=True)
        assert summary['qualification']['passed'], 'Measured workload did not establish sprint and concurrent fire; evidence retained'
        assert not reference or summary['pairedComparison']['matchedTerrainAndProbe'], 'Different terrain/view; retain evidence, do not claim matched comparison'
        lease.outcome = 'passed'
        lease.note = 'Dense native-input workload captured; no production acceptance or deployment'


if __name__ == '__main__':
    main()
