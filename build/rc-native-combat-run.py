"""Independent-process RC comparison with one unchanged native-input probe.

The baseline is formal 574D. A candidate needs explicit source/compile/SWF
fingerprints, not a prior runtime acceptance. No RC diagnostic API is used.
This runner never builds RC, changes production files, or accepts a release.
"""
from pathlib import Path
import argparse
import json
import shutil

import importlib.util
import sys
sys.dont_write_bytecode = True
B = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('rc_native_timing_support', B / 'rc-offline-combat-run.py')
timing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(timing)
base, r, m, support = timing.base, timing.r, timing.m, timing.support
OUT = B / 'generated/rc-native-combat-20261023'
RC_PATH = timing.RC_PATH
FORMAL_RC = '574D2B51490AE8B25A1396555600F56A301F8A20AE50104C0E35CF2796441AFE'


def runner_inputs():
    values = timing.original_runner_inputs()
    for path in (Path(__file__), B / 'rc-offline-combat-run.py', B / 'rc-offline-probe-build.py'):
        values[str(path)] = r.sha(path)
    return values


def probe_inputs():
    # The CS probe does not compile against either RC binary. Keep this input
    # identical for both processes so the exact same frozen SWF can be reused.
    path = support.OUT / 'source-provenance.json'
    assert r.sha(path) == support.PROVENANCE_SHA
    return {str(path): support.PROVENANCE_SHA}


base.OUT, base.runner_inputs, base.candidate_inputs = OUT, runner_inputs, probe_inputs


def verify_probe(path, baseline, scripts, compiler, inputs):
    probe = base.verify_probe(path, baseline, scripts, compiler, inputs)
    source = (Path(probe['frozenSourcePath']) / 'ContinuousSceneMotionProbe.as').read_text('utf-8-sig')
    for token in ('"rcnative"', '"rc-native-"+rcCase', 'row.caseBeginAtMs=caseBegin',
                  'row.caseEndAtMs=getTimer()', 'if(cfg.drawControl=="rcnative")last=caseBegin',
                  'cfg.drawControl && cfg.drawControl!="rcnative"',
                  'row.continuousFramesMs.push(now-continuousPreviousSampleAt)'):
        assert token in source, ('Missing reviewed noop fixture wiring', token)
    return probe


def candidate_inputs(args):
    names = ('candidate_swf', 'candidate_sha256', 'source_proof', 'source_proof_sha256',
             'compile_receipt', 'compile_receipt_sha256')
    if args.arm == 'baseline':
        assert not any(getattr(args, key) for key in names), 'Baseline uses only deployed formal 574D'
        assert args.candidate_source_root is None
        return {}, r.ROOT / RC_PATH, FORMAL_RC
    assert all(getattr(args, key) for key in names), 'Candidate source, compile receipt and SWF must be explicit'
    paths = [(args.candidate_swf.resolve(), args.candidate_sha256.upper()),
             (args.source_proof.resolve(), args.source_proof_sha256.upper()),
             (args.compile_receipt.resolve(), args.compile_receipt_sha256.upper())]
    for path, digest in paths:
        assert len(digest) == 64 and all(c in '0123456789ABCDEF' for c in digest)
        assert r.sha(path) == digest, path
    swf, proof_path, compile_path = [item[0] for item in paths]
    swf_sha, proof_sha = paths[0][1], paths[1][1]
    assert swf_sha not in (FORMAL_RC, timing.RC_SHA), 'Need the production-form candidate, not the diagnostic carrier'
    proof, compiled = r.read(proof_path), r.read(compile_path)
    # prepared.json records preparation, so its compiled=false is expected.
    # Runtime/multiplayer qualification is deliberately not a prerequisite.
    assert proof['kind'] == 'isolated-offline-production' and proof['base_sha256'].upper() == FORMAL_RC
    assert len(proof['source']) == len(proof['proposal_source']) == 78 and len(proof['inputs']) == 71
    assert proof['compiled'] is False and not proof['air_started'] and not proof['installed']
    source_root = args.candidate_source_root.resolve() if args.candidate_source_root else proof_path.parent
    assert proof_path == source_root / 'prepared.json' and compile_path == source_root / 'compile.json'
    recipe = r.ROOT / 'mods/RConnect/experimental/recovery-offline-production/prepare.py'
    assert r.sha(recipe) == proof['recipe_sha256'].upper()
    reviewer = timing.load('rc_native_production_source_review', recipe)
    assert reviewer.verify(source_root) == proof  # Read-only byte/source/toolchain reconstruction.
    assert compiled['compiled'] is True and compiled['compile_exit'] == 0
    assert compiled['prepared_sha256'].upper() == proof_sha and compiled['candidate_sha256'].upper() == swf_sha
    assert compiled['installation_before'] == compiled['installation_after'] == proof['installation_before']
    assert compiled['installation_unchanged'] and compiled['sources_unchanged']
    assert not compiled['air_started'] and not compiled['installed']
    assert len(compiled['commands']) == 2 and all(c['exit_code'] == 0 and c['reaped'] and c['pid'] > 0 for c in compiled['commands'])
    values = {str(path): digest for path, digest in paths}
    for relative, digest in {**proof['source'], **proof['inputs'], **compiled['artifacts']}.items():
        path = (source_root / relative).resolve()
        assert path.is_relative_to(source_root) and r.sha(path) == digest.upper(), relative
        values[str(path)] = digest.upper()
    for name, digest in proof['toolchain_inputs'].items():
        path = Path(name)
        assert r.sha(path) == digest.upper(), path
        values[str(path)] = digest.upper()
    for path, digest in ((recipe, proof['recipe_sha256']), (recipe.parent / 'README.md', proof['readme_sha256']),
                         (source_root / 'proposal-proof.json', proof['proposal_proof_sha256']),
                         (source_root / 'proposal.patch', proof['proposal_patch_sha256'])):
        assert r.sha(path) == digest.upper(), path
        values[str(path)] = digest.upper()
    return values, swf, swf_sha


def continuous_intervals(result):
    info = result['continuousSampling']
    assert info['version'] == 'motion-continuous-wall-1'
    started = previous = info['startedAtMs']
    assert isinstance(started, int) and started >= 0
    intervals, previous_end = [], None
    assert len(result['samples']) == 20
    for row in result['samples']:
        stamps, values = row['sampleAtMs'], row['continuousFramesMs']
        assert len(stamps) == len(values) == len(row['frames']) == 60
        assert previous <= row['caseBeginAtMs'] <= stamps[0]
        if previous_end is not None:
            assert previous_end <= row['caseBeginAtMs']
        assert row['frames'][0] == stamps[0] - row['caseBeginAtMs']
        for frame, (stamp, interval) in enumerate(zip(stamps, values)):
            assert isinstance(stamp, int) and isinstance(interval, int) and interval >= 0
            assert stamp - previous == interval, 'Continuous interval omitted or reset'
            assert interval >= row['frames'][frame]
            if frame:
                assert interval == row['frames'][frame]
            intervals.append(interval);previous = stamp
        assert row['caseEndAtMs'] >= stamps[-1]
        previous_end = row['caseEndAtMs']
    assert len(intervals) == 1200 and sum(intervals) == previous - started
    return dict(version=info['version'], startedAtMs=started, lastSampleAtMs=previous,
                intervalCount=1200, totalMs=sum(intervals), metrics=base.metrics(intervals))


def summarize(result, name, arm):
    cfg, view, warm = result['config'], result['viewport'], result['playerFireWarmup']
    assert cfg['drawControl'] == 'rcnative' and cfg['benchmark'] == 'scene'
    assert cfg['nativeInputMotion'] and cfg['stableMotion'] and cfg['fixedEnemies'] and cfg['playerFire']
    assert not any(cfg[key] for key in ('localEnemies', 'nativeSprint', 'sleepingRootShort', 'sleepingRootCheck', 'presentationCheck', 'vision'))
    assert cfg['noLighting'] and cfg['noWall']
    assert result['world']['layoutSeed'] == 20261019 and (result['world']['width'], result['world']['height']) == (240, 125)
    assert view['stageWidth'] == view['cameraWidth'] == 2032 and view['stageHeight'] == view['cameraHeight'] == 1084 and view['zoom'] == 1
    assert warm['frames'] >= 100 and warm['quietWarmFrames'] >= 100 and warm['shotFrames'] >= 5
    assert warm['encounter']['actualShotFrames'] > 0
    base.six_armed(warm['encounter'])
    assert not any(key in result for key in ('rcOfflineInitial', 'rcOfflineCleanup'))
    continuous = continuous_intervals(result)
    samples = []
    for index, row in enumerate(result['samples']):
        assert row['name'] == 'rc-native-' + str(index) and 'rcOffline' not in row
        assert len(row['frames']) == len(row['nativeBand']) == len(row['warm']) == 60
        assert len(row['totalScript']) == (59 if index == 0 else 60)
        assert row['empty'] == row['misses'] == 0 and row['playerShotFrames'] > 0 and row['enemyShotFrames'] >= 0
        base.six_armed(row['encounter'])
        samples.append(dict(index=index, continuousIntervals=base.metrics(row['continuousFramesMs']),
            withinSegmentFrames=base.metrics(row['frames']), nativeBand=base.metrics(row['nativeBand']),
            totalScript=base.metrics(row['totalScript']), probeTiming=timing.check_probe_timing(row, index),
            playerShots=row['playerShotFrames'], enemyShots=row['enemyShotFrames'],
            combatWindows=base.combat_windows(row, 60), nativeInput=base.check_native_driver(result, row, index),
            activity=row['activity'], activityEnd=row.get('activityEnd'), activityCensus=row.get('activityCensus'),
            scene=dict(warmed=sum(row['warm']), forced=row.get('forced'), slices=row.get('slices')),
            encounterEnd=row['encounter']))
    engaged = sum(row['enemyShots'] > 0 for row in samples)
    assert engaged >= 16, 'Too few genuine two-way combat windows'
    blocks = []
    for start in range(0, 20, 4):
        assert sum(row['enemyShots'] for row in samples[start:start + 4]) > 0
        blocks.append(dict(block=start // 4,
            continuousIntervals=base.metrics([dt for row in result['samples'][start:start + 4] for dt in row['continuousFramesMs']]),
            playerShots=sum(row['playerShots'] for row in samples[start:start + 4]),
            enemyShots=sum(row['enemyShots'] for row in samples[start:start + 4])))
    return dict(version='rc-native-combat-summary-1', name=name, arm=arm,
        diagnosticOnly=True, performanceEligible=False, performanceAcceptance=False, deployed=False,
        driver=result['driver'], nativeInputMotion=result['nativeInputMotion'], viewport=view,
        world=result['world'], combatRoute=result['combatRoute'], warmup=warm,
        selectedCombatRoomTiles=result['selectedCombatRoomTiles'], selectedCombatCorridorTiles=result['selectedCombatCorridorTiles'],
        continuousSampling=continuous, withinSegmentFrames=base.metrics([dt for row in result['samples'] for dt in row['frames']]),
        samples=samples, blocks=blocks, bothFiringWindows=engaged,
        primaryTiming='Continuous sample-to-sample wall time; no boundary reset or subtraction of probe work',
        limitations=['One RC binary for the whole process, including warmup; no RC probe API or within-process ABBA.',
            'Segment first intervals include the preceding census/save tail; final post-sample cleanup is outside these intervals.',
            'AI and combat randomness are not seeded by the layout seed; population and actual fire can differ between processes.',
            'Observed timing differences are not automatically an exact RC causal estimate or a release acceptance.',
            'Only this scale-1, lights/vision/WallBlend-off scene fixture is covered; multiplayer is not tested.'])


def main():
    if not __debug__:
        raise RuntimeError('Assertions required; do not use -O')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    parser.add_argument('--arm', required=True, choices=['baseline', 'candidate'])
    parser.add_argument('--baseline-evidence', help='Candidate must reference a completed baseline using the same frozen probe')
    for key in ('candidate-swf', 'source-proof', 'compile-receipt', 'candidate-source-root'):
        parser.add_argument('--' + key, type=Path)
    for key in ('candidate-sha256', 'source-proof-sha256', 'compile-receipt-sha256'):
        parser.add_argument('--' + key)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--compile-probe', action='store_true');source.add_argument('--probe-build', type=Path)
    parser.add_argument('--registry-wait', type=int, default=600)
    args = parser.parse_args()
    assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
    folder = r.E / args.name
    assert not folder.exists(), 'Preserve existing evidence'
    assert (args.arm == 'candidate') == bool(args.baseline_evidence)
    assert args.arm != 'candidate' or args.probe_build, 'Reuse the baseline frozen probe'
    with m.Registration(owner='ContinuousScene / RC native processes / 01a13816', purpose=args.name,
            run_dir=m.RUNTIME, evidence=folder, wait=args.registry_wait) as lease:
        assert not m.air_pids(), 'Other AIR present; untouched'
        baseline, scripts, compiler, common = r.baseline(), runner_inputs(), support.compiler_inputs(), probe_inputs()
        assert baseline['pfe.swf'] == base.FORMAL_HOST and baseline[base.CS_PATH] == base.FORMAL_CS and baseline[RC_PATH] == FORMAL_RC
        candidate, target, actual_rc = candidate_inputs(args)
        build_path = base.compile_frozen_probe(lease, baseline, scripts, compiler, common) if args.compile_probe else args.probe_build.resolve()
        probe = verify_probe(build_path, baseline, scripts, compiler, common)
        reference = None
        if args.baseline_evidence:
            assert all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.baseline_evidence)
            reference_folder = r.E / args.baseline_evidence
            r.result(args.baseline_evidence)  # Original result, loader and process-policy gates.
            reference = r.read(reference_folder / 'summary.json')
            previous = r.read(reference_folder / 'runner-inputs.json')
            assert reference['arm'] == 'baseline' and reference['actualRConnectSHA256'] == FORMAL_RC
            assert previous['baseline'] == baseline and previous['runnerInputs'] == scripts and previous['compilerInputs'] == compiler
            assert r.read(reference_folder / 'probe-build.json')['probeSHA256'] == probe['probeSHA256']
        m.prepare()
        shutil.copy2(probe['probePath'], m.RUNTIME / base.PROBE_PATH)
        if args.arm == 'candidate':
            shutil.copy2(target, m.RUNTIME / RC_PATH)
        assert r.sha(m.RUNTIME / 'pfe.swf') == base.FORMAL_HOST and r.sha(m.RUNTIME / base.CS_PATH) == base.FORMAL_CS
        assert r.sha(m.RUNTIME / RC_PATH) == actual_rc and r.sha(m.RUNTIME / base.PROBE_PATH) == probe['probeSHA256']
        assert r.read(m.RUNTIME / 'mods/Rconnect/release/config.txt').get('autoRole', '') not in ('host', 'join')
        options = ['--name', args.name, '--high-qos', '--land', 'random_mane', '--encounter', '--fixed-enemies',
            '--benchmark', 'scene', '--speed', '4', '--short', '--stable-motion', '--native-input-motion', '--player-fire',
            '--combat-route', '--combat-route-length', '200', '--window-width', '2048', '--window-height', '1123',
            '--no-lighting', '--no-wall', '--expect-no-signs', '--draw-control', 'rcnative']
        if reference:
            assert previous['options'][0] == options[0] == '--name' and previous['options'][2:] == options[2:]
        assert baseline == r.baseline() and scripts == runner_inputs() and compiler == support.compiler_inputs()
        assert candidate_inputs(args) == (candidate, target, actual_rc)
        try:
            m.run_owned(m.parse_args(options), lease)
        finally:
            if folder.exists():
                r.save(folder / 'probe-build.json', probe)
                r.save(folder / 'runner-inputs.json', dict(options=options, baseline=baseline, runnerInputs=scripts,
                    compilerInputs=compiler, candidateInputs=candidate, actualRConnectSHA256=actual_rc,
                    probeBuildPath=str(build_path), arm=args.arm, baselineEvidence=args.baseline_evidence))
        assert baseline == r.baseline() and scripts == runner_inputs() and compiler == support.compiler_inputs()
        assert candidate_inputs(args) == (candidate, target, actual_rc)
        verify_probe(build_path, baseline, scripts, compiler, common)
        result, inputs = r.result(args.name)  # Also validates one loader session and all expected mods.
        for path, digest in baseline.items():
            if path not in ('application.xml', 'mods/loader-manifest.txt', RC_PATH):
                assert inputs[path] == digest, path
        assert inputs[RC_PATH] == actual_rc and inputs[base.PROBE_PATH] == probe['probeSHA256']
        policy = r.read(folder / 'process-policy.json')
        assert policy['performanceEligible'] is False and not policy.get('runFailure')
        assert not policy.get('memoryAbort') and not policy.get('otherAirProcessIds')
        summary = summarize(result, args.name, args.arm)
        summary.update(probeBuildPath=str(build_path), hostSHA256=base.FORMAL_HOST,
            actualContinuousSceneSHA256=base.FORMAL_CS, actualRConnectSHA256=actual_rc)
        if reference:
            before, after = reference['continuousSampling']['metrics'], summary['continuousSampling']['metrics']
            summary['comparison'] = dict(baselineEvidence=args.baseline_evidence,
                baselineSummarySHA256=r.sha(reference_folder / 'summary.json'),
                baselineResultSHA256=r.sha(reference_folder / 'storage/result.json'),
                baseline=before, candidate=after, exactCausalAcceptance=False,
                note='Compare population, fire and block trends before interpreting this independent-process timing difference.')
        r.save(folder / 'summary.json', summary)
        print(json.dumps({key: summary[key] for key in ('name', 'arm', 'continuousSampling', 'withinSegmentFrames', 'blocks')}), flush=True)
        lease.outcome = 'passed';lease.note = 'Independent-process native combat captured; no RC API, networking, release acceptance or deployment'


if __name__ == '__main__':
    main()
