"""Registered empty-native-terrain rendering attribution on formal BEFC bytes.

Compile a unique frozen source copy; subsequent verification checks that copy,
not live src. Both ABBA arms scan alpha; only B hides completely empty buffers.
Four 300-frame real-fire segments retain native AI and a 200 px walking route.
This is a diagnostic, not pixel validation, performance acceptance or deployment.
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
OUT = B / 'generated/empty-terrain-20261022'
FORMAL_HOST = 'BEFCF0509E11FAC9FEF7AFB834708B8B93752A14AE3D5CD72B42AA6D42F9B82A'
FORMAL_CS = '7F1F2961C6E299D949423591F3C65C610C2EAEFA7FC72E8A583A402770D6B51F'
CS_PATH = 'mods/ContinuousScene/release/ContinuousSceneMod.swf'
PROBE_PATH = 'mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf'
CASES = ('draw-baseline-a', 'draw-control-b', 'draw-control-b-repeat', 'draw-baseline-a-repeat')
COUNTERS = ('updates', 'enabledUpdates', 'beginCalls', 'contextChanges', 'satsBypasses',
    'surfaceObservations', 'visibleLayerObservations', 'transparentLayerObservations',
    'hiddenWrites', 'restoredWrites', 'alreadyRestored', 'samples', 'cacheHits',
    'surfaceRevisionChanges', 'dataIdentityChanges', 'scanCost', 'updateCost',
    'updatePendingRestores', 'errors')
LIMITATIONS = [
    'Only fully alpha-empty native 400x400 buffers are hidden; occupied gutters prevent hiding.',
    'Both arms enumerate and scan. Cached alpha bounds rely on native surface revisions.',
    'The first frame of every display-control segment is excluded from summarized timing.',
    'Cumulative probe counters are differenced by segment. First-segment totals also include '
    'any one-time helper application before its first measured frame; updateCalls is explicit.',
    'Native enemy reload gaps and evolving combat/destruction populations remain; '
    'ABBA results do not alone establish a causal production improvement.',
    'No pixel, scale/shake, SATS or lifecycle acceptance is performed by this timing runner.',
    'Frame minus script time is an unattributed remainder, not renderer CPU time.'
]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


r = load('empty_terrain_runner_helpers', B / 'enemy-release.py')
m = r.motion


def tree_hashes(folder):
    return {p.relative_to(folder).as_posix(): r.sha(p)
            for p in sorted(folder.rglob('*')) if p.is_file()}


def runner_inputs():
    paths = (Path(__file__), B / 'enemy-release.py', B / 'enemy-speed.py',
             B / 'motion-test.py', B / 'profile-vision.py',
             r.ROOT / 'mods/ModLoader/tools/test_registry.py',
             r.ROOT / 'mods/ModLoader/tools/air_test_process.py')
    return {str(p): r.sha(p) for p in paths}


def compiler_inputs():
    paths = (r.enemy.JAVA, r.enemy.TOOLS / 'flexsdk/lib/mxmlc.jar',
             r.enemy.TOOLS / 'airsdk/frameworks/libs/air/airglobal.swc')
    return {str(p): r.sha(p) for p in paths}


def compile_frozen_probe(lease, baseline, scripts, compiler):
    assert not m.air_pids(), 'Other AIR present; untouched'
    memory = m.memory_status()
    assert memory['availableCommit'] >= 1024 * 1024**2, ('Insufficient commit', memory)
    assert memory['availablePhysical'] >= 1.5 * 1024**3, ('Insufficient physical memory', memory)
    source = B.parent / 'src'
    captured = tree_hashes(source)
    folder = OUT / 'probe-source' / uuid.uuid4().hex
    frozen = folder / 'src'
    folder.mkdir(parents=True, exist_ok=False)
    shutil.copytree(source, frozen)
    assert captured == tree_hashes(source) == tree_hashes(frozen), 'Source changed while freezing'
    r.save(folder / 'source-snapshot.json', dict(sharedSourcePath=str(source),
        sharedSourceSnapshotSHA256=captured, frozenSourcePath=str(frozen),
        frozenSourceSHA256=tree_hashes(frozen), capturedAt=datetime.now().astimezone().isoformat()))
    assert (frozen / 'tests/SceneEmptyTerrainProbe.as').is_file(), 'Empty terrain helper missing'
    probe_source = (frozen / 'ContinuousSceneMotionProbe.as').read_text(encoding='utf-8-sig')
    for token in ('SceneEmptyTerrainProbe', 'emptyterrain', 'emptyTerrainCleanup', 'row.emptyTerrain'):
        assert token in probe_source, ('Frozen probe integration missing', token)
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
    lease.before_launch('Empty terrain frozen probe compiler')
    try:
        process = subprocess.Popen(command)
        lease.child(process.pid)
        code = process.wait()
        if code:
            raise subprocess.CalledProcessError(code, command)
    finally:
        if process is not None:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=15)
            lease.child_stopped()
    assert captured == tree_hashes(frozen), 'Frozen source changed during compile'
    assert scripts == runner_inputs() and compiler == compiler_inputs(), 'Build helper drift'
    assert baseline == r.baseline(), 'Production drift during compile'
    receipt = dict(version='empty-terrain-probe-1',
        capturedAt=datetime.now().astimezone().isoformat(), sharedSourcePath=str(source),
        sharedSourceSnapshotSHA256=captured, frozenSourcePath=str(frozen),
        frozenSourceSHA256=tree_hashes(frozen), probePath=str(output), probeSHA256=r.sha(output),
        configPath=str(config), configSHA256=r.sha(config), command=command,
        runnerInputs=scripts, compilerInputs=compiler, productionSHA256=baseline,
        deployed=False, performanceAcceptance=False)
    path = folder / 'probe-build.json'
    r.save(path, receipt)
    print(json.dumps({'frozenProbeBuild': str(path), 'reuse': '--probe-build ' + str(path)}), flush=True)
    return path


def verify_probe(path, baseline, scripts, compiler):
    probe = r.read(path)
    assert probe['version'] == 'empty-terrain-probe-1'
    assert not probe['deployed'] and not probe['performanceAcceptance']
    assert probe['sharedSourceSnapshotSHA256'] == probe['frozenSourceSHA256']
    assert tree_hashes(Path(probe['frozenSourcePath'])) == probe['frozenSourceSHA256']
    assert r.sha(Path(probe['probePath'])) == probe['probeSHA256']
    assert r.sha(Path(probe['configPath'])) == probe['configSHA256']
    assert probe['runnerInputs'] == scripts and probe['compilerInputs'] == compiler
    assert probe['productionSHA256'] == baseline, 'Compare modes with the same production inputs'
    return probe


def six_armed(encounter):
    assert encounter['alive'] == 6 and encounter['armed'] == 6
    assert len(encounter['actors']) == 6
    assert all(a['hp'] > 0 and a['weapon'] and a['weapon']['hp'] > 0 for a in encounter['actors'])


def metrics(values):
    assert values and all(isinstance(x, (int, float)) and math.isfinite(x) and x >= 0 for x in values)
    return dict(count=len(values), median=statistics.median(values), mean=statistics.mean(values),
        p95=sorted(values)[math.ceil(len(values) * .95) - 1], maximum=max(values),
        over100=sum(x > 100 for x in values))


def check_probe_stats(stats):
    assert stats['version'] == 'empty-native-terrain-diagnostic-1'
    assert stats['diagnosticOnly'] is True and stats['performanceAcceptance'] is False
    assert stats['valid'] is True and stats['errors'] == 0 and not stats['errorDetails']
    assert stats['updatePendingRestores'] == 0, 'Pre-native beginFrame hook was missed'
    for key in COUNTERS + ('pendingRestore', 'scanMax'):
        value = stats[key]
        assert isinstance(value, (int, float)) and not isinstance(value, bool), (key, value)
        assert math.isfinite(value) and value >= 0 and value == int(value), (key, value)
    assert stats['hiddenWrites'] == stats['restoredWrites'] + stats['alreadyRestored'] + stats['pendingRestore']
    assert stats['enabledUpdates'] <= stats['updates']
    assert stats['scanMax'] <= stats['scanCost'] <= stats['updateCost']
    assert stats['transparentLayerObservations'] <= stats['visibleLayerObservations']
    assert stats['hiddenWrites'] <= stats['transparentLayerObservations']


def summarize(result, name):
    cfg, route = result['config'], result['combatRoute']
    assert cfg['benchmark'] == 'scene' and cfg['drawControl'] == 'emptyterrain'
    assert cfg['noLighting'] and cfg['noWall'] and not cfg['vision']
    assert cfg['fixedEnemies'] and not cfg['localEnemies'] and cfg['stableMotion'] and cfg['playerFire']
    assert result['driver']['stableMotion']
    assert result['driver']['perFrameMethod'] == 'Unit.setPos (position/bounds/target only)'
    assert result['playerFire']['enabled'] and result['playerFire']['shotFrames'] > 0
    assert result['world']['layoutSeed'] == 20261019
    assert (result['world']['width'], result['world']['height']) == (240, 125)
    assert result['viewport']['stageWidth'] == result['viewport']['cameraWidth'] == 2032
    assert result['viewport']['stageHeight'] == result['viewport']['cameraHeight'] == 1084
    assert result['viewport']['zoom'] == 1
    assert route['path'] == route['evidence']['playerPath'] == 200
    assert route['evidence']['version'] == 'existing-flat-combat-route-1' and route['evidence']['selected']
    assert route['checkedNativeSightLines'] == 30 and len(route['enemies']) == 6
    assert route['enemySpacing'] == 80
    assert result['path']['speed'] == 4 and result['path']['endX'] - result['path']['startX'] == 200
    warmup = result['playerFireWarmup']
    assert warmup['frames'] >= 100 and warmup['quietWarmFrames'] >= 100 and warmup['shotFrames'] >= 5
    assert warmup['encounter']['actualShotFrames'] > 0
    six_armed(warmup['encounter'])
    assert len(result['samples']) == 4
    summary = dict(name=name, mode='combat', control='emptyterrain', diagnosticOnly=True,
        performanceEligible=False, performanceAcceptance=False, deployed=False,
        checks=len(result['assertions']), driver=result['driver'], world=result['world'],
        viewport=result['viewport'], combatRoute=route, path=result['path'],
        playerFire=result['playerFire'], playerFireWarmup=warmup, encounterInitial=result['encounter'],
        limitations=LIMITATIONS, samples=[])
    previous = {key: 0 for key in COUNTERS}
    arm_frames = {'A': [], 'B': []}
    for ri, row in enumerate(result['samples']):
        enabled = ri in (1, 2)
        assert row['name'] == CASES[ri]
        assert len(row['frames']) == len(row['nativeBand']) == len(row['warm']) == 300
        assert row['empty'] == row['misses'] == 0
        assert len(row['totalScript']) in ((299, 300) if ri == 0 else (300,))
        assert row['enemyShotFrames'] > 0 and row['playerShotFrames'] > 0
        six_armed(row['encounter'])
        assert len(row['combatWindows']) == 20
        windows = []
        for wi in range(10):
            pair = sorted((x for x in row['combatWindows'] if x['frame'] // 30 == wi), key=lambda x: x['frame'])
            assert len(pair) == 2 and [x['frame'] for x in pair] == [wi*30, wi*30+29]
            for observation in pair:
                six_armed(observation['encounter'])
            player = pair[1]['playerShots'] - pair[0]['playerShots']
            enemy = pair[1]['encounter']['actualShotFrames'] - pair[0]['encounter']['actualShotFrames']
            assert player > 0 and enemy >= 0
            windows.append(dict(window=wi, playerShots=player, enemyShots=enemy, population=pair))
        stats = row['emptyTerrain']
        check_probe_stats(stats)
        delta = {key: stats[key] - previous[key] for key in COUNTERS}
        assert all(value >= 0 for value in delta.values()), 'Probe counters reset during ABBA'
        assert delta['updates'] >= 300 and delta['visibleLayerObservations'] > 0
        assert delta['surfaceObservations'] > 0 and delta['transparentLayerObservations'] > 0
        assert delta['satsBypasses'] == 0, 'SATS contaminated this combat timing segment'
        assert delta['enabledUpdates'] == (delta['updates'] if enabled else 0)
        assert bool(stats['last']['enabled']) == enabled
        assert stats['last']['surfaces'] > 0 and stats['last']['visibleLayers'] > 0
        assert stats['last']['foreignBindings'] == stats['last']['foreignParents'] == 0
        assert stats['last']['unsupportedDisplay'] == 0
        if enabled:
            assert delta['hiddenWrites'] > 0 and stats['last']['hidden'] > 0
        else:
            assert delta['hiddenWrites'] == 0 and stats['last']['hidden'] == 0
            assert stats['pendingRestore'] == 0
        assert delta['samples'] + delta['cacheHits'] == delta['visibleLayerObservations']
        if ri:
            assert delta['contextChanges'] == 0, 'Native scene or layer identity changed'
        previous = {key: stats[key] for key in COUNTERS}
        frames = row['frames'][1:]
        arm_frames['B' if enabled else 'A'].extend(frames)
        summary['samples'].append(dict(index=ri, name=row['name'], arm='B' if enabled else 'A',
            enabled=enabled, excludedSwitchFrames=1, measuredFrames=metrics(frames),
            allFrames=metrics(row['frames']), nativeBand=metrics(row['nativeBand'][1:]),
            totalScript=metrics(row['totalScript'][1:]),
            playerShots=row['playerShotFrames'], enemyShots=row['enemyShotFrames'],
            warmed=sum(row['warm']), camera=row['camera'], activity=row['activity'],
            encounterEnd=row['encounter'], quietEnemyWindows=sum(w['enemyShots'] == 0 for w in windows),
            combatWindows=windows, emptyTerrain=stats, counterDelta=delta,
            probeCostPerFrame=dict(scanMs=delta['scanCost']/300, updateMs=delta['updateCost']/300,
                hiddenWrites=delta['hiddenWrites']/300, scans=delta['samples']/300,
                updateCalls=delta['updates']),
            costPerUpdate=dict(scanMs=delta['scanCost']/delta['updates'],
                updateMs=delta['updateCost']/delta['updates'], hiddenWrites=delta['hiddenWrites']/delta['updates'])))
    cleanup = result['emptyTerrainCleanup']
    check_probe_stats(cleanup)
    assert cleanup['pendingRestore'] == 0 and not cleanup['last']['enabled']
    assert cleanup['last']['reason'] == 'cleared'
    assert all(cleanup[key] >= previous[key] for key in COUNTERS)
    summary['cleanup'] = cleanup
    summary['arms'] = {arm: metrics(values) for arm, values in arm_frames.items()}
    summary['observedMedianDifferenceMs'] = summary['arms']['A']['median'] - summary['arms']['B']['median']
    return summary


def main():
    if not __debug__:
        raise RuntimeError('This diagnostic runner requires assertions; do not use -O')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--compile-probe', action='store_true')
    source.add_argument('--probe-build', type=Path)
    parser.add_argument('--registry-wait', type=int, default=600)
    args = parser.parse_args()
    assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name), 'Evidence name'
    assert not (r.E / args.name).exists(), 'Use a fresh evidence name'
    with m.Registration(owner='ContinuousScene / empty native terrain attribution / 01a13816',
            purpose=args.name, run_dir=m.RUNTIME, evidence=r.E / args.name, wait=args.registry_wait) as lease:
        assert not m.air_pids(), 'Other AIR present; untouched'
        baseline, scripts, compiler = r.baseline(), runner_inputs(), compiler_inputs()
        assert baseline['pfe.swf'] == FORMAL_HOST and baseline[CS_PATH] == FORMAL_CS
        build_path = compile_frozen_probe(lease, baseline, scripts, compiler) if args.compile_probe else args.probe_build.resolve()
        probe = verify_probe(build_path, baseline, scripts, compiler)
        m.prepare()
        shutil.copy2(probe['probePath'], m.RUNTIME / PROBE_PATH)
        assert r.sha(m.RUNTIME / 'pfe.swf') == FORMAL_HOST and r.sha(m.RUNTIME / CS_PATH) == FORMAL_CS
        assert r.sha(m.RUNTIME / PROBE_PATH) == probe['probeSHA256']
        assert baseline == r.baseline() and scripts == runner_inputs() and compiler == compiler_inputs()
        verify_probe(build_path, baseline, scripts, compiler)
        options = ['--name', args.name, '--high-qos', '--land', 'random_mane', '--encounter', '--fixed-enemies',
            '--benchmark', 'scene', '--speed', '4', '--short', '--stable-motion', '--player-fire',
            '--combat-route', '--combat-route-length', '200', '--window-width', '2048', '--window-height', '1123',
            '--no-lighting', '--no-wall', '--expect-no-signs']
        run_args = m.parse_args(options)
        run_args.draw_control = 'emptyterrain'
        m.run_owned(run_args, lease)
        result, inputs = r.result(args.name)
        assert baseline == r.baseline(), 'Production drift'
        assert scripts == runner_inputs() and compiler == compiler_inputs(), 'Runner/compiler drift'
        verify_probe(build_path, baseline, scripts, compiler)
        for path, digest in baseline.items():
            if path not in ('application.xml', 'mods/loader-manifest.txt'):
                assert inputs[path] == digest, path
        assert inputs[PROBE_PATH] == probe['probeSHA256']
        policy = r.read(r.E / args.name / 'process-policy.json')
        assert policy['performanceEligible'] is False, 'motion-test diagnostic-only policy is not integrated'
        assert not policy.get('runFailure') and not policy.get('memoryAbort') and not policy.get('otherAirProcessIds')
        r.save(r.E / args.name / 'probe-build.json', probe)
        r.save(r.E / args.name / 'runner-inputs.json', dict(options=options, argumentOverrides=dict(draw_control='emptyterrain'),
            baseline=baseline, probeBuildPath=str(build_path), runnerInputs=scripts, compilerInputs=compiler))
        summary = summarize(result, args.name)
        summary['probeBuildPath'] = str(build_path)
        summary['hostSHA256'], summary['continuousSceneSHA256'] = FORMAL_HOST, FORMAL_CS
        r.save(r.E / args.name / 'summary.json', summary)
        print(json.dumps(dict(name=args.name, probeBuildPath=str(build_path),
            samples=[{key: row[key] for key in ('name', 'arm', 'measuredFrames', 'totalScript', 'playerShots', 'enemyShots', 'probeCostPerFrame')}
                for row in summary['samples']], arms=summary['arms'], cleanupPendingRestore=summary['cleanup']['pendingRestore'],
            performanceEligible=False, performanceAcceptance=False, deployed=False)), flush=True)
        lease.outcome = 'passed'
        lease.note = 'Empty native terrain real-fire ABBA captured; diagnostic only, no pixel acceptance or deployment'


if __name__ == '__main__':
    main()
