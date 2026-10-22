"""Registered native-room / continuous-map experience baseline on formal bytes.

The first run uses --compile-probe. Reuse its printed --probe-build path for a
second --mode scene run, with a fresh evidence name. Only the unique frozen
source copy is compiled and checked after capture; live src may then evolve.
Four 300-frame segments retain native weapons/AI and real fire on both sides.
Camera bounds and natural populations differ: this is not identical-workload
attribution, a loading benchmark, a deployment, or performance acceptance.
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
OUT = B / 'generated/native-combat-baseline-20261022'
FORMAL_HOST = 'BEFCF0509E11FAC9FEF7AFB834708B8B93752A14AE3D5CD72B42AA6D42F9B82A'
FORMAL_CS = '7F1F2961C6E299D949423591F3C65C610C2EAEFA7FC72E8A583A402770D6B51F'
CS_PATH = 'mods/ContinuousScene/release/ContinuousSceneMod.swf'
PROBE_PATH = 'mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf'
CASES = ('enemy-idle', 'enemy-fast-forward', 'enemy-fast-back', 'enemy-idle-end')
LIMITATIONS = [
    'Normal camera centers the 1920 x 1000 room in the 2032 x 1084 viewport; '
    'the continuous camera follows the player and also shows neighboring rooms.',
    'The same layout seed and selected-room tile hash do not fix entity, loot, '
    'combat RNG, destruction history, or warmup duration. Natural populations remain.',
    'Room-edge destruction and travel rules differ. Initial route checks and '
    'native room-identity guards do not imply identical later gameplay states.',
    'Entry time includes one explicit native gotoXY and 20 settle frames; '
    'do not use entryMs as a loading benchmark.',
    'The 30-frame population boundary deltas cover frames 1..29 of each window; '
    'whole-segment counters retain boundary shots and natural reload gaps.',
    'Frame minus script time is an unattributed remainder, not renderer CPU time.'
]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


r = load('native_combat_baseline_helpers', B / 'enemy-release.py')
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
    lease.before_launch('Native combat baseline frozen probe compiler')
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
    receipt = dict(version='native-combat-baseline-probe-1',
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
    assert probe['version'] == 'native-combat-baseline-probe-1'
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


def summarize(result, name, mode):
    cfg, world, route = result['config'], result['world'], result['combatRoute']
    assert cfg['benchmark'] == mode and not cfg['drawControl']
    assert cfg['noLighting'] and cfg['noWall'] and not cfg['vision']
    assert cfg['fixedEnemies'] and not cfg['localEnemies'] and cfg['stableMotion'] and cfg['playerFire']
    assert result['driver']['perFrameMethod'] == 'Unit.setPos (position/bounds/target only)'
    assert world['layoutSeed'] == 20261019
    assert world['width'] == (48 if mode == 'normal' else 240)
    assert world['height'] == (25 if mode == 'normal' else 125)
    assert result['viewport']['stageWidth'] == result['viewport']['cameraWidth'] == 2032
    assert result['viewport']['stageHeight'] == result['viewport']['cameraHeight'] == 1084
    assert result['viewport']['zoom'] == 1
    if mode == 'normal':
        room = result['nativeRoom']
        assert (room['x'], room['y'], room['z']) == (2, 4, 0) and room['settleFrames'] >= 20
        assert (cfg['nativeRoomX'], cfg['nativeRoomY'], cfg['nativeRouteX'], cfg['nativeRouteY']) == (2, 4, 480, 119)
    else:
        assert cfg['nativeRoomX'] == cfg['nativeRoomY'] == -1
    ox, oy = (0, 0) if mode == 'normal' else (3840, 4000)
    assert (route['x'] - ox, route['y'] - oy, route['path']) == (480, 119, 200), 'Selected a different combat route'
    assert route['checkedNativeSightLines'] == 30 and route['enemySpacing'] == 80
    assert [(p['x'] - ox, p['y'] - oy) for p in route['enemies']] == [(1000 + i*80, 119) for i in range(6)]
    assert route['evidence']['selected'] and route['evidence']['playerPath'] == 200
    assert result['path'] == dict(startX=480+ox, endX=680+ox, y=119+oy, speed=4)
    tile_owner = world if 'selectedCombatRoomTiles' in world else result
    tile_hash = tile_owner['selectedCombatRoomTiles']
    assert isinstance(tile_hash, int) and not isinstance(tile_hash, bool) and 0 <= tile_hash <= 0xffffffff
    corridor = result['selectedCombatCorridorTiles']
    assert corridor['cells'] == 100
    assert isinstance(corridor['hash'], int) and not isinstance(corridor['hash'], bool) and 0 <= corridor['hash'] <= 0xffffffff
    warmup = result['playerFireWarmup']
    assert warmup['frames'] >= 100 and warmup['quietWarmFrames'] >= 100 and warmup['shotFrames'] >= 5
    assert warmup['encounter']['actualShotFrames'] > 0
    six_armed(warmup['encounter'])
    assert len(result['samples']) == 4
    summary = dict(name=name, mode=mode, purpose='same-terrain combat experience baseline',
        diagnosticOnly=True, performanceAcceptance=False, deployed=False,
        checks=len(result['assertions']), driver=result['driver'], world=world,
        nativeRoom=result.get('nativeRoom'), selectedCombatRoom=result.get('selectedCombatRoom', world.get('selectedCombatRoom')),
        selectedCombatRoomTiles=tile_hash, tileHashSource='world' if tile_owner is world else 'result',
        selectedCombatCorridorTiles=corridor,
        tileHashFields=['front', 'back', 'phis', 'diagon', 'zForm', 'door'],
        viewport=result['viewport'], combatRoute=route, path=result['path'],
        normalizedLocalRoute=dict(startX=480, endX=680, y=119, roomX=2, roomY=4),
        playerFire=result['playerFire'], playerFireWarmup=warmup, encounterInitial=result['encounter'],
        entryMsNotLoadingBenchmark=result.get('entryMs'), limitations=LIMITATIONS, samples=[])
    for ri, row in enumerate(result['samples']):
        assert row['name'] == CASES[ri]
        assert len(row['frames']) == 300 and row['empty'] == 0 and row['misses'] == 0
        assert len(row['nativeBand']) == len(row['warm']) == 300
        assert len(row['totalScript']) in ((299, 300) if ri == 0 else (300,))
        assert row['enemyShotFrames'] > 0 and row['playerShotFrames'] > 0
        six_armed(row['encounter'])
        assert len(row['combatWindows']) == 20
        windows = []
        for wi in range(10):
            pair = sorted((x for x in row['combatWindows'] if x['frame'] // 30 == wi), key=lambda x: x['frame'])
            assert len(pair) == 2 and [x['frame'] for x in pair] == [wi*30, wi*30+29]
            for sample in pair:
                six_armed(sample['encounter'])
            player = pair[1]['playerShots'] - pair[0]['playerShots']
            enemy = pair[1]['encounter']['actualShotFrames'] - pair[0]['encounter']['actualShotFrames']
            assert player > 0 and enemy >= 0
            windows.append(dict(window=wi, playerShots=player, enemyShots=enemy, population=pair))
        summary['samples'].append(dict(name=row['name'], frames=metrics(row['frames']),
            nativeBand=metrics(row['nativeBand']), totalScript=metrics(row['totalScript']),
            playerShots=row['playerShotFrames'], enemyShots=row['enemyShotFrames'],
            warmed=sum(row['warm']), camera=row['camera'], activity=row['activity'],
            encounterEnd=row['encounter'], quietEnemyWindows=sum(w['enemyShots'] == 0 for w in windows),
            combatWindows=windows))
    return summary


def main():
    if not __debug__:
        raise RuntimeError('This baseline runner requires assertions; do not use -O')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    parser.add_argument('--mode', choices=['normal', 'scene'], default='normal')
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--compile-probe', action='store_true')
    source.add_argument('--probe-build', type=Path)
    parser.add_argument('--registry-wait', type=int, default=600)
    args = parser.parse_args()
    assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name), 'Evidence name'
    assert not (r.E / args.name).exists(), 'Use a fresh evidence name'
    with m.Registration(owner='ContinuousScene / native combat experience baseline / 01a13816',
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
            '--benchmark', args.mode, '--speed', '4', '--short', '--stable-motion', '--player-fire',
            '--combat-route', '--combat-route-length', '200', '--window-width', '2048', '--window-height', '1123',
            '--no-lighting', '--no-wall']
        if args.mode == 'normal':
            options += ['--native-room-x', '2', '--native-room-y', '4', '--native-route-x', '480', '--native-route-y', '119']
        else:
            options += ['--expect-no-signs']
        m.run_owned(m.parse_args(options), lease)
        result, inputs = r.result(args.name)
        assert baseline == r.baseline(), 'Production drift'
        assert scripts == runner_inputs() and compiler == compiler_inputs(), 'Runner/compiler drift'
        verify_probe(build_path, baseline, scripts, compiler)
        for path, digest in baseline.items():
            if path not in ('application.xml', 'mods/loader-manifest.txt'):
                assert inputs[path] == digest, path
        assert inputs[PROBE_PATH] == probe['probeSHA256']
        policy = r.read(r.E / args.name / 'process-policy.json')
        assert policy['performanceEligible'] and not policy.get('runFailure') and not policy.get('memoryAbort')
        r.save(r.E / args.name / 'probe-build.json', probe)
        r.save(r.E / args.name / 'runner-inputs.json', dict(options=options, baseline=baseline,
            probeBuildPath=str(build_path), runnerInputs=scripts, compilerInputs=compiler))
        summary = summarize(result, args.name, args.mode)
        summary['probeBuildPath'] = str(build_path)
        summary['hostSHA256'], summary['continuousSceneSHA256'] = FORMAL_HOST, FORMAL_CS
        r.save(r.E / args.name / 'summary.json', summary)
        print(json.dumps(dict(name=args.name, mode=args.mode, selectedCombatRoomTiles=summary['selectedCombatRoomTiles'],
            selectedCombatCorridorTiles=summary['selectedCombatCorridorTiles'],
            probeBuildPath=str(build_path), samples=[{key: row[key] for key in ('name', 'frames', 'totalScript', 'playerShots', 'enemyShots')}
                for row in summary['samples']], performanceAcceptance=False, deployed=False)), flush=True)
        lease.outcome = 'passed'
        lease.note = 'Native/continuous experience baseline complete; camera/population limits retained, no acceptance or deployment'


if __name__ == '__main__':
    main()
