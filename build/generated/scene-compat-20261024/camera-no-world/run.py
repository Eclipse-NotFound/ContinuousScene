"""Isolated ABE2 no-world camera-follow/held ABBA; retains all original simulation gates; never deploys."""
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
DENSE_DIR = BUILD/'generated/combat-near-native-20261023/fixture-audit-v2'
VERSION = 'combat-camera-no-world-1'
HOST = 'ABE2B65EDF3D0E4E0FA8ECA76A60E577D40E47F20B9ACECEBEC7730849A2602A'
RC = 'DF0FA0E2CA952E77E5132E75D71E73558DC919C7B8CDEBA5DA05FC9E94DC01E7'
SEED_RECEIPT = BUILD.parent/'knowledge/experiments/evidence/vertical-camera-band-20261023-combat-candidate-r3/probe-build.json'
SEED_SHA = 'B7ED1EAB8BEE0DC1024D6EF0A56A965F311B97E8CED9A9F32A2BCDE35B35FF13'
SEED_PROBE = '39A1497BE832282CAC25E2A508A954432F9F31B15A2FBE5A650AB8C4D9C97E9E'
CHANGED = ['ContinuousSceneMotionProbe.as', 'tests/SceneCombatCameraHoldProbe.as']


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


dense = load('combat_camera_dense', DENSE_DIR/'dense-combat-run.py')
patcher = load('combat_camera_patch', HERE/'probe_patch.py')
base, r, m, support = dense.base, dense.r, dense.m, dense.support
base.FORMAL_HOST = HOST
dense.FORMAL_RC = RC


def seed():
    assert r.sha(SEED_RECEIPT) == SEED_SHA, 'Frozen real-combat receipt changed'
    value = r.read(SEED_RECEIPT)
    assert value['probeSHA256'] == SEED_PROBE == r.sha(Path(value['probePath']))
    assert base.tree_hashes(Path(value['frozenSourcePath'])) == value['frozenSourceSHA256']
    return value


def runner_inputs():
    return dict(dense.runner_inputs(), **{str(HERE/'run.py'): r.sha(HERE/'run.py'),
        str(HERE/'probe_patch.py'): r.sha(HERE/'probe_patch.py')})


def fixture_inputs():
    seed()
    files = [SEED_RECEIPT, HERE/patcher.HELPER, HERE/'probe_patch.py',
             support.OUT/'source-provenance.json']
    return {str(p): r.sha(p) for p in files}


def memory_gate():
    value = m.memory_status()
    assert value['availableCommit'] >= 4*1024**3 and value['availablePhysical'] >= 2*1024**3, (
        'Camera diagnostic requires 4 GiB commit and 2 GiB physical headroom', value)
    return value


def verify_probe(path, baseline, scripts, compiler, fixture):
    probe = base.verify_probe(path, baseline, scripts, compiler, fixture)
    assert probe['cameraDiagnosticVersion'] == VERSION and probe['denseFixture'] == dense.VERSION
    origin_path = Path(probe['sourceOrigin'])
    assert r.sha(origin_path) == probe['sourceOriginSHA256']
    origin = r.read(origin_path)
    old = seed()
    assert origin['seedReceiptSHA256'] == SEED_SHA and origin['seedProbeSHA256'] == SEED_PROBE
    assert origin['seedSourceSHA256'] == old['frozenSourceSHA256']
    assert origin['changed'] == CHANGED and origin['fixtureInputs'] == fixture
    assert origin['stagedSHA256'] == probe['frozenSourceSHA256']
    changed = sorted(k for k in set(origin['seedSourceSHA256']) | set(probe['frozenSourceSHA256'])
                     if origin['seedSourceSHA256'].get(k) != probe['frozenSourceSHA256'].get(k))
    assert changed == CHANGED, 'Only the sidecar helper and integration may differ'
    frozen = Path(probe['frozenSourcePath'])
    assert r.sha(frozen/patcher.HELPER) == r.sha(HERE/patcher.HELPER)
    expected = patcher.transform((Path(old['frozenSourcePath'])/'ContinuousSceneMotionProbe.as').read_text('utf-8-sig'))
    assert (frozen/'ContinuousSceneMotionProbe.as').read_text('utf-8-sig') == expected
    return probe


def compile_probe(lease, baseline, scripts, compiler, fixture):
    old = seed(); staging = HERE/'source-staging'/uuid.uuid4().hex
    patcher.prepare(Path(old['frozenSourcePath']), staging/'src')
    staged = base.tree_hashes(staging/'src')
    changed = sorted(k for k in set(old['frozenSourceSHA256']) | set(staged)
                     if old['frozenSourceSHA256'].get(k) != staged.get(k))
    assert changed == CHANGED
    origin = staging/'source-origin.json'
    r.save(origin, dict(version=VERSION, seedReceipt=str(SEED_RECEIPT), seedReceiptSHA256=SEED_SHA,
        seedProbeSHA256=SEED_PROBE, seedSource=old['frozenSourcePath'], seedSourceSHA256=old['frozenSourceSHA256'],
        stagedSource=str(staging/'src'), stagedSHA256=staged, changed=changed, fixtureInputs=fixture))
    base.B = staging/'build'
    path = base.compile_frozen_probe(lease, baseline, scripts, compiler, fixture)
    probe = r.read(path)
    probe.update(cameraDiagnosticVersion=VERSION, denseFixture=dense.VERSION,
                 sourceOrigin=str(origin), sourceOriginSHA256=r.sha(origin))
    r.save(path, probe)
    return path


def inside(q, viewport):
    return all(isinstance(q[k], (int, float)) and math.isfinite(q[k]) for k in ('left', 'right', 'top', 'bottom')) and (
        q['left'] >= viewport['left'] and q['right'] <= viewport['right'] and
        q['top'] >= viewport['top'] and q['bottom'] <= viewport['bottom'])


def camera_summary(result):
    hold, pre = result['cameraHold'], result['cameraPrewarm']
    assert hold['version'] == VERSION and hold['valid'] and hold['complete'] and not hold['incomplete']
    assert hold['error'] is None and hold['frames'] == 1200 and hold['order'] == [False, True, True, False]
    assert hold['cleanup']['restored'] and hold['cleanup']['cameraIdentity'] and hold['cleanup']['finalMoved'] is True
    assert hold['controlWrites'] == 2 and hold['apiWrites'] == hold['actorPositionWrites'] == hold['actorVelocityWrites'] == 0
    assert not hold['cleanup']['obsoleteCoordinatesRestored']
    assert hold['originalWorldVisible'] is True and hold['worldHiddenThroughout'] is True
    assert hold['worldVisibilityWrites'] == 2
    assert hold['cleanup']['worldIdentity'] and hold['cleanup']['worldVisibilityRestored']
    assert hold['cleanup']['originalWorldVisible'] is True and hold['cleanup']['finalWorldVisible'] is True
    assert pre['version'] == 'combat-camera-prewarm-1' and pre['beforeFixtureActors'] and pre['worldStepsCalled'] == 0
    assert pre['restored'] and pre['actorUnchanged'] and pre['drained'] and pre['ready']
    assert pre['estimatedResidentUpperBound'] <= 256 and pre['after']['resident'] <= 256
    assert len(hold['windows']) == len(result['samples']) == 4
    rows, pooled = [], {False: [], True: []}
    for index, (window, native) in enumerate(zip(hold['windows'], result['samples'])):
        held = index in (1, 2)
        assert window['index'] == index and window['held'] is held and len(window['frames']) == 300
        assert window['previousHeld'] is (index in (2, 3))
        assert window['startWorldVisible'] is False and window['endWorldVisible'] is False
        assert native['caseBeginAtMs'] <= window['switchAtMs'] <= window['switchEndMs'] <= native['sampleAtMs'][0]
        for age, (frame, stamp, dt) in enumerate(zip(window['frames'], native['sampleAtMs'], native['continuousFramesMs'])):
            assert (frame['window'], frame['index'], frame['atMs'], frame['dtMs']) == (index, age, stamp, dt)
            assert frame['held'] is held and frame['ownMs'] >= 0
            assert frame['worldVisible'] is False
            c, v = frame['camera'], frame['viewport']
            assert c['moved'] is (not held) and c['scale'] == hold['scale'] == 1
            assert c['visualX'] == c['satsX'] and c['visualY'] == c['satsY']
            assert v['left'] == -c['visualX'] and v['top'] == -c['visualY']
            assert v['right']-v['left'] == hold['width'] and v['bottom']-v['top'] == hold['height']
            assert inside(hold['platform'], v) and inside(frame['player'], v) and len(frame['actors']) == 6
            assert all(inside(actor, v) for actor in frame['actors'])
            assert all(frame['counters'][k] == hold['initialCounters'][k]
                       for k in ('resident', 'warm', 'slices', 'forced', 'misses', 'evictions'))
            if held:
                assert c['vx'] == window['heldX'] and c['vy'] == window['heldY']
                assert c['quakeX'] == c['quakeY'] == 0
                assert c['visualX'] == window['frames'][0]['camera']['visualX']
                assert c['visualY'] == window['frames'][0]['camera']['visualY']
            pooled[held].append(dt)
        xs = [f['camera']['visualX'] for f in window['frames']]
        ys = [f['camera']['visualY'] for f in window['frames']]
        assert held or max(xs)-min(xs) > 1, 'Follow arm must actually move'
        rows.append(dict(index=index, held=held, cameraXRange=max(xs)-min(xs), cameraYRange=max(ys)-min(ys),
            intervals=base.metrics(native['continuousFramesMs']), ownMs=base.metrics([f['ownMs'] for f in window['frames']]),
            switchAtMs=window['switchAtMs'], switchEndMs=window['switchEndMs'],
            activityStart=window['frames'][0]['activity'], activityEnd=window['frames'][-1]['activity'],
            cacheStart=window['startCounters'], cacheEnd=window['endCounters']))
    assert len(pooled[False]) == len(pooled[True]) == 600
    return dict(passed=True, complete=True, frames=1200, order=['follow', 'held', 'held', 'follow'],
        follow=base.metrics(pooled[False]), held=base.metrics(pooled[True]), windows=rows,
        prewarm=pre, cleanup=hold['cleanup'], allContinuousIntervalsRetained=True,
        worldHiddenThroughout=True, worldVisibilityWrites=hold['worldVisibilityWrites'],
        actorPositionWrites=0, actorVelocityWrites=0, apiWrites=0)


def main():
    assert __debug__, 'Do not disable assertions'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    parser.add_argument('--registry-wait', type=int, default=600)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--compile-probe', action='store_true')
    group.add_argument('--probe-build', type=Path)
    args = parser.parse_args(); args.mode = 'scene'
    assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
    folder = r.E/args.name
    assert not folder.exists(), 'Preserve existing evidence'
    with m.Registration(owner='ContinuousScene / no-world camera dense ABBA / 01a13816', purpose=args.name,
                        run_dir=m.RUNTIME, evidence=folder, wait=args.registry_wait) as lease:
        assert not m.air_pids(), 'Other AIR remains untouched'
        memory_before = memory_gate()
        baseline, scripts, compiler, fixture = r.baseline(), runner_inputs(), support.compiler_inputs(), fixture_inputs()
        assert baseline['pfe.swf'] == HOST and baseline[base.CS_PATH] == base.FORMAL_CS
        assert baseline[dense.RC] == RC
        path = compile_probe(lease, baseline, scripts, compiler, fixture) if args.compile_probe else args.probe_build.resolve()
        probe = verify_probe(path, baseline, scripts, compiler, fixture)
        m.prepare()
        shutil.copy2(probe['probePath'], m.RUNTIME/base.PROBE_PATH)
        assert baseline == r.baseline(), 'Installed dependencies changed while preparing'
        for key, digest in baseline.items():
            if key not in ('application.xml', 'mods/loader-manifest.txt'): assert r.sha(m.RUNTIME/key) == digest, key
        memory_before_air = memory_gate()
        options = ['--name', args.name, '--high-qos', '--land', 'random_mane', '--encounter', '--fixed-enemies',
            '--benchmark', 'scene', '--short', '--stable-motion', '--native-input-motion', '--native-sprint',
            '--player-fire', '--combat-route', '--combat-route-length', '200', '--window-width', '2048',
            '--window-height', '1123', '--no-lighting', '--no-wall', '--draw-control', 'rcnative', '--expect-no-signs']
        try:
            try: m.run_owned(m.parse_args(options), lease)
            finally:
                if folder.exists():
                    r.save(folder/'probe-build.json', probe)
                    r.save(folder/'runner-inputs.json', dict(options=options, baseline=baseline,
                        runnerInputs=scripts, compilerInputs=compiler, fixtureInputs=fixture,
                        probeBuildPath=str(path), hostSHA256=HOST, cameraDiagnosticVersion=VERSION,
                        memoryBefore=memory_before, memoryBeforeAir=memory_before_air,
                        requiredAvailableCommit=4*1024**3, requiredAvailablePhysical=2*1024**3))
            assert baseline == r.baseline() and scripts == runner_inputs() and fixture == fixture_inputs()
            assert compiler == support.compiler_inputs()
            verify_probe(path, baseline, scripts, compiler, fixture)
            result, inputs = r.result(args.name)
            for key, digest in baseline.items():
                if key not in ('application.xml', 'mods/loader-manifest.txt'): assert inputs[key] == digest, key
            assert inputs[base.PROBE_PATH] == probe['probeSHA256']
            policy = r.read(folder/'process-policy.json')
            assert not policy['performanceEligible'] and not policy.get('runFailure')
            assert not policy.get('memoryAbort') and not policy.get('otherAirProcessIds')
            summary = dense.summarize(result, args)
            summary.update(cameraDiagnosticVersion=VERSION, cameraComparison=camera_summary(result),
                           hostSHA256=HOST, complete=True, incomplete=False)
            summary['qualification']['cameraValid'] = summary['cameraComparison']['passed']
            summary['qualification']['passed'] &= summary['qualification']['cameraValid']
            summary['limitations'] += [
                'Four consecutive 300-frame follow/held/held/follow windows retain every continuous interval, including mode boundaries.',
                'A boundary interval spans the preceding frame and the new control; it is retained, not presented as a pure-mode render interval.',
                'Held control only writes cam.moved. In both arms the world parent visible flag is false; all original simulation and load gates remain.',
                'Native Camera.calc, sceneTick, sound/aim conversion and player firing still run. World parent visibility is restored after timing.',
                'This is a no-world attribution control, not a rendering optimization or a playable mode. HUD and separate parents remain.',
                'Fixing the viewport can change native activity visibility; inspect per-frame activity and unchanged dense fire/population counters.',
                'This attributes the joint camera-follow path; it does not by itself prove GPU, rasterization or World.step is the cause.',
                'The route plus original view is deliberately prewarmed before fixture creation. Timed cache growth invalidates the round.',
                'Cleanup restores injected moved control only; actor/world coordinates and the native camera cache are never rolled back.',
                'RV, WallBlend and lighting are disabled; this does not assess the separate RV-enabled slowdown.']
            r.save(folder/'summary.json', summary)
            print(json.dumps(dict(name=args.name, qualification=summary['qualification'],
                follow=summary['cameraComparison']['follow'], held=summary['cameraComparison']['held']), ensure_ascii=False), flush=True)
            assert summary['qualification']['passed']
            lease.outcome = 'passed'; lease.note = 'No-world camera dense ABBA recorded; diagnostic, no deployment'
        except Exception as error:
            if folder.exists() and not (folder/'summary.json').exists():
                raw = r.read(folder/'storage/result.json') if (folder/'storage/result.json').exists() else {}
                r.save(folder/'summary.json', dict(name=args.name, cameraDiagnosticVersion=VERSION,
                    diagnosticOnly=True, performanceEligible=False, performanceAcceptance=False, deployed=False,
                    complete=False, incomplete=True, qualification=dict(passed=False), error=repr(error),
                    cameraHold=raw.get('cameraHold'), cameraPrewarm=raw.get('cameraPrewarm'),
                    completedNativeSamples=len(raw.get('samples', [])), hostSHA256=HOST))
            raise


base.OUT = HERE/'probe-builds'
base.runner_inputs = runner_inputs
base.candidate_inputs = fixture_inputs
if __name__ == '__main__': main()
