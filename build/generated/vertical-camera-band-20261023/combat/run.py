"""Camera-band combat regression: unchanged dense-sprint-2 fixture, no deployment."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
BUILD = HERE.parents[2]
PRODUCT = HERE.parent
DENSE_DIR = BUILD / 'generated/combat-near-native-20261023/fixture-audit-v2'
HOST = '80CFD8CF3138EE59CBF6EDA0A1824A9EC960F413BD95E4B90D41DD0322B4FD3D'
XML = 'B92260A7A0DFA80EB129C60AEF273645C32BBBA9B3588770BD7083D6984E7E04'
TARGET = 'fe.inter.Camera::0:1:calc'
VERSION = 'vertical-camera-band-combat-1'
COMPONENT_FILES = ()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


dense = load('camera_band_dense', DENSE_DIR / 'dense-combat-run.py')
dense.FORMAL_RC = 'DF0FA0E2CA952E77E5132E75D71E73558DC919C7B8CDEBA5DA05FC9E94DC01E7'
base, r, m, support = dense.base, dense.r, dense.m, dense.support
original_inputs = dense.runner_inputs
base.FORMAL_HOST = HOST
# Keep the original patch module and fixture files, but put every new staging
# tree and probe build in this task's directory. No shared source is edited.
dense.HERE = HERE


def runner_inputs():
    return dict(original_inputs(), **{str(Path(__file__)): r.sha(Path(__file__))})


def fixture_inputs():
    files = [DENSE_DIR / 'probe_patch.py', DENSE_DIR / 'SceneDenseCombatMetrics.as']
    files.extend(COMPONENT_FILES)
    receipt = r.read(PRODUCT / 'build.json')
    files.extend(Path(path) for path in receipt['sourceInputs'])
    files.extend([Path(receipt['originalPath']), PRODUCT / 'source/fe/inter/Camera.as'])
    for name in ('pfe.swf', 'pfe.xml', 'build.json', 'semantic-audit.json'):
        files.append(PRODUCT / name)
    return {str(path): r.sha(path) for path in files}


def product():
    build, proof = r.read(PRODUCT/'build.json'), r.read(PRODUCT/'semantic-audit.json')
    assert build['version'] == 'vertical-camera-band-1'
    assert build['base'] == HOST and build['baseXML'] == XML and build['target'] == TARGET
    assert r.sha(PRODUCT/'pfe.swf') == build['candidate']
    assert r.sha(PRODUCT/'pfe.xml') == build['candidateXML']
    assert r.sha(PRODUCT/'semantic-audit.json') == build['audit']
    assert build['productionCandidate'] and not build['diagnosticOnly'] and not build['deployed']
    assert build['sourceTransformReversible'] and build['originalCallOrderPreserved']
    assert build['timerCalls'] == 0 and build['carrierStateKey'] == 'verticalCameraState'
    assert not build['newClassMembers'] and not build['newClosures'] and not build['newTryCatchFinally']
    assert proof['passed'] and proof['auditTarget'] == TARGET
    assert proof['baseSHA256'] == HOST and proof['baseXMLSHA256'] == XML
    assert proof['candidateSHA256'] == build['candidate'] and proof['candidateXMLSHA256'] == build['candidateXML']
    assert proof['actualChangedBodies'] == proof['allowedChangedMethods'] == [TARGET]
    assert proof['unchangedMethodBodies'] == 5770 and proof['unchangedClassLayouts'] == 1016
    for key in ('preservedOriginalLayout', 'constructorsPreserved', 'methodAndClassIndicesPreserved',
                'originalConstantPoolPreserved', 'nonABCSWFEnvelopePreserved'):
        assert proof[key] is True, key
    assert proof['addedFields'] == proof['addedMethods'] == []
    assert proof['timerBinding']['callCount'] == 0 and proof['importedClassCopied'] is False
    assert proof['wrapperSHA256'] == r.sha(PRODUCT / 'audit.py')
    assert r.sha(Path(build['originalPath'])) == build['originalSource']
    assert r.sha(PRODUCT / 'source/fe/inter/Camera.as') == build['instrumentedSource']
    for path, digest in build['sourceInputs'].items():
        assert r.sha(Path(path)) == digest, path
    return build


def component(name, build, baseline):
    global COMPONENT_FILES
    assert name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in name)
    folder = r.E / name
    result, inputs = r.result(name)
    value = r.read(folder / 'summary.json')
    assert value['qualification']['passed'] and value['hostKind'] == 'candidate'
    assert value['componentsOnly'] and value['hostSHA256'] == build['candidate']
    assert value['installedHostSHA256'] == HOST and not value['deployed'] and not value['performanceEligible']
    checks = value['verification']
    assert checks['version'] == 'vertical-camera-components-1'
    assert checks['passed'] and checks['terminalOnly'] and checks['expectCandidate']
    assert checks['cases'] and all(case['passed'] for case in checks['cases']) and checks['restore']['passed']
    assert result['verticalCameraComponents'] == checks
    assert not result.get('verticalMotion') and not result['samples']
    control = dict(version='vertical-camera-band-test-controls-1', componentsOnly=True,
        expectedCandidate=True, hostSHA256=build['candidate'])
    assert value['isolatedControl'] == result['cameraBandHostControl'] == control
    recorded = r.read(folder / 'runner-inputs.json')
    assert recorded['isolatedControl'] == control and recorded['baseline'] == baseline
    assert inputs['camera-band-controls.json'] == recorded['isolatedControlSHA256']
    assert recorded['host']['kind'] == 'candidate' and recorded['host']['sha256'] == build['candidate']
    assert recorded['host']['inputs'][str(PRODUCT / 'build.json')] == r.sha(PRODUCT / 'build.json')
    for key, digest in baseline.items():
        if key not in ('application.xml', 'mods/loader-manifest.txt'):
            assert inputs[key] == (build['candidate'] if key == 'pfe.swf' else digest), key
    probe = r.read(folder / 'probe-build.json')
    assert probe['verticalMotionVersion'] == 'vertical-camera-band-test-1' and probe['componentsOnly']
    assert not probe['growthRequested'] and probe['diagnosticOnly'] and not probe['deployed']
    assert inputs[base.PROBE_PATH] == probe['probeSHA256'] == r.sha(Path(probe['probePath']))
    assert base.tree_hashes(Path(probe['frozenSourcePath'])) == probe['frozenSourceSHA256']
    assert r.sha(Path(probe['sourceOriginPath'])) == probe['sourceOriginSHA256']
    policy = r.read(folder / 'process-policy.json')
    assert not policy['performanceEligible'] and not policy.get('runFailure')
    COMPONENT_FILES = tuple(folder / item for item in ('summary.json', 'storage/result.json', 'inputs.json',
        'process-policy.json', 'loader-check.json', 'storage/tdfc.log', 'probe-build.json', 'runner-inputs.json'))
    return value


def main():
    assert __debug__
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--name', required=True)
    p.add_argument('--host-kind', choices=['baseline', 'candidate'], required=True)
    p.add_argument('--mode', choices=['scene', 'normal'], default='scene')
    p.add_argument('--host-build', type=Path, default=PRODUCT / 'build.json')
    p.add_argument('--component-evidence', required=True)
    p.add_argument('--paired-evidence')
    p.add_argument('--registry-wait', type=int, default=600)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--compile-probe', action='store_true')
    g.add_argument('--probe-build', type=Path)
    a = p.parse_args()
    assert all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in a.name)
    folder = r.E/a.name
    assert not folder.exists(), 'Preserve evidence'
    assert not a.paired_evidence or a.probe_build
    assert a.host_build.resolve() == PRODUCT / 'build.json', 'Only this camera candidate family'
    with m.Registration(owner='ContinuousScene / camera-band dense combat / 01a13816',
            purpose=a.name, run_dir=m.RUNTIME, evidence=folder, wait=a.registry_wait) as lease:
        assert not m.air_pids(), 'Other AIR remains untouched'
        build, baseline = product(), r.baseline()
        component(a.component_evidence, build, baseline)
        scripts, compiler, fixture = runner_inputs(), support.compiler_inputs(), fixture_inputs()
        assert baseline['pfe.swf'] == base.FORMAL_HOST and baseline[base.CS_PATH] == base.FORMAL_CS
        assert baseline[dense.RC] == dense.FORMAL_RC
        path = dense.compile_probe(lease, baseline, scripts, compiler, fixture) if a.compile_probe else a.probe_build.resolve()
        probe = dense.verify_probe(path, baseline, scripts, compiler, fixture)
        reference = None
        if a.paired_evidence:
            assert all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in a.paired_evidence)
            r.result(a.paired_evidence)
            ref_dir = r.E/a.paired_evidence
            reference = r.read(ref_dir/'summary.json')
            assert reference['cameraBandCombatVersion'] == VERSION and reference['mode'] == a.mode
            assert reference['qualification']['passed'], 'Unqualified reference workload'
            assert reference['hostKind'] in ('baseline', 'candidate')
            assert reference['hostKind'] != a.host_kind
            assert reference['hostSHA256'] == (build['candidate'] if reference['hostKind'] == 'candidate' else HOST)
            assert r.read(ref_dir/'probe-build.json')['probeSHA256'] == probe['probeSHA256']
            assert r.read(ref_dir/'runner-inputs.json')['baseline'] == baseline
            assert r.read(ref_dir/'runner-inputs.json')['fixtureInputs'] == fixture
            assert r.read(ref_dir/'runner-inputs.json')['runnerInputs'] == scripts
            assert r.read(ref_dir/'runner-inputs.json')['compilerInputs'] == compiler
            assert reference['componentEvidence'] == a.component_evidence
        m.prepare()
        if a.host_kind == 'candidate': shutil.copy2(PRODUCT/'pfe.swf', m.RUNTIME/'pfe.swf')
        shutil.copy2(probe['probePath'], m.RUNTIME/base.PROBE_PATH)
        host_sha = build['candidate'] if a.host_kind == 'candidate' else HOST
        assert r.sha(m.RUNTIME/'pfe.swf') == host_sha
        for key in (base.CS_PATH, dense.RC): assert r.sha(m.RUNTIME/key) == baseline[key]
        options = ['--name', a.name, '--high-qos', '--land', 'random_mane', '--encounter', '--fixed-enemies',
            '--benchmark', a.mode, '--short', '--stable-motion', '--native-input-motion', '--native-sprint',
            '--player-fire', '--combat-route', '--combat-route-length', '200', '--window-width', '2048',
            '--window-height', '1123', '--no-lighting', '--no-wall', '--draw-control', 'rcnative']
        if a.mode == 'normal':
            options += ['--native-room-x', '2', '--native-room-y', '4', '--native-route-x', '480', '--native-route-y', '119']
        else: options += ['--expect-no-signs']
        try: m.run_owned(m.parse_args(options), lease)
        finally:
            if folder.exists():
                r.save(folder/'probe-build.json', probe)
                r.save(folder/'product-build.json', build)
                r.save(folder/'runner-inputs.json', dict(options=options, baseline=baseline, runnerInputs=scripts,
                    compilerInputs=compiler, fixtureInputs=fixture, probeBuildPath=str(path), hostKind=a.host_kind,
                    hostSHA256=host_sha, componentEvidence=a.component_evidence, pairedEvidence=a.paired_evidence))
        assert baseline == r.baseline() and scripts == runner_inputs() and fixture == fixture_inputs()
        assert compiler == support.compiler_inputs()
        assert build == product(); dense.verify_probe(path, baseline, scripts, compiler, fixture)
        result, inputs = r.result(a.name)
        for key, digest in baseline.items():
            if key not in ('application.xml', 'mods/loader-manifest.txt'):
                assert inputs[key] == (host_sha if key == 'pfe.swf' else digest), key
        assert inputs[base.PROBE_PATH] == probe['probeSHA256']
        policy = r.read(folder/'process-policy.json')
        assert not policy['performanceEligible'] and not policy.get('runFailure')
        assert not policy.get('memoryAbort') and not policy.get('otherAirProcessIds')
        summary = dense.summarize(result, a)
        summary.update(cameraBandCombatVersion=VERSION, hostKind=a.host_kind, hostSHA256=host_sha,
            componentEvidence=a.component_evidence, installedHostSHA256=HOST,
            productionHostWithoutCounters=True, wholeTaskComplete=False)
        if reference:
            matched = all(summary[k] == reference[k] for k in
                ('normalizedRoute', 'nativeRouteHash', 'selectedCombatCorridorTiles', 'viewport'))
            summary['pairedComparison'] = dict(evidence=a.paired_evidence, matchedTerrainAndProbe=matched,
                previous=reference['continuous'], current=summary['continuous'], exactCausalAcceptance=False)
        summary['limitations'] += ['The candidate changes only Camera.calc; no diagnostic switch, counters or timers in that host method.',
            'The unchanged dense-sprint-2 probe still instruments the workload. These intervals are not uninstrumented final-game FPS.',
            'Horizontal sprint and real firing test combat regression; they do not reproduce or establish the jump-buffer benefit.',
            'Random AI activity/population and prewarming remain recorded confounders. Component success alone is not a speed acceptance.']
        r.save(folder/'summary.json', summary)
        print(json.dumps({k: summary[k] for k in ('name', 'hostKind', 'mode', 'continuous', 'qualification')}, ensure_ascii=False), flush=True)
        assert summary['qualification']['passed']
        assert not reference or summary['pairedComparison']['matchedTerrainAndProbe']
        lease.outcome = 'passed'; lease.note = 'Exact-host workload captured; review paired results before deployment'


base.OUT = HERE/'probe-builds'
base.runner_inputs = runner_inputs
base.candidate_inputs = fixture_inputs
if __name__ == '__main__': main()
