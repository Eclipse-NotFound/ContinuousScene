"""Installed-path terminal tint smoke; actual deployed host must match audited candidate."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys
import uuid

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
BUILD = HERE.parents[3]
HOST = 'ABE2B65EDF3D0E4E0FA8ECA76A60E577D40E47F20B9ACECEBEC7730849A2602A'
CS = '7F1F2961C6E299D949423591F3C65C610C2EAEFA7FC72E8A583A402770D6B51F'
TARGET = 'fe.graph.Grafon::0:1:sceneUpdateEntityColor'
TARGETS = [TARGET, 'fe.graph.Grafon::0:1:sceneEntitySameColor']


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base = load('tint_native_support', BUILD / 'native-input-combat-run.py')
patch = load('tint_source_patch', HERE / 'probe_patch.py')
r, m = base.r, base.m
base.FORMAL_HOST = HOST


def host_inputs(path):
    path = path.resolve()
    receipt = r.read(path)
    assert receipt['base'] == HOST and receipt['target'] == TARGET and receipt['targets'] == TARGETS
    assert receipt['productionCandidate'] and not receipt['deployed']
    folder = path.parent
    required = {path: r.sha(path), folder / 'pfe.swf': receipt['candidate'],
                folder / 'pfe.xml': receipt['candidateXML'], folder / 'semantic-audit.json': receipt['audit']}
    required.update({Path(p): value for p, value in receipt['sourceInputs'].items()})
    for p, digest in required.items():
        assert r.sha(p) == digest, str(p)
    audit = r.read(folder / 'semantic-audit.json')
    assert audit['passed'] and audit['auditTarget'] == TARGET
    assert audit['baseSHA256'] == HOST and audit['candidateSHA256'] == receipt['candidate']
    assert audit['baseXMLSHA256'] == receipt['baseXML'] and audit['candidateXMLSHA256'] == receipt['candidateXML']
    assert audit['actualChangedBodies'] == audit['allowedChangedMethods'] == TARGETS
    assert audit['unchangedMethodBodies'] == 5769 and audit['unchangedClassLayouts'] == 1016
    assert not audit['addedFields'] and not audit['addedMethods'] and not audit['importedClassCopied']
    for key in ('methodAndClassIndicesPreserved', 'originalConstantPoolPreserved',
                'nonABCSWFEnvelopePreserved', 'preservedOriginalLayout', 'constructorsPreserved'):
        assert audit[key] is True, key
    assert audit['wrapperSHA256'] == r.sha(folder / 'audit.py')
    assert r.sha(r.ROOT / 'pfe.swf') == receipt['candidate'], 'Installed host is not the audited candidate'
    return dict(kind='installed', path=str(r.ROOT / 'pfe.swf'), artifactPath=str(folder / 'pfe.swf'), sha256=receipt['candidate'],
                inputs={str(p): value for p, value in required.items()}, receiptPath=str(path))


def runner_inputs():
    files = [Path(__file__), HERE / 'probe_patch.py', patch.SOURCE]
    files += [BUILD / name for name in ('native-input-combat-run.py', 'sleeping-root-r2-run.py',
        'sleeping-root-r2-build.py', 'enemy-release.py', 'enemy-speed.py', 'motion-test.py', 'profile-vision.py')]
    files += [r.ROOT / 'mods/ModLoader/tools' / name for name in ('test_registry.py', 'air_test_process.py')]
    files.append(base.support.OUT / 'source-provenance.json')
    return {str(p): r.sha(p) for p in files}


def fixture_inputs():
    assert r.sha(patch.SOURCE) == patch.HELPER_SHA, 'Frozen component changed'
    return {str(p): r.sha(p) for p in (patch.SOURCE, HERE / 'probe_patch.py')}


base.runner_inputs = runner_inputs
base.candidate_inputs = fixture_inputs
original_runtime_hashes = m.hashes


def runtime_hashes():
    values = original_runtime_hashes()
    control = m.RUNTIME / patch.CONTROL
    if control.exists():
        values[patch.CONTROL] = r.sha(control)
    return values


m.hashes = runtime_hashes


def compile_probe(lease, baseline, scripts, compiler, fixture):
    source = BUILD.parent / 'src'
    before = base.tree_hashes(source)
    staging = HERE / 'staging' / uuid.uuid4().hex
    patch.prepare(source, staging / 'src')
    after = base.tree_hashes(staging / 'src')
    changed = {key for key in set(before) | set(after) if before.get(key) != after.get(key)}
    assert changed == {'ContinuousSceneMotionProbe.as', patch.HELPER}
    assert before == base.tree_hashes(source), 'Shared source changed during copy'
    origin = dict(sharedSource=str(source), sharedSourceSHA256=before, changed=sorted(changed),
                  stagedSourceSHA256=after, terminalOnly=True, diagnosticOnly=True)
    r.save(staging / 'source-origin.json', origin)
    base.B, base.OUT = staging / 'build', HERE / 'probe-builds'
    path = base.compile_frozen_probe(lease, baseline, scripts, compiler, fixture)
    receipt = r.read(path)
    receipt.update(tintProbeVersion='scene-entity-tint-installed-test-1', terminalOnly=True,
        sourceOriginPath=str(staging / 'source-origin.json'), sourceOriginSHA256=r.sha(staging / 'source-origin.json'))
    r.save(path, receipt)
    return path


def verify_probe(path, baseline, scripts, compiler, fixture):
    receipt = base.verify_probe(path, baseline, scripts, compiler, fixture)
    assert receipt['tintProbeVersion'] == 'scene-entity-tint-installed-test-1' and receipt['terminalOnly']
    assert r.sha(Path(receipt['sourceOriginPath'])) == receipt['sourceOriginSHA256']
    assert r.sha(Path(receipt['frozenSourcePath']) / patch.HELPER) == patch.HELPER_SHA
    return receipt


def main():
    assert __debug__, 'Assertions required'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    parser.add_argument('--land', default='random_mane')
    parser.add_argument('--host-build', type=Path, required=True,
                        help='Exact retained two-method candidate build.json; current installation must match')
    parser.add_argument('--compile-probe', action='store_true', required=True,
                        help='Build a fresh frozen probe against the actual installed-input snapshot')
    parser.add_argument('--registry-wait', type=int, default=600)
    args = parser.parse_args()
    assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
    assert not (r.E / args.name).exists(), 'Fresh evidence name required'
    selected = host_inputs(args.host_build)
    with m.Registration(owner='ContinuousScene / installed tint smoke / 01a13816', purpose=args.name,
            run_dir=m.RUNTIME, evidence=r.E / args.name, wait=args.registry_wait) as lease:
        assert not m.air_pids(), 'Other AIR is left untouched'
        baseline, scripts, compiler, fixture = r.baseline(), runner_inputs(), base.support.compiler_inputs(), fixture_inputs()
        assert baseline['pfe.swf'] == selected['sha256'] and baseline[base.CS_PATH] == CS
        base.FORMAL_HOST = selected['sha256']
        path = compile_probe(lease, baseline, scripts, compiler, fixture)
        probe = verify_probe(path, baseline, scripts, compiler, fixture)
        assert selected == host_inputs(args.host_build)
        m.prepare()
        # m.prepare copied the actual installed host. Never substitute the candidate artifact here.
        assert r.sha(m.RUNTIME / 'pfe.swf') == baseline['pfe.swf'] == r.sha(r.ROOT / 'pfe.swf')
        shutil.copy2(probe['probePath'], m.RUNTIME / base.PROBE_PATH)
        assert r.sha(m.RUNTIME / 'pfe.swf') == selected['sha256'] and r.sha(m.RUNTIME / base.CS_PATH) == CS
        assert r.sha(m.RUNTIME / base.PROBE_PATH) == probe['probeSHA256']
        control = m.RUNTIME / patch.CONTROL
        assert not control.exists(), 'Stale control must be inspected, not overwritten'
        controls = dict(version='scene-tint-test-controls-2', expectFixed=True, installedPathSmoke=True,
                        hostSHA256=selected['sha256'], componentSHA256=patch.HELPER_SHA)
        options = ['--name', args.name, '--high-qos', '--land', args.land, '--benchmark', 'scene',
                   '--short', '--window-width', '2048', '--window-height', '1123',
                   '--no-lighting', '--no-wall', '--presentation-check']
        assert baseline == r.baseline() and scripts == runner_inputs() and fixture == fixture_inputs()
        verify_probe(path, baseline, scripts, compiler, fixture)
        r.save(control, controls)
        control_sha = r.sha(control)
        try:
            m.run_owned(m.parse_args(options), lease)
        finally:
            folder = r.E / args.name
            if folder.exists():
                r.save(folder / 'probe-build.json', probe)
                r.save(folder / 'runner-inputs.json', dict(options=options, baseline=baseline, runnerInputs=scripts,
                    compilerInputs=compiler, fixtureInputs=fixture, probeBuildPath=str(path), host=selected,
                    isolatedControl=controls, isolatedControlSHA256=control_sha))
            if control.exists():
                assert r.sha(control) == control_sha, 'Isolated control changed'
                control.unlink()
        result, inputs = r.result(args.name)
        assert baseline == r.baseline() and scripts == runner_inputs() and fixture == fixture_inputs()
        assert compiler == base.support.compiler_inputs() and selected == host_inputs(args.host_build)
        verify_probe(path, baseline, scripts, compiler, fixture)
        for key, value in baseline.items():
            if key not in ('pfe.swf', 'application.xml', 'mods/loader-manifest.txt'):
                assert inputs[key] == value, key
        assert inputs['pfe.swf'] == selected['sha256'] and inputs[patch.CONTROL] == control_sha
        assert inputs[base.PROBE_PATH] == probe['probeSHA256'] and result['tintHostControl'] == controls
        policy = r.read(folder / 'process-policy.json')
        assert policy['desktopPolicy'] == 'private' and not policy['performanceEligible']
        assert not policy.get('runFailure') and not policy.get('memoryAbort') and not policy['otherAirProcessIds']
        c = result['tintComponents']
        assert c['passed'] and c['terminalOnly'] and c['expectFixed'] == controls['expectFixed']
        assert c['cases'] and all(case['passed'] for case in c['cases']) and c['restore']['passed']
        assert not c['restore']['privateColorCacheRestored'] and c['restore']['terminalProcessRequired']
        assert c['residualReproduced'] == c['ordinaryResidualReproduced'] == (not controls['expectFixed'])
        assert c['nativeCalls'] >= 14 and c['version'] == 'scene-entity-tint-components-2'
        assert not result['samples'], 'Terminal component must never enter timing'
        summary = dict(name=args.name, qualification=dict(passed=True), componentsOnly=True, verification=c,
            diagnosticOnly=True, performanceEligible=False, performanceAcceptance=False, deployed=False,
            hostKind=selected['kind'], hostSHA256=selected['sha256'], installedHostSHA256=selected['sha256'],
            candidateBaseSHA256=HOST, installedPathSmoke=True, copiedActualInstalledHost=True,
            isolatedControl=controls, probeBuildPath=str(path),
            meaning='Actual installed-path component smoke passed; no performance claim')
        r.save(folder / 'summary.json', summary)
        lease.outcome = 'passed'
        lease.note = summary['meaning'] + '; owned terminal process only; runner does not deploy'
        print(json.dumps(dict(name=args.name, passed=True, expectFixed=controls['expectFixed'],
            residualReproduced=c['residualReproduced'], cases=len(c['cases']), performanceEligible=False)), flush=True)


if __name__ == '__main__':
    main()
