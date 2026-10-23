"""No-counter production lighting component. Never a performance acceptance.

First --host baseline --compile-probe. Then --host candidate with the identical
original --probe-build receipt and --reference-evidence from the passed baseline.
Candidate pins are separate reviewed data, not part of probe compilation inputs.
No game class copies or replacement externs are introduced.
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
DENSE = HERE.parents[1] / 'fixture-audit-v2'
PRODUCT = HERE.parent / 'fog-last-blocker-production-minimal'
HELPER = HERE / 'SceneFogProductCheck.as'
PINS = HERE / 'candidate-pins.json'
VERSION = 'fog-production-legacy-component-1'
FORMAL_RC = 'DF0FA0E2CA952E77E5132E75D71E73558DC919C7B8CDEBA5DA05FC9E94DC01E7'
WITNESS = 'fog-last-blocker-20261023-check-r1'
WITNESS_FILES = {
    'summary.json': '10E79F90E24D6A3B0B489512C462B8ECAF0867797F1171E8AEC6C964CCEDFA32',
    'storage/result.json': '1BFEFACB95CC297E1211809C82C07A39027F7AC654E07FC80738819B32145656',
    'inputs.json': '9D908B74D18019753FF7921C51296EFCC3ABB0A0A2949D28E01F8CCCE62F7287'}
OLD_HELPER = HERE.parent / 'fog-last-blocker/SceneFogLastBlockerProbe.as'
OLD_HELPER_SHA = '9B6278438A08251E6C73BA02C0AE3658403E2A1DA51D9576B744C11CCE628C37'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


dense = load('fog_product_dense', DENSE / 'dense-combat-run.py')
patcher = load('fog_product_patch', HERE / 'probe_patch.py')
base, r, m, support = dense.base, dense.r, dense.m, dense.support
# Explicit current dependency override in this isolated runner, never old source.
dense.FORMAL_RC = FORMAL_RC
original_inputs, original_fixture = dense.runner_inputs, dense.fixture_inputs


def runner_inputs():
    return dict(original_inputs(), **{str(Path(__file__)): r.sha(Path(__file__))})


def witness_inputs():
    values = {}
    for name, expected in WITNESS_FILES.items():
        path = r.E / WITNESS / name
        assert r.sha(path) == expected, 'Original diagnostic evidence changed'
        values[str(path)] = expected
    original = r.read(r.E / WITNESS / 'summary.json')
    assert original['qualification']['passed'] and len(original['verification']['cases']) == 89
    positive = [c for c in original['verification']['cases'] if c.get('requiresCacheHit')]
    assert len(positive) == 4 and all(c['candidate']['cacheHits'] > 0 and c['candidate']['cacheUpdates'] > 0 for c in positive)
    assert r.sha(OLD_HELPER) == OLD_HELPER_SHA
    values[str(OLD_HELPER)] = OLD_HELPER_SHA
    return values


def fixture_inputs():
    values = dict(original_fixture(), **witness_inputs())
    for path in (HELPER, HERE / 'probe_patch.py'):
        values[str(path)] = r.sha(path)
    return values


def selected_host(kind):
    if kind == 'baseline':
        path = dense.BUILD / 'generated/fog-typed/pfe.swf'
        assert r.sha(path) == base.FORMAL_HOST
        return path, base.FORMAL_HOST, {'hostKind': kind, 'hostSHA256': base.FORMAL_HOST}, {str(path): base.FORMAL_HOST}
    pins = r.read(PINS)
    assert set(pins) == {'hostSHA256', 'xmlSHA256', 'auditSHA256'}
    assert all(isinstance(v, str) and len(v) == 64 and set(v) <= set('0123456789ABCDEF') for v in pins.values()), 'Production candidate not yet reviewed/pinned'
    expected = {'pfe.swf': pins['hostSHA256'], 'pfe.xml': pins['xmlSHA256'], 'semantic-audit.json': pins['auditSHA256']}
    for name, digest in expected.items(): assert r.sha(PRODUCT / name) == digest, name
    build, proof = r.read(PRODUCT / 'build.json'), r.read(PRODUCT / 'semantic-audit.json')
    assert build['base'] == base.FORMAL_HOST and build['candidate'] == pins['hostSHA256']
    assert build['candidateXML'] == pins['xmlSHA256'] and build['audit'] == pins['auditSHA256']
    assert build['productionCandidate'] and not build['diagnosticOnly'] and not build['performanceEligible'] and not build['deployed']
    assert proof['passed'] and proof['actualChangedBodies'] == ['fe.loc.Location::0:1:lighting']
    assert proof['unchangedMethodBodies'] == 5770 and proof['unchangedClassLayouts'] == 1016
    assert proof['preservedOriginalLayout'] and proof['constructorsPreserved']
    assert proof['originalConstantPoolPreserved'] and proof['nonABCSWFEnvelopePreserved']
    assert proof['addedFields'] == proof['addedMethods'] == []
    for path, digest in build['sourceInputs'].items(): assert r.sha(Path(path)) == digest, path
    files = {str(PRODUCT / name): r.sha(PRODUCT / name) for name in (*expected, 'build.json')}
    files[str(PINS)] = r.sha(PINS)
    return PRODUCT / 'pfe.swf', pins['hostSHA256'], build, files


def compile_probe(lease, baseline, scripts, compiler, fixture):
    shared = dense.BUILD.parent / 'src'
    before = base.tree_hashes(shared)
    staging = HERE / 'probe-source-staging' / uuid.uuid4().hex
    patcher.prepare(shared, staging / 'src', dense.patcher, HELPER)
    assert before == base.tree_hashes(shared), 'Shared source changed during capture'
    after = base.tree_hashes(staging / 'src')
    changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    assert changed == sorted(['ContinuousSceneMotionProbe.as', 'tests/SceneEncounter.as',
                             'tests/SceneDenseCombatMetrics.as', 'tests/SceneFogProductCheck.as'])
    origin = staging / 'source-origin.json'
    r.save(origin, dict(version=VERSION, sharedSource=str(shared), sharedSHA256=before,
        stagedSource=str(staging / 'src'), stagedSHA256=after, changed=changed, fixtureInputs=fixture))
    base.B = staging / 'build'
    path = base.compile_frozen_probe(lease, baseline, scripts, compiler, fixture)
    receipt = r.read(path)
    receipt.update(denseFixture=dense.VERSION, fogProductComponent=VERSION,
        sourceOrigin=str(origin), sourceOriginSHA256=r.sha(origin))
    r.save(path, receipt)
    return path


def verify_probe(path, baseline, scripts, compiler, fixture):
    probe = dense.verify_probe(path, baseline, scripts, compiler, fixture)
    assert probe['fogProductComponent'] == VERSION
    assert probe['frozenSourceSHA256']['tests/SceneFogProductCheck.as'] == r.sha(HELPER)
    return probe


def validate_verification(v):
    assert v['version'] == 'fog-production-legacy-check-1'
    assert v['valid'] and v['equal'] and v['restored'] and len(v['cases']) == 91
    assert v['positiveOpaque'] and v['positiveWater'] and v['legacyCovered'] == 2 and v['inactiveCovered']
    assert v['negativeCovered'] == 2 and v['weakWaterCovered'] and v['sceneFlagBypassCovered'] == 2
    assert v['cacheHitsMeasured'] is False and v['simulationFramesAdvanced'] == 0
    names = []
    for c in v['cases']:
        names.append(c['name'])
        assert all(c[k] for k in ('equal', 'tilesEqual', 'pixelsEqual', 'stateEqual', 'identityPreserved',
                                  'positiveChange', 'identicalArmInputs', 'noDiagnosticAPI'))
        assert c['referenceTyped'] is False and c['cacheHitsMeasured'] is False
        assert c['candidateTyped'] is (not c['name'].startswith('legacy-'))
        assert c['sceneFlagOnlyBypass'] is c['name'].startswith('scene-flag-false-')
        if c['sceneFlagOnlyBypass']: assert c['sceneLarge'] is False and not c['expectedLastBlockerEligibility'] and c['changedTiles'] > 0
        else: assert c['sceneLarge'] is True
    assert len(set(names)) == 91
    original = r.read(r.E / WITNESS / 'summary.json')['verification']['cases']
    assert names[:89] == [c['name'] for c in original]
    assert names[89:] == ['scene-flag-false-opaque', 'scene-flag-false-water']
    for old, new in zip(original, v['cases']):
        for key in ('dark', 'pattern', 'terrain', 'typed', 'bounds', 'active'):
            actual = new['candidateTyped'] if key == 'typed' else new[key]
            assert actual == old[key], (old['name'], key)
    for name in ('sparse-opaque-low', 'sparse-water-low', 'sparse-opaque-negative-low', 'sparse-opaque-negative-near'):
        c = next(c for c in v['cases'] if c['name'] == name)
        assert c['expectedLastBlockerEligibility'] and c['changedTiles'] > 0


def validate_result(result):
    assert result['ok'] and not result.get('error') and all(c['ok'] for c in result['assertions'])
    validate_verification(result['fogProductVerification'])
    assert result['driver']['forcedPositionCalls'] == 0 and result['nativeInputMotion']['spawn']['calls'] == 1
    assert result['fogProductEarlyCheck']['groundContactRun'] >= 10 and not result['samples']
    assert result['config']['benchmark'] == 'scene' and result['world']['layoutSeed'] == 20261019


def reference_evidence(name, probe, baseline, scripts, compiler, fixture):
    assert name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in name)
    folder = r.E / name
    checked, inputs = r.result(name)
    summary, recorded = r.read(folder / 'summary.json'), r.read(folder / 'runner-inputs.json')
    assert summary['version'] == VERSION and summary['qualification']['passed']
    assert summary['hostKind'] == 'baseline' and summary['hostSHA256'] == base.FORMAL_HOST
    assert summary['referenceEvidence'] is None and summary['verification'] == checked['fogProductVerification']
    validate_result(checked)
    assert recorded['baseline'] == baseline and recorded['runnerInputs'] == scripts
    assert recorded['compilerInputs'] == compiler and recorded['fixtureInputs'] == fixture
    original_receipt = Path(recorded['probeBuildPath'])
    original = verify_probe(original_receipt, baseline, scripts, compiler, fixture)
    copy = r.read(folder / 'probe-build.json')
    assert original == copy and original['probeSHA256'] == probe['probeSHA256']
    assert original['configSHA256'] == probe['configSHA256'] and original['frozenSourceSHA256'] == probe['frozenSourceSHA256']
    for key, digest in baseline.items():
        if key not in ('application.xml', 'mods/loader-manifest.txt'): assert inputs[key] == digest, key
    assert inputs[base.PROBE_PATH] == probe['probeSHA256']
    policy = r.read(folder / 'process-policy.json')
    assert policy['performanceEligible'] is False and not policy.get('runFailure') and not policy.get('memoryAbort') and not policy.get('otherAirProcessIds')
    return checked, {str(folder / path): r.sha(folder / path) for path in
        ('summary.json', 'storage/result.json', 'inputs.json', 'runner-inputs.json', 'probe-build.json', 'process-policy.json')}


def summarize(result, args, host_sha, reference):
    validate_result(result)
    v = result['fogProductVerification']
    if reference:
        assert v['geometry'] == reference['fogProductVerification']['geometry']
        for key in ('width', 'height', 'layoutSeed', 'entryRoomTiles'):
            assert result['world'][key] == reference['world'][key], key
        assert result['viewport'] == reference['viewport']
    return dict(name=args.name, mode='scene', version=VERSION, hostKind=args.host, hostSHA256=host_sha,
        referenceEvidence=args.reference_evidence, qualification=dict(passed=True), verification=v,
        diagnosticOnly=True, performanceEligible=False, performanceAcceptance=False, deployed=False,
        continuous=dict(count=0, notMeasured=True), priorDiagnosticHitEvidence=dict(name=WITNESS, files=WITNESS_FILES,
            observedHere=False, productionCacheHitsMeasured=False),
        limitations=['This compares each host with its preserved BEFC legacy branch in the same state; it does not compare two different-startup states as equal.',
            'The exact frozen probe must first qualify legacy versus typed on BEFC with the same installed dependencies.',
            'The last two cases only change sceneLarge in a large grid; they are not normal-room gameplay tests.',
            'Positive cache-hit counts belong only to the separately pinned diagnostic host. Production has no counters.',
            'Exact Tile/lightBmp equivalence is not whole-stage visual or performance acceptance.'])


def main():
    if not __debug__: raise RuntimeError('Do not disable assertions')
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--name', required=True); p.add_argument('--host', choices=['baseline', 'candidate'], required=True)
    p.add_argument('--reference-evidence')
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--compile-probe', action='store_true'); g.add_argument('--probe-build', type=Path)
    p.add_argument('--registry-wait', type=int, default=600)
    args = p.parse_args()
    assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
    assert (args.host == 'baseline' and not args.reference_evidence) or (args.host == 'candidate' and args.reference_evidence and args.probe_build and not args.compile_probe)
    folder = r.E / args.name
    assert not folder.exists(), 'Preserve existing evidence'
    host_path, host_sha, host_build, host_inputs = selected_host(args.host)
    with m.Registration(owner='ContinuousScene / production fog legacy component / 01a13816', purpose=args.name,
                        run_dir=m.RUNTIME, evidence=folder, wait=args.registry_wait) as lease:
        assert not m.air_pids(), 'Other AIR remains untouched'
        baseline, scripts, compiler, fixture = r.baseline(), runner_inputs(), support.compiler_inputs(), fixture_inputs()
        assert baseline['pfe.swf'] == base.FORMAL_HOST and baseline[base.CS_PATH] == base.FORMAL_CS
        assert baseline[dense.RC] == FORMAL_RC
        path = compile_probe(lease, baseline, scripts, compiler, fixture) if args.compile_probe else args.probe_build.resolve()
        probe = verify_probe(path, baseline, scripts, compiler, fixture)
        reference, reference_inputs = (None, {}) if args.host == 'baseline' else reference_evidence(args.reference_evidence, probe, baseline, scripts, compiler, fixture)
        assert selected_host(args.host)[3] == host_inputs
        m.prepare()
        shutil.copy2(host_path, m.RUNTIME / 'pfe.swf')
        shutil.copy2(probe['probePath'], m.RUNTIME / base.PROBE_PATH)
        assert r.sha(m.RUNTIME / 'pfe.swf') == host_sha
        for key in (base.CS_PATH, dense.RC): assert r.sha(m.RUNTIME / key) == baseline[key]
        options = ['--name', args.name, '--high-qos', '--land', 'random_mane', '--encounter', '--fixed-enemies',
            '--benchmark', 'scene', '--short', '--stable-motion', '--native-input-motion', '--native-sprint',
            '--player-fire', '--combat-route', '--combat-route-length', '200', '--window-width', '2048',
            '--window-height', '1123', '--no-lighting', '--no-wall', '--draw-control', 'rcnative', '--expect-no-signs', '--presentation-check']
        try:
            m.run_owned(m.parse_args(options), lease)
        finally:
            if folder.exists():
                r.save(folder / 'probe-build.json', probe)
                r.save(folder / 'component-host-build.json', host_build)
                r.save(folder / 'runner-inputs.json', dict(options=options, baseline=baseline, runnerInputs=scripts,
                    compilerInputs=compiler, fixtureInputs=fixture, componentHostInputs=host_inputs,
                    probeBuildPath=str(path), referenceEvidence=args.reference_evidence, referenceInputs=reference_inputs))
        assert baseline == r.baseline() and scripts == runner_inputs() and fixture == fixture_inputs()
        assert selected_host(args.host)[3] == host_inputs
        for file, digest in reference_inputs.items(): assert r.sha(Path(file)) == digest
        verify_probe(path, baseline, scripts, compiler, fixture)
        result, inputs = r.result(args.name)
        for key, digest in baseline.items():
            if key not in ('application.xml', 'mods/loader-manifest.txt'): assert inputs[key] == (host_sha if key == 'pfe.swf' else digest), key
        assert inputs[base.PROBE_PATH] == probe['probeSHA256']
        policy = r.read(folder / 'process-policy.json')
        assert policy['performanceEligible'] is False and not policy.get('runFailure')
        assert not policy.get('memoryAbort') and not policy.get('otherAirProcessIds')
        summary = summarize(result, args, host_sha, reference)
        r.save(folder / 'summary.json', summary)
        print(json.dumps({k: summary[k] for k in ('name', 'hostKind', 'hostSHA256', 'referenceEvidence', 'qualification')}, ensure_ascii=False), flush=True)
        lease.outcome = 'passed'; lease.note = '91 same-state legacy/typed component cases; no production hit counter or performance acceptance'


base.runner_inputs = runner_inputs
base.candidate_inputs = fixture_inputs
base.OUT = HERE / 'probe-builds'

if __name__ == '__main__': main()
