"""Frozen native-controller combat diagnostic on formal BEFC.

The player walks through Controller input and native control/run; this runner
must reject position-stepping fixtures. Formal CS and the reviewed sleeping-root
r2 candidate are selectable. All runs remain isolated and diagnostic-only.
"""
from pathlib import Path
from datetime import datetime
from xml.sax.saxutils import escape
import argparse
import importlib.util
import json
import math
import shutil
import statistics
import subprocess
import sys
import uuid

sys.dont_write_bytecode = True
B = Path(__file__).resolve().parent
OUT = B / 'generated/native-input-combat-20261022'
FORMAL_HOST = 'BEFCF0509E11FAC9FEF7AFB834708B8B93752A14AE3D5CD72B42AA6D42F9B82A'
FORMAL_CS = '7F1F2961C6E299D949423591F3C65C610C2EAEFA7FC72E8A583A402770D6B51F'
CANDIDATE_SHA = '76748C8EDF4B3320B330ED60A84AE6C179A63DE52B24C42DD82333501ADA0172'
CS_PATH = 'mods/ContinuousScene/release/ContinuousSceneMod.swf'
PROBE_PATH = 'mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf'
HELPER = 'tests/SceneSleepingRootPresentation.as'
PIXEL_CHECK = 'sleeping-root-20261022-pixels-r2'
PIXEL_RESULT_SHA = '23BCF1DFFEEB21711C95E2D38FA2D83D00D92D80719140F8C92A57A78ED6EF71'
NATIVE_CONTRACT_READY = True
SHORT_CONTRACT_READY = True
CONTROL_CASES = ('draw-baseline-a', 'draw-control-b', 'draw-control-b-repeat', 'draw-baseline-a-repeat')
BASE_CASES = ('enemy-idle', 'enemy-fast-forward', 'enemy-fast-back', 'enemy-idle-end')
LIMITATIONS = [
    'Native room camera is bounded; continuous camera follows and can show neighboring rooms.',
    'Normal and scene experience comparisons include different offscreen populations.',
    'The source layout seed does not seed all AI decisions or combat randomness.',
    'Combat population, wake propagation and terrain revisions are reported by time window; pooled ABBA is not sufficient causality.',
    'All segment frame times, including switch overhead, are primary. Excluding the first two boundary frames is only a secondary view; gate installation precedes actual detachment by one frame.',
    'Only scale 1 with lighting, RealisticVision and WallBlend off is covered.',
    'This diagnostic does not accept production performance or deploy any file.'
]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


support = load('native_input_sleeping_root_support', B / 'sleeping-root-r2-run.py')
r, m = support.r, support.m
metrics, six_armed, check_sleeping_stats = support.metrics, support.six_armed, support.check_stats


def tree_hashes(folder):
    return {p.relative_to(folder).as_posix(): r.sha(p)
            for p in sorted(folder.rglob('*')) if p.is_file()}


def runner_inputs():
    paths = (Path(__file__), B / 'sleeping-root-r2-run.py', B / 'sleeping-root-r2-build.py',
             B / 'enemy-release.py', B / 'enemy-speed.py', B / 'motion-test.py', B / 'profile-vision.py',
             r.ROOT / 'mods/ModLoader/tools/test_registry.py',
             r.ROOT / 'mods/ModLoader/tools/air_test_process.py')
    return {str(p): r.sha(p) for p in paths}


def candidate_inputs():
    values = support.candidate_inputs()
    folder = r.E / PIXEL_CHECK
    assert r.sha(folder / 'storage/result.json') == PIXEL_RESULT_SHA
    checked, inputs = r.result(PIXEL_CHECK)
    verification = checked['sleepingRootVerification']
    assert verification['passed'] and verification['complete']
    assert verification['detached']['changedPixels'] == verification['restored']['changedPixels'] == 0
    assert verification['zeroClipsWake']['status'] == 'passed'
    check_sleeping_stats(verification['cleanup'])
    assert verification['cleanup']['pendingRestore'] == 0 and verification['parked']['parkedUnits'] > 0
    assert inputs[CS_PATH] == CANDIDATE_SHA
    old_probe = r.read(folder / 'probe-build.json')
    assert inputs[PROBE_PATH] == old_probe['probeSHA256']
    assert r.sha(Path(old_probe['probePath'])) == old_probe['probeSHA256']
    old_source = Path(old_probe['frozenSourcePath'])
    assert tree_hashes(old_source) == old_probe['frozenSourceSHA256']
    helper_sha = r.read(support.OUT / 'source-provenance.json')['probeHelperSHA256']
    assert r.sha(old_source / HELPER) == helper_sha
    for name in ('storage/result.json', 'inputs.json', 'probe-build.json', 'candidate-build.json',
                 'loader-check.json', 'process-policy.json'):
        values[str(folder / name)] = r.sha(folder / name)
    values[str(old_source / HELPER)] = helper_sha
    values[str(support.OUT / 'whitelist-audit.json')] = r.sha(support.OUT / 'whitelist-audit.json')
    return values


def compile_frozen_probe(lease, baseline, scripts, compiler, candidate):
    assert not m.air_pids(), 'Other AIR present; untouched'
    memory = m.memory_status()
    assert memory['availableCommit'] >= 1024**3 and memory['availablePhysical'] >= 1.5 * 1024**3
    source = B.parent / 'src'
    captured = tree_hashes(source)
    folder = OUT / 'probe-source' / uuid.uuid4().hex
    frozen = folder / 'src'
    folder.mkdir(parents=True, exist_ok=False)
    shutil.copytree(source, frozen)
    assert captured == tree_hashes(source) == tree_hashes(frozen), 'Source changed while freezing'
    assert r.sha(frozen / HELPER) == r.read(support.OUT / 'source-provenance.json')['probeHelperSHA256']
    probe_source = (frozen / 'ContinuousSceneMotionProbe.as').read_text(encoding='utf-8-sig')
    for token in ('nativeInputMotion', 'SceneSleepingRootPresentation', 'row.sleepingRoots', 'sleepingRootCleanup'):
        assert token in probe_source, ('Frozen probe integration missing', token)
    r.save(folder / 'source-snapshot.json', dict(sharedSourcePath=str(source),
        sharedSourceSnapshotSHA256=captured, frozenSourcePath=str(frozen),
        frozenSourceSHA256=tree_hashes(frozen), capturedAt=datetime.now().astimezone().isoformat()))
    output, config = folder / 'ContinuousSceneProbe.swf', folder / 'ContinuousSceneProbe.xml'
    config.write_text('''<flex-config><target-player>32.0</target-player><compiler>
<external-library-path><path-element>{air}</path-element></external-library-path>
<source-path><path-element>{source}</path-element></source-path><debug>false</debug><optimize>true</optimize><theme/>
</compiler></flex-config>'''.format(air=escape(str(r.enemy.TOOLS / 'airsdk/frameworks/libs/air/airglobal.swc')),
                                  source=escape(str(frozen))), 'utf-8')
    command = [str(r.enemy.JAVA), '-Xmx512m', '-Dfile.encoding=UTF-8', '-jar',
        str(r.enemy.TOOLS / 'flexsdk/lib/mxmlc.jar'), '+flexlib=' + str(r.enemy.TOOLS / 'flexsdk/frameworks'),
        '-load-config=' + str(config), '-swf-version=32', '-static-link-runtime-shared-libraries=true',
        '-output=' + str(output), str(frozen / 'ContinuousSceneProbeDoc.as')]
    process = None
    lease.before_launch('Native input frozen probe compiler')
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        lease.child(process.pid)
        log, _ = process.communicate()
        (folder / 'compile.log').write_bytes(log)
        if process.returncode:
            raise RuntimeError('Probe compile failed; inspect ' + str(folder / 'compile.log'))
    finally:
        if process is not None:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=15)
            lease.child_stopped()
    assert captured == tree_hashes(frozen), 'Frozen source changed during compile'
    assert scripts == runner_inputs() and compiler == support.compiler_inputs()
    assert candidate == candidate_inputs() and baseline == r.baseline()
    receipt = dict(version='native-input-combat-probe-1', capturedAt=datetime.now().astimezone().isoformat(),
        sharedSourcePath=str(source), sharedSourceSnapshotSHA256=captured, frozenSourcePath=str(frozen),
        frozenSourceSHA256=tree_hashes(frozen), probePath=str(output), probeSHA256=r.sha(output),
        configPath=str(config), configSHA256=r.sha(config), command=command,
        compilerLogSHA256=r.sha(folder / 'compile.log'), runnerInputs=scripts,
        compilerInputs=compiler, candidateInputs=candidate, productionSHA256=baseline,
        diagnosticOnly=True, deployed=False, performanceAcceptance=False)
    path = folder / 'probe-build.json'
    r.save(path, receipt)
    print(json.dumps({'frozenProbeBuild': str(path), 'reuse': '--probe-build ' + str(path)}), flush=True)
    return path


def verify_probe(path, baseline, scripts, compiler, candidate):
    probe = r.read(path)
    assert probe['version'] == 'native-input-combat-probe-1'
    assert not probe['deployed'] and not probe['performanceAcceptance'] and probe['diagnosticOnly']
    assert probe['sharedSourceSnapshotSHA256'] == probe['frozenSourceSHA256']
    assert tree_hashes(Path(probe['frozenSourcePath'])) == probe['frozenSourceSHA256']
    assert r.sha(Path(probe['frozenSourcePath']) / HELPER) == r.read(support.OUT / 'source-provenance.json')['probeHelperSHA256']
    assert r.sha(Path(probe['probePath'])) == probe['probeSHA256']
    assert r.sha(Path(probe['configPath'])) == probe['configSHA256']
    assert r.sha(path.parent / 'compile.log') == probe['compilerLogSHA256']
    assert probe['runnerInputs'] == scripts and probe['compilerInputs'] == compiler
    assert probe['candidateInputs'] == candidate and probe['productionSHA256'] == baseline
    return probe


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def check_motion_state(state, route):
    for key in ('X', 'Y', 'dx', 'dy', 'floorY', 'collisionFloorY'):
        assert finite(state[key]), (key, state)
    bounds = route['safeCenterRange']
    assert bounds['left'] - .01 <= state['X'] <= bounds['right'] + .01
    assert abs(state['floorY'] - route['floorY']) < .01
    assert isinstance(state['stay'], bool) and isinstance(state['floorContact'], bool)
    assert state['control'] is True
    if state['floorContact']:
        assert state['stay'] and abs(state['Y'] - route['floorY']) < .01 and abs(state['dy']) < .01
        assert abs(state['collisionFloorY'] - route['floorY']) < .01
    pose = state['bodypose']
    assert all(key in pose for key in ('osnLabel', 'frame', 'label', 'playing'))
    assert finite(pose['frame']) and pose['frame'] > 0 and isinstance(pose['playing'], bool)
    keys = state['keys']
    assert all(isinstance(keys[key], bool) for key in ('left', 'right', 'attack', 'run', 'jump'))
    assert not (keys['left'] and keys['right']) and not keys['run'] and not keys['jump']


def check_motion_bucket(bucket, route, expected=None, check_windows=True):
    count = bucket['samples']
    assert isinstance(count, int) and count > 0
    if expected is not None:
        assert count == expected
    counters = ('groundedSamples', 'airborneSamples', 'movingSamples', 'floorContactSamples')
    assert all(isinstance(bucket[k], int) and 0 <= bucket[k] <= count for k in counters)
    assert bucket['groundedSamples'] + bucket['airborneSamples'] == count
    assert bucket['floorContactSamples'] <= bucket['groundedSamples']
    assert all(finite(bucket[k]) for k in ('minX', 'maxX', 'minY', 'maxY'))
    bounds = route['safeCenterRange']
    assert bounds['left'] - .01 <= bucket['minX'] <= bucket['maxX'] <= bounds['right'] + .01
    assert bucket['minY'] <= bucket['maxY']
    for name in ('first', 'last'):
        check_motion_state(bucket[name], route)
    if check_windows:
        windows = bucket['windows']
        assert len(windows) == (count + 29) // 30
        for index, window in enumerate(windows):
            assert window['startSample'] == index * 30
            check_motion_bucket(window, route, min(30, count - index * 30), False)
        assert sum(w['samples'] for w in windows) == count
        assert all(sum(w[k] for w in windows) == bucket[k] for k in counters)


def check_native_driver(result, row, index):
    driver, motion = result['driver'], result['nativeInputMotion']
    assert driver['nativeInputMotion'] is True and driver['stableMotion'] is True
    assert driver['forcedPositionCalls'] == 0
    assert driver['perFrameMethod'] == 'Ctr.keyLeft/keyRight; native acceleration, vertical physics and collision'
    assert motion['version'] == 'native-input-motion-3' and motion['enabled'] and motion['diagnosticFixture']
    assert motion['spawn']['calls'] == 1
    route = motion['route']
    assert route['terrainVerified'] and route['enemiesMoved'] is True and route['nativeSightLines'] == 30
    assert route['margin'] == 80 and finite(route['bodyHalfWidth']) and route['bodyHalfWidth'] > 0
    assert route['endX'] - route['playerX'] == 200
    assert route['turnMarginRange'] == dict(left=route['playerX'] - 80, right=route['endX'] + 80)
    assert route['safeCenterRange'] == dict(left=route['verifiedBounds']['left'] + route['bodyHalfWidth'],
        right=route['verifiedBounds']['right'] - route['bodyHalfWidth'])
    assert route['actualEnemyGap'] > 120 + route['bodyHalfWidth']
    assert route['enemyBodyMargin'] == 40
    assert len(route['originalEnemies']) == len(route['enemies']) == 6
    assert route['enemies'] == result['combatRoute']['enemies']
    enemies = route['enemies']
    assert all(enemies[i]['x'] < enemies[i + 1]['x'] for i in range(5))
    assert all(e['x'] < route['playerX'] for e in enemies[:3])
    assert all(e['x'] > route['endX'] for e in enemies[3:])
    assert route['leftEnemyGap'] == route['playerX'] - enemies[2]['x']
    assert route['rightEnemyGap'] == enemies[3]['x'] - route['endX']
    assert route['actualEnemyGap'] == min(route['leftEnemyGap'], route['rightEnemyGap'])
    assert route['cells'] > 0 and isinstance(route['hash'], int)
    assert result['path']['speed'] is None and result['path']['startX'] == route['playerX']
    assert result['path']['endX'] == route['endX'] and result['combatRoute']['x'] == route['playerX']
    warm = motion['warmup']
    assert warm['ready'] and warm['roundTrips'] >= 1 and warm['groundContactRun'] >= 10
    check_motion_bucket(warm, route)
    assert warm['movingSamples'] > 0 and warm['floorContactSamples'] >= 10
    check_motion_state(motion['timingStart'], route)
    assert motion['timingStart']['floorContact'] is True
    bucket = row['nativeInputMotion']
    check_motion_bucket(bucket, route, len(row['frames']))
    moving = bool(result['config'].get('drawControl')) or index % 4 in (1, 2)
    assert bucket['movementRequested'] is moving
    check_motion_state(bucket['inputAtStart'], route)
    if moving:
        assert bucket['movingSamples'] > 0 and bucket['maxX'] - bucket['minX'] > 1
    return bucket


def combat_windows(row, count):
    observations = row['combatWindows']
    assert len(observations) == count // 30 * 2
    windows = []
    for wi in range(count // 30):
        pair = sorted((x for x in observations if x['frame'] // 30 == wi), key=lambda x: x['frame'])
        assert len(pair) == 2 and [x['frame'] for x in pair] == [wi * 30, wi * 30 + 29]
        for observation in pair:
            six_armed(observation['encounter'])
        player = pair[1]['playerShots'] - pair[0]['playerShots']
        enemy = pair[1]['encounter']['actualShotFrames'] - pair[0]['encounter']['actualShotFrames']
        assert player > 0 and enemy >= 0
        windows.append(dict(window=wi, playerShots=player, enemyShots=enemy, population=pair))
    return windows


def summarize(result, args):
    cfg, world, route = result['config'], result['world'], result['combatRoute']
    control = args.draw_control == 'sleepingroots'
    assert cfg['benchmark'] == args.mode and cfg['drawControl'] == args.draw_control
    assert cfg['nativeInputMotion'] is True and bool(cfg['nativeSprint']) == args.native_sprint
    assert bool(cfg['sleepingRootShort']) == args.short_interleave
    assert not cfg['sleepingRootCheck']
    assert cfg['noLighting'] and cfg['noWall'] and not cfg['vision']
    assert cfg['fixedEnemies'] and not cfg['localEnemies'] and cfg['playerFire'] and cfg['stableMotion']
    assert world['layoutSeed'] == 20261019
    assert (world['width'], world['height']) == ((48, 25) if args.mode == 'normal' else (240, 125))
    assert result['viewport']['stageWidth'] == result['viewport']['cameraWidth'] == 2032
    assert result['viewport']['stageHeight'] == result['viewport']['cameraHeight'] == 1084
    assert result['viewport']['zoom'] == 1
    if args.mode == 'normal':
        room = result['nativeRoom']
        assert (room['x'], room['y'], room['z']) == (2, 4, 0) and room['settleFrames'] >= 20
        assert (cfg['nativeRoomX'], cfg['nativeRoomY'], cfg['nativeRouteX'], cfg['nativeRouteY']) == (2, 4, 480, 119)
    else:
        assert cfg['nativeRoomX'] == cfg['nativeRoomY'] == -1
    ox, oy = (0, 0) if args.mode == 'normal' else (3840, 4000)
    assert route['path'] == 200
    assert route['checkedNativeSightLines'] == 30 and route['enemySpacing'] == 80
    assert len(route['enemies']) == 6
    assert route['evidence']['selected'] and route['evidence']['playerPath'] == 200
    corridor = result['selectedCombatCorridorTiles']
    assert corridor['cells'] > 0 and isinstance(corridor['hash'], int)
    warmup = result['playerFireWarmup']
    assert warmup['frames'] >= 100 and warmup['quietWarmFrames'] >= 100 and warmup['shotFrames'] >= 5
    assert warmup['encounter']['actualShotFrames'] > 0
    six_armed(warmup['encounter'])
    segments, frames = (20, 60) if args.short_interleave else (4, 300)
    assert len(result['samples']) == segments
    summary = dict(name=args.name, mode=args.mode, candidate=args.candidate, control=args.draw_control,
        nativeSprint=args.native_sprint, shortInterleave=args.short_interleave,
        diagnosticOnly=True, performanceEligible=False, performanceAcceptance=False, deployed=False,
        checks=len(result['assertions']), driver=result['driver'], world=world,
        nativeInputMotion=result['nativeInputMotion'],
        nativeRoom=result.get('nativeRoom'), selectedCombatRoom=result.get('selectedCombatRoom'),
        selectedCombatRoomTiles=result['selectedCombatRoomTiles'], selectedCombatCorridorTiles=corridor,
        normalizedLocalRoute=dict(startX=route['x'] - ox, endX=route['x'] + route['path'] - ox,
            y=route['y'] - oy, enemies=[dict(x=p['x'] - ox, y=p['y'] - oy) for p in route['enemies']]),
        viewport=result['viewport'], combatRoute=route, path=result['path'],
        playerFire=result['playerFire'], playerFireWarmup=warmup, encounterInitial=result['encounter'],
        limitations=LIMITATIONS, primaryTiming='All frames including switching overhead', samples=[])
    previous = {key: 0 for key in support.COUNTERS}
    arms = {'A': [], 'B': []}
    for index, row in enumerate(result['samples']):
        enabled = control and index % 4 in (1, 2)
        expected_name = ('sleeping-root-' + ('b' if enabled else 'a') + '-' + str(index)) if args.short_interleave else (CONTROL_CASES if control else BASE_CASES)[index % 4]
        assert row['name'] == expected_name
        assert len(row['frames']) == len(row['nativeBand']) == len(row['warm']) == frames
        assert row['empty'] == row['misses'] == 0
        assert len(row['totalScript']) in ((frames - 1, frames) if index == 0 else (frames,))
        assert row['playerShotFrames'] > 0 and row['enemyShotFrames'] >= 0
        if not args.short_interleave:
            assert row['enemyShotFrames'] > 0
        six_armed(row['encounter'])
        pose = check_native_driver(result, row, index)
        windows = combat_windows(row, frames)
        item = dict(index=index, name=row['name'], frames=metrics(row['frames']),
            totalScript=metrics(row['totalScript']), nativeBand=metrics(row['nativeBand']),
            playerShots=row['playerShotFrames'], enemyShots=row['enemyShotFrames'],
            quietEnemyWindows=sum(w['enemyShots'] == 0 for w in windows), combatWindows=windows,
            nativeInput=pose, camera=row['camera'], activity=row['activity'],
            activityEnd=row.get('activityEnd'), activityCensus=row.get('activityCensus'),
            scene=dict(residentStart=row.get('residentStart'), residentEnd=row.get('residentEnd'),
                slices=row.get('slices'), forced=row.get('forced'), warmed=sum(row['warm'])),
            encounterEnd=row['encounter'])
        if control:
            stats = row['sleepingRoots']
            check_sleeping_stats(stats)
            assert stats['enabled'] == enabled
            assert (stats['pendingRestore'] > 0) == enabled
            delta = {key: stats[key] - previous[key] for key in support.COUNTERS}
            assert all(value >= 0 for value in delta.values())
            if enabled:
                assert stats['parkedUnits'] > 0 and delta['callbacks'] > 0
            previous = {key: stats[key] for key in support.COUNTERS}
            arms['B' if enabled else 'A'].extend(row['frames'])
            item.update(arm='B' if enabled else 'A', enabled=enabled, sleepingRoots=stats,
                counterDelta=delta, callbackCostPerFrame=delta['callbackMs'] / frames,
                secondaryExcludingTwoBoundaryFrames=metrics(row['frames'][2:]),
                boundaryFramesMs=row['frames'][:2])
        summary['samples'].append(item)
    if control:
        cleanup = result['sleepingRootCleanup']
        check_sleeping_stats(cleanup)
        assert cleanup['changed'] > 0 and not cleanup['enabled'] and cleanup['pendingRestore'] == 0
        assert all(cleanup[key] >= previous[key] for key in support.COUNTERS)
        assert 'sleepingRootVerification' not in result
        summary['cleanup'] = cleanup
        summary['armsIncludingSwitchOverhead'] = {arm: metrics(values) for arm, values in arms.items()}
        summary['observedMedianDifferenceMs'] = statistics.median(arms['A']) - statistics.median(arms['B'])
        assert all(sum(s['nativeInput']['floorContactSamples'] for s in summary['samples'] if s['arm'] == arm) > 0 for arm in ('A', 'B'))
        if args.short_interleave:
            engaged = sum(s['playerShots'] > 0 and s['enemyShots'] > 0 for s in summary['samples'])
            blocks = []
            for start in range(0, 20, 4):
                rows = summary['samples'][start:start + 4]
                for arm in ('A', 'B'):
                    assert sum(s['enemyShots'] for s in rows if s['arm'] == arm) > 0
                raw = result['samples'][start:start + 4]
                values = {arm: [dt for j, s in enumerate(raw) if ('B' if j in (1, 2) else 'A') == arm for dt in s['frames']] for arm in ('A', 'B')}
                blocks.append(dict(block=start // 4, arms={arm: metrics(v) for arm, v in values.items()},
                    medianDifferenceMs=statistics.median(values['A']) - statistics.median(values['B']),
                    bothFiringWindows=sum(s['enemyShots'] > 0 for s in rows)))
            assert engaged >= 16, ('Too few genuine two-way combat windows', engaged)
            summary['bothFiringWindows'] = engaged
            summary['blocksIncludingSwitchOverhead'] = blocks
    return summary


def main():
    if not __debug__:
        raise RuntimeError('Assertions are required; do not use -O')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    parser.add_argument('--mode', choices=['normal', 'scene'], default='scene')
    parser.add_argument('--candidate', choices=['formal', 'sleepingroots'], default='formal')
    parser.add_argument('--draw-control', choices=['sleepingroots'])
    parser.add_argument('--sleeping-roots', action='store_true', help='Select r2 candidate and ABBA control')
    parser.add_argument('--native-sprint', action='store_true')
    parser.add_argument('--short-interleave', action='store_true', help='60-frame ABBA repeated five times; all switch costs retained')
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--compile-probe', action='store_true')
    source.add_argument('--probe-build', type=Path)
    parser.add_argument('--registry-wait', type=int, default=600)
    args = parser.parse_args()
    if args.sleeping_roots:
        args.candidate, args.draw_control = 'sleepingroots', 'sleepingroots'
    assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
    assert not (r.E / args.name).exists(), 'Use a fresh evidence name'
    assert not args.draw_control or (args.mode == 'scene' and args.candidate == 'sleepingroots')
    assert not args.short_interleave or (args.draw_control and SHORT_CONTRACT_READY), 'Short-window contract is not yet frozen'
    assert NATIVE_CONTRACT_READY, 'Wait for reviewed native input/ground-pose fixture schema before running'
    assert not args.native_sprint, 'First native-input fixture accepts ordinary walking only'
    with m.Registration(owner='ContinuousScene / native input combat / 01a13816',
            purpose=args.name, run_dir=m.RUNTIME, evidence=r.E / args.name, wait=args.registry_wait) as lease:
        assert not m.air_pids(), 'Other AIR present; untouched'
        baseline, scripts = r.baseline(), runner_inputs()
        compiler, candidate = support.compiler_inputs(), candidate_inputs()
        assert baseline['pfe.swf'] == FORMAL_HOST and baseline[CS_PATH] == FORMAL_CS
        build_path = compile_frozen_probe(lease, baseline, scripts, compiler, candidate) if args.compile_probe else args.probe_build.resolve()
        probe = verify_probe(build_path, baseline, scripts, compiler, candidate)
        m.prepare()
        actual_cs = FORMAL_CS
        if args.candidate == 'sleepingroots':
            shutil.copy2(support.OUT / 'ContinuousSceneMod.swf', m.RUNTIME / CS_PATH)
            actual_cs = CANDIDATE_SHA
        shutil.copy2(probe['probePath'], m.RUNTIME / PROBE_PATH)
        assert r.sha(m.RUNTIME / 'pfe.swf') == FORMAL_HOST and r.sha(m.RUNTIME / CS_PATH) == actual_cs
        assert r.sha(m.RUNTIME / PROBE_PATH) == probe['probeSHA256']
        assert baseline == r.baseline() and scripts == runner_inputs() and compiler == support.compiler_inputs()
        assert candidate == candidate_inputs()
        verify_probe(build_path, baseline, scripts, compiler, candidate)
        options = ['--name', args.name, '--high-qos', '--land', 'random_mane', '--encounter', '--fixed-enemies',
            '--benchmark', args.mode, '--speed', '4', '--short', '--stable-motion', '--native-input-motion', '--player-fire',
            '--combat-route', '--combat-route-length', '200', '--window-width', '2048', '--window-height', '1123',
            '--no-lighting', '--no-wall']
        if args.mode == 'normal':
            options += ['--native-room-x', '2', '--native-room-y', '4', '--native-route-x', '480', '--native-route-y', '119']
        else:
            options += ['--expect-no-signs']
        if args.draw_control:
            options += ['--draw-control', args.draw_control]
        if args.native_sprint:
            options += ['--native-sprint']
        if args.short_interleave:
            options += ['--sleeping-root-short']
        m.run_owned(m.parse_args(options), lease)
        result, inputs = r.result(args.name)
        assert baseline == r.baseline(), 'Production drift'
        assert scripts == runner_inputs() and compiler == support.compiler_inputs() and candidate == candidate_inputs()
        verify_probe(build_path, baseline, scripts, compiler, candidate)
        for path, digest in baseline.items():
            if path not in ('application.xml', 'mods/loader-manifest.txt', CS_PATH):
                assert inputs[path] == digest, path
        assert inputs[CS_PATH] == actual_cs and inputs[PROBE_PATH] == probe['probeSHA256']
        policy = r.read(r.E / args.name / 'process-policy.json')
        assert not policy.get('runFailure') and not policy.get('memoryAbort') and not policy.get('otherAirProcessIds')
        if args.draw_control:
            assert policy['performanceEligible'] is False
        r.save(r.E / args.name / 'probe-build.json', probe)
        r.save(r.E / args.name / 'runner-inputs.json', dict(options=options, baseline=baseline,
            actualContinuousSceneSHA256=actual_cs, probeBuildPath=str(build_path), runnerInputs=scripts,
            compilerInputs=compiler, candidateInputs=candidate))
        summary = summarize(result, args)
        summary.update(probeBuildPath=str(build_path), hostSHA256=FORMAL_HOST,
            baselineContinuousSceneSHA256=FORMAL_CS, actualContinuousSceneSHA256=actual_cs)
        r.save(r.E / args.name / 'summary.json', summary)
        print(json.dumps(dict(name=args.name, mode=args.mode, candidate=args.candidate, control=args.draw_control,
            probeBuildPath=str(build_path), arms=summary.get('armsIncludingSwitchOverhead'),
            samples=[{key: row[key] for key in ('name', 'frames', 'totalScript', 'playerShots', 'enemyShots', 'nativeInput')}
                for row in summary['samples']], performanceEligible=False, performanceAcceptance=False, deployed=False)), flush=True)
        lease.outcome = 'passed'
        lease.note = 'Native-controller combat diagnostic captured; no production acceptance or deployment'


if __name__ == '__main__':
    main()
