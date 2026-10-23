"""Exact-host dense native workload; candidate versus installed baseline, no deployment."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PRODUCT = HERE.parent / 'fog-last-blocker-production-minimal'
HOST = '80CFD8CF3138EE59CBF6EDA0A1824A9EC960F413BD95E4B90D41DD0322B4FD3D'
XML = 'B92260A7A0DFA80EB129C60AEF273645C32BBBA9B3588770BD7083D6984E7E04'
AUDIT = 'D239A9D614C26F2704E6ED7E6F452ABF49D6D27E0A98CB58EE9BD933F0E19A66'
VERSION = 'fog-last-blocker-production-performance-1'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


dense = load('product_dense', HERE.parents[1] / 'fixture-audit-v2/dense-combat-run.py')
# The RConnect owner deployed aura1 after the EB365 diagnostic pair. New
# baseline/candidate runs both freeze this actual package; old evidence stays separate.
dense.FORMAL_RC = 'DF0FA0E2CA952E77E5132E75D71E73558DC919C7B8CDEBA5DA05FC9E94DC01E7'
base, r, m, support = dense.base, dense.r, dense.m, dense.support
original_inputs, original_fixture = dense.runner_inputs, dense.fixture_inputs


def runner_inputs():
    return dict(original_inputs(), **{str(Path(__file__)): r.sha(Path(__file__))})


def fixture_inputs():
    result = original_fixture()
    for name in ('pfe.swf', 'pfe.xml', 'build.json', 'semantic-audit.json'):
        result[str(PRODUCT / name)] = r.sha(PRODUCT / name)
    return result


def product():
    assert all(x is not None for x in (HOST, XML, AUDIT)), 'Unreviewed product'
    assert r.sha(PRODUCT/'pfe.swf') == HOST and r.sha(PRODUCT/'pfe.xml') == XML
    assert r.sha(PRODUCT/'semantic-audit.json') == AUDIT
    build, proof = r.read(PRODUCT/'build.json'), r.read(PRODUCT/'semantic-audit.json')
    assert build['base'] == base.FORMAL_HOST and build['candidate'] == HOST
    assert build['candidateXML'] == XML and build['audit'] == AUDIT
    assert build['productionCandidate'] and not build['diagnosticOnly'] and not build['deployed']
    assert proof['passed'] and proof['actualChangedBodies'] == ['fe.loc.Location::0:1:lighting']
    assert proof['unchangedMethodBodies'] == 5770 and proof['unchangedClassLayouts'] == 1016
    assert proof['preservedOriginalLayout'] and proof['constructorsPreserved']
    assert proof['originalConstantPoolPreserved'] and proof['nonABCSWFEnvelopePreserved']
    assert proof['addedFields'] == proof['addedMethods'] == []
    assert proof['timerBinding']['callCount'] == 0
    for path, digest in build['sourceInputs'].items():
        assert r.sha(Path(path)) == digest, path
    return build


def component(name):
    assert name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in name)
    value = r.read(r.E/name/'summary.json')
    assert value['qualification']['passed'] and value['hostKind'] == 'candidate'
    assert value['hostSHA256'] == HOST and value['referenceEvidence']
    checks = value['verification']
    assert checks['valid'] and checks['equal'] and checks['restored']
    assert len(checks['cases']) == 91
    return value


def main():
    assert __debug__
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--name', required=True)
    p.add_argument('--host-kind', choices=['baseline', 'candidate'], required=True)
    p.add_argument('--mode', choices=['scene', 'normal'], required=True)
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
    assert all(x is not None for x in (HOST, XML, AUDIT)), 'Unreviewed product'
    with m.Registration(owner='ContinuousScene / exact production combat / 01a13816',
            purpose=a.name, run_dir=m.RUNTIME, evidence=folder, wait=a.registry_wait) as lease:
        assert not m.air_pids(), 'Other AIR remains untouched'
        build = product(); component(a.component_evidence)
        baseline, scripts, compiler, fixture = r.baseline(), runner_inputs(), support.compiler_inputs(), fixture_inputs()
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
            assert reference['productPerformanceVersion'] == VERSION and reference['mode'] == a.mode
            assert reference['qualification']['passed'], 'Unqualified reference workload'
            assert reference['hostKind'] in ('baseline', 'candidate')
            assert reference['hostKind'] != a.host_kind
            assert reference['hostSHA256'] == (HOST if reference['hostKind'] == 'candidate' else base.FORMAL_HOST)
            assert r.read(ref_dir/'probe-build.json')['probeSHA256'] == probe['probeSHA256']
            assert r.read(ref_dir/'runner-inputs.json')['baseline'] == baseline
            assert r.read(ref_dir/'runner-inputs.json')['fixtureInputs'] == fixture
        m.prepare()
        if a.host_kind == 'candidate': shutil.copy2(PRODUCT/'pfe.swf', m.RUNTIME/'pfe.swf')
        shutil.copy2(probe['probePath'], m.RUNTIME/base.PROBE_PATH)
        host_sha = HOST if a.host_kind == 'candidate' else base.FORMAL_HOST
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
        summary.update(productPerformanceVersion=VERSION, hostKind=a.host_kind, hostSHA256=host_sha,
            componentEvidence=a.component_evidence, productionHostWithoutCounters=True, wholeTaskComplete=False)
        if reference:
            matched = all(summary[k] == reference[k] for k in
                ('normalizedRoute', 'nativeRouteHash', 'selectedCombatCorridorTiles', 'viewport'))
            summary['pairedComparison'] = dict(evidence=a.paired_evidence, matchedTerrainAndProbe=matched,
                previous=reference['continuous'], current=summary['continuous'], exactCausalAcceptance=False)
        summary['limitations'] += ['The candidate host has no diagnostic switch, counters or timers; comparison requires separate processes.',
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
