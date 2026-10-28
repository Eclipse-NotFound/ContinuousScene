"""Verify original dense-v2 bytes and current dependencies; no compiler or AIR."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SILENT = HERE.parent / 'camera-live-current-silent-20261028'
VERSION = 'dense-reference-rc2-1'
UPSTREAM = {
    'verify_reuse.py': '45D37D6F47EEFA9F1BF2B5C3DBCCDB75AC1488BF6AFF77F602B5AD7D9AAA40D5',
    'silence.py': 'C743847410D6084549AE525BF12E85C3B9E6BDBB318219432522462A1BA04942',
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def read(path):
    return json.loads(Path(path).read_text('utf-8-sig'))


def save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), 'utf-8')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


assert __debug__, 'Assertions must remain enabled'
assert {name: sha(SILENT / name) for name in UPSTREAM} == UPSTREAM
prior = load('dense_reference_reviewed_reuse', SILENT / 'verify_reuse.py')
base, dense, r, m = prior.base, prior.dense, prior.r, prior.m
ROOT, MOD, EVIDENCE = prior.ROOT, prior.MOD, prior.EVIDENCE
OLD_RECEIPT = EVIDENCE / 'dense-v2-20261023-normal-r1/probe-build.json'
OLD_RECEIPT_SHA = '1AB690B790CC06F8C5092931C1D10DE1813D78B385DBD2CD722F852B191F67DC'
PROBE_SHA = '7F1F0B4361D78E2736EE8EC969C9495FB0CB3CD93A1446F38E0FDDDE4805E0F9'
PREVIOUS = HERE.parent / 'camera-dense-reference-current-20261028'
PREVIOUS_PREPARED_SHA = '5F2AFF74696DFCC2B45B6C2DF62F896F2B5661140FE1F860B8FEBB5A9A21C19B'
RC_PATH = 'mods/Rconnect/release/RConnectMod.swf'
RC_PREVIOUS = '2C49DFD05D524085EA43FB8FFA537D1A9359FEBD52FB13D6A19FAAE6E2563621'
RC_CURRENT = 'F14A44E74AC98EC480875203D4D714ACFBC496141980E5A1D7B0DE0C7AD222FB'
RC_DEPLOYMENT = ROOT / 'mods/RConnect/build/m52/a-stutter-deploy-a3a3e26e/deployment.json'
RC_DEPLOYMENT_SHA = '125F922285D85A144A5DF68FCC7B5CE9F35566487B925639ECE2209F44211D13'


def runtime_pin_override(production):
    assert sha(PREVIOUS / 'prepared.json') == PREVIOUS_PREPARED_SHA
    old = read(PREVIOUS / 'prepared.json')
    assert len(old['production']) == 526 and old['production'][RC_PATH] == RC_PREVIOUS
    assert all(sha(name) == digest for name, digest in old['successorInputs'].items()), 'Old executed recipe changed'
    assert sha(RC_DEPLOYMENT) == RC_DEPLOYMENT_SHA, 'Reviewed RC deployment receipt changed'
    receipt = read(RC_DEPLOYMENT)
    assert receipt['status'] == 'verified' and receipt['version'] == '0.2.24-animfix2'
    assert receipt['previous_sha256'].upper() == RC_PREVIOUS
    assert receipt['candidate_sha256'].upper() == receipt['installed_sha256'].upper() == RC_CURRENT
    assert receipt['untouched_before'] == receipt['untouched_after']
    assert all(sha(name) == digest.upper() for name, digest in receipt['untouched_after'].items())
    changed = prior.difference(old['production'], production)
    assert changed == {RC_PATH: {'historical': RC_PREVIOUS, 'current': RC_CURRENT}}, 'Only the reviewed RC binary may differ'
    return dict(path=RC_PATH, previous=RC_PREVIOUS, current=RC_CURRENT,
                deploymentReceipt=str(RC_DEPLOYMENT), deploymentReceiptSHA256=RC_DEPLOYMENT_SHA,
                status=receipt['status'], version=receipt['version'],
                previousPrepared=str(PREVIOUS / 'prepared.json'), previousPreparedSHA256=PREVIOUS_PREPARED_SHA,
                previousRecipeInputs=old['successorInputs'], productionInputCount=526,
                onlyProductionChange=changed, historicalCompilationRelabeled=False)



def verify_reuse():
    assert sha(OLD_RECEIPT) == OLD_RECEIPT_SHA
    receipt = read(OLD_RECEIPT)
    original = Path(receipt['probePath']).parent / 'probe-build.json'
    assert sha(original) == OLD_RECEIPT_SHA and read(original) == receipt
    assert receipt['probeSHA256'] == PROBE_SHA == sha(receipt['probePath'])
    # Original validator and original compilation inputs, without relabeling.
    assert dense.verify_probe(original, receipt['productionSHA256'], receipt['runnerInputs'],
                              receipt['compilerInputs'], receipt['candidateInputs']) == receipt
    assert len(receipt['frozenSourceSHA256']) == 85
    transitions, historical_files = {}, {}
    for field in ('runnerInputs', 'compilerInputs', 'candidateInputs'):
        for name, before in receipt[field].items():
            actual = sha(name)
            historical_files[name] = actual
            if actual != before:
                key = Path(name).relative_to(ROOT).as_posix()
                assert field == 'runnerInputs' and key in prior.TRANSITIONS
                assert (before, actual) == prior.TRANSITIONS[key]
                assert key not in transitions
                transitions[key] = {'historical': before, 'current': actual}
    assert set(transitions) == set(prior.TRANSITIONS)
    seed = prior.camera.seed()
    assert seed['frozenSourceSHA256'] == receipt['frozenSourceSHA256']
    assert sha(prior.OLD_RECEIPT) == prior.OLD_RECEIPT_SHA
    camera = read(prior.OLD_RECEIPT)
    differences = prior.difference(receipt['frozenSourceSHA256'], camera['frozenSourceSHA256'])
    assert set(differences) == {'ContinuousSceneMotionProbe.as', 'tests/SceneCombatCameraHoldProbe.as'}
    common = set(receipt['frozenSourceSHA256']) & set(camera['frozenSourceSHA256']) - set(differences)
    assert len(common) == 84
    return dict(originalReceipt=str(original), originalReceiptSHA256=OLD_RECEIPT_SHA,
                historicalValidatorPassed=True, reusedOriginalCompilation=True, rebuilt=False,
                probePath=receipt['probePath'], probeSHA256=PROBE_SHA,
                historicalProduction=receipt['productionSHA256'], historicalInputFiles=historical_files,
                toolingTransitions=transitions, identical39ASources=85,
                identicalFA2BCommonSources=84, sourceDifferencesFromFA2B=differences,
                releaseCompatibility=prior.release_compatibility(receipt),
                boundary='Original dense-v2 normal/scene fixture, no camera hold or forced 177-tile prewarm. All timed asynchronous warming remains in the result.')


def current_snapshot():
    assert {name: sha(SILENT / name) for name in UPSTREAM} == UPSTREAM
    proof = verify_reuse()
    production = r.baseline()
    assert len(production) == 526
    override = runtime_pin_override(production)
    pins = dict(prior.PINS)
    assert pins[RC_PATH] == RC_PREVIOUS
    pins[RC_PATH] = RC_CURRENT  # runtime-only successor pin, never a historical compilation input
    for key, digest in pins.items():
        assert production[key] == digest, key
    files = [ROOT / 'adl64.exe'] + sorted((ROOT / 'runtimes/air/win64').rglob('*'))
    runtime = {p.relative_to(ROOT).as_posix(): sha(p) for p in files if p.is_file()}
    assert len(runtime) == 13
    assert runtime == read(PREVIOUS / 'prepared.json')['runtime'], 'AIR runtime changed'
    scripts = {str(HERE / name): sha(HERE / name)
               for name in ('run.py', 'verify_reuse.py', 'verify_run.py', 'README.md')}
    return dict(version=VERSION, runtimePinOverride=override, provenance=proof, production=production,
                productionDifferences=prior.difference(proof['historicalProduction'], production),
                tooling=prior.tooling(), runtime=runtime, successorInputs=scripts,
                upstreamInputs={str(SILENT / key): value for key, value in UPSTREAM.items()})


def prepared():
    expected = read(HERE / 'prepared.json')
    actual = current_snapshot()
    assert expected == actual, 'Prepared inputs changed; review before a new preparation'
    return actual


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    args = parser.parse_args()
    snapshot = current_snapshot()
    if args.prepare:
        assert not (HERE / 'runs').exists() or not any((HERE / 'runs').iterdir()), 'Keep attempted-run preparation immutable'
        save(HERE / 'prepared.json', snapshot)
    print(json.dumps(dict(verified=True, prepared=args.prepare, probe=PROBE_SHA,
                          productionFiles=len(snapshot['production']), runtimeFiles=len(snapshot['runtime']),
                          identical39ASources=85, identicalFA2BCommonSources=84)))
