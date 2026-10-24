"""Registered, read-only native fog coverage census; scene only, never performance acceptance."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys
import uuid

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
VERSION = 'occlusion-census-1'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


control = load('occlusion_dense_control', HERE.parent / 'shell-stop-candidate/combat_run.py')
dense, base, r, m = control.dense, control.base, control.r, control.m
support = dense.support
patch = load('occlusion_census_patch', HERE / 'probe_patch.py')
CHANGED = patch.CHANGED


def runner_inputs():
    paths = [HERE / 'run.py', HERE / 'probe_patch.py', patch.HELPER]
    return dict(control.runner_inputs(), **{str(p): r.sha(p) for p in paths})


def fixture_inputs():
    old = control.seed()
    paths = [control.SEED_RECEIPT, Path(old['probePath']), Path(old['sourceOrigin']),
             patch.HELPER, HERE / 'probe_patch.py', support.OUT / 'source-provenance.json']
    return {str(p): r.sha(p) for p in paths}


def compile_probe(lease, baseline, scripts, compiler, fixture):
    old = control.seed(); staging = HERE / 'source-staging' / uuid.uuid4().hex
    patch.prepare(Path(old['frozenSourcePath']), staging / 'src')
    after = base.tree_hashes(staging / 'src')
    changed = sorted(k for k in set(after) | set(old['frozenSourceSHA256'])
                     if after.get(k) != old['frozenSourceSHA256'].get(k))
    assert changed == CHANGED and len(after) == 86
    origin = staging / 'source-origin.json'
    r.save(origin, dict(version=VERSION, seedReceiptSHA256=control.SEED_SHA,
        seedProbeSHA256=control.PROBE, seedSourceSHA256=old['frozenSourceSHA256'],
        stagedSHA256=after, changed=changed, fixtureInputs=fixture))
    base.B = staging / 'build'
    path = base.compile_frozen_probe(lease, baseline, scripts, compiler, fixture)
    value = r.read(path)
    value.update(occlusionCensusVersion=VERSION, denseFixture=dense.VERSION,
                 sourceOrigin=str(origin), sourceOriginSHA256=r.sha(origin))
    r.save(path, value); return path


def verify_probe(path, baseline, scripts, compiler, fixture):
    value = base.verify_probe(path, baseline, scripts, compiler, fixture)
    assert value['occlusionCensusVersion'] == VERSION and value['denseFixture'] == dense.VERSION
    origin_path = Path(value['sourceOrigin']); assert r.sha(origin_path) == value['sourceOriginSHA256']
    origin, old = r.read(origin_path), control.seed()
    assert origin['seedReceiptSHA256'] == control.SEED_SHA and origin['seedProbeSHA256'] == control.PROBE
    assert origin['seedSourceSHA256'] == old['frozenSourceSHA256'] and origin['changed'] == CHANGED
    assert origin['stagedSHA256'] == value['frozenSourceSHA256'] and origin['fixtureInputs'] == fixture
    frozen = Path(value['frozenSourcePath'])
    source = (Path(old['frozenSourcePath']) / CHANGED[0]).read_text('utf-8-sig')
    assert (frozen / CHANGED[0]).read_text('utf-8-sig') == patch.transform(source)
    assert r.sha(frozen / CHANGED[1]) == r.sha(patch.HELPER)
    return value


def census(result):
    marker = result['occlusionCensus']
    assert marker == dict(version=VERSION, readOnly=True, diagnosticOnly=True,
                          performanceEligible=False, measurementAffected=True)
    snapshots = []; reasons = {}
    for i, row in enumerate(result['samples']):
        values = row['occlusionCensus']
        assert [x['frame'] for x in values] == [-1] + list(range(29, 300, 30))
        for x in values:
            assert x['segment'] == i and x['version'] == VERSION and x['errors'] == []
            assert x['readOnly'] and x['diagnosticOnly'] and not x['performanceEligible']
            assert x['rootCountNotUnitCount'] and x['areaIsSummedBoundsNotUnion']
            assert 0 <= x['onScreenOccluded'] <= x['occluded'] <= x['eligible'] <= x['roots']
            assert len(x['covered']) == x['occluded'] and x['elapsedMs'] >= 0
            assert x['valid'] or x.get('reason')
            if x['valid']: assert x['roots'] == x['occluded'] + sum(x['skipped'].values())
            else: reasons[x['reason']] = reasons.get(x['reason'], 0) + 1
            snapshots.append(x)
    assert len(snapshots) == 44
    established = any(x['valid'] and x['eligible'] > 0 for x in snapshots)
    return dict(snapshotCount=44, validSnapshots=sum(x['valid'] for x in snapshots),
        coverageEstablished=established, applicability='applicable' if established else 'not-applicable',
        skippedSnapshotReasons=reasons,
        fullyOccludedObserved=any(x['valid'] and x['occluded'] > 0 for x in snapshots),
        onScreenOccludedObserved=any(x['valid'] and x['onScreenOccluded'] > 0 for x in snapshots),
        totalObservationMs=sum(x['elapsedMs'] for x in snapshots),
        snapshots=snapshots, diagnosticOnly=True, performanceEligible=False,
        limitations=['Roots are display children, not distinct units; no unit/weapon ownership inferred.',
            'Areas sum projected bounding rectangles, not pixel coverage or a spatial union.',
            'Only fully black native pixels after all eligibility gates prove coverage; skipped roots remain unknown.',
            'No display/world writes, draw calls or timeline advancement; bounds and pixel reads still incur observation cost.',
            'These 44 observations contaminate timing; this run cannot accept a performance improvement.'])


def main():
    assert __debug__
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    parser.add_argument('--mode', choices=['scene'], default='scene')
    parser.add_argument('--registry-wait', type=int, default=600)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--compile-probe', action='store_true')
    group.add_argument('--probe-build', type=Path)
    args = parser.parse_args()
    assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
    folder = r.E / args.name; assert not folder.exists(), 'Preserve prior evidence'
    record = dict(version=VERSION, mode='scene', diagnosticOnly=True, performanceEligible=False)
    with m.Registration(owner='ContinuousScene / fog coverage census / 01a13816', purpose=args.name,
                        run_dir=m.RUNTIME, evidence=folder, wait=args.registry_wait) as lease:
        try:
            assert not m.air_pids(), 'Other AIR remains untouched'
            memory = control.memory_gate()
            baseline, scripts, compiler, fixture = r.baseline(), runner_inputs(), support.compiler_inputs(), fixture_inputs()
            for key, digest in control.PINS.items(): assert baseline[key] == digest, key
            record.update(baseline=baseline, runnerInputs=scripts, compilerInputs=compiler,
                          fixtureInputs=fixture, memoryBefore=memory, hostSHA256=control.HOST)
            path = compile_probe(lease, baseline, scripts, compiler, fixture) if args.compile_probe else args.probe_build.resolve()
            probe = verify_probe(path, baseline, scripts, compiler, fixture)
            m.prepare(); shutil.copy2(probe['probePath'], m.RUNTIME / base.PROBE_PATH)
            for key, digest in baseline.items():
                if key not in ('application.xml', 'mods/loader-manifest.txt'): assert r.sha(m.RUNTIME / key) == digest, key
            assert baseline == r.baseline() and scripts == runner_inputs()
            record.update(probeBuildPath=str(path), probeSHA256=probe['probeSHA256'],
                          options=control.options(args), memoryBeforeAir=control.memory_gate())
            try: m.run_owned(m.parse_args(record['options']), lease)
            finally:
                if folder.exists():
                    r.save(folder / 'probe-build.json', probe)
                    r.save(folder / 'runner-inputs.json', record)
            assert baseline == r.baseline() and scripts == runner_inputs() and fixture == fixture_inputs()
            assert compiler == support.compiler_inputs()
            verify_probe(path, baseline, scripts, compiler, fixture)
            result, actual = r.result(args.name)
            assert len(result['assertions']) == 26
            for key, digest in baseline.items():
                if key not in ('application.xml', 'mods/loader-manifest.txt'): assert actual[key] == digest, key
            assert actual[base.PROBE_PATH] == probe['probeSHA256']
            policy = r.read(folder / 'process-policy.json')
            assert policy['desktopPolicy'] == 'private' and not policy['performanceEligible']
            assert not policy.get('runFailure') and not policy.get('memoryAbort') and not policy.get('otherAirProcessIds')
            workload = dense.summarize(result, args); verification = census(result)
            summary = dict(version=VERSION, name=args.name, verification=verification, workload=workload,
                hostSHA256=control.HOST, probeSHA256=probe['probeSHA256'], resultSHA256=r.sha(folder / 'storage/result.json'),
                complete=True, diagnosticOnly=True, performanceEligible=False, performanceAcceptance=False, deployed=False)
            r.save(folder / 'summary.json', summary)
            assert workload['qualification']['passed']
            lease.outcome = 'passed'; lease.note = 'Read-only native fog census: ' + verification['applicability'] + '; no performance acceptance'
            print(json.dumps(dict(name=args.name, snapshots=44, valid=verification['validSnapshots'],
                coverageEstablished=verification['coverageEstablished'], observationMs=verification['totalObservationMs'])), flush=True)
        except BaseException as error:
            lease.outcome = 'failed'; lease.note = repr(error)
            folder.mkdir(parents=True, exist_ok=True)
            r.save(folder / 'runner-failure.json', dict(record, error=repr(error), complete=False, deployed=False))
            raise


base.OUT = HERE / 'probe-builds'
base.runner_inputs = runner_inputs
base.candidate_inputs = fixture_inputs
if __name__ == '__main__': main()
