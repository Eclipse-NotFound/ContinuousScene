"""Native paint-stamp tolerance/accumulation component; no performance acceptance."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys
import uuid

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
HELPER = HERE / 'tests/SceneDecalStampProof.as'
VERSION = 'decal-stamp-tolerance-runner-1'
HOST = '80CFD8CF3138EE59CBF6EDA0A1824A9EC960F413BD95E4B90D41DD0322B4FD3D'
RC = 'DF0FA0E2CA952E77E5132E75D71E73558DC919C7B8CDEBA5DA05FC9E94DC01E7'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


dense = load('stamp_tolerance_dense', HERE.parents[1] / 'fixture-audit-v2/dense-combat-run.py')
base, r, m, support = dense.base, dense.r, dense.m, dense.support
# This new wrapper preserves the installed lighting optimization and owner RC.
# Historical frozen runners and their negative evidence remain unchanged.
base.FORMAL_HOST, dense.FORMAL_RC = HOST, RC
original_inputs, original_fixture = dense.runner_inputs, dense.fixture_inputs


def runner_inputs():
    return dict(original_inputs(), **{str(Path(__file__)): r.sha(Path(__file__))})


def fixture_inputs():
    return dict(original_fixture(), **{str(HELPER): r.sha(HELPER)})


def once(text, before, after):
    assert text.count(before) == 1, ('Source anchor drift', before)
    return text.replace(before, after, 1)


def prepare(source, destination):
    dense.patcher.prepare(source, destination)
    path = destination / 'ContinuousSceneMotionProbe.as'
    text = path.read_text('utf-8-sig')
    text = once(text, '    import tests.SceneEncounter;',
                '    import tests.SceneEncounter;\n    import tests.SceneDecalStampProof;')
    anchor = '                    if(cfg.drawControl=="backgrounds") {\n                        if(!cfg.presentationCheck'
    text = once(text, anchor, '''                    if(cfg.presentationCheck && cfg.drawControl=="rcnative") {
                        if(nativeGroundRun>=10 && w.grafon.sceneViewReady()) {
                            report.decalStampEarlyCheck={groundContactRun:nativeGroundRun,startPose:warmMotion};
                            report.decalStampProof=SceneDecalStampProof.run(w);
                            check("decal-stamp-executed",report.decalStampProof.valid,report.decalStampProof);
                            check("decal-stamp-state-preserved",report.decalStampProof.hostStateUnchanged,report.decalStampProof);
                            finish();return;
                        }
                        if(++age>240)throw new Error("Stamp proof did not reach native ground");
                        return;
                    }
''' + anchor)
    path.write_text(text, 'utf-8')
    shutil.copy2(HELPER, destination / 'tests/SceneDecalStampProof.as')


def main():
    assert __debug__
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    args = parser.parse_args()
    assert all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
    folder = r.E / args.name
    assert not folder.exists(), 'Preserve previous evidence'
    with m.Registration(owner='ContinuousScene / decal tolerance / 01a13816',
            purpose=args.name, run_dir=m.RUNTIME, evidence=folder, wait=600) as lease:
        assert not m.air_pids(), 'Other AIR remains untouched'
        baseline, scripts, compiler, fixture = r.baseline(), runner_inputs(), support.compiler_inputs(), fixture_inputs()
        assert baseline['pfe.swf'] == HOST and baseline[base.CS_PATH] == base.FORMAL_CS
        assert baseline[dense.RC] == RC
        shared = dense.BUILD.parent / 'src'
        before = base.tree_hashes(shared)
        staging = HERE / 'staging' / uuid.uuid4().hex
        prepare(shared, staging / 'src')
        assert before == base.tree_hashes(shared)
        after = base.tree_hashes(staging / 'src')
        changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
        assert changed == sorted(['ContinuousSceneMotionProbe.as', 'tests/SceneEncounter.as',
                                 'tests/SceneDenseCombatMetrics.as', 'tests/SceneDecalStampProof.as']), changed
        origin = staging / 'source-origin.json'
        r.save(origin, dict(version=VERSION, sharedSHA256=before, stagedSHA256=after,
                            changed=changed, fixtureInputs=fixture))
        base.B, base.OUT = staging / 'build', HERE / 'probe-builds'
        path = base.compile_frozen_probe(lease, baseline, scripts, compiler, fixture)
        probe = r.read(path)
        probe.update(denseFixture=dense.VERSION, stampProof=VERSION,
                     sourceOrigin=str(origin), sourceOriginSHA256=r.sha(origin))
        r.save(path, probe)
        dense.verify_probe(path, baseline, scripts, compiler, fixture)
        m.prepare()
        shutil.copy2(probe['probePath'], m.RUNTIME / base.PROBE_PATH)
        assert r.sha(m.RUNTIME / 'pfe.swf') == HOST
        options = ['--name', args.name, '--high-qos', '--land', 'random_mane', '--encounter',
            '--fixed-enemies', '--benchmark', 'scene', '--short', '--stable-motion',
            '--native-input-motion', '--native-sprint', '--player-fire', '--combat-route',
            '--combat-route-length', '200', '--window-width', '2048', '--window-height', '1123',
            '--no-lighting', '--no-wall', '--draw-control', 'rcnative', '--expect-no-signs',
            '--presentation-check']
        try:
            m.run_owned(m.parse_args(options), lease)
        finally:
            if folder.exists():
                r.save(folder / 'probe-build.json', probe)
                r.save(folder / 'runner-inputs.json', dict(options=options, baseline=baseline,
                    runnerInputs=scripts, compilerInputs=compiler, fixtureInputs=fixture, probeBuildPath=str(path)))
        assert baseline == r.baseline() and scripts == runner_inputs() and fixture == fixture_inputs()
        result, inputs = r.result(args.name)
        for key, digest in baseline.items():
            if key not in ('application.xml', 'mods/loader-manifest.txt'):
                assert inputs[key] == digest, key
        assert inputs[base.PROBE_PATH] == probe['probeSHA256']
        policy = r.read(folder / 'process-policy.json')
        assert not policy['performanceEligible'] and not policy.get('runFailure')
        assert not policy.get('memoryAbort') and not policy.get('otherAirProcessIds')
        proof = result['decalStampProof']
        assert proof['valid'] and proof['hostStateUnchanged'] and proof['cases']
        assert proof['requiredHostSHA256'] == HOST
        assert result['decalStampEarlyCheck']['groundContactRun'] >= 10 and not result['samples']
        summary = dict(name=args.name, version=VERSION, diagnosticOnly=True, performanceEligible=False,
            deployed=False, executed=True, pixelEquivalent=proof['equal'], proof=proof)
        r.save(folder / 'summary.json', summary)
        # A tolerance failure is a valid negative experiment; never relabel exact
        # equality or component success as a live workload speed acceptance.
        acceptable = proof['tolerancePassed']
        lease.outcome = 'passed' if acceptable else 'failed'
        lease.note = 'Component only: alpha exact / RGB per-channel <=1; accumulation and edge details in result'
        print(json.dumps(dict(name=args.name, executed=True, exact=proof['equal'],
                              tolerancePassed=acceptable, cases=len(proof['cases'])), ensure_ascii=False), flush=True)


base.runner_inputs, base.candidate_inputs = runner_inputs, fixture_inputs
if __name__ == '__main__':
    main()
