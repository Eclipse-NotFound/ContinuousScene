"""Isolated RC offline collection: native-input combat, five 60-frame ABBA blocks.

Only the already reviewed RC SWF is substituted. Native host/CS stay formal;
the probe is compiled from a frozen source copy. Never builds RC or deploys.
"""
from pathlib import Path
import argparse
import contextlib
import importlib.util
import io
import json
import shutil
import statistics
import sys

sys.dont_write_bytecode = True
B = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base = load('rc_offline_native_input_base', B / 'native-input-combat-run.py')
builder = load('rc_offline_candidate_builder', B / 'rc-offline-probe-build.py')
r, m, support = base.r, base.m, base.support
OUT = B / 'generated/rc-offline-combat-20261023'
RC_PATH = 'mods/Rconnect/release/RConnectMod.swf'
RC_SHA = '88CC639E8293FD38DFE4B4855ED2359F2DACF58A8DF18B3F7766B20AE1D0E968'
PROOF_SHA = '0BE07E23517B619520D841B83913EDE88C28142604C6189F8E199C60FC5EC81C'
BUILD_SHA = '945F8C6D8197C414A150D7A74FC59E4EF9003D273F30AC7086B22017A0F6FA16'
BUILDER_SHA = 'AE15084FE82185974EB50BD51A95536A580B7AE1D868F3B4F3B3FFC8D8D3AC77'
COUNTERS = ('mirrorSkipped', 'finalSkipped', 'eligibilityChecks', 'eligibilityErrors', 'perceptionSkipped')
original_runner_inputs = base.runner_inputs


def runner_inputs():
    values = original_runner_inputs()
    for path in (Path(__file__), B / 'rc-offline-probe-build.py'):
        values[str(path)] = r.sha(path)
    return values


def candidate_inputs():
    assert r.sha(B / 'rc-offline-probe-build.py') == BUILDER_SHA
    assert r.sha(builder.OUT / 'source-provenance.json') == PROOF_SHA
    assert r.sha(builder.OUT / 'compile.json') == BUILD_SHA
    assert r.sha(builder.OUT / 'RConnectMod.swf') == RC_SHA
    with contextlib.redirect_stdout(io.StringIO()):
        assert builder.check()['valid']  # Read-only reverse-source reconstruction.
    proof, compiled = r.read(builder.OUT / 'source-provenance.json'), r.read(builder.OUT / 'compile.json')
    assert compiled['sourceProofSHA'] == PROOF_SHA and compiled['builderSHA'] == BUILDER_SHA
    assert compiled['candidateSHA'] == RC_SHA and compiled['diagnosticOnly']
    assert not compiled['performanceAcceptance'] and not compiled['AIRLaunched'] and not compiled['deployed']
    assert proof['formalRC'] == builder.FORMAL_RC and proof['defaultEnabled'] is False
    assert proof['reverseByteReconstruction'] and proof['networkAttemptReset'] is False
    assert r.sha(builder.OUT / 'compile.log') == compiled['logSHA']
    paths = ('source-provenance.json', 'compile.json', 'compile.log', 'source.diff', 'RConnectMod.swf')
    values = {str(builder.OUT / name): r.sha(builder.OUT / name) for name in paths}
    provenance = support.OUT / 'source-provenance.json'
    assert r.sha(provenance) == support.PROVENANCE_SHA
    values[str(provenance)] = support.PROVENANCE_SHA
    return values


base.OUT = OUT
base.runner_inputs = runner_inputs
base.candidate_inputs = candidate_inputs


def verify_probe(path, baseline, scripts, compiler, candidate):
    probe = base.verify_probe(path, baseline, scripts, compiler, candidate)
    source = (Path(probe['frozenSourcePath']) / 'ContinuousSceneMotionProbe.as').read_text('utf-8-sig')
    for token in ('"rcoffline"', 'RConnectOfflineProbeCarrier', 'readRcOffline', 'row.rcOffline.end',
                  'rcOfflineCleanup', 'row.probeTiming', 'row.continuousFramesMs.push(now-continuousPreviousSampleAt)',
                  'last=cfg.drawControl=="rcoffline"?caseBegin:getTimer()'):
        assert token in source, token
    return probe


def check_rc(state, enabled):
    assert state['version'] == 'rc-offline-probe-1' and state['diagnosticOnly'] and not state['performanceAcceptance']
    assert state['enabled'] is enabled and state['eligible'] is enabled
    assert state['mode'] == 'offline' and state['networkAttempted'] is False
    assert state['perceptionGated'] is False and state['perceptionSkipped'] == state['eligibilityErrors'] == 0
    assert all(isinstance(state[k], int) and not isinstance(state[k], bool) and state[k] >= 0 for k in COUNTERS)


def check_probe_timing(row, index):
    timing = row['probeTiming']
    assert timing['version'] == 'probe-self-time-1' and timing['diagnosticOnly']
    assert timing['frame'] == timing['frameIndex'] == list(range(60))
    columns = ('totalMs', 'workMs', 'preSampleMs', 'postSampleMs', 'censusMs', 'saveMs',
               'progressSaveMs', 'heartbeatSaveMs', 'startCaseMs', 'bookkeepingMs', 'laterListenersMs', 'terminal')
    assert all(len(timing[k]) == 60 for k in columns)
    for frame in range(60):
        assert timing['terminal'][frame] is (index == 19 and frame == 59)
        for key in columns[:-1]:
            value = timing[key][frame]
            if key == 'laterListenersMs' and index == 19 and frame == 59:
                assert value is None
            else:
                assert base.finite(value) and value >= 0, (index, frame, key, value)
        assert timing['totalMs'][frame] == sum(timing[k][frame] for k in ('workMs', 'censusMs', 'saveMs', 'startCaseMs'))
    return {key: base.metrics([v for v in timing[key] if v is not None]) for key in columns[:-1]}


def continuous_intervals(result):
    info = result['continuousSampling']
    assert info['version'] == 'motion-continuous-wall-1'
    started = previous = info['startedAtMs']
    assert isinstance(started, int) and started >= 0
    intervals, previous_end = [], None
    assert len(result['samples']) == 20
    for row in result['samples']:
        stamps, values, rc = row['sampleAtMs'], row['continuousFramesMs'], row['rcOffline']
        assert len(stamps) == len(values) == len(row['frames']) == 60
        assert previous <= rc['caseBeginAtMs'] <= rc['beginAt'] <= rc['switchAfterAtMs'] <= stamps[0]
        if previous_end is not None:
            assert previous_end <= rc['caseBeginAtMs']
        assert rc['switchAfterAtMs'] - rc['beginAt'] == rc['switchMs']
        assert row['frames'][0] == stamps[0] - rc['caseBeginAtMs']
        for frame, (stamp, interval) in enumerate(zip(stamps, values)):
            assert isinstance(stamp, int) and isinstance(interval, int) and interval >= 0
            assert stamp - previous == interval, 'A sample interval was omitted or reset at a segment boundary'
            assert interval >= row['frames'][frame]
            if frame > 0:
                assert interval == row['frames'][frame]
            previous = stamp;intervals.append(interval)
        assert rc['endAtMs'] >= stamps[-1]
        previous_end = rc['endAtMs']
    assert len(intervals) == 1200 and sum(intervals) == previous - started
    return dict(version=info['version'], startedAtMs=started, lastSampleAtMs=previous,
        intervalCount=len(intervals), totalMs=sum(intervals), metrics=base.metrics(intervals),
        boundaryAttribution='An interval belongs to the segment containing its ending sample, including the preceding segment tail.',
        terminalBoundary='Work after the last sample, including final census/save/cleanup, has no following interval and is excluded.')


def summarize(result, name):
    cfg = result['config']
    assert cfg['drawControl'] == 'rcoffline' and cfg['benchmark'] == 'scene'
    assert cfg['nativeInputMotion'] and cfg['stableMotion'] and cfg['fixedEnemies'] and cfg['playerFire']
    assert not cfg['localEnemies'] and not cfg['nativeSprint'] and not cfg['sleepingRootShort']
    assert not cfg['sleepingRootCheck'] and not cfg['presentationCheck']
    assert cfg['noLighting'] and cfg['noWall'] and not cfg['vision']
    assert result['world']['layoutSeed'] == 20261019 and (result['world']['width'], result['world']['height']) == (240, 125)
    view = result['viewport']
    assert view['stageWidth'] == view['cameraWidth'] == 2032 and view['stageHeight'] == view['cameraHeight'] == 1084 and view['zoom'] == 1
    warm = result['playerFireWarmup']
    assert warm['frames'] >= 100 and warm['quietWarmFrames'] >= 100 and warm['shotFrames'] >= 5
    assert warm['encounter']['actualShotFrames'] > 0
    base.six_armed(warm['encounter'])
    check_rc(result['rcOfflineInitial'], False)
    assert result['rcOfflineInitial']['mirrorSkipped'] == result['rcOfflineInitial']['finalSkipped'] == 0
    assert len(result['samples']) == 20
    continuous = continuous_intervals(result)
    samples, arms, within_arms, blocks = [], {'A': [], 'B': []}, {'A': [], 'B': []}, []
    previous = result['rcOfflineInitial']
    for index, row in enumerate(result['samples']):
        enabled = index % 4 in (1, 2)
        arm = 'B' if enabled else 'A'
        assert row['name'] == 'rc-offline-' + arm.lower() + '-' + str(index)
        assert len(row['frames']) == len(row['nativeBand']) == len(row['warm']) == 60
        assert len(row['totalScript']) == (59 if index == 0 else 60)
        assert row['empty'] == row['misses'] == 0 and row['playerShotFrames'] > 0 and row['enemyShotFrames'] >= 0
        base.six_armed(row['encounter'])
        pose, windows = base.check_native_driver(result, row, index), base.combat_windows(row, 60)
        rc = row['rcOffline']
        check_rc(rc['before'], previous['enabled'])
        check_rc(rc['after'], enabled)
        check_rc(rc['end'], enabled)
        if index == 0:
            assert rc['before']['mirrorSkipped'] == rc['before']['finalSkipped'] == 0, 'Warmup must retain native sampling'
        assert all(rc['before'][k] >= previous[k] and rc['before'][k] == rc['after'][k] for k in COUNTERS)
        delta = {k: rc['end'][k] - rc['after'][k] for k in COUNTERS}
        assert all(v >= 0 for v in delta.values()) and delta['eligibilityChecks'] > 0
        assert (delta['mirrorSkipped'] > 0) is enabled and (delta['finalSkipped'] > 0) is enabled
        assert [x['frame'] for x in rc['windows']] == [0, 29, 30, 59]
        earlier = rc['after']
        for sample in rc['windows']:
            check_rc(sample['snapshot'], enabled)
            assert all(sample['snapshot'][k] >= earlier[k] for k in COUNTERS)
            earlier = sample['snapshot']
        assert all(rc['end'][k] >= earlier[k] for k in COUNTERS)
        assert base.finite(rc['switchMs']) and 0 <= rc['switchMs'] <= row['frames'][0]
        previous = rc['end'];arms[arm].extend(row['continuousFramesMs']);within_arms[arm].extend(row['frames'])
        samples.append(dict(index=index, arm=arm, continuousIntervals=base.metrics(row['continuousFramesMs']),
            withinSegmentFrames=base.metrics(row['frames']), firstIntervalMs=row['continuousFramesMs'][0],
            firstWithinSegmentFrameMs=row['frames'][0], nativeBand=base.metrics(row['nativeBand']),
            totalScript=base.metrics(row['totalScript']), probeTiming=check_probe_timing(row, index), rcOffline=rc, counterDelta=delta,
            playerShots=row['playerShotFrames'], enemyShots=row['enemyShotFrames'], combatWindows=windows,
            nativeInput=pose, activity=row['activity'], activityEnd=row.get('activityEnd'), activityCensus=row.get('activityCensus'),
            scene=dict(warmed=sum(row['warm']), forced=row.get('forced'), slices=row.get('slices')), encounterEnd=row['encounter']))
    for start in range(0, 20, 4):
        rows = samples[start:start + 4]
        values = {arm: [dt for i, row in enumerate(result['samples'][start:start + 4])
                       if ('B' if i in (1, 2) else 'A') == arm for dt in row['continuousFramesMs']] for arm in ('A', 'B')}
        within = {arm: [dt for i, row in enumerate(result['samples'][start:start + 4])
                       if ('B' if i in (1, 2) else 'A') == arm for dt in row['frames']] for arm in ('A', 'B')}
        assert all(sum(row['enemyShots'] for row in rows if row['arm'] == arm) > 0 for arm in ('A', 'B'))
        blocks.append(dict(block=start // 4, arms={arm: base.metrics(v) for arm, v in values.items()},
            withinSegmentArms={arm: base.metrics(v) for arm, v in within.items()},
            medianDifferenceMs=statistics.median(values['A']) - statistics.median(values['B'])))
    assert sum(row['enemyShots'] > 0 for row in samples) >= 16, 'Too few genuine two-way combat windows'
    cleanup = result['rcOfflineCleanup']
    check_rc(cleanup['before'], False);check_rc(cleanup['after'], False)
    assert all(cleanup['before'][k] >= previous[k] and cleanup['before'][k] == cleanup['after'][k] for k in COUNTERS)
    return dict(version='rc-offline-combat-summary-2', name=name, diagnosticOnly=True, performanceEligible=False,
        performanceAcceptance=False, deployed=False, driver=result['driver'], nativeInputMotion=result['nativeInputMotion'],
        viewport=view, samples=samples, continuousSampling=continuous,
        armsContinuousIntervals={arm: base.metrics(v) for arm, v in arms.items()},
        armsWithinSegmentFrames={arm: base.metrics(v) for arm, v in within_arms.items()},
        blocksContinuousIntervals=blocks, cleanup=cleanup,
        primaryTiming='Continuous sample-to-sample wall intervals, without resetting at segment boundaries or subtracting probe work',
        withinSegmentTiming='Legacy frames reset at startCase; they include current switch cost but omit the preceding segment final census/save gap',
        limitations=['Only offline pre-network eligibility; no multiplayer behavior acceptance.',
            'Only mirror/final presentation/bodyEffects collection is gated; perception, wall/ports and actual display remain active.',
            'The switch happens in the probe before lower-priority RC callbacks; native motion and later callbacks straddle the boundary.',
            'A cross-segment interval is assigned to its ending segment; its preceding census/save cost is not pure current-arm execution.',
            'Final work after the last sample is outside continuous intervals; probeTiming still records own final work before cleanup.',
            'Heavy census/save and probe work remain measured separately; battle population and terrain evolve.'])


def main():
    if not __debug__:
        raise RuntimeError('Assertions required; do not use -O')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--compile-probe', action='store_true');source.add_argument('--probe-build', type=Path)
    parser.add_argument('--registry-wait', type=int, default=600)
    args = parser.parse_args()
    assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
    folder = r.E / args.name
    assert not folder.exists(), 'Preserve existing evidence'
    with m.Registration(owner='ContinuousScene / RC offline combat / 01a13816', purpose=args.name,
            run_dir=m.RUNTIME, evidence=folder, wait=args.registry_wait) as lease:
        assert not m.air_pids(), 'Other AIR present; untouched'
        baseline, scripts, compiler, candidate = r.baseline(), runner_inputs(), support.compiler_inputs(), candidate_inputs()
        assert baseline['pfe.swf'] == base.FORMAL_HOST and baseline[base.CS_PATH] == base.FORMAL_CS and baseline[RC_PATH] == builder.FORMAL_RC
        build_path = base.compile_frozen_probe(lease, baseline, scripts, compiler, candidate) if args.compile_probe else args.probe_build.resolve()
        probe = verify_probe(build_path, baseline, scripts, compiler, candidate)
        m.prepare()
        shutil.copy2(probe['probePath'], m.RUNTIME / base.PROBE_PATH)
        shutil.copy2(builder.OUT / 'RConnectMod.swf', m.RUNTIME / RC_PATH)
        assert r.sha(m.RUNTIME / 'pfe.swf') == base.FORMAL_HOST and r.sha(m.RUNTIME / base.CS_PATH) == base.FORMAL_CS
        assert r.sha(m.RUNTIME / RC_PATH) == RC_SHA and r.sha(m.RUNTIME / base.PROBE_PATH) == probe['probeSHA256']
        # The application id is fresh, so the shipped JSON is the only stored
        # RC configuration. Refuse auto-networking instead of changing config.
        assert r.read(m.RUNTIME / 'mods/Rconnect/release/config.txt').get('autoRole', '') not in ('host', 'join')
        options = ['--name', args.name, '--high-qos', '--land', 'random_mane', '--encounter', '--fixed-enemies',
            '--benchmark', 'scene', '--speed', '4', '--short', '--stable-motion', '--native-input-motion', '--player-fire',
            '--combat-route', '--combat-route-length', '200', '--window-width', '2048', '--window-height', '1123',
            '--no-lighting', '--no-wall', '--expect-no-signs', '--draw-control', 'rcoffline']
        assert baseline == r.baseline() and scripts == runner_inputs() and compiler == support.compiler_inputs() and candidate == candidate_inputs()
        try:
            m.run_owned(m.parse_args(options), lease)
        finally:
            if folder.exists():
                r.save(folder / 'probe-build.json', probe)
                r.save(folder / 'runner-inputs.json', dict(options=options, baseline=baseline, runnerInputs=scripts,
                    compilerInputs=compiler, candidateInputs=candidate, probeBuildPath=str(build_path), actualRConnectSHA256=RC_SHA))
        assert baseline == r.baseline() and scripts == runner_inputs() and compiler == support.compiler_inputs() and candidate == candidate_inputs()
        verify_probe(build_path, baseline, scripts, compiler, candidate)
        # r.result also requires one loader session, all 15 expected entries
        # loaded, no TDFC runtime error, and no competing AIR/memory abort.
        result, inputs = r.result(args.name)
        for path, digest in baseline.items():
            if path not in ('application.xml', 'mods/loader-manifest.txt', RC_PATH):
                assert inputs[path] == digest, path
        assert inputs[RC_PATH] == RC_SHA and inputs[base.PROBE_PATH] == probe['probeSHA256']
        policy = r.read(folder / 'process-policy.json')
        assert policy['performanceEligible'] is False and not policy.get('runFailure')
        assert not policy.get('memoryAbort') and not policy.get('otherAirProcessIds')
        summary = summarize(result, args.name)
        summary.update(probeBuildPath=str(build_path), hostSHA256=base.FORMAL_HOST,
            actualContinuousSceneSHA256=base.FORMAL_CS, actualRConnectSHA256=RC_SHA)
        r.save(folder / 'summary.json', summary)
        print(json.dumps({key: summary[key] for key in ('name', 'armsContinuousIntervals', 'armsWithinSegmentFrames', 'blocksContinuousIntervals', 'cleanup')}), flush=True)
        lease.outcome = 'passed';lease.note = 'Offline RC sampling ABBA captured; no networking, deployment or performance acceptance'


if __name__ == '__main__':
    main()
