"""Native-input r3 sleeping-root diagnostic. Check pixels before short ABBA.

Only a frozen probe source copy receives the reviewed r3 helper. The native CS
candidate is the already frozen r2 binary; no live AS or production file changes.
"""
from pathlib import Path
from datetime import datetime
from xml.sax.saxutils import escape
from types import SimpleNamespace
import argparse
import contextlib
import io
import importlib.util
import json
import math
import shutil
import subprocess
import sys
import uuid

sys.dont_write_bytecode = True
B = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base = load('native_input_r3_base', B / 'native-input-combat-run.py')
builder = load('native_input_r3_builder', B / 'sleeping-root-r3-build.py')
r, m, support = base.r, base.m, base.support
OUT = B / 'generated/native-input-r3-20261023'
HELPER = base.HELPER
HELPER_SOURCE = builder.OUT / 'probe-helper/SceneSleepingRootPresentation.as'
HELPER_SHA = '210DD1BF60EBAA0D2AED2E1F8513D50F3FE9243AF3398353B7D31B096409B8A5'
PROOF_SHA = '7EFEFC2130F56B37095F2084419017AE6EEEEA12B19C4E8E84D7302C1B0FDF26'
BUILDER_SHA = 'A924F632662F2412D358FA6CAFE33708348046A5021130EACA1F7DA6DB82CB5D'
ALLOWED = ['fe.unit::' + name for name in ('UnitRaider', 'UnitSlaver') + builder.CLASSES]


def runner_inputs():
    values = base.runner_inputs()
    values[str(Path(__file__))] = r.sha(Path(__file__))
    values[str(B / 'sleeping-root-r3-build.py')] = BUILDER_SHA
    return values


def candidate_inputs():
    assert r.sha(B / 'sleeping-root-r3-build.py') == BUILDER_SHA
    assert r.sha(builder.OUT / 'source-provenance.json') == PROOF_SHA
    assert r.sha(HELPER_SOURCE) == HELPER_SHA
    # This verifies r2 native source ancestry and the reversible r3 helper diff.
    # No r2 pixel result is treated as evidence of r3 pixel equivalence.
    with contextlib.redirect_stdout(io.StringIO()):
        builder.check()
    values = support.candidate_inputs()
    proof = r.read(builder.OUT / 'source-provenance.json')
    values.update(proof['sourceReferences']['inputs'])
    for path in (B / 'sleeping-root-r3-build.py', builder.OUT / 'source-provenance.json', HELPER_SOURCE):
        values[str(path)] = r.sha(path)
    return values


def check_stats(stats):
    assert stats['version'] == 'sleeping-root-probe-3'
    assert stats['diagnosticOnly'] and not stats['performanceAcceptance']
    assert stats['allowedClasses'] == ALLOWED
    assert set(stats['claimEventsByClass']) <= set(ALLOWED)
    assert sum(stats['claimEventsByClass'].values()) == stats['claimedUnits']
    assert stats['valid'] and stats['errors'] == stats['abandoned'] == 0 and not stats['conflicts']
    for key in support.COUNTERS + ('pendingRestore', 'parkedUnits', 'parkingChildren', 'maxCallbackMs'):
        value = stats[key]
        assert isinstance(value, (int, float)) and not isinstance(value, bool)
        assert math.isfinite(value) and value >= 0 and int(value) == value, (key, value)
    assert stats['changed'] == stats['restored'] + stats['pendingRestore'] + stats['abandoned']
    assert stats['pendingRestore'] == stats['parkingChildren'] and not stats['parkingOnStage']
    assert stats['restoreBeforeWake'] <= stats['wakeCalls'] and stats['maxCallbackMs'] <= stats['callbackMs']


# Reuse unchanged native movement/combat validation; only helper snapshot version
# and the explicitly reviewed class list differ from the r2 measurement runner.
base.check_sleeping_stats = check_stats


def compile_probe(lease, baseline, scripts, compiler, candidate):
    assert not m.air_pids(), 'Other AIR present; untouched'
    memory = m.memory_status()
    assert memory['availableCommit'] >= 1024**3 and memory['availablePhysical'] >= 1.5 * 1024**3
    source = B.parent / 'src'
    captured = base.tree_hashes(source)
    folder = OUT / 'probe-source' / uuid.uuid4().hex
    frozen = folder / 'src'
    folder.mkdir(parents=True, exist_ok=False)
    shutil.copytree(source, frozen)
    assert captured == base.tree_hashes(source) == base.tree_hashes(frozen)
    assert captured[HELPER] == builder.R2_HELPER, 'Unexpected live helper; no implicit WIP merge'
    shutil.copy2(HELPER_SOURCE, frozen / HELPER)
    after = base.tree_hashes(frozen)
    expected = dict(captured)
    expected[HELPER] = HELPER_SHA
    assert after == expected and r.sha(HELPER_SOURCE) == HELPER_SHA
    override = dict(relativePath=HELPER, beforeSHA256=captured[HELPER], afterSHA256=HELPER_SHA,
        pinnedSourcePath=str(HELPER_SOURCE), pinnedSourceSHA256=HELPER_SHA,
        sourceProvenancePath=str(builder.OUT / 'source-provenance.json'), sourceProvenanceSHA256=PROOF_SHA)
    probe_source = (frozen / 'ContinuousSceneMotionProbe.as').read_text('utf-8-sig')
    for token in ('nativeInputMotion', 'sleepingRootShort', 'sleepingRootEarlyCheck', 'sleepingRoots.verify(w)', 'phase==89', 'sleepingRootCleanup'):
        assert token in probe_source, token
    snapshot = dict(sharedSourcePath=str(source), sharedSourceSnapshotSHA256=captured,
        frozenSourcePath=str(frozen), frozenSourceSHA256=after, sourceOverride=override)
    r.save(folder / 'source-snapshot.json', snapshot)
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
    lease.before_launch('Native-input r3 frozen probe compiler')
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
    assert after == base.tree_hashes(frozen)
    assert scripts == runner_inputs() and compiler == support.compiler_inputs()
    assert candidate == candidate_inputs() and baseline == r.baseline()
    receipt = dict(snapshot, version='native-input-r3-probe-1', capturedAt=datetime.now().astimezone().isoformat(),
        probePath=str(output), probeSHA256=r.sha(output), configPath=str(config), configSHA256=r.sha(config),
        command=command, compilerLogSHA256=r.sha(folder / 'compile.log'), runnerInputs=scripts,
        compilerInputs=compiler, candidateInputs=candidate, productionSHA256=baseline,
        diagnosticOnly=True, deployed=False, performanceAcceptance=False)
    path = folder / 'probe-build.json'
    r.save(path, receipt)
    print(json.dumps({'frozenProbeBuild': str(path), 'reuse': '--probe-build ' + str(path)}), flush=True)
    return path


def verify_probe(path, baseline, scripts, compiler, candidate):
    probe = r.read(path)
    assert probe['version'] == 'native-input-r3-probe-1' and probe['diagnosticOnly']
    assert not probe['deployed'] and not probe['performanceAcceptance']
    expected = dict(probe['sharedSourceSnapshotSHA256'])
    assert expected[HELPER] == builder.R2_HELPER
    expected[HELPER] = HELPER_SHA
    assert expected == probe['frozenSourceSHA256'] == base.tree_hashes(Path(probe['frozenSourcePath']))
    override = probe['sourceOverride']
    assert override['relativePath'] == HELPER and override['beforeSHA256'] == builder.R2_HELPER
    assert override['afterSHA256'] == override['pinnedSourceSHA256'] == HELPER_SHA
    assert Path(override['pinnedSourcePath']).resolve() == HELPER_SOURCE.resolve()
    assert override['sourceProvenanceSHA256'] == PROOF_SHA
    assert r.sha(Path(probe['probePath'])) == probe['probeSHA256']
    assert r.sha(Path(probe['configPath'])) == probe['configSHA256']
    assert r.sha(path.parent / 'compile.log') == probe['compilerLogSHA256']
    assert probe['runnerInputs'] == scripts and probe['compilerInputs'] == compiler
    assert probe['candidateInputs'] == candidate and probe['productionSHA256'] == baseline
    return probe


def verification(result):
    verify = result['sleepingRootVerification']
    assert verify['version'] == 'sleeping-root-pixels-3' and verify['terminalOnly']
    assert verify['passed'] and verify['valid'] and verify['equal'] and verify['restoredEqual']
    assert verify['detached']['changedPixels'] == verify['restored']['changedPixels'] == 0
    check_stats(verify['parked'])
    assert verify['parked']['pendingRestore'] > 0
    check_stats(verify['cleanup'])
    wake = verify['zeroClipsWake']
    assert verify['complete'] and wake['status'] == 'passed', 'Real zero-clips wake must pass before timing'
    assert wake['nativeClips'] == 0 and wake['wasParked'] and wake['callbackRestored']
    assert wake['restoredBeforeResume'] and wake['restoredParents'] and wake['sleepEntryRemoved']
    cleanup = result['sleepingRootCleanup']
    check_stats(cleanup)
    assert cleanup['changed'] > 0 and not cleanup['enabled']
    assert cleanup['pendingRestore'] == cleanup['parkedUnits'] == 0
    return verify


def summarize_early(result, name):
    """Lifecycle/pixels check only; no timed combat or warmup-shot requirement."""
    cfg, motion, driver = result['config'], result['nativeInputMotion'], result['driver']
    assert cfg['benchmark'] == 'scene' and cfg['sleepingRootCheck'] and cfg['sleepingRootEarlyCheck']
    assert not cfg['sleepingRootShort'] and cfg['drawControl'] is None
    assert cfg['nativeInputMotion'] and cfg['stableMotion'] and not cfg['nativeSprint']
    assert cfg['fixedEnemies'] and not cfg['localEnemies']
    assert cfg['noLighting'] and cfg['noWall'] and not cfg['vision']
    assert driver['nativeInputMotion'] and driver['stableMotion'] and driver['forcedPositionCalls'] == 0
    assert driver['perFrameMethod'] == 'Ctr.keyLeft/keyRight; native acceleration, vertical physics and collision'
    assert motion['version'] == 'native-input-motion-3' and motion['enabled'] and motion['diagnosticFixture']
    assert motion['spawn']['calls'] == 1 and not result['samples']
    assert result['world']['layoutSeed'] == 20261019
    assert (result['world']['width'], result['world']['height']) == (240, 125)
    view = result['viewport']
    assert view['stageWidth'] == view['cameraWidth'] == 2032
    assert view['stageHeight'] == view['cameraHeight'] == 1084 and view['zoom'] == 1
    route = motion['route']
    assert route['terrainVerified'] and route['nativeSightLines'] == 30
    base.check_motion_bucket(motion['warmup'], route)
    assert motion['warmup']['floorContactSamples'] >= 10
    early = result['sleepingRootEarlyCheck']
    assert early['version'] == 'sleeping-root-early-check-1' and early['diagnosticOnly']
    assert early['groundContactRun'] >= 10
    base.check_motion_state(early['startPose'], route)
    assert early['startPose']['floorContact'] is True
    assert early['requiredHoldFrames'] == early['nativeHeldFrames'] == 10
    assert len(early['holdSamples']) == 10
    previous = {key: 0 for key in support.COUNTERS}
    for frame, sample in enumerate(early['holdSamples'], 1):
        assert sample['frame'] == frame
        stats = sample['snapshot']
        check_stats(stats)
        assert stats['enabled']
        assert all(stats[key] >= previous[key] for key in support.COUNTERS)
        previous = {key: stats[key] for key in support.COUNTERS}
    assert any(s['snapshot']['pendingRestore'] > 0 for s in early['holdSamples'])
    assert previous['callbacks'] > 0 and previous['changed'] > 0
    verified = verification(result)
    assert all(result['sleepingRootCleanup'][key] >= previous[key] for key in support.COUNTERS)
    return dict(version='native-input-r3-summary-1', name=name, runKind='check', earlyCheck=True,
        diagnosticOnly=True, performanceEligible=False, performanceAcceptance=False, deployed=False,
        checks=len(result['assertions']), helperSHA256=HELPER_SHA, helperSourceProvenanceSHA256=PROOF_SHA,
        driver=driver, world=result['world'], viewport=view, nativeInputMotion=motion,
        early=early, verification=verified, cleanup=result['sleepingRootCleanup'], samples=[],
        limitations=['No combat timing or sustained movement acceptance.',
            'Ten future native frames check lifecycle ownership; final same-frame pixels compare presentation only.',
            'The final real zero-clips wake changes one engaged latch; exit without saving.'])


def summarize(result, args):
    assert result['config']['sleepingRootCheck'] == args.check
    assert bool(result['config']['sleepingRootShort']) == args.short_interleave
    assert bool(result['config'].get('sleepingRootEarlyCheck')) == args.early_check
    if args.early_check:
        return summarize_early(result, args.name)
    # The common validator checks only measured native-input segments. Present a
    # shallow config view with terminal-check flag removed; separately validate
    # that actual terminal check above and its complete r3 result below.
    measured = dict(result, config=dict(result['config'], sleepingRootCheck=False))
    common = SimpleNamespace(name=args.name, mode='scene', candidate='sleepingroots-r3',
        draw_control=None if args.check else 'sleepingroots', native_sprint=False,
        short_interleave=args.short_interleave)
    summary = base.summarize(measured, common)
    summary.update(version='native-input-r3-summary-1', runKind='check' if args.check else 'timing', earlyCheck=False,
        helperSHA256=HELPER_SHA, helperSourceProvenanceSHA256=PROOF_SHA)
    if args.check:
        summary['verification'] = verification(result)
        summary['cleanup'] = result['sleepingRootCleanup']
    return summary


def prior_check(name, probe, baseline, candidate):
    result, inputs = r.result(name)
    folder = r.E / name
    summary, record = r.read(folder / 'summary.json'), r.read(folder / 'runner-inputs.json')
    assert summary['version'] == 'native-input-r3-summary-1' and summary['runKind'] == 'check'
    assert summary['helperSHA256'] == HELPER_SHA and summary['verification']['complete']
    assert result['config']['nativeInputMotion'] and result['config']['sleepingRootCheck']
    assert not result['config']['sleepingRootShort']
    verification(result)
    if result['config'].get('sleepingRootEarlyCheck'):
        assert summary['earlyCheck'] is True
        summarize_early(result, name)
    assert inputs[base.CS_PATH] == base.CANDIDATE_SHA and inputs[base.PROBE_PATH] == probe['probeSHA256']
    assert r.read(folder / 'probe-build.json') == probe
    assert record['baseline'] == baseline and record['candidateInputs'] == candidate
    assert record['runnerInputs'] == runner_inputs()
    return {str(folder / path): r.sha(folder / path) for path in
        ('storage/result.json', 'inputs.json', 'summary.json', 'runner-inputs.json', 'probe-build.json', 'process-policy.json')}


def main():
    if not __debug__:
        raise RuntimeError('Assertions required; do not use -O')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--check', action='store_true')
    modes.add_argument('--short-interleave', action='store_true')
    parser.add_argument('--early-check', action='store_true', help='Only with --check: check pixels after native landing and ten held frames')
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--compile-probe', action='store_true')
    source.add_argument('--probe-build', type=Path)
    parser.add_argument('--check-evidence')
    parser.add_argument('--registry-wait', type=int, default=600)
    args = parser.parse_args()
    for name in (args.name, args.check_evidence):
        if name is not None:
            assert name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in name)
    assert not (r.E / args.name).exists(), 'Preserve existing evidence'
    assert not args.early_check or args.check, '--early-check is only valid with --check'
    assert args.check or (args.probe_build and args.check_evidence), 'Timing must reuse its successful r3 checked probe'
    with m.Registration(owner='ContinuousScene / native input r3 / 01a13816', purpose=args.name,
            run_dir=m.RUNTIME, evidence=r.E / args.name, wait=args.registry_wait) as lease:
        assert not m.air_pids(), 'Other AIR present; untouched'
        baseline, scripts, compiler, candidate = r.baseline(), runner_inputs(), support.compiler_inputs(), candidate_inputs()
        assert baseline['pfe.swf'] == base.FORMAL_HOST and baseline[base.CS_PATH] == base.FORMAL_CS
        build_path = compile_probe(lease, baseline, scripts, compiler, candidate) if args.compile_probe else args.probe_build.resolve()
        probe = verify_probe(build_path, baseline, scripts, compiler, candidate)
        check_inputs = prior_check(args.check_evidence, probe, baseline, candidate) if args.short_interleave else {}
        m.prepare()
        shutil.copy2(support.OUT / 'ContinuousSceneMod.swf', m.RUNTIME / base.CS_PATH)
        shutil.copy2(probe['probePath'], m.RUNTIME / base.PROBE_PATH)
        assert r.sha(m.RUNTIME / 'pfe.swf') == base.FORMAL_HOST
        assert r.sha(m.RUNTIME / base.CS_PATH) == base.CANDIDATE_SHA
        assert r.sha(m.RUNTIME / base.PROBE_PATH) == probe['probeSHA256']
        assert baseline == r.baseline() and scripts == runner_inputs() and compiler == support.compiler_inputs()
        assert candidate == candidate_inputs()
        options = ['--name', args.name, '--high-qos', '--land', 'random_mane', '--encounter', '--fixed-enemies',
            '--benchmark', 'scene', '--speed', '4', '--short', '--stable-motion', '--native-input-motion', '--player-fire',
            '--combat-route', '--combat-route-length', '200', '--window-width', '2048', '--window-height', '1123',
            '--no-lighting', '--no-wall', '--expect-no-signs']
        options += ['--sleeping-root-check'] if args.check else ['--draw-control', 'sleepingroots', '--sleeping-root-short']
        if args.early_check:
            options += ['--sleeping-root-early-check']
        m.run_owned(m.parse_args(options), lease)
        result, inputs = r.result(args.name)
        assert baseline == r.baseline() and scripts == runner_inputs() and compiler == support.compiler_inputs()
        assert candidate == candidate_inputs()
        verify_probe(build_path, baseline, scripts, compiler, candidate)
        assert all(r.sha(Path(path)) == digest for path, digest in check_inputs.items())
        for path, digest in baseline.items():
            if path not in ('application.xml', 'mods/loader-manifest.txt', base.CS_PATH):
                assert inputs[path] == digest, path
        assert inputs[base.CS_PATH] == base.CANDIDATE_SHA and inputs[base.PROBE_PATH] == probe['probeSHA256']
        policy = r.read(r.E / args.name / 'process-policy.json')
        assert policy['performanceEligible'] is False
        assert not policy.get('runFailure') and not policy.get('memoryAbort') and not policy.get('otherAirProcessIds')
        r.save(r.E / args.name / 'probe-build.json', probe)
        r.save(r.E / args.name / 'runner-inputs.json', dict(options=options, baseline=baseline, runnerInputs=scripts,
            compilerInputs=compiler, candidateInputs=candidate, checkEvidence=args.check_evidence,
            checkEvidenceSHA256=check_inputs, probeBuildPath=str(build_path)))
        summary = summarize(result, args)
        summary.update(probeBuildPath=str(build_path), hostSHA256=base.FORMAL_HOST,
            baselineContinuousSceneSHA256=base.FORMAL_CS, actualContinuousSceneSHA256=base.CANDIDATE_SHA)
        r.save(r.E / args.name / 'summary.json', summary)
        print(json.dumps(dict(name=args.name, runKind=summary['runKind'], probeBuildPath=str(build_path),
            arms=summary.get('armsIncludingSwitchOverhead'), verification=summary.get('verification'),
            blocks=summary.get('blocksIncludingSwitchOverhead'), performanceEligible=False, deployed=False)), flush=True)
        lease.outcome = 'passed'
        lease.note = 'Native-input r3 diagnostic complete; no deployment or production performance acceptance'


if __name__ == '__main__':
    main()
