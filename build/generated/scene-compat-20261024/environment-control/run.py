"""Frozen dense-sprint-2 environment control with aligned owned-process CPU samples.

No camera manipulation, extra terrain preparation, deployment or shared-source writes.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import math
import shutil
import sys
import time
import uuid

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
BUILD = HERE.parents[2]
DENSE_DIR = BUILD / 'generated/combat-near-native-20261023/fixture-audit-v2'
VERSION = 'environment-control-1'
HOST = 'A796827173AF7D6FAB9885FB66ECC62182AB5335918A30C7CCE4C44914A238B7'
RC = 'DF0FA0E2CA952E77E5132E75D71E73558DC919C7B8CDEBA5DA05FC9E94DC01E7'
SEED_RECEIPT = BUILD.parent / 'knowledge/experiments/evidence/vertical-camera-band-20261023-combat-candidate-r3/probe-build.json'
SEED_SHA = 'B7ED1EAB8BEE0DC1024D6EF0A56A965F311B97E8CED9A9F32A2BCDE35B35FF13'
SEED_PROBE = '39A1497BE832282CAC25E2A508A954432F9F31B15A2FBE5A650AB8C4D9C97E9E'
DEPLOYMENT = BUILD.parent / 'state/scene-tint-deployment-20261024.json'
CHANGED = ['ContinuousSceneMotionProbe.as']


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


dense = load('environment_dense', DENSE_DIR / 'dense-combat-run.py')
patcher = load('environment_patch', HERE / 'probe_patch.py')
base, r, m, support = dense.base, dense.r, dense.m, dense.support
base.FORMAL_HOST = HOST
dense.FORMAL_RC = RC


def deployment():
    value = r.read(DEPLOYMENT)
    assert value['version'] == 'scene-player-region-tint-2' and value['status'] == 'verified'
    assert value['candidate'] == HOST and value['installedInputsAfter']['pfe.swf'] == HOST
    assert r.sha(Path(value['buildReceipt'])) == value['buildReceiptSHA256']
    assert r.sha(Path(value['smokeSummary'])) == value['smokeSummarySHA256']
    smoke = r.read(Path(value['smokeSummary']))
    assert smoke['qualification']['passed'] and smoke['verification']['passed']
    assert smoke['installedPathSmoke'] and smoke['copiedActualInstalledHost']
    assert smoke['hostKind'] == 'installed' and smoke['hostSHA256'] == HOST
    return value


def seed():
    assert r.sha(SEED_RECEIPT) == SEED_SHA, 'Original real-combat receipt changed'
    value = r.read(SEED_RECEIPT)
    assert value['probeSHA256'] == SEED_PROBE == r.sha(Path(value['probePath']))
    assert base.tree_hashes(Path(value['frozenSourcePath'])) == value['frozenSourceSHA256']
    return value


def runner_inputs():
    return dict(dense.runner_inputs(), **{str(HERE / name): r.sha(HERE / name)
        for name in ('run.py', 'probe_patch.py')})


def fixture_inputs():
    seed(); installed = deployment()
    files = [SEED_RECEIPT, DEPLOYMENT, Path(installed['buildReceipt']), Path(installed['smokeSummary']),
             HERE / 'probe_patch.py', support.OUT / 'source-provenance.json']
    return {str(path): r.sha(path) for path in files}


def memory_gate():
    value = m.memory_status()
    assert value['availableCommit'] >= 4 * 1024**3 and value['availablePhysical'] >= 2 * 1024**3, (
        'Requires 4 GiB commit and 2 GiB physical headroom', value)
    return value


def verify_probe(path, baseline, scripts, compiler, fixture):
    probe = base.verify_probe(path, baseline, scripts, compiler, fixture)
    assert probe['environmentControlVersion'] == VERSION and probe['denseFixture'] == dense.VERSION
    origin_path = Path(probe['sourceOrigin'])
    assert r.sha(origin_path) == probe['sourceOriginSHA256']
    origin, old = r.read(origin_path), seed()
    assert origin['seedReceiptSHA256'] == SEED_SHA and origin['seedProbeSHA256'] == SEED_PROBE
    assert origin['seedSourceSHA256'] == old['frozenSourceSHA256']
    assert origin['changed'] == CHANGED and origin['fixtureInputs'] == fixture
    assert origin['stagedSHA256'] == probe['frozenSourceSHA256']
    changed = sorted(k for k in set(old['frozenSourceSHA256']) | set(probe['frozenSourceSHA256'])
        if old['frozenSourceSHA256'].get(k) != probe['frozenSourceSHA256'].get(k))
    assert changed == CHANGED, 'Only two clock anchors in the original probe may differ'
    original = (Path(old['frozenSourcePath']) / CHANGED[0]).read_text(encoding='utf-8-sig')
    assert (Path(probe['frozenSourcePath']) / CHANGED[0]).read_text(encoding='utf-8-sig') == patcher.transform(original)
    return probe


def compile_probe(lease, baseline, scripts, compiler, fixture):
    old = seed(); staging = HERE / 'source-staging' / uuid.uuid4().hex
    patcher.prepare(Path(old['frozenSourcePath']), staging / 'src')
    staged = base.tree_hashes(staging / 'src')
    changed = sorted(k for k in set(old['frozenSourceSHA256']) | set(staged)
        if old['frozenSourceSHA256'].get(k) != staged.get(k))
    assert changed == CHANGED
    origin = staging / 'source-origin.json'
    r.save(origin, dict(version=VERSION, seedReceipt=str(SEED_RECEIPT), seedReceiptSHA256=SEED_SHA,
        seedProbeSHA256=SEED_PROBE, seedSource=old['frozenSourcePath'], seedSourceSHA256=old['frozenSourceSHA256'],
        stagedSource=str(staging / 'src'), stagedSHA256=staged, changed=changed, fixtureInputs=fixture))
    base.B = staging / 'build'
    path = base.compile_frozen_probe(lease, baseline, scripts, compiler, fixture)
    probe = r.read(path)
    probe.update(environmentControlVersion=VERSION, denseFixture=dense.VERSION,
        sourceOrigin=str(origin), sourceOriginSHA256=r.sha(origin))
    r.save(path, probe)
    return path


def aligned_cpu_owned(original):
    def read(process, elapsed):
        before = time.time() * 1000
        value = original(process, elapsed)
        after = time.time() * 1000
        return dict(value, epochBeforeMs=before, epochAfterMs=after, epochMs=(before + after) / 2)
    return read


def alignment(result, policy):
    clock = result['environmentClock']
    assert clock['version'] == 'environment-clock-1' and clock['start'] and clock['end']
    start, end = clock['start'], clock['end']
    assert start['sampleAtMs'] == result['continuousSampling']['startedAtMs']
    assert end['sampleAtMs'] == result['samples'][-1]['sampleAtMs'][-1]
    for mark in (start, end):
        assert all(isinstance(mark[k], (int, float)) and math.isfinite(mark[k])
            for k in ('sampleAtMs', 'timerBeforeMs', 'epochMs', 'timerAfterMs'))
        assert mark['sampleAtMs'] <= mark['timerBeforeMs'] <= mark['timerAfterMs']
    mid = lambda x: (x['timerBeforeMs'] + x['timerAfterMs']) / 2
    drift = (end['epochMs'] - start['epochMs']) - (mid(end) - mid(start))
    assert abs(drift) <= 100, 'Clock discontinuity; do not interpret CPU alignment'
    start_latest = start['epochMs'] + start['sampleAtMs'] - start['timerBeforeMs']
    end_earliest = end['epochMs'] + end['sampleAtMs'] - end['timerAfterMs']
    samples = policy['ownedProcessCpuSamples']; accepted = []
    assert len(samples) >= 2 and not policy.get('cpuSamplingErrors')
    for first, last in zip(samples, samples[1:]):
        assert first['epochBeforeMs'] <= first['epochMs'] <= first['epochAfterMs']
        assert last['epochBeforeMs'] <= last['epochMs'] <= last['epochAfterMs']
        elapsed = (last['elapsed'] - first['elapsed']) * 1000
        assert elapsed > 0 and abs(last['epochMs'] - first['epochMs'] - elapsed) <= 100
        cpu = last['kernelMs'] + last['userMs'] - first['kernelMs'] - first['userMs']
        assert cpu >= 0
        if first['epochBeforeMs'] >= start_latest and last['epochAfterMs'] <= end_earliest:
            accepted.append(dict(startEpochMs=first['epochMs'], endEpochMs=last['epochMs'],
                elapsedMs=elapsed, processCpuMs=cpu))
    assert accepted, 'No complete owned-CPU interval inside measured phase'
    elapsed = sum(x['elapsedMs'] for x in accepted)
    cpu = sum(x['processCpuMs'] for x in accepted)
    return dict(passed=True, version='environment-clock-alignment-1', anchors=clock,
        clockDriftMs=drift, conservativeStartEpochMs=start_latest, conservativeEndEpochMs=end_earliest,
        wholeIntervals=accepted, coveredElapsedMs=elapsed, processCpuMs=cpu,
        meanCoreEquivalent=cpu / elapsed, processSampleCount=len(samples),
        endpointDelayMs=dict(start=start['timerBeforeMs']-start['sampleAtMs'], end=end['timerBeforeMs']-end['sampleAtMs']),
        mainThreadCpu=False, exactWholePhaseCpu=False)


def main():
    assert __debug__, 'Do not disable assertions'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    parser.add_argument('--mode', choices=['normal', 'scene'], required=True)
    parser.add_argument('--paired-evidence', help='Other mode from this runner, same frozen probe and inputs')
    parser.add_argument('--registry-wait', type=int, default=600)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--compile-probe', action='store_true')
    group.add_argument('--probe-build', type=Path)
    args = parser.parse_args()
    assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
    folder = r.E / args.name
    assert not folder.exists(), 'Preserve all existing evidence'
    assert not args.paired_evidence or args.probe_build
    with m.Registration(owner='ContinuousScene / frozen environment control / 01a13816', purpose=args.name,
            run_dir=m.RUNTIME, evidence=folder, wait=args.registry_wait) as lease:
        assert not m.air_pids(), 'Other AIR remains untouched'
        memory_before = memory_gate()
        baseline, scripts, compiler, fixture = r.baseline(), runner_inputs(), support.compiler_inputs(), fixture_inputs()
        assert baseline['pfe.swf'] == HOST and baseline[base.CS_PATH] == base.FORMAL_CS
        assert baseline[dense.RC] == RC
        path = compile_probe(lease, baseline, scripts, compiler, fixture) if args.compile_probe else args.probe_build.resolve()
        probe = verify_probe(path, baseline, scripts, compiler, fixture)
        reference = None
        if args.paired_evidence:
            assert all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.paired_evidence)
            r.result(args.paired_evidence)
            old = r.E / args.paired_evidence; reference = r.read(old / 'summary.json')
            recorded = r.read(old / 'runner-inputs.json')
            assert reference['environmentControlVersion'] == VERSION and reference['mode'] != args.mode
            assert reference['qualification']['passed'] and reference['clockAlignment']['passed']
            assert reference['hostSHA256'] == HOST
            assert r.read(old / 'probe-build.json')['probeSHA256'] == probe['probeSHA256']
            assert recorded['baseline'] == baseline and recorded['runnerInputs'] == scripts
            assert recorded['compilerInputs'] == compiler and recorded['fixtureInputs'] == fixture
        m.prepare(); shutil.copy2(probe['probePath'], m.RUNTIME / base.PROBE_PATH)
        assert baseline == r.baseline(), 'Installed inputs changed while preparing'
        for key, digest in baseline.items():
            if key not in ('application.xml', 'mods/loader-manifest.txt'): assert r.sha(m.RUNTIME / key) == digest, key
        memory_before_air = memory_gate()
        options = ['--name', args.name, '--high-qos', '--land', 'random_mane', '--encounter', '--fixed-enemies',
            '--benchmark', args.mode, '--short', '--stable-motion', '--native-input-motion', '--native-sprint',
            '--player-fire', '--combat-route', '--combat-route-length', '200', '--window-width', '2048',
            '--window-height', '1123', '--no-lighting', '--no-wall', '--draw-control', 'rcnative']
        if args.mode == 'normal':
            options += ['--native-room-x', '2', '--native-room-y', '4', '--native-route-x', '480', '--native-route-y', '119']
        else: options += ['--expect-no-signs']
        original_cpu = m.cpu_owned
        try:
            try:
                m.cpu_owned = aligned_cpu_owned(original_cpu)
                m.run_owned(m.parse_args(options), lease)
            finally:
                m.cpu_owned = original_cpu
                if folder.exists():
                    r.save(folder / 'probe-build.json', probe)
                    r.save(folder / 'runner-inputs.json', dict(options=options, baseline=baseline,
                        runnerInputs=scripts, compilerInputs=compiler, fixtureInputs=fixture,
                        probeBuildPath=str(path), pairedEvidence=args.paired_evidence, hostSHA256=HOST,
                        environmentControlVersion=VERSION, memoryBefore=memory_before, memoryBeforeAir=memory_before_air,
                        requiredAvailableCommit=4*1024**3, requiredAvailablePhysical=2*1024**3))
            assert baseline == r.baseline() and scripts == runner_inputs() and fixture == fixture_inputs()
            assert compiler == support.compiler_inputs()
            verify_probe(path, baseline, scripts, compiler, fixture)
            result, inputs = r.result(args.name)
            for key, digest in baseline.items():
                if key not in ('application.xml', 'mods/loader-manifest.txt'): assert inputs[key] == digest, key
            assert inputs[base.PROBE_PATH] == probe['probeSHA256']
            assert 'cameraHold' not in result and 'cameraPrewarm' not in result
            policy = r.read(folder / 'process-policy.json')
            assert not policy['performanceEligible'] and not policy.get('runFailure')
            assert not policy.get('memoryAbort') and not policy.get('otherAirProcessIds')
            summary = dense.summarize(result, args)
            summary.update(environmentControlVersion=VERSION, hostSHA256=HOST, complete=True, incomplete=False,
                seedReceiptSHA256=SEED_SHA, seedProbeSHA256=SEED_PROBE, clockAlignment=alignment(result, policy))
            if reference:
                matched = all(summary[k] == reference[k] for k in
                    ('normalizedRoute', 'nativeRouteHash', 'selectedCombatCorridorTiles', 'viewport'))
                summary['pairedComparison'] = dict(evidence=args.paired_evidence, matchedTerrainAndProbe=matched,
                    previous=reference['continuous'], current=summary['continuous'], exactCausalAcceptance=False)
            summary['limitations'] += [
                'Only two in-memory UTC/getTimer anchors differ from original frozen 39A probe source; no new per-frame AS branch or IO.',
                'No camera hold/hide or new 177-block prewarm; original dense-sprint-2 preparation remains.',
                'Owned CPU is summed across all process threads and complete one-second intervals inside measurement; not main-thread or exact-phase CPU.',
                'UTC/timer bracketing and endpoint delay are retained; no CPU extrapolation or frame-time subtraction.',
                'Current installed A796 includes the tint correction, so comparison with prior ABE2 is not an identical-host causal test.',
                'System CPU, page faults and scheduling are not measured by this minimal alignment control.']
            r.save(folder / 'summary.json', summary)
            print(json.dumps(dict(name=args.name, mode=args.mode, continuous=summary['continuous'],
                qualification=summary['qualification'], alignedProcessCoreEquivalent=summary['clockAlignment']['meanCoreEquivalent']),
                ensure_ascii=False), flush=True)
            assert summary['qualification']['passed']
            assert not reference or summary['pairedComparison']['matchedTerrainAndProbe']
            lease.outcome = 'passed'; lease.note = 'Frozen dense environment control completed; no production performance acceptance'
        except Exception as error:
            if folder.exists() and not (folder / 'summary.json').exists():
                raw = r.read(folder / 'storage/result.json') if (folder / 'storage/result.json').exists() else {}
                r.save(folder / 'summary.json', dict(name=args.name, mode=args.mode, environmentControlVersion=VERSION,
                    hostSHA256=HOST, complete=False, incomplete=True, qualification=dict(passed=False), error=repr(error),
                    diagnosticOnly=True, performanceEligible=False, performanceAcceptance=False, deployed=False,
                    completedNativeSamples=len(raw.get('samples', [])), environmentClock=raw.get('environmentClock')))
            raise


base.OUT = HERE / 'probe-builds'
base.runner_inputs = runner_inputs
base.candidate_inputs = fixture_inputs
if __name__ == '__main__': main()
