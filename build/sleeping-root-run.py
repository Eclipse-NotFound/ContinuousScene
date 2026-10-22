"""Isolated sleeping UnitRaider display-root diagnostic, never deployment.

--check keeps ordinary four-segment combat, then performs terminal same-frame
pixels/restoration and a real zero-clips wake when observed. --timing uses ABBA
with the exact checked probe/candidate. Only the isolated CS file is replaced;
formal BEFC/CS7F1F and every other production input must remain unchanged.
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
OUT = B / 'generated/sleeping-root-20261022'
FORMAL_HOST = 'BEFCF0509E11FAC9FEF7AFB834708B8B93752A14AE3D5CD72B42AA6D42F9B82A'
FORMAL_CS = '7F1F2961C6E299D949423591F3C65C610C2EAEFA7FC72E8A583A402770D6B51F'
CANDIDATE_SHA = '61D3C9150871FF045FBD4B12CCF96A49D7E9CF8471672D7FBCF49C5A970000D0'
PROVENANCE_SHA = 'A09CDDFF1B8BEC2859078202AE568103864B9DAEEF02A030A076EC472E8336A7'
CS_PATH = 'mods/ContinuousScene/release/ContinuousSceneMod.swf'
PROBE_PATH = 'mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf'
HELPER = 'tests/SceneSleepingRootPresentation.as'
TIMING_CASES = ('draw-baseline-a', 'draw-control-b', 'draw-control-b-repeat', 'draw-baseline-a-repeat')
CHECK_CASES = ('enemy-idle', 'enemy-fast-forward', 'enemy-fast-back', 'enemy-idle-end')
COUNTERS = ('changed', 'restored', 'abandoned', 'claimedUnits', 'callbacks', 'sleepCalls',
            'wakeCalls', 'restoreBeforeWake', 'callbackMs', 'errors')
LIMITATIONS = [
    'Only exact UnitRaider sleeping units with safe roots outside viewport plus 320 px are detached.',
    'A disables the callback and restores all roots; B includes callback, ownership and viewport checks.',
    'B callback overhead is measured; frame-time differences alone are not renderer CPU cost.',
    'The first frame of every ABBA segment is excluded because display control is changed after native stepping.',
    'Combat populations/destruction and native reload gaps evolve; ABBA is diagnostic, not release acceptance.',
    'The terminal zero-clips check calls native wake once and changes that unit engaged latch; the process exits without saving.',
    'An unavailable native zero-clips unit is explicitly inconclusive, never a passed wake check.',
    'Only scale 1, this route and lighting/RV/WallBlend off are covered; no SATS/travel/mod-combination acceptance.'
]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


r = load('sleeping_root_runner_helpers', B / 'enemy-release.py')
m = r.motion


def tree_hashes(folder):
    return {p.relative_to(folder).as_posix(): r.sha(p)
            for p in sorted(folder.rglob('*')) if p.is_file()}


def runner_inputs():
    paths = (Path(__file__), B / 'sleeping-root-build.py', B / 'enemy-release.py',
             B / 'enemy-speed.py', B / 'motion-test.py', B / 'profile-vision.py',
             r.ROOT / 'mods/ModLoader/tools/test_registry.py',
             r.ROOT / 'mods/ModLoader/tools/air_test_process.py')
    return {str(p): r.sha(p) for p in paths}


def compiler_inputs():
    paths = (r.enemy.JAVA, r.enemy.TOOLS / 'flexsdk/lib/mxmlc.jar',
             r.enemy.TOOLS / 'airsdk/frameworks/libs/air/airglobal.swc')
    return {str(p): r.sha(p) for p in paths}


def candidate_inputs():
    """Recheck formal-source proof, reversible insertions and compiled inputs."""
    provenance_path, build_path = OUT / 'source-provenance.json', OUT / 'build.json'
    assert r.sha(provenance_path) == PROVENANCE_SHA
    proof, build = r.read(provenance_path), r.read(build_path)
    assert proof['version'] == 'sleeping-root-source-1' and proof['reverseInsertionCheck']
    assert proof['baseline'] == FORMAL_CS and proof['host'] == FORMAL_HOST
    assert build['version'] == 'sleeping-root-build-1' and build['diagnosticOnly']
    assert not build['performanceAcceptance'] and not build['deployed'] and not build['airRun']
    assert build['sourceProvenanceSHA256'] == PROVENANCE_SHA
    assert build['baseline'] == FORMAL_CS and build['host'] == FORMAL_HOST
    assert build['candidateSHA256'] == CANDIDATE_SHA
    assert build['compilerInputs'] == compiler_inputs()
    assert proof['builderSHA256'] == r.sha(B / 'sleeping-root-build.py')
    manifest = B / 'large-map/source-manifest.json'
    receipt = B.parent / 'state/deployment-v090.json'
    assert r.sha(manifest) == proof['productionSourceManifestSHA256']
    assert r.sha(receipt) == proof['productionReceiptSHA256']
    source_manifest = r.read(manifest)
    deployment = r.read(receipt)
    assert deployment['status'] == 'verified' and deployment['after'][CS_PATH] == FORMAL_CS
    assert set(tree_hashes(OUT / 'source')) == set(proof['sourceClosure'])
    assert set(tree_hashes(OUT / 'original-source')) == set(proof['sourceClosure'])
    for name in proof['sourceClosure']:
        original, modified = OUT / 'original-source' / name, OUT / 'source' / name
        assert r.sha(original) == proof['before'][name] == source_manifest['mods\\ContinuousScene\\src\\' + name]
        assert r.sha(modified) == proof['after'][name]
        reverse = modified.read_bytes().decode('utf-8')
        for edit in reversed(proof['edits'].get(name, [])):
            assert reverse.count(edit['after']) == 1
            reverse = reverse.replace(edit['after'], edit['before'], 1)
        assert reverse.encode('utf-8') == original.read_bytes(), ('Reverse proof', name)
    helper = OUT / 'probe-helper/SceneSleepingRootPresentation.as'
    assert r.sha(helper) == proof['probeHelperSHA256']
    paths = [provenance_path, build_path, manifest, receipt, helper]
    paths.extend(OUT / directory / name for directory in ('source', 'original-source') for name in proof['sourceClosure'])
    for entry in build['builds']:
        output = Path(entry['output'])
        assert output.parent.resolve() == OUT.resolve()
        assert r.sha(output) == entry['sha256']
        config, log = OUT / (entry['name'] + '.xml'), OUT / (entry['name'] + '-compile.log')
        assert r.sha(config) == entry['configSHA256'] and r.sha(log) == entry['compilerLogSHA256']
        paths.extend((output, config, log))
    assert r.sha(OUT / 'ContinuousSceneMod.swf') == CANDIDATE_SHA
    return {str(p): r.sha(p) for p in paths}


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
    assert r.sha(frozen / HELPER) == r.read(OUT / 'source-provenance.json')['probeHelperSHA256']
    probe_source = (frozen / 'ContinuousSceneMotionProbe.as').read_text(encoding='utf-8-sig')
    for token in ('SceneSleepingRootPresentation', 'sleepingRoots.verify(w)', 'sleepingRootCleanup',
                  'row.sleepingRoots', 'phase==89', 'sleepingRoots.update(w,true);phase=89;age=0;return;'):
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
    lease.before_launch('Sleeping root frozen probe compiler')
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
    assert scripts == runner_inputs() and compiler == compiler_inputs() and candidate == candidate_inputs()
    assert baseline == r.baseline(), 'Production drift during compile'
    receipt = dict(version='sleeping-root-probe-1', capturedAt=datetime.now().astimezone().isoformat(),
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
    assert probe['version'] == 'sleeping-root-probe-1'
    assert not probe['deployed'] and not probe['performanceAcceptance'] and probe['diagnosticOnly']
    assert probe['sharedSourceSnapshotSHA256'] == probe['frozenSourceSHA256']
    assert tree_hashes(Path(probe['frozenSourcePath'])) == probe['frozenSourceSHA256']
    assert r.sha(Path(probe['frozenSourcePath']) / HELPER) == r.read(OUT / 'source-provenance.json')['probeHelperSHA256']
    assert r.sha(Path(probe['probePath'])) == probe['probeSHA256']
    assert r.sha(Path(probe['configPath'])) == probe['configSHA256']
    assert r.sha(path.parent / 'compile.log') == probe['compilerLogSHA256']
    assert probe['runnerInputs'] == scripts and probe['compilerInputs'] == compiler
    assert probe['candidateInputs'] == candidate and probe['productionSHA256'] == baseline
    return probe


def six_armed(encounter):
    assert encounter['alive'] == encounter['armed'] == len(encounter['actors']) == 6
    assert all(a['hp'] > 0 and a['weapon'] and a['weapon']['hp'] > 0 for a in encounter['actors'])


def metrics(values):
    assert values and all(isinstance(x, (int, float)) and math.isfinite(x) and x >= 0 for x in values)
    return dict(count=len(values), median=statistics.median(values), mean=statistics.mean(values),
        p95=sorted(values)[math.ceil(len(values) * .95) - 1], maximum=max(values), over100=sum(x > 100 for x in values))


def check_stats(stats):
    assert stats['version'] == 'sleeping-root-probe-1'
    assert stats['diagnosticOnly'] and not stats['performanceAcceptance']
    assert stats['valid'] and stats['errors'] == stats['abandoned'] == 0 and not stats['conflicts']
    for key in COUNTERS + ('pendingRestore', 'parkedUnits', 'parkingChildren', 'maxCallbackMs'):
        value = stats[key]
        assert isinstance(value, (int, float)) and not isinstance(value, bool)
        assert math.isfinite(value) and value >= 0 and int(value) == value, (key, value)
    assert stats['changed'] == stats['restored'] + stats['abandoned'] + stats['pendingRestore']
    assert stats['pendingRestore'] == stats['parkingChildren'] and not stats['parkingOnStage']
    assert stats['restoreBeforeWake'] <= stats['wakeCalls']
    assert stats['maxCallbackMs'] <= stats['callbackMs']


def summarize(result, name, timing):
    cfg, route = result['config'], result['combatRoute']
    assert cfg['benchmark'] == 'scene' and cfg['sleepingRootCheck'] == (not timing)
    assert cfg['drawControl'] == ('sleepingroots' if timing else None)
    assert cfg['noLighting'] and cfg['noWall'] and not cfg['vision']
    assert cfg['fixedEnemies'] and not cfg['localEnemies'] and cfg['stableMotion'] and cfg['playerFire']
    assert result['driver']['stableMotion']
    assert result['driver']['perFrameMethod'] == 'Unit.setPos (position/bounds/target only)'
    assert result['world']['layoutSeed'] == 20261019
    assert (result['world']['width'], result['world']['height']) == (240, 125)
    assert result['viewport']['stageWidth'] == result['viewport']['cameraWidth'] == 2032
    assert result['viewport']['stageHeight'] == result['viewport']['cameraHeight'] == 1084
    assert result['viewport']['zoom'] == 1
    assert route['path'] == route['evidence']['playerPath'] == 200
    assert route['evidence']['version'] == 'existing-flat-combat-route-1' and route['evidence']['selected']
    assert route['checkedNativeSightLines'] == 30 and len(route['enemies']) == 6 and route['enemySpacing'] == 80
    assert result['path']['speed'] == 4 and result['path']['endX'] - result['path']['startX'] == 200
    warmup = result['playerFireWarmup']
    assert warmup['frames'] >= 100 and warmup['quietWarmFrames'] >= 100 and warmup['shotFrames'] >= 5
    assert warmup['encounter']['actualShotFrames'] > 0
    six_armed(warmup['encounter'])
    assert len(result['samples']) == 4
    summary = dict(name=name, mode='timing' if timing else 'check', diagnosticOnly=True,
        performanceEligible=False, performanceAcceptance=False, deployed=False, checks=len(result['assertions']),
        driver=result['driver'], world=result['world'], viewport=result['viewport'], combatRoute=route,
        path=result['path'], playerFire=result['playerFire'], playerFireWarmup=warmup,
        encounterInitial=result['encounter'], limitations=LIMITATIONS, samples=[])
    previous = {key: 0 for key in COUNTERS}
    arm_frames = {'A': [], 'B': []}
    for ri, row in enumerate(result['samples']):
        enabled = timing and ri in (1, 2)
        assert row['name'] == (TIMING_CASES if timing else CHECK_CASES)[ri]
        assert len(row['frames']) == len(row['nativeBand']) == len(row['warm']) == 300
        assert row['empty'] == row['misses'] == 0
        assert len(row['totalScript']) in ((299, 300) if ri == 0 else (300,))
        assert row['enemyShotFrames'] > 0 and row['playerShotFrames'] > 0
        six_armed(row['encounter'])
        assert len(row['combatWindows']) == 20
        windows = []
        for wi in range(10):
            pair = sorted((x for x in row['combatWindows'] if x['frame'] // 30 == wi), key=lambda x: x['frame'])
            assert len(pair) == 2 and [x['frame'] for x in pair] == [wi * 30, wi * 30 + 29]
            for observation in pair:
                six_armed(observation['encounter'])
            player = pair[1]['playerShots'] - pair[0]['playerShots']
            enemy = pair[1]['encounter']['actualShotFrames'] - pair[0]['encounter']['actualShotFrames']
            assert player > 0 and enemy >= 0
            windows.append(dict(window=wi, playerShots=player, enemyShots=enemy, population=pair))
        item = dict(index=ri, name=row['name'], enabled=enabled,
            allFrames=metrics(row['frames']), totalScript=metrics(row['totalScript'][1:]),
            playerShots=row['playerShotFrames'], enemyShots=row['enemyShotFrames'],
            camera=row['camera'], activity=row['activity'], encounterEnd=row['encounter'],
            combatWindows=windows, quietEnemyWindows=sum(w['enemyShots'] == 0 for w in windows))
        if timing:
            stats = row['sleepingRoots']
            check_stats(stats)
            delta = {key: stats[key] - previous[key] for key in COUNTERS}
            assert all(value >= 0 for value in delta.values()), 'Counters reset during ABBA'
            assert stats['enabled'] == enabled
            if enabled:
                assert stats['pendingRestore'] > 0 and stats['parkedUnits'] > 0
                assert delta['callbacks'] > 0 and delta['sleepCalls'] > 0
            else:
                assert stats['pendingRestore'] == stats['parkedUnits'] == 0
            previous = {key: stats[key] for key in COUNTERS}
            frames = row['frames'][1:]
            arm_frames['B' if enabled else 'A'].extend(frames)
            item.update(arm='B' if enabled else 'A', excludedSwitchFrames=1,
                measuredFrames=metrics(frames), sleepingRoots=stats, counterDelta=delta,
                callbackCostPer300Frames=delta['callbackMs'] / 300,
                callbackCostPerCall=delta['callbackMs'] / delta['callbacks'] if delta['callbacks'] else None)
        summary['samples'].append(item)
    cleanup = result['sleepingRootCleanup']
    check_stats(cleanup)
    assert not cleanup['enabled'] and cleanup['pendingRestore'] == cleanup['parkedUnits'] == 0
    assert cleanup['changed'] > 0, 'Detachment was never exercised'
    assert all(cleanup[key] >= previous[key] for key in COUNTERS)
    summary['cleanup'] = cleanup
    if timing:
        assert 'sleepingRootVerification' not in result, 'Terminal wake must not contaminate ABBA'
        summary['arms'] = {arm: metrics(values) for arm, values in arm_frames.items()}
        summary['observedMedianDifferenceMs'] = summary['arms']['A']['median'] - summary['arms']['B']['median']
    else:
        verification = result['sleepingRootVerification']
        assert verification['version'] == 'sleeping-root-pixels-1' and verification['terminalOnly']
        assert verification['passed'] and verification['valid'] and verification['equal'] and verification['restoredEqual']
        assert verification['detached']['changedPixels'] == verification['restored']['changedPixels'] == 0
        assert verification['parked']['pendingRestore'] > 0
        check_stats(verification['parked'])
        check_stats(verification['cleanup'])
        wake = verification['zeroClipsWake']
        assert wake['status'] in ('passed', 'inconclusive')
        assert verification['complete'] == (wake['status'] == 'passed')
        if wake['status'] == 'passed':
            assert wake['nativeClips'] == 0 and wake['wasParked'] and wake['callbackRestored']
            assert wake['restoredBeforeResume'] and wake['restoredParents'] and wake['sleepEntryRemoved']
        summary['verification'] = verification
    return summary


def main():
    if not __debug__:
        raise RuntimeError('This diagnostic runner requires assertions; do not use -O')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--timing', action='store_true')
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--compile-probe', action='store_true')
    source.add_argument('--probe-build', type=Path)
    parser.add_argument('--check-evidence', help='Passed terminal-check evidence name required before ABBA')
    parser.add_argument('--registry-wait', type=int, default=600)
    args = parser.parse_args()
    assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
    assert not (r.E / args.name).exists(), 'Use a fresh evidence name'
    assert not args.timing or (args.check_evidence and args.probe_build), 'Timing must reuse the checked frozen probe'
    if args.check_evidence:
        assert all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.check_evidence)
    with m.Registration(owner='ContinuousScene / sleeping roots diagnostic / 01a13816',
            purpose=args.name, run_dir=m.RUNTIME, evidence=r.E / args.name, wait=args.registry_wait) as lease:
        assert not m.air_pids(), 'Other AIR present; untouched'
        baseline, scripts, compiler, candidate = r.baseline(), runner_inputs(), compiler_inputs(), candidate_inputs()
        assert baseline['pfe.swf'] == FORMAL_HOST and baseline[CS_PATH] == FORMAL_CS
        build_path = compile_frozen_probe(lease, baseline, scripts, compiler, candidate) if args.compile_probe else args.probe_build.resolve()
        probe = verify_probe(build_path, baseline, scripts, compiler, candidate)
        if args.timing:
            checked, checked_inputs = r.result(args.check_evidence)
            checked_summary = r.read(r.E / args.check_evidence / 'summary.json')
            assert checked_summary['mode'] == 'check' and checked_summary['verification']['passed']
            assert checked_inputs[CS_PATH] == CANDIDATE_SHA and checked_inputs[PROBE_PATH] == probe['probeSHA256']
            assert checked['sleepingRootVerification']['equal'] and checked['sleepingRootVerification']['restoredEqual']
            check_record = r.read(r.E / args.check_evidence / 'runner-inputs.json')
            assert check_record['baseline'] == baseline and check_record['candidateInputs'] == candidate
        m.prepare()
        shutil.copy2(OUT / 'ContinuousSceneMod.swf', m.RUNTIME / CS_PATH)
        shutil.copy2(probe['probePath'], m.RUNTIME / PROBE_PATH)
        assert r.sha(m.RUNTIME / 'pfe.swf') == FORMAL_HOST and r.sha(m.RUNTIME / CS_PATH) == CANDIDATE_SHA
        assert r.sha(m.RUNTIME / PROBE_PATH) == probe['probeSHA256']
        assert baseline == r.baseline() and scripts == runner_inputs() and compiler == compiler_inputs()
        assert candidate == candidate_inputs()
        verify_probe(build_path, baseline, scripts, compiler, candidate)
        options = ['--name', args.name, '--high-qos', '--land', 'random_mane', '--encounter', '--fixed-enemies',
            '--benchmark', 'scene', '--speed', '4', '--short', '--stable-motion', '--player-fire',
            '--combat-route', '--combat-route-length', '200', '--window-width', '2048', '--window-height', '1123',
            '--no-lighting', '--no-wall', '--expect-no-signs']
        options.extend(['--draw-control', 'sleepingroots'] if args.timing else ['--sleeping-root-check'])
        m.run_owned(m.parse_args(options), lease)
        result, inputs = r.result(args.name)
        assert baseline == r.baseline(), 'Production drift'
        assert scripts == runner_inputs() and compiler == compiler_inputs() and candidate == candidate_inputs()
        verify_probe(build_path, baseline, scripts, compiler, candidate)
        for path, digest in baseline.items():
            if path not in ('application.xml', 'mods/loader-manifest.txt', CS_PATH):
                assert inputs[path] == digest, path
        assert inputs[CS_PATH] == CANDIDATE_SHA and inputs[PROBE_PATH] == probe['probeSHA256']
        policy = r.read(r.E / args.name / 'process-policy.json')
        assert policy['performanceEligible'] is False
        assert not policy.get('runFailure') and not policy.get('memoryAbort') and not policy.get('otherAirProcessIds')
        r.save(r.E / args.name / 'probe-build.json', probe)
        r.save(r.E / args.name / 'candidate-build.json', r.read(OUT / 'build.json'))
        r.save(r.E / args.name / 'runner-inputs.json', dict(options=options, baseline=baseline,
            checkEvidence=args.check_evidence, probeBuildPath=str(build_path), runnerInputs=scripts,
            compilerInputs=compiler, candidateInputs=candidate))
        summary = summarize(result, args.name, args.timing)
        summary.update(probeBuildPath=str(build_path), hostSHA256=FORMAL_HOST,
            baselineContinuousSceneSHA256=FORMAL_CS, candidateContinuousSceneSHA256=CANDIDATE_SHA)
        r.save(r.E / args.name / 'summary.json', summary)
        print(json.dumps(dict(name=args.name, mode=summary['mode'], probeBuildPath=str(build_path),
            arms=summary.get('arms'), verification=summary.get('verification'),
            cleanup=summary['cleanup'], performanceEligible=False, performanceAcceptance=False, deployed=False)), flush=True)
        lease.outcome = 'passed'
        lease.note = 'Sleeping root ' + summary['mode'] + ' diagnostic captured; no production acceptance or deployment'


if __name__ == '__main__':
    main()
