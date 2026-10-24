"""Isolated shell-stop host comparison using the unchanged frozen 39A probe.

No compilation, production writes, sceneLarge switching, or additional AS timers.
Each invocation runs one host/mode and retains all 1,200 continuous intervals.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
BUILD = HERE.parents[2]
VERSION = 'shell-stop-combat-1'
TARGET = 'fe.graph.Part::0:1:initVis'
HOST = 'A796827173AF7D6FAB9885FB66ECC62182AB5335918A30C7CCE4C44914A238B7'
BASE_XML = '1D2642C7D55D1F97121738E6AE84996A140EBFEFF686E6706C88CEF82A7338DA'
CANDIDATE = '50D6D718A95891DFC1B64503FE1E7A12E9BCFA5C960BCC5A93668BEC8DD800BD'
CANDIDATE_XML = 'B6DF90F5F886E7BC5920EB4BC79A1C77406F8CB63E7010ED4D0BF8CCA19B2CBF'
AUDIT = '2B605A06CF9582DC19FE681B047A7EEAB637F6473654FABBC561B08120FD342F'
SEED_RECEIPT = BUILD.parent / 'knowledge/experiments/evidence/vertical-camera-band-20261023-combat-candidate-r3/probe-build.json'
SEED_SHA = 'B7ED1EAB8BEE0DC1024D6EF0A56A965F311B97E8CED9A9F32A2BCDE35B35FF13'
PROBE = '39A1497BE832282CAC25E2A508A954432F9F31B15A2FBE5A650AB8C4D9C97E9E'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


dense = load('shell_stop_dense', BUILD / 'generated/combat-near-native-20261023/fixture-audit-v2/dense-combat-run.py')
base, r, m = dense.base, dense.r, dense.m
PINS = {
    'pfe.swf': HOST,
    base.CS_PATH: '7F1F2961C6E299D949423591F3C65C610C2EAEFA7FC72E8A583A402770D6B51F',
    dense.RC: '78C052AEA963F1689B705AE1E14D274916AE1A1F7E81933390CAF8D1A88F4699',
    'mods/RealisticVision/release/RealisticVisionMod.swf': 'BF4AC9CD87272B03FAE7EC22EE67D045F037362F412EE801CAD3F9BA9FE3AFEF',
    'mods/ModLoader/release/ModLoaderMod.swf': '2050E023205E87FDFDF7FBA4B54B9BAD7769868E51767D0BFBE1742CDC7542E2',
    'mods/TDFC/release/TDFCMod.swf': '7ACD45193109267DBBF875240528048AD6F1D09FA3B8B36BAA6F98EBB5FDDCE5',
}


def runner_inputs():
    paths = [Path(__file__), Path(dense.__file__).with_name('probe_patch.py')]
    return dict(dense.runner_inputs(), **{str(p): r.sha(p) for p in paths})


def seed():
    assert r.sha(SEED_RECEIPT) == SEED_SHA
    value = r.read(SEED_RECEIPT)
    assert value['version'] == 'native-input-combat-probe-1' and value['denseFixture'] == dense.VERSION
    assert value['probeSHA256'] == PROBE == r.sha(Path(value['probePath']))
    assert len(value['frozenSourceSHA256']) == 85
    assert value['sharedSourceSnapshotSHA256'] == value['frozenSourceSHA256']
    assert base.tree_hashes(Path(value['frozenSourcePath'])) == value['frozenSourceSHA256']
    assert r.sha(Path(value['configPath'])) == value['configSHA256']
    assert r.sha(Path(value['sourceOrigin'])) == value['sourceOriginSHA256']
    return value


def candidate():
    receipt, audit = r.read(HERE / 'build.json'), r.read(HERE / 'semantic-audit.json')
    assert receipt['version'] == audit['version'] == 'shell-stop-candidate-1'
    assert receipt['base'] == audit['baseSHA256'] == HOST
    assert receipt['baseXML'] == audit['baseXMLSHA256'] == BASE_XML
    assert receipt['target'] == audit['auditTarget'] == TARGET
    for name, expected, receipt_key, audit_key in (
        ('pfe.swf', CANDIDATE, 'candidate', 'candidateSHA256'),
        ('pfe.xml', CANDIDATE_XML, 'candidateXML', 'candidateXMLSHA256')):
        assert r.sha(HERE / name) == receipt[receipt_key] == audit[audit_key] == expected
    assert r.sha(HERE / 'semantic-audit.json') == receipt['audit'] == AUDIT
    assert receipt['productionCandidate'] is True and receipt['installedUnchanged'] is True
    assert receipt['diagnosticOnly'] is False
    for key in ('runtimeVerified', 'performanceEligible', 'deployed'):
        assert receipt[key] is False and audit[key] is False
    assert audit['actualChangedBodies'] == [TARGET]
    assert audit['unchangedMethodBodies'] == 5770 and audit['unchangedClassLayouts'] == 1016
    assert audit['addedFields'] == audit['addedMethods'] == []
    for key in ('passed', 'constructorsPreserved', 'preservedOriginalLayout',
                'methodAndClassIndicesPreserved', 'originalPrivateIdentitiesPreserved',
                'originalBranchesPreserved', 'originalRandomCallsPreserved',
                'untouchedRawTagsPreserved', 'otherABCRawTagPreserved',
                'nonABCSWFEnvelopePreserved', 'otherABCXMLPreserved',
                'originalConstantPoolPrefixBytesPreserved'):
        assert audit[key] is True, key
    assert (audit['addedStringIndex'], audit['addedPublicQNameIndex'],
            audit['newConstants'], audit['newNamespaces']) == (8161, 9705, 2, 0)
    assert r.sha(HERE / 'product.py') == audit['wrapperSHA256']
    assert r.sha(HERE / 'audit.py') == audit['frozenPlanSHA256']
    assert r.sha(HERE / 'static-proof.json') == audit['staticProofSHA256'] == receipt['staticProof']
    assert r.sha(HERE / 'steps.json') == receipt['steps']
    files = dict(receipt['sourceInputs'])
    for path, digest in files.items():
        assert r.sha(Path(path)) == digest, path
    for name in ('build.json', 'semantic-audit.json', 'pfe.swf', 'pfe.xml', 'steps.json'):
        files[str(HERE / name)] = r.sha(HERE / name)
    return dict(buildReceipt=str(HERE / 'build.json'), buildReceiptSHA256=r.sha(HERE / 'build.json'),
                auditSHA256=AUDIT, candidateSHA256=CANDIDATE, candidateXMLSHA256=CANDIDATE_XML,
                inputs=files)


def memory_gate():
    value = m.memory_status()
    assert value['availableCommit'] >= 4 * 1024**3 and value['availablePhysical'] >= 2 * 1024**3, value
    return value


def options(args):
    value = ['--name', args.name, '--high-qos', '--land', 'random_mane', '--encounter', '--fixed-enemies',
        '--benchmark', args.mode, '--short', '--stable-motion', '--native-input-motion', '--native-sprint',
        '--player-fire', '--combat-route', '--combat-route-length', '200', '--window-width', '2048',
        '--window-height', '1123', '--no-lighting', '--no-wall', '--draw-control', 'rcnative']
    if args.mode == 'normal':
        value += ['--native-room-x', '2', '--native-room-y', '4', '--native-route-x', '480', '--native-route-y', '119']
    else:
        value += ['--expect-no-signs']
    return value


def main():
    assert __debug__, 'Do not disable assertions'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', choices=['baseline', 'candidate'], required=True)
    parser.add_argument('--mode', choices=['scene', 'normal'], required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--registry-wait', type=int, default=600)
    args = parser.parse_args()
    assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
    folder = r.E / args.name
    assert not folder.exists(), 'Preserve existing evidence; use a new name'
    host = HOST if args.host == 'baseline' else CANDIDATE
    record = dict(version=VERSION, hostKind=args.host, hostSHA256=host, mode=args.mode,
        probeBuildPath=str(SEED_RECEIPT), seedReceiptSHA256=SEED_SHA, probeSHA256=PROBE,
        reusedFrozenProbe=True, compiled=False, requiredAvailableCommit=4*1024**3,
        requiredAvailablePhysical=2*1024**3, runningAvailableCommitFloor=512*1024**2)
    with m.Registration(owner='ContinuousScene / shell-stop combat / 01a13816', purpose=args.name,
                        run_dir=m.RUNTIME, evidence=folder, wait=args.registry_wait) as lease:
        try:
            assert not m.air_pids(), 'Other AIR remains untouched'
            record['memoryBefore'] = memory_gate()
            baseline, scripts, probe = r.baseline(), runner_inputs(), seed()
            for key, digest in PINS.items():
                assert baseline[key] == digest, key
            proof = candidate() if args.host == 'candidate' else None
            record.update(baseline=baseline, runnerInputs=scripts, candidateProof=proof, options=options(args))
            m.prepare()
            for key, digest in baseline.items():
                if key not in ('application.xml', 'mods/loader-manifest.txt'):
                    assert r.sha(m.RUNTIME / key) == digest, key
            shutil.copy2(probe['probePath'], m.RUNTIME / base.PROBE_PATH)
            if proof:
                shutil.copy2(HERE / 'pfe.swf', m.RUNTIME / 'pfe.swf')
            assert r.sha(m.RUNTIME / 'pfe.swf') == host
            assert r.sha(m.RUNTIME / base.PROBE_PATH) == PROBE
            assert baseline == r.baseline() and scripts == runner_inputs()
            assert not m.air_pids(), 'Other AIR remains untouched'
            record['memoryBeforeAir'] = memory_gate()
            try:
                m.run_owned(m.parse_args(record['options']), lease)
            finally:
                if folder.exists():
                    # Original receipt remains an unchanged historical build receipt.
                    shutil.copy2(SEED_RECEIPT, folder / 'probe-build.json')
                    r.save(folder / 'runner-inputs.json', record)
            assert baseline == r.baseline(), 'Installed inputs changed during isolated run'
            assert scripts == runner_inputs() and probe == seed(), 'Frozen test input changed'
            assert not proof or proof == candidate(), 'Candidate proof/input changed'
            result, actual = r.result(args.name)
            for key, digest in baseline.items():
                if key not in ('application.xml', 'mods/loader-manifest.txt'):
                    assert actual[key] == (host if key == 'pfe.swf' else digest), key
            assert actual[base.PROBE_PATH] == PROBE
            assert len(result['assertions']) == 26
            assert 'cameraHold' not in result and 'cameraPrewarm' not in result
            policy = r.read(folder / 'process-policy.json')
            assert policy['desktopPolicy'] == 'private' and policy['performanceEligible'] is False
            assert not policy.get('runFailure') and not policy.get('memoryAbort') and not policy.get('otherAirProcessIds')
            summary = dense.summarize(result, args)
            summary.update(shellStopCombatVersion=VERSION, hostKind=args.host, hostSHA256=host,
                installedHostSHA256=HOST, probeSHA256=PROBE, seedReceiptSHA256=SEED_SHA,
                runnerSHA256=scripts[str(Path(__file__))], candidateProof=proof,
                checks=len(result['assertions']), complete=True, incomplete=False,
                reusedFrozenProbe=True, compiled=False, inputsUnchanged=True)
            summary['limitations'] += [
                'The original 39A probe and all 85 frozen source files are reused without recompilation or extra AS timers.',
                'One host and map mode per process; sceneLarge is never toggled for comparison.',
                'Normal mode exercises the candidate bypass; no shell-stop branch coverage counter exists in this production candidate.',
                'Continuous wall intervals are primary; no slow-frame removal, observer subtraction or UTC CPU alignment.',
                'Independent-process AI/population and fire differ; compare the actual per-window workload before inferring benefit.',
                'This run alone neither establishes a performance gain nor authorizes production deployment.']
            r.save(folder / 'summary.json', summary)
            assert summary['qualification']['passed'], 'Sprint/concurrent-fire qualification failed; retained'
            lease.outcome = 'passed'
            lease.note = 'Frozen 1200-frame native sprint/fire captured; no performance acceptance or deployment'
            print(json.dumps({key: summary[key] for key in
                ('name', 'mode', 'hostKind', 'hostSHA256', 'continuous', 'qualification', 'checks')}, ensure_ascii=False), flush=True)
        except BaseException as error:
            lease.outcome = 'failed'
            lease.note = repr(error)
            folder.mkdir(parents=True, exist_ok=True)
            r.save(folder / 'runner-failure.json', dict(record, error=repr(error), complete=False,
                diagnosticOnly=True, performanceEligible=False, performanceAcceptance=False, deployed=False))
            if not (folder / 'summary.json').exists():
                r.save(folder / 'summary.json', dict(name=args.name, mode=args.mode, hostKind=args.host,
                    hostSHA256=host, shellStopCombatVersion=VERSION, complete=False, incomplete=True,
                    qualification=dict(passed=False), error=repr(error), diagnosticOnly=True,
                    performanceEligible=False, performanceAcceptance=False, deployed=False))
            raise


if __name__ == '__main__':
    main()
