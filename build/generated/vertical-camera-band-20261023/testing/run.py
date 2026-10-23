"""Exact audited camera-band host, real six-window jumps or separate terminal components."""
from pathlib import Path
import argparse
import importlib.util
import json
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


base = load('vertical_native_support', BUILD / 'native-input-combat-run.py')
patch = load('vertical_source_patch', HERE / 'probe_patch.py')
r, m = base.r, base.m
HOST = '80CFD8CF3138EE59CBF6EDA0A1824A9EC960F413BD95E4B90D41DD0322B4FD3D'
CS = '7F1F2961C6E299D949423591F3C65C610C2EAEFA7FC72E8A583A402770D6B51F'
RC = 'DF0FA0E2CA952E77E5132E75D71E73558DC919C7B8CDEBA5DA05FC9E94DC01E7'
RC_PATH = 'mods/RConnect/release/RConnectMod.swf'
ORDER = ['still', 'jump', 'jump', 'jump', 'jump', 'still']
TARGET = 'fe.inter.Camera::0:1:calc'
BASE_XML = 'B92260A7A0DFA80EB129C60AEF273645C32BBBA9B3588770BD7083D6984E7E04'
CONTROL_NAME = 'camera-band-controls.json'
COMPONENT_MODE = False


def host_inputs(receipt_path):
    if receipt_path is None:
        return dict(kind='baseline', path=str(r.ROOT / 'pfe.swf'), sha256=HOST, inputs={})
    receipt_path = receipt_path.resolve()
    assert receipt_path == HERE.parent / 'build.json', 'Only this reviewed candidate family is accepted'
    receipt = r.read(receipt_path)
    assert receipt['version'] == 'vertical-camera-band-1' and receipt['base'] == HOST
    assert receipt['baseXML'] == BASE_XML and receipt['target'] == TARGET
    assert receipt['productionCandidate'] and not receipt['deployed']
    folder = receipt_path.parent
    required = {folder / 'pfe.swf': receipt['candidate'], folder / 'pfe.xml': receipt['candidateXML'],
        folder / 'semantic-audit.json': receipt['audit'], Path(receipt['originalPath']): receipt['originalSource'],
        folder / 'source/fe/inter/Camera.as': receipt['instrumentedSource']}
    for path, digest in required.items():
        assert r.sha(path) == digest, str(path)
    audit = r.read(folder / 'semantic-audit.json')
    assert audit['passed'] and audit['auditTarget'] == TARGET
    assert audit['baseSHA256'] == HOST and audit['candidateSHA256'] == receipt['candidate']
    assert audit['baseXMLSHA256'] == BASE_XML and audit['candidateXMLSHA256'] == receipt['candidateXML']
    assert audit['actualChangedBodies'] == audit['allowedChangedMethods'] == [TARGET]
    assert audit['unchangedMethodBodies'] == 5770 and audit['unchangedClassLayouts'] == 1016
    assert not audit['addedFields'] and not audit['addedMethods'] and audit['timerBinding']['callCount'] == 0
    for key in ('methodAndClassIndicesPreserved', 'originalConstantPoolPreserved',
                'nonABCSWFEnvelopePreserved', 'preservedOriginalLayout', 'constructorsPreserved'):
        assert audit[key] is True, key
    assert audit['importedClassCopied'] is False
    assert audit['wrapperSHA256'] == r.sha(folder / 'audit.py')
    assert receipt['timerCalls'] == 0 and receipt['sourceTransformReversible']
    assert not receipt['newClassMembers'] and not receipt['newClosures'] and not receipt['newTryCatchFinally']
    required.update({Path(path): digest for path, digest in receipt['sourceInputs'].items()})
    for path, digest in required.items():
        assert r.sha(path) == digest, str(path)
    required[receipt_path] = r.sha(receipt_path)
    return dict(kind='candidate', path=str(folder / 'pfe.swf'), sha256=receipt['candidate'],
        inputs={str(path): digest for path, digest in required.items()}, receiptPath=str(receipt_path))


def runner_inputs():
    files = [Path(__file__), HERE / 'probe_patch.py', HERE / patch.HELPER]
    files += [BUILD / name for name in ('native-input-combat-run.py', 'sleeping-root-r2-run.py',
        'sleeping-root-r2-build.py', 'enemy-release.py', 'enemy-speed.py', 'motion-test.py', 'profile-vision.py')]
    files += [r.ROOT / 'mods/ModLoader/tools' / name for name in ('test_registry.py', 'air_test_process.py')]
    return {str(p): r.sha(p) for p in files}


def fixture_inputs():
    files = [HERE / patch.HELPER, HERE / 'probe_patch.py']
    if COMPONENT_MODE:
        files.append(patch.COMPONENT_SOURCE)
    return {str(p): r.sha(p) for p in files}


base.runner_inputs = runner_inputs
base.candidate_inputs = fixture_inputs
base.FORMAL_HOST = HOST
original_runtime_hashes = m.hashes


def runtime_hashes():
    values = original_runtime_hashes()
    control = m.RUNTIME / CONTROL_NAME
    if control.exists():
        values[CONTROL_NAME] = r.sha(control)
    return values


m.hashes = runtime_hashes


def compile_probe(lease, baseline, scripts, compiler, fixture, grow):
    source = BUILD.parent / 'src'
    before = base.tree_hashes(source)
    staging = HERE / 'staging' / uuid.uuid4().hex
    patch.prepare(source, staging / 'src', grow, COMPONENT_MODE)
    after = base.tree_hashes(staging / 'src')
    changed = {key for key in set(before) | set(after) if before.get(key) != after.get(key)}
    expected = {'ContinuousSceneMotionProbe.as', patch.HELPER}
    if COMPONENT_MODE:
        expected.add(patch.COMPONENT_HELPER)
    assert changed == expected
    assert before == base.tree_hashes(source), 'Shared source changed while copying'
    origin = dict(sharedSource=str(source), sharedSourceSHA256=before, changed=sorted(changed),
        stagedSourceSHA256=after, growthRequested=grow, componentsOnly=COMPONENT_MODE, diagnosticOnly=True)
    r.save(staging / 'source-origin.json', origin)
    base.B, base.OUT = staging / 'build', HERE / 'probe-builds'
    path = base.compile_frozen_probe(lease, baseline, scripts, compiler, fixture)
    receipt = r.read(path)
    receipt.update(verticalMotionVersion='vertical-camera-band-test-1', growthRequested=grow, componentsOnly=COMPONENT_MODE,
        sourceOriginPath=str(staging / 'source-origin.json'), sourceOriginSHA256=r.sha(staging / 'source-origin.json'))
    r.save(path, receipt)
    return path


def verify_probe(path, baseline, scripts, compiler, fixture, grow):
    receipt = base.verify_probe(path, baseline, scripts, compiler, fixture)
    assert receipt['verticalMotionVersion'] == 'vertical-camera-band-test-1' and receipt['growthRequested'] == grow
    assert receipt['componentsOnly'] == COMPONENT_MODE
    assert r.sha(Path(receipt['sourceOriginPath'])) == receipt['sourceOriginSHA256']
    assert r.sha(Path(receipt['frozenSourcePath']) / patch.HELPER) == r.sha(HERE / patch.HELPER)
    if COMPONENT_MODE:
        assert r.sha(Path(receipt['frozenSourcePath']) / patch.COMPONENT_HELPER) == r.sha(patch.COMPONENT_SOURCE)
    return receipt


def summarize(result, args):
    v, cfg = result['verticalMotion'], result['config']
    assert v['version'] == 'vertical-camera-band-test-1' and v['valid'] and v['complete'] and not v['error']
    assert v['sceneLarge'] == (args.mode == 'scene') and v['growthRequested'] == args.grow
    assert cfg['nativeInputMotion'] and cfg['stableMotion'] and cfg['presentationCheck']
    assert not cfg['encounter'] and not cfg['fixedEnemies'] and not cfg['playerFire']
    assert cfg['noLighting'] and cfg['noWall'] and not cfg['vision']
    assert result['nativeInputMotion']['spawn']['calls'] == 1
    assert result['driver']['forcedPositionCalls'] == v['forcedPositionCalls'] == v['fixtureActorsAdded'] == 0
    assert not result['playerFire']['enabled'] and result['playerFire']['shotFrames'] == 0
    assert v['cameraObservation'] == dict(originalMoved=True, propertyWrites=0) and not args.grow
    assert v['cleanup'] == dict(keysCleared=True, positionWrites=0, velocityWrites=0,
        displayBindingsChanged=0, nativeDataDisposed=0, cameraPropertyWrites=0, cameraMovedUnchanged=True)
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
        assert row['originalCamMoved'] is True
        assert row['steady'] and abs(row['startPose']['dx']) < .01
        assert not row['startPose']['left'] and not row['startPose']['right']
        keys = ['sceneResident','sceneWarmCount','sceneWarmSlices','sceneWarmForced','sceneRedraws','sceneMisses','sceneEvictions']
        assert all(row['startCounters'][k] == row['endCounters'][k] for k in keys)
        assert all(all(f['counters'][k] == row['startCounters'][k] for k in keys) for f in frames)
        assert all(p['cameraMoved'] is True and p['originalCamMoved'] is True
                   and abs(p['dx']) < .01 and not p['left'] and not p['right'] for p in poses)
        geometry = ('cameraTargetY','cameraOvy','vy','scale','scY','screenY','headScreenY','feetScreenY','visualY','visualScaleY')
        assert all(all(base.finite(p[k]) for k in geometry) for p in poses)
        assert all(p['scale'] == p['visualScaleY'] == 1 and p['scY'] > 0 and p['screenY'] == 1084
                   and p['vy'] == p['cameraY'] and p['visualY'] == p['vy'] + p['quakeY']
                   and p['headScreenY'] == (p['y'] - p['scY']) * p['scale'] + p['vy'] + p['quakeY']
                   and p['feetScreenY'] == p['y'] * p['scale'] + p['vy'] + p['quakeY']
                   and 0 <= p['headScreenY'] < p['feetScreenY'] <= p['screenY'] for p in poses)
        previous_poses = [row['startPose']] + poses[:-1]
        changed_y = sum(p['cameraY'] != previous['cameraY'] for p, previous in zip(poses, previous_poses))
        changed_target = sum(p['cameraTargetY'] != previous['cameraTargetY'] for p, previous in zip(poses, previous_poses))
        assert (row['cameraYChangedFrames'], row['cameraTargetChangedFrames']) == (changed_y, changed_target)
        jumps = [j for j in v['jumps'] if (j['startEpoch'], j['endEpoch'], j['startWindow'], j['endWindow']) == (epoch, epoch, index, index)
                 and j['rose'] and j['fell'] and j['landed'] and j['height'] > 1]
        assert row['completedJumps'] == len(jumps)
        spans = {key: max(p[key] for p in poses) - min(p[key] for p in poses) for key in ('x', 'y', 'cameraX', 'cameraY')}
        if row['mode'] == 'jump':
            assert len(jumps) >= 3 and any(p['jump'] for p in poses) and any(p['dy'] < -.1 for p in poses) and any(p['dy'] > .1 for p in poses)
            assert not any(p['left'] or p['right'] for p in poses)
        elif row['mode'] == 'walk':
            assert spans['x'] > 40 and all(p['left'] != p['right'] for p in poses) and not any(p['jump'] for p in poses)
        else:
            assert not any(p['left'] or p['right'] or p['jump'] for p in poses)
            assert all(abs(p['dy']) < .01 and p['floorContact'] for p in poses)
        samples.append(dict(epoch=epoch, index=index, mode=row['mode'], frames=base.metrics([f['dtMs'] for f in frames]),
            nativeBand=base.metrics([f['nativeBandMs'] for f in frames]),
            priorScript=base.metrics([f['priorScriptMs'] for f in frames if f['priorScriptMs'] is not None]),
            spans=spans, completedJumps=len(jumps), jumpHeights=[j['height'] for j in jumps],
            cameraYChangedFrames=changed_y, cameraTargetChangedFrames=changed_target,
            screenHeadRange=[min(p['headScreenY'] for p in poses),max(p['headScreenY'] for p in poses)],
            screenFeetRange=[min(p['feetScreenY'] for p in poses),max(p['feetScreenY'] for p in poses)],
            steadyCache=row['steady'], startCounters=row['startCounters'], endCounters=row['endCounters'],
            startMemory=row['startMemory'], endMemory=row['endMemory'], startActivity=row['startActivity'], endActivity=row['endActivity']))
    return dict(name=args.name, mode=args.mode, qualification=dict(passed=True), diagnosticOnly=True,
        performanceEligible=False, performanceAcceptance=False, deployed=False, hostSHA256=HOST,
        setup=v['setup'], growth=v['growth'], headroom=v['headroom'], cleanup=v['cleanup'],cameraObservation=v['cameraObservation'],
        jumpFrames=base.metrics([f['dtMs'] for i in (1,2,3,4) for f in v['windows'][i]['frames']]),
        timelineFrames=len(timeline), timelineMs=sum(f['dtMs'] for f in timeline), windows=samples,
        normalizedTerrain=result['selectedCombatCorridorTiles'], nativeRoute=v['route'],
        limitations=v['limitations'] + ['Observer allocation and periodic telemetry are included; these are attribution samples, not production acceptance.',
            'Natural enemies are retained; differences in their activity and attacks may confound mode comparison.',
            'Native room camera bounds differ; zero camera motion does not disprove vertical actor motion cost.'])


def main():
    global COMPONENT_MODE
    assert __debug__, 'Assertions required'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    parser.add_argument('--mode', choices=['scene'], default='scene')
    parser.add_argument('--components-only', action='store_true', help='Separate terminal component process; never captures timing')
    host = parser.add_mutually_exclusive_group(required=True)
    host.add_argument('--baseline', action='store_true', help='Exact installed 80CF, no candidate state required')
    host.add_argument('--host-build', type=Path, help='Strict retained candidate build.json, never compiled import')
    parser.set_defaults(grow=False)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--compile-probe', action='store_true')
    source.add_argument('--probe-build', type=Path)
    parser.add_argument('--registry-wait', type=int, default=600)
    args = parser.parse_args()
    COMPONENT_MODE = args.components_only
    assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
    assert not (r.E / args.name).exists(), 'Fresh evidence name required'
    selected = host_inputs(args.host_build)
    with m.Registration(owner='ContinuousScene / vertical camera band / 01a13816', purpose=args.name,
            run_dir=m.RUNTIME, evidence=r.E / args.name, wait=args.registry_wait) as lease:
        assert not m.air_pids(), 'Other AIR is left untouched'
        baseline, scripts, compiler, fixture = r.baseline(), runner_inputs(), base.support.compiler_inputs(), fixture_inputs()
        assert baseline['pfe.swf'] == HOST and baseline[base.CS_PATH] == CS
        assert next(value for key, value in baseline.items() if key.lower() == RC_PATH.lower()) == RC
        path = compile_probe(lease, baseline, scripts, compiler, fixture, args.grow) if args.compile_probe else args.probe_build.resolve()
        probe = verify_probe(path, baseline, scripts, compiler, fixture, args.grow)
        assert selected == host_inputs(args.host_build)
        m.prepare()
        if selected['kind'] == 'candidate':
            shutil.copy2(selected['path'], m.RUNTIME / 'pfe.swf')
        shutil.copy2(probe['probePath'], m.RUNTIME / base.PROBE_PATH)
        assert r.sha(m.RUNTIME / 'pfe.swf') == selected['sha256'] and r.sha(m.RUNTIME / base.CS_PATH) == CS
        assert r.sha(m.RUNTIME / base.PROBE_PATH) == probe['probeSHA256']
        control = m.RUNTIME / CONTROL_NAME
        assert not control.exists(), 'Stale camera test control must be inspected, not overwritten'
        control_data = dict(version='vertical-camera-band-test-controls-1', componentsOnly=COMPONENT_MODE,
            expectedCandidate=selected['kind'] == 'candidate', hostSHA256=selected['sha256'])
        options = ['--name', args.name, '--high-qos', '--land', 'random_mane', '--benchmark',
            'scene' if args.mode == 'scene' else 'normal', '--short', '--stable-motion', '--native-input-motion',
            '--combat-route', '--combat-route-length', '200', '--window-width', '2048', '--window-height', '1123',
            '--no-lighting', '--no-wall', '--presentation-check']
        options += ['--expect-no-signs']
        assert baseline == r.baseline() and scripts == runner_inputs() and fixture == fixture_inputs()
        verify_probe(path, baseline, scripts, compiler, fixture, args.grow)
        r.save(control, control_data)
        control_sha = r.sha(control)
        try:
            m.run_owned(m.parse_args(options), lease)
        finally:
            folder = r.E / args.name
            if folder.exists():
                r.save(folder / 'probe-build.json', probe)
                r.save(folder / 'runner-inputs.json', dict(options=options, baseline=baseline, runnerInputs=scripts,
                    compilerInputs=compiler, fixtureInputs=fixture, probeBuildPath=str(path), host=selected,
                    isolatedControl=control_data, isolatedControlSHA256=control_sha))
            if control.exists():
                assert r.sha(control) == control_sha, 'Isolated control changed'
                control.unlink()
        result, inputs = r.result(args.name)
        assert baseline == r.baseline() and scripts == runner_inputs() and fixture == fixture_inputs()
        assert compiler == base.support.compiler_inputs()
        assert selected == host_inputs(args.host_build)
        verify_probe(path, baseline, scripts, compiler, fixture, args.grow)
        for key, value in baseline.items():
            if key not in ('pfe.swf', 'application.xml', 'mods/loader-manifest.txt'):
                assert inputs[key] == value, key
        assert inputs['pfe.swf'] == selected['sha256'] and inputs[CONTROL_NAME] == control_sha
        assert inputs[base.PROBE_PATH] == probe['probeSHA256']
        assert result['cameraBandHostControl'] == control_data
        policy = r.read(folder / 'process-policy.json')
        assert not policy['performanceEligible'] and not policy.get('runFailure') and not policy.get('memoryAbort') and not policy['otherAirProcessIds']
        try:
            if COMPONENT_MODE:
                c = result['verticalCameraComponents']
                assert c['passed'] and c['terminalOnly'] and c['expectCandidate'] == control_data['expectedCandidate']
                assert c['cases'] and all(case['passed'] for case in c['cases']) and c['restore']['passed']
                assert not result.get('verticalMotion') and not result['samples']
                summary = dict(name=args.name, qualification=dict(passed=True), componentsOnly=True,
                    verification=c, diagnosticOnly=True, performanceEligible=False, deployed=False, windows=[])
            else:
                assert 'verticalCameraComponents' not in result
                summary = summarize(result, args)
        except Exception as error:
            r.save(folder / 'summary.json', dict(qualification=dict(passed=False, error=repr(error)),
                diagnosticOnly=True, performanceEligible=False, deployed=False, rawResult='storage/result.json'))
            raise
        summary['probeBuildPath'] = str(path)
        summary.update(hostKind=selected['kind'], hostSHA256=selected['sha256'], installedHostSHA256=HOST,
            isolatedControl=control_data)
        r.save(folder / 'summary.json', summary)
        print(json.dumps(dict(name=args.name, mode=args.mode, host=selected['kind'], componentsOnly=COMPONENT_MODE, passed=True, windows=[
            dict(mode=s['mode'], epoch=s['epoch'], frames=s['frames'], spans=s['spans'], completedJumps=s['completedJumps'])
            for s in summary['windows']], performanceEligible=False)), flush=True)
        lease.outcome = 'passed'
        lease.note = 'Exact camera-band host isolated check; installed 80CF unchanged, no deployment or performance acceptance'


if __name__ == '__main__':
    main()
