"""Isolated front-shadow component or five complete 60-frame ABBA blocks.

No host patch or production write. Timing requires this exact frozen probe's
successful 30-native-frame pixel component. Tail endpoints retain every switch.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys
import uuid

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
VERSION = 'front-shadow-runner-3'
HOST = '80CFD8CF3138EE59CBF6EDA0A1824A9EC960F413BD95E4B90D41DD0322B4FD3D'
CS = '7F1F2961C6E299D949423591F3C65C610C2EAEFA7FC72E8A583A402770D6B51F'
RC = 'DF0FA0E2CA952E77E5132E75D71E73558DC919C7B8CDEBA5DA05FC9E94DC01E7'
HELPER = HERE / 'tests/SceneFrontShadowProbe.as'
HELPER_SHA = 'FB4496ED1C7C6234AFA059B168C6B93939447806F0C311F115D32E56E25051B6'
METRICS = HERE.parents[1] / 'render-audit/background-short-v5/short_metrics.py'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


dense = load('front_shadow_dense', HERE.parents[1] / 'fixture-audit-v2/dense-combat-run.py')
patcher = load('front_shadow_patch', HERE / 'probe_patch.py')
short = load('front_shadow_short_metrics', METRICS)
base, r, m, support = dense.base, dense.r, dense.m, dense.support
short.base = base
base.FORMAL_HOST, dense.FORMAL_RC = HOST, RC
original_inputs, original_fixture = dense.runner_inputs, dense.fixture_inputs


def runner_inputs():
    return dict(original_inputs(), **{str(Path(__file__)): r.sha(Path(__file__))})


def fixture_inputs():
    assert r.sha(HELPER) == HELPER_SHA, 'Reviewed helper changed'
    result = original_fixture()
    for path in (HELPER, HERE / 'probe_patch.py', METRICS):
        result[str(path)] = r.sha(path)
    return result


def compile_probe(lease, baseline, scripts, compiler, fixture):
    shared = dense.BUILD.parent / 'src'
    before = base.tree_hashes(shared)
    staging = HERE / 'staging' / uuid.uuid4().hex
    patcher.prepare(shared, staging / 'src', dense.patcher, HELPER)
    assert before == base.tree_hashes(shared), 'Live source changed while capturing'
    after = base.tree_hashes(staging / 'src')
    changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    assert changed == sorted(['ContinuousSceneMotionProbe.as', 'tests/SceneEncounter.as',
                             'tests/SceneDenseCombatMetrics.as', 'tests/SceneFrontShadowProbe.as']), changed
    origin = staging / 'source-origin.json'
    r.save(origin, dict(version=VERSION, sharedSource=str(shared), sharedSHA256=before,
                        stagedSource=str(staging / 'src'), stagedSHA256=after,
                        changed=changed, fixtureInputs=fixture))
    base.B, base.OUT = staging / 'build', HERE / 'probe-builds'
    path = base.compile_frozen_probe(lease, baseline, scripts, compiler, fixture)
    probe = r.read(path)
    probe.update(denseFixture=dense.VERSION, frontShadow=VERSION,
                 sourceOrigin=str(origin), sourceOriginSHA256=r.sha(origin))
    r.save(path, probe)
    return path


def verify_probe(path, baseline, scripts, compiler, fixture):
    probe = dense.verify_probe(path, baseline, scripts, compiler, fixture)
    assert probe['frontShadow'] == VERSION
    assert probe['frozenSourceSHA256']['tests/SceneFrontShadowProbe.as'] == HELPER_SHA
    assert probe['productionSHA256']['pfe.swf'] == HOST
    return probe


def cleanup(result):
    state, restored = result['frontShadowFinal'], result['frontShadowCleanup']
    assert state['version'] == 'front-shadow-diagnostic-1' and state['started'] and state['closed']
    assert not state['aborted'] and not state['heldBindings'] and not state['prepared']
    assert not state['failures'] and restored['restored'] and not restored['heldBindings']
    assert restored['nativeDataDisposed'] == restored['leakedClones'] == restored['cleanupErrors'] == 0
    assert restored['disposedClones'] == state['residentEntries'] > 0
    assert all(w['acceptable'] and w['closed'] and not w['failures'] for w in state['windows'])
    assert result['frontShadowSetup']['quietFramesBeforeStart'] >= 20
    pre = result['frontShadowPrewarm']
    assert pre['version'] == 'front-shadow-native-prewarm-1' and pre['beforeEncounter']
    assert pre['worldStepsCalled'] == 0 and not pre['scenePreloadUsed']
    assert not pre['loadingBenchmark'] and not pre['performanceAcceptance']
    assert pre['restored'] and pre['playerUnchanged'] and pre['drained'] and pre['viewReady']
    assert 0 < pre['calls'] <= 66 and pre['testPreparationMs'] >= 0
    assert pre['after']['sceneResident'] <= 256 and pre['estimatedResidentUpperBound'] <= 256
    return state


def summarize_check(result, args):
    assert result['ok'] and result['error'] is None and not result['samples']
    cfg, motion = result['config'], result['nativeInputMotion']
    assert cfg['presentationCheck'] and cfg['drawControl'] == 'rcnative' and cfg['benchmark'] == 'scene'
    assert cfg['nativeInputMotion'] and cfg['nativeSprint'] and cfg['fixedEnemies'] and cfg['playerFire']
    assert cfg['noLighting'] and cfg['noWall'] and not cfg['vision']
    assert result['driver']['forcedPositionCalls'] == 0 and motion['spawn']['calls'] == 1
    assert motion['route']['terrainVerified']
    state = cleanup(result)
    observed, proof = result['frontShadowCheck'], result['frontShadowVerification']
    assert observed['groundContactRun'] >= 10 and observed['quietFrames'] >= 20
    preparation = result['frontShadowPreparation']
    assert preparation['version'] == 'front-shadow-preparation-2' and preparation['readyFrames'] > 0
    assert preparation['last']['ready'] and preparation['last']['reasons'] == []
    assert observed['startPose']['floorContact'] and observed['nativeFrames'] == observed['tailFrames'] == 30
    short.check_motion_bucket(observed['nativeMotion'], motion['route'], 30)
    assert observed['playerShots'] > 0 and observed['enemyShots'] > 0
    assert len(state['windows']) == 1 and state['windows'][0]['enabled'] is True
    assert state['windows'][0]['counts']['frames'] == state['totals']['frames'] == 30
    assert proof['valid'] and proof['equal'] and proof['restored'] and proof['error'] is None
    assert proof['sameFrame'] and proof['tailImageChecked'] and proof['tailSyncsObserved'] > 0
    assert proof['nativePixelWrites'] == 0 and proof['bitmapPropertiesPreserved']
    for key in ('referenceRepeat', 'bindingImage', 'tailImage', 'restoreImage'):
        assert proof[key]['equal'] and proof[key]['diffCount'] == proof[key]['maxChannelDelta'] == 0
    return dict(version=VERSION, name=args.name, mode='check', passed=True,
        diagnosticOnly=True, performanceEligible=False, performanceAcceptance=False, deployed=False,
        verification=proof, preparation=preparation, prewarm=result['frontShadowPrewarm'],
        nativeFrames=observed['nativeFrames'], playerShots=observed['playerShots'],
        enemyShots=observed['enemyShots'], cleanup=result['frontShadowCleanup'], state=state,
        limitations=['Scale 1, current viewport, thirty real native frames; no SATS/resize/travel certification.',
            'Revision-triggered tail synchronization is covered; revisions also include non-front changes.',
            'Native viewport preparation is completed before fixture actors, separately timed; it is not loading-performance evidence.',
            'Component pixel equality does not establish frame-time benefit or permission to deploy.'])


def summarize_timing(result, args):
    args.mode = 'scene'
    summary = short.summarize(result, args)
    assert not result['config']['presentationCheck']
    metadata = result['frontShadowTiming']
    assert metadata == dict(version='front-shadow-tail-sampling-2', order=[False, True, True, False],
        windows=20, windowFrames=60, headPriority=2147483647, tailPriority=-2147483647,
        controlAlias='rcnative', primaryEndsAfterTail=True, includesTransitions=True,
        initialAllocationOutsideTiming=True, finalCleanupOutsideTiming=True, tickEvidenceRetained=True,
        firstIntervalTailToTail=True)
    assert result['continuousSampling']['primeTailAtMs'] == result['continuousSampling']['startedAtMs']
    assert result['continuousSampling']['primeTailAtMs'] <= result['samples'][0]['caseBeginAtMs']
    state = cleanup(result)
    assert len(state['windows']) == 20 and state['totals']['frames'] == 1200
    arms = {'A': [], 'B': []}
    windows, blocks = [], []
    for index, row in enumerate(result['samples']):
        enabled = index % 4 in (1, 2)
        data = row['frontShadow']
        assert data['index'] == index and data['enabled'] is enabled
        assert data['headModes'] == data['tailModes'] == [enabled] * 60
        assert data['headIndices'] == data['tailIndices'] == [index] * 60
        assert len(row['tickSampleAtMs']) == len(row['tickFramesMs']) == 60
        assert all(head <= tail for head, tail in zip(row['tickSampleAtMs'], row['sampleAtMs']))
        assert row['tickCaseBeginAtMs'] <= row['caseBeginAtMs'] == data['beginAtMs']
        assert row['tickCaseEndAtMs'] <= row['caseEndAtMs'] == row['sampleAtMs'][-1]
        end, final = data['end'], state['windows'][index]
        assert not end['aborted'] and not end['prepared']
        assert end['heldBindings'] is enabled and end['currentEnabled'] is enabled
        assert end['window']['index'] == index and end['window']['enabled'] is enabled
        assert end['window']['acceptable'] and not end['window']['failures']
        assert end['window']['counts'] == final['counts'] and final['counts']['frames'] == 60
        assert end['window']['switchMs'] == final['switchMs'] >= 0
        assert final['counts']['tailSyncs'] == (final['counts']['changedEntries'] if enabled else 0)
        assert row['slices'] == row['forced'] == sum(row['warm']) == 0, 'No redraw/prewarm interval is eligible'
        arm = 'B' if enabled else 'A'
        arms[arm].extend(row['continuousFramesMs'])
        windows.append(dict(index=index, arm=arm, continuous=base.metrics(row['continuousFramesMs']),
            counts=final['counts'], switchMs=final['switchMs'], playerShots=row['playerShotFrames'],
            enemyShots=row['enemyShotFrames'], bothFired=row['playerShotFrames'] > 0 and row['enemyShotFrames'] > 0,
            totalScript=base.metrics(row['totalScript']), activity=row['activity'], activityEnd=row.get('activityEnd'),
            nativeBand=base.metrics(row['nativeBand']), workload=summary['samples'][index]['workload']))
    for offset in range(0, 20, 4):
        block = dict(index=offset // 4)
        for arm in ('A', 'B'):
            selected = [result['samples'][i] for i in range(offset, offset + 4) if windows[i]['arm'] == arm]
            block[arm] = dict(continuous=base.metrics([v for row in selected for v in row['continuousFramesMs']]),
                playerShots=sum(row['playerShotFrames'] for row in selected),
                enemyShots=sum(row['enemyShotFrames'] for row in selected),
                fixtureBullets=base.metrics([v for row in selected for v in row['denseFrames']['fixtureBullets']]),
                absoluteDx=base.metrics([abs(v) for row in selected for v in row['denseFrames']['dx']]))
        block['bothArmsFired'] = all(block[a]['playerShots'] > 0 and block[a]['enemyShots'] > 0 for a in ('A', 'B'))
        block['meanChangeMs'] = block['B']['continuous']['mean'] - block['A']['continuous']['mean']
        blocks.append(block)
    both_fired = sum(w['bothFired'] for w in windows)
    qualification = summary['qualification']
    qualification.update(bothFiredWindows=both_fired,
        shortCombat=both_fired >= 16 and all(b['bothArmsFired'] for b in blocks),
        actualTailSynchronization=state['totals']['tailSyncs'] > 0)
    qualification['passed'] = qualification['passed'] and qualification['shortCombat'] and qualification['actualTailSynchronization']
    summary.update(version=VERSION, mode='timing', tailSampling=metadata,
        arms={key: base.metrics(values) for key, values in arms.items()}, frontShadowWindows=windows,
        blocks=blocks, frontShadowState=state, frontShadowCleanup=result['frontShadowCleanup'],
        prewarm=result['frontShadowPrewarm'])
    summary['limitations'] += [
        'Primary boundaries are this probe\'s late ENTER_FRAME tail, not historical tick-based runs; compare A/B in this probe only.',
        'All 1200 complete primary intervals and all window switches are retained; no first-frame exclusion or subtraction.',
        'Tick timestamps/intervals remain separate raw fields. Initial clone allocation and final disposal are separately reported outside sampling.',
        'Any warm/redraw/resident identity change aborts the entire run; restored-but-aborted results never qualify.',
        'A bounded native synchronous viewport preparation runs before actors and outside all timing; no full-map preload or load-time claim.',
        'Runtime scheduling and combat randomness can vary. Inspect all five ABBA blocks and shot/active/bullet loads.',
        'No production or near-original frame-rate acceptance is inferred from this experiment.']
    return summary


def pixel_reference(name, probe, baseline):
    assert name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in name)
    folder = r.E / name
    result, _ = r.result(name)
    summary = summarize_check(result, argparse.Namespace(name=name))
    assert r.read(folder / 'summary.json')['passed'] and summary['passed']
    assert r.read(folder / 'probe-build.json')['probeSHA256'] == probe['probeSHA256']
    assert r.read(folder / 'runner-inputs.json')['baseline'] == baseline
    return dict(name=name, resultSHA256=r.sha(folder / 'storage/result.json'), probeSHA256=probe['probeSHA256'])


def main():
    assert __debug__
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--check-evidence')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--compile-probe', action='store_true')
    group.add_argument('--probe-build', type=Path)
    parser.add_argument('--registry-wait', type=int, default=600)
    args = parser.parse_args()
    assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
    assert args.check or (args.check_evidence and args.probe_build), 'Timing reuses a pixel-qualified frozen probe'
    assert not args.check or not args.check_evidence
    folder = r.E / args.name
    assert not folder.exists(), 'Preserve existing evidence'
    with m.Registration(owner='ContinuousScene / front shadow / 01a13816', purpose=args.name,
                        run_dir=m.RUNTIME, evidence=folder, wait=args.registry_wait) as lease:
        assert not m.air_pids(), 'Other AIR remains untouched'
        baseline, scripts, compiler, fixture = r.baseline(), runner_inputs(), support.compiler_inputs(), fixture_inputs()
        assert baseline['pfe.swf'] == HOST and baseline[base.CS_PATH] == CS and baseline[dense.RC] == RC
        path = compile_probe(lease, baseline, scripts, compiler, fixture) if args.compile_probe else args.probe_build.resolve()
        probe = verify_probe(path, baseline, scripts, compiler, fixture)
        reference = None if args.check else pixel_reference(args.check_evidence, probe, baseline)
        m.prepare()
        shutil.copy2(probe['probePath'], m.RUNTIME / base.PROBE_PATH)
        for key in ('pfe.swf', base.CS_PATH, dense.RC):
            assert r.sha(m.RUNTIME / key) == baseline[key]
        options = ['--name', args.name, '--high-qos', '--land', 'random_mane', '--encounter', '--fixed-enemies',
            '--benchmark', 'scene', '--short', '--stable-motion', '--native-input-motion', '--native-sprint',
            '--player-fire', '--combat-route', '--combat-route-length', '200', '--window-width', '2048',
            '--window-height', '1123', '--no-lighting', '--no-wall', '--draw-control', 'rcnative', '--expect-no-signs']
        if args.check:
            options += ['--presentation-check']
        try:
            m.run_owned(m.parse_args(options), lease)
        finally:
            if folder.exists():
                r.save(folder / 'probe-build.json', probe)
                r.save(folder / 'runner-inputs.json', dict(options=options, baseline=baseline, runnerInputs=scripts,
                    compilerInputs=compiler, fixtureInputs=fixture, probeBuildPath=str(path), pixelReference=reference))
        assert baseline == r.baseline() and scripts == runner_inputs() and fixture == fixture_inputs()
        verify_probe(path, baseline, scripts, compiler, fixture)
        result, inputs = r.result(args.name)
        for key, digest in baseline.items():
            if key not in ('application.xml', 'mods/loader-manifest.txt'):
                assert inputs[key] == digest, key
        assert inputs[base.PROBE_PATH] == probe['probeSHA256']
        policy = r.read(folder / 'process-policy.json')
        assert policy['performanceEligible'] is False and not policy.get('runFailure')
        assert not policy.get('memoryAbort') and not policy.get('otherAirProcessIds')
        summary = summarize_check(result, args) if args.check else summarize_timing(result, args)
        summary['pixelReference'] = reference
        r.save(folder / 'summary.json', summary)
        assert args.check or summary['qualification']['passed'], 'Insufficient real workload; retained, not qualified'
        lease.outcome = 'passed'
        lease.note = 'Exact pixels and restoration' if args.check else 'Five complete ABBA blocks captured; no deployment acceptance'
        print(json.dumps({k: summary[k] for k in ('name', 'mode', 'passed' if args.check else 'arms')}, ensure_ascii=False), flush=True)


base.runner_inputs, base.candidate_inputs = runner_inputs, fixture_inputs
if __name__ == '__main__':
    main()
