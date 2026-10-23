# Frozen parent vertical-motion source SHA256 67B9E449B9BC562D9883A7C9D4AAAAA4A736014C7D864158C813CEE86194CE4A
"""Isolated native-camera follow/hold ABBA; six 120-frame windows, no cache growth."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys
import uuid

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
BUILD = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base = load('vertical_native_support', BUILD / 'native-input-combat-run.py')
patch = load('vertical_source_patch', HERE / 'probe_patch.py')
r, m = base.r, base.m
HOST = '80CFD8CF3138EE59CBF6EDA0A1824A9EC960F413BD95E4B90D41DD0322B4FD3D'
CS = '7F1F2961C6E299D949423591F3C65C610C2EAEFA7FC72E8A583A402770D6B51F'
RC = 'DF0FA0E2CA952E77E5132E75D71E73558DC919C7B8CDEBA5DA05FC9E94DC01E7'
RC_PATH = 'mods/RConnect/release/RConnectMod.swf'
ORDER = ['still', 'jump', 'jump', 'jump', 'jump', 'still']


def runner_inputs():
    files = [Path(__file__), HERE / 'probe_patch.py', HERE / patch.HELPER]
    files += [BUILD / name for name in ('native-input-combat-run.py', 'sleeping-root-r2-run.py',
        'sleeping-root-r2-build.py', 'enemy-release.py', 'enemy-speed.py', 'motion-test.py', 'profile-vision.py')]
    files += [r.ROOT / 'mods/ModLoader/tools' / name for name in ('test_registry.py', 'air_test_process.py')]
    return {str(p): r.sha(p) for p in files}


def fixture_inputs():
    return {str(p): r.sha(p) for p in (HERE / patch.HELPER, HERE / 'probe_patch.py')}


base.runner_inputs = runner_inputs
base.candidate_inputs = fixture_inputs
base.FORMAL_HOST = HOST


def compile_probe(lease, baseline, scripts, compiler, fixture, grow):
    source = BUILD.parent / 'src'
    before = base.tree_hashes(source)
    staging = HERE / 'staging' / uuid.uuid4().hex
    patch.prepare(source, staging / 'src', grow)
    after = base.tree_hashes(staging / 'src')
    changed = {key for key in set(before) | set(after) if before.get(key) != after.get(key)}
    assert changed == {'ContinuousSceneMotionProbe.as', patch.HELPER}
    assert before == base.tree_hashes(source), 'Shared source changed while copying'
    origin = dict(sharedSource=str(source), sharedSourceSHA256=before, changed=sorted(changed),
        stagedSourceSHA256=after, growthRequested=grow, diagnosticOnly=True)
    r.save(staging / 'source-origin.json', origin)
    base.B, base.OUT = staging / 'build', HERE / 'probe-builds'
    path = base.compile_frozen_probe(lease, baseline, scripts, compiler, fixture)
    receipt = r.read(path)
    receipt.update(verticalMotionVersion='vertical-camera-1', growthRequested=grow,
        sourceOriginPath=str(staging / 'source-origin.json'), sourceOriginSHA256=r.sha(staging / 'source-origin.json'))
    r.save(path, receipt)
    return path


def verify_probe(path, baseline, scripts, compiler, fixture, grow):
    receipt = base.verify_probe(path, baseline, scripts, compiler, fixture)
    assert receipt['verticalMotionVersion'] == 'vertical-camera-1' and receipt['growthRequested'] == grow
    assert r.sha(Path(receipt['sourceOriginPath'])) == receipt['sourceOriginSHA256']
    assert r.sha(Path(receipt['frozenSourcePath']) / patch.HELPER) == r.sha(HERE / patch.HELPER)
    return receipt


def summarize(result, args):
    v, cfg = result['verticalMotion'], result['config']
    assert v['version'] == 'vertical-camera-1' and v['valid'] and v['complete'] and not v['error']
    assert v['sceneLarge'] == (args.mode == 'scene') and v['growthRequested'] == args.grow
    assert cfg['nativeInputMotion'] and cfg['stableMotion'] and cfg['presentationCheck']
    assert not cfg['encounter'] and not cfg['fixedEnemies'] and not cfg['playerFire']
    assert cfg['noLighting'] and cfg['noWall'] and not cfg['vision']
    assert result['nativeInputMotion']['spawn']['calls'] == 1
    assert result['driver']['forcedPositionCalls'] == v['forcedPositionCalls'] == v['fixtureActorsAdded'] == 0
    assert not result['playerFire']['enabled'] and result['playerFire']['shotFrames'] == 0
    assert v['cameraControl']['originalMoved'] is True and not args.grow
    assert v['cleanup'] == dict(keysCleared=True, positionWrites=0, velocityWrites=0,
        displayBindingsChanged=0, nativeDataDisposed=0,cameraOriginalMoved=True,cameraMoved=True,
        cameraHeld=False,cameraRestored=True,heldRestores=2)
    assert all(e['restored'] for e in v['cameraControl']['restores'])
    timeline, previous = v['timeline'], v['timelineStartedAtMs']
    for serial, f in enumerate(timeline, 1):
        assert f['serial'] == serial and f['atMs'] - previous == f['dtMs'] and f['dtMs'] >= 0
        previous = f['atMs']
        p = f['pose']
        assert all(base.finite(p[k]) for k in ('x', 'y', 'dx', 'dy', 'cameraX', 'cameraY'))
        assert not p['attack'] and not p['run'] and not p['isFly'] and p['levit'] == 0
        bounds = v['route']['safeCenterRange']
        assert bounds['left'] <= p['x'] <= bounds['right']
    assert sum(f['dtMs'] for f in timeline) == v['endedAtMs'] - v['timelineStartedAtMs']
    grown = bool(v.get('growth') and v['growth'].get('applied'))
    assert not grown and v['growth'] is None and len(v['windows']) == 6
    samples = []
    for n, row in enumerate(v['windows']):
        epoch, index = divmod(n, 6)
        assert (row['epoch'], row['index'], row['mode']) == (epoch, index, ORDER[index])
        frames = row['frames']
        assert len(frames) == 120 and row['endedAtMs'] - row['startedAtMs'] == sum(f['dtMs'] for f in frames)
        assert all(f['phase'] == 'sample' and f['epoch'] == epoch and f['window'] == index for f in frames)
        assert all(timeline[f['serial'] - 1] == f for f in frames)
        poses = [f['pose'] for f in frames]
        held = index in (2,3)
        assert row['cameraHeld'] is held and row['originalCamMoved'] is True and row['cameraRestored']
        assert row['steady'] and abs(row['startPose']['dx']) < .01
        assert not row['startPose']['left'] and not row['startPose']['right']
        keys = ['sceneResident','sceneWarmCount','sceneWarmSlices','sceneWarmForced','sceneRedraws','sceneMisses','sceneEvictions']
        assert all(row['startCounters'][k] == row['endCounters'][k] for k in keys)
        assert all(all(f['counters'][k] == row['startCounters'][k] for k in keys) for f in frames)
        assert all(p['cameraHeld'] is held and p['cameraMoved'] is (not held) and p['originalCamMoved'] is True
                   and abs(p['dx']) < .01 and not p['left'] and not p['right'] for p in poses)
        if held:
            assert all(p['cameraX'] == row['heldX'] and p['cameraY'] == row['heldY']
                       and p['quakeX'] == 0 and p['quakeY'] == 0 for p in poses)
        jumps = [j for j in v['jumps'] if (j['startEpoch'], j['endEpoch'], j['startWindow'], j['endWindow']) == (epoch, epoch, index, index)
                 and j['rose'] and j['fell'] and j['landed'] and j['height'] > 1]
        assert row['completedJumps'] == len(jumps)
        spans = {key: max(p[key] for p in poses) - min(p[key] for p in poses) for key in ('x', 'y', 'cameraX', 'cameraY')}
        if row['mode'] == 'jump':
            assert jumps and any(p['jump'] for p in poses) and any(p['dy'] < -.1 for p in poses) and any(p['dy'] > .1 for p in poses)
            if not held: assert spans['cameraY'] > 1, 'Native follow A must actually move the camera'
            assert not any(p['left'] or p['right'] for p in poses)
        elif row['mode'] == 'walk':
            assert spans['x'] > 40 and all(p['left'] != p['right'] for p in poses) and not any(p['jump'] for p in poses)
        else:
            assert not any(p['left'] or p['right'] or p['jump'] for p in poses)
            assert all(abs(p['dy']) < .01 and p['floorContact'] for p in poses)
        samples.append(dict(epoch=epoch, index=index, mode=row['mode'], cameraHeld=held, cameraRestored=row['cameraRestored'], frames=base.metrics([f['dtMs'] for f in frames]),
            nativeBand=base.metrics([f['nativeBandMs'] for f in frames]),
            priorScript=base.metrics([f['priorScriptMs'] for f in frames if f['priorScriptMs'] is not None]),
            spans=spans, completedJumps=len(jumps), jumpHeights=[j['height'] for j in jumps],
            steadyCache=row['steady'], startCounters=row['startCounters'], endCounters=row['endCounters'],
            startMemory=row['startMemory'], endMemory=row['endMemory'], startActivity=row['startActivity'], endActivity=row['endActivity']))
    return dict(name=args.name, mode=args.mode, qualification=dict(passed=True), diagnosticOnly=True,
        performanceEligible=False, performanceAcceptance=False, deployed=False, hostSHA256=HOST,
        setup=v['setup'], growth=v['growth'], headroom=v['headroom'], cleanup=v['cleanup'],cameraControl=v['cameraControl'],
        cameraArms={label:base.metrics([f['dtMs'] for i in indices for f in v['windows'][i]['frames']])
            for label,indices in [('A-native-follow',[1,4]),('B-held-viewport',[2,3])]},
        timelineFrames=len(timeline), timelineMs=sum(f['dtMs'] for f in timeline), windows=samples,
        normalizedTerrain=result['selectedCombatCorridorTiles'], nativeRoute=v['route'],
        limitations=v['limitations'] + ['Observer allocation and periodic telemetry are included; these are attribution samples, not production acceptance.',
            'Natural enemies are retained; differences in their activity and attacks may confound mode comparison.',
            'Native room camera bounds differ; zero camera motion does not disprove vertical actor motion cost.'])


def main():
    assert __debug__, 'Assertions required'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    parser.add_argument('--mode', choices=['scene'], default='scene')
    parser.set_defaults(grow=False)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--compile-probe', action='store_true')
    source.add_argument('--probe-build', type=Path)
    parser.add_argument('--registry-wait', type=int, default=600)
    args = parser.parse_args()
    assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
    assert not (r.E / args.name).exists(), 'Fresh evidence name required'
    with m.Registration(owner='ContinuousScene / vertical camera follow-hold / 01a13816', purpose=args.name,
            run_dir=m.RUNTIME, evidence=r.E / args.name, wait=args.registry_wait) as lease:
        assert not m.air_pids(), 'Other AIR is left untouched'
        baseline, scripts, compiler, fixture = r.baseline(), runner_inputs(), base.support.compiler_inputs(), fixture_inputs()
        assert baseline['pfe.swf'] == HOST and baseline[base.CS_PATH] == CS
        assert next(value for key, value in baseline.items() if key.lower() == RC_PATH.lower()) == RC
        path = compile_probe(lease, baseline, scripts, compiler, fixture, args.grow) if args.compile_probe else args.probe_build.resolve()
        probe = verify_probe(path, baseline, scripts, compiler, fixture, args.grow)
        m.prepare()
        shutil.copy2(probe['probePath'], m.RUNTIME / base.PROBE_PATH)
        assert r.sha(m.RUNTIME / 'pfe.swf') == HOST and r.sha(m.RUNTIME / base.CS_PATH) == CS
        assert r.sha(m.RUNTIME / base.PROBE_PATH) == probe['probeSHA256']
        options = ['--name', args.name, '--high-qos', '--land', 'random_mane', '--benchmark',
            'scene' if args.mode == 'scene' else 'normal', '--short', '--stable-motion', '--native-input-motion',
            '--combat-route', '--combat-route-length', '200', '--window-width', '2048', '--window-height', '1123',
            '--no-lighting', '--no-wall', '--presentation-check']
        if args.mode == 'native':
            options += ['--native-room-x', '2', '--native-room-y', '4', '--native-route-x', '480', '--native-route-y', '119']
        else:
            options += ['--expect-no-signs']
        assert baseline == r.baseline() and scripts == runner_inputs() and fixture == fixture_inputs()
        verify_probe(path, baseline, scripts, compiler, fixture, args.grow)
        try:
            m.run_owned(m.parse_args(options), lease)
        finally:
            folder = r.E / args.name
            if folder.exists():
                r.save(folder / 'probe-build.json', probe)
                r.save(folder / 'runner-inputs.json', dict(options=options, baseline=baseline, runnerInputs=scripts,
                    compilerInputs=compiler, fixtureInputs=fixture, probeBuildPath=str(path)))
        result, inputs = r.result(args.name)
        assert baseline == r.baseline() and scripts == runner_inputs() and fixture == fixture_inputs()
        assert compiler == base.support.compiler_inputs()
        verify_probe(path, baseline, scripts, compiler, fixture, args.grow)
        for key, value in baseline.items():
            if key not in ('application.xml', 'mods/loader-manifest.txt'):
                assert inputs[key] == value, key
        assert inputs[base.PROBE_PATH] == probe['probeSHA256']
        policy = r.read(folder / 'process-policy.json')
        assert not policy['performanceEligible'] and not policy.get('runFailure') and not policy.get('memoryAbort') and not policy['otherAirProcessIds']
        try:
            summary = summarize(result, args)
        except Exception as error:
            r.save(folder / 'summary.json', dict(qualification=dict(passed=False, error=repr(error)),
                diagnosticOnly=True, performanceEligible=False, deployed=False, rawResult='storage/result.json'))
            raise
        summary['probeBuildPath'] = str(path)
        r.save(folder / 'summary.json', summary)
        print(json.dumps(dict(name=args.name, mode=args.mode, passed=True, windows=[
            dict(mode=s['mode'], epoch=s['epoch'], frames=s['frames'], spans=s['spans'], completedJumps=s['completedJumps'])
            for s in summary['windows']], performanceEligible=False)), flush=True)
        lease.outcome = 'passed'
        lease.note = 'Native jump camera follow/hold attribution; restored camera flag, no deployment or performance acceptance'


if __name__ == '__main__':
    main()
