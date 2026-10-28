"""Read-only provenance checks; --prepare writes only this successor directory."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
BUILD = HERE.parents[1]
MOD = BUILD.parent
ROOT = MOD.parents[1]
EVIDENCE = MOD / 'knowledge/experiments/evidence'
VERSION = 'camera-live-current-silent-3'
OLD = HERE.parent / 'scene-compat-20261024/camera'
OLD_RECEIPT = EVIDENCE / 'camera-combat-20261024-r1/probe-build.json'
OLD_RECEIPT_SHA = 'E10693B023EB011E660C7B760791ED883614F9DE78B10B68D96B7B8F770FC7B6'
PROBE_SHA = 'FA2B76CBCF4C5029E006B835C99F3EB67B3B4EA5FD03AC736E37AE4E79BC1B22'
CURRENT_SEED = EVIDENCE / 'camera-atlas-paged-combat-20261025-r1/probe-build.json'
CURRENT_SEED_SHA = '983727AEB832BC586AF3767613B7C9D61564D92DC9D8E2435F972EEBF1D1D5EE'
PINS = {
    'pfe.swf': '4E5FAB45D6F5A2634C83BE5E7EAF387443F9FB4E56B945CD2BF54880F1F73C75',
    'mods/ContinuousScene/release/ContinuousSceneMod.swf': '9A5E24E13AF2E2E211FAEAC038697D2CA2641CD6482766048BC3B9B4A506AA31',
    'mods/Rconnect/release/RConnectMod.swf': '2C49DFD05D524085EA43FB8FFA537D1A9359FEBD52FB13D6A19FAAE6E2563621',
    'mods/RealisticVision/release/RealisticVisionMod.swf': '638E2D408E2CF46683C41114F75773829A1B4417D74BFFE9D08855A4FE343710',
    'mods/ModLoader/release/ModLoaderMod.swf': '2050E023205E87FDFDF7FBA4B54B9BAD7769868E51767D0BFBE1742CDC7542E2',
    'mods/TDFC/release/TDFCMod.swf': '7ACD45193109267DBBF875240528048AD6F1D09FA3B8B36BAA6F98EBB5FDDCE5',
}
TOOLS = {
    'mods/ModLoader/tools/test_registry.py': 'E3E43581D677D26C83B7E887C64669634CCC8D901AEFA5A826E1CFED8A5F0CF0',
    'mods/ModLoader/tools/air_test_process.py': 'ECE3ED087D9E31AC4EC91FA1E7B7F82985A149D503C55E682C1C2241027CC3B0',
    'mods/ModLoader/tools/test_resources.py': '86D5F280320DE95DC7DFEDA27020DBCCF432668BB7D2D0DB8C9F3D93FF55CFCB',
}
TRANSITIONS = {
    'mods/ModLoader/tools/test_registry.py': ('58DB3A594F34E9906D55992F769B3E154970D8FA37FDA1C2F43AE1F6751B0033', TOOLS['mods/ModLoader/tools/test_registry.py']),
    'mods/ModLoader/tools/air_test_process.py': ('628FFED886DB293ABE0177FD42C61AC09482E04AEE6AAE358CF2E3D6DEB0D1F9', TOOLS['mods/ModLoader/tools/air_test_process.py']),
}
SOURCE_DIFFERENCES = {
    'ContinuousSceneMotionProbe.as': ('5A3A042CFA213BB886FBF19EB67FFD25155D703BD2A198205769D1A3A42EE609', '5087CBB3D6FA9E1F92E1F24D5D386D7CA48F7D5974F56352AB8DEC25CE856333'),
    'SceneRasterPresentation.as': ('C0E40368FD8BF6FE1413EC4C8D533C7034B18297AEB35119FBFEC4ADD5D93175', 'AD472C796A8006227C5523E51C5803511C2F3904AE0E970D08136BB37C02AD48'),
    'tests/SceneCombatCameraHoldProbe.as': ('1CCF6F1E2A137A8EF9694B3C4AD19EF928E2B844EC808BE732174D280AC29397', None),
    'tests/SceneEncounter.as': ('448A2BD8C710132B9EBF3FC7D9C2EB18B35B9118EA669948231617E0914707AA', '609E1E834C4A9CCEFA7F3FD124761D637880F1BDA347BD52421F730DF5F8A5BB'),
}
RELEASE_EVIDENCE = {
    'state/alicorn-alert-deployment-20261028.json': '2B2CBB6A7D79DC8CBB8FF52FD94CA3B9B7E5445B7BEFF251703B1056B5AB6BB3',
    'build/generated/alicorn-alerts-20261028/build.json': '9575560C129DE842FC404C61EEDA90F7CCA79746B01563768B64A48C729FAFFE',
    'build/generated/alicorn-alerts-20261028/audit.json': '73AB8EDA0701CBF492C249F86C76F700765A5CF7110F4F78662F5265322C49EB',
    'knowledge/experiments/evidence/alicorn-alerts-370c4afb26fa4946924c4f44df73a5b2/summary.json': '971B6933C396A890888E59830CB1D135A89C8DD0BDE6C3921ED6B11E7382F20D',
    'knowledge/experiments/evidence/alicorn-alerts-370c4afb26fa4946924c4f44df73a5b2/inputs.json': '4063DD3B89C5891BD332E0CCBB6F39D3E64D53DF3DA5CBC475D41592B7254049',
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


def tooling():
    actual = {key: sha(ROOT / key) for key in TOOLS}
    assert actual == TOOLS, 'Reviewed shared tooling changed'
    return actual


tooling()
camera = load('camera_live_historical_recipe', OLD / 'run.py')
base, dense, r, m = camera.base, camera.dense, camera.r, camera.m


def difference(before, after):
    return {key: {'historical': before.get(key), 'current': after.get(key)}
            for key in sorted(set(before) | set(after)) if before.get(key) != after.get(key)}


def release_compatibility(receipt):
    actual = {key: sha(MOD / key) for key in RELEASE_EVIDENCE}
    assert actual == RELEASE_EVIDENCE, 'Reviewed 0.9.1 deployment evidence changed'
    deploy = read(MOD / 'state/alicorn-alert-deployment-20261028.json')
    build = read(HERE.parent / 'alicorn-alerts-20261028/build.json')
    audit = read(HERE.parent / 'alicorn-alerts-20261028/audit.json')
    host, mod = PINS['pfe.swf'], PINS['mods/ContinuousScene/release/ContinuousSceneMod.swf']
    assert deploy['version'] == build['version'] == '0.9.1'
    assert deploy['host'] == build['host'] == audit['host'] == host
    assert deploy['mod'] == build['mod'] == mod and deploy['installedReadbackPassed']
    assert deploy['verification']['ok'] and deploy['verification']['checks'] == 31
    assert deploy['verification']['host'] == host and deploy['verification']['mod'] == mod
    assert deploy['priorHost'] == audit['base'] == 'A796827173AF7D6FAB9885FB66ECC62182AB5335918A30C7CCE4C44914A238B7'
    assert audit['ok'] and audit['unchangedBodies'] == 5766
    assert audit['allClassLayoutsPreserved'] and audit['oldConstantsPreserved'] and audit['otherTagsPreserved']
    assert set(audit['methods']) == {'fe.unit.UnitAlicorn::0:1:' + name
                                   for name in ('alarma', 'budilo', 'control', 'setNull', 'telepat')}
    for name in ('NativeSceneActivity.as', 'NativeSceneAdapter.as', 'NativeSceneWalls.as'):
        assert build['source']['src\\' + name] == receipt['frozenSourceSHA256'][name]
    assert build['source']['src\\ContinuousSceneMod.as'] == 'ED2CEC86A45907D057DE1E45957A518425E1F6E159200C899F0E22FFB3B08784'
    assert build['source']['src\\SceneAlicornAlerts.as'] == 'A301E2619B96A927CCB94CDC1F3F0E860D59282634EE30EA17061B7F0922FEA3'
    # Reviewed loader/entrypoint chain: FA2B is installed only as MotionMod;
    # it obtains the current release carrier and never initializes a CS mod.
    source = Path(receipt['frozenSourcePath'])
    assert 'keep:Array=[ContinuousSceneProbe,ContinuousSceneMotionMod]' in (source / 'ContinuousSceneProbeDoc.as').read_text('utf-8-sig')
    assert 'ContinuousSceneProbe.init(main)' in (source / 'ContinuousSceneMotionMod.as').read_text('utf-8-sig')
    assert 'ContinuousSceneMotionProbe.init(host);return;' in (source / 'ContinuousSceneProbe.as').read_text('utf-8-sig')
    return dict(version='0.9.1', evidenceSHA256=actual, host=host, mod=mod,
                unchangedNativeSources=['NativeSceneActivity.as', 'NativeSceneAdapter.as', 'NativeSceneWalls.as'],
                currentCarrierProvidedByRelease=True, historicalProductSourcesNotInitialized=True,
                alicornBehaviorCoverage=False,
                boundary='Reviewed deployment/build records and frozen probe entrypoints; no active WIP source reads. Six ordinary LMG enemies do not exercise alicorn alerts.')


def verify_reuse():
    assert sha(OLD_RECEIPT) == OLD_RECEIPT_SHA
    receipt = read(OLD_RECEIPT)
    original = Path(receipt['probePath']).parent / 'probe-build.json'
    assert sha(original) == OLD_RECEIPT_SHA and read(original) == receipt
    assert receipt['probeSHA256'] == PROBE_SHA == sha(receipt['probePath'])
    # Call the original validator with its original inputs. Never relabel the
    # historical compilation as having used today's host, scripts or compiler.
    checked = camera.verify_probe(original, receipt['productionSHA256'],
                                  receipt['runnerInputs'], receipt['compilerInputs'],
                                  receipt['candidateInputs'])
    assert checked == receipt and len(receipt['frozenSourceSHA256']) == 86
    transitions = {}
    current_inputs = {}
    for field in ('runnerInputs', 'compilerInputs', 'candidateInputs'):
        for name, previous in receipt[field].items():
            path = Path(name)
            current = sha(path)
            current_inputs[name] = current
            if current != previous:
                key = path.relative_to(ROOT).as_posix()
                assert field == 'runnerInputs' and key in TRANSITIONS, (field, name)
                assert (previous, current) == TRANSITIONS[key], key
                assert key not in transitions
                transitions[key] = {'historical': previous, 'current': current}
    assert set(transitions) == set(TRANSITIONS)
    assert sha(CURRENT_SEED) == CURRENT_SEED_SHA
    seed = read(CURRENT_SEED)
    assert len(seed['frozenSourceSHA256']) == 85
    assert base.tree_hashes(Path(seed['frozenSourcePath'])) == seed['frozenSourceSHA256']
    actual_diff = difference(receipt['frozenSourceSHA256'], seed['frozenSourceSHA256'])
    expected_diff = {key: {'historical': old, 'current': new}
                     for key, (old, new) in SOURCE_DIFFERENCES.items()}
    assert actual_diff == expected_diff
    common = sorted(set(receipt['frozenSourceSHA256']) & set(seed['frozenSourceSHA256']) - set(SOURCE_DIFFERENCES))
    assert len(common) == 82
    assert all(name in common for name in ('ContinuousSceneMod.as', 'NativeSceneActivity.as', 'NativeSceneAdapter.as'))
    source = Path(receipt['frozenSourcePath'])
    main = (source / 'ContinuousSceneMotionProbe.as').read_text('utf-8-sig')
    assert 'if(cfg.drawControl && cfg.drawControl!="rcnative")' in main
    assert 'if(cfg.drawControl || cfg.impactABBA || cfg.fogABBA || cfg.fogTypedABBA)return true;' in main
    encounter = (source / 'tests/SceneEncounter.as').read_text('utf-8-sig')
    assert 'weap:"lmg"' in encounter and 'if(localOnly)' in encounter
    return dict(version=VERSION, reusedOriginalCompilation=True, rebuilt=False,
                historicalValidatorPassed=True, historicalReceipt=str(original),
                historicalReceiptSHA256=OLD_RECEIPT_SHA, probePath=receipt['probePath'],
                probeSHA256=PROBE_SHA, historicalProduction=receipt['productionSHA256'],
                currentHistoricalInputFiles=current_inputs, toolingTransitions=transitions,
                currentSeedReceiptSHA256=CURRENT_SEED_SHA, sourceDifferences=actual_diff,
                identicalCommonSources=common, commonSourceCount=82,
                releaseCompatibility=release_compatibility(receipt),
                interpretation='Original six-LMG fixture; raster presenter unused under rcnative. 82 sources match the historical 29AF seed, not a claim of unchanged 0.9.1 product source. Current release supplies nativeAPI.')


def current_snapshot():
    prior = read(HERE / 'prior-recipe.json')
    assert prior['airStarted'] is False
    assert prior['failedRun'] == 'camera-live-current-20261028-r1'
    prior_root = HERE.parent / 'camera-live-current-20261028'
    assert Path(prior['directory']) == prior_root
    assert all(sha(prior_root / name) == digest for name, digest in prior['inputs'].items())
    proof = verify_reuse()
    production = r.baseline()
    assert len(production) == 526
    for key, value in PINS.items():
        assert production[key] == value, key
    runtime_files = [ROOT / 'adl64.exe'] + sorted((ROOT / 'runtimes/air/win64').rglob('*'))
    runtime = {p.relative_to(ROOT).as_posix(): sha(p) for p in runtime_files if p.is_file()}
    assert len(runtime) == 13
    scripts = {str(HERE / name): sha(HERE / name)
               for name in ('run.py', 'verify_reuse.py', 'verify_run.py', 'silence.py', 'README.md', 'prior-recipe.json', 'seed_check.py')}
    return dict(version=VERSION, provenance=proof, production=production,
                productionDifferences=difference(proof['historicalProduction'], production),
                tooling=tooling(), runtime=runtime, successorInputs=scripts)


def prepared():
    expected = read(HERE / 'prepared.json')
    actual = current_snapshot()
    assert actual == expected, 'Prepared inputs changed; review and explicitly prepare again before running'
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
                          identicalCommonSources=82, changedSources=sorted(SOURCE_DIFFERENCES),
                          historicalProductionDifferences=len(snapshot['productionDifferences']),
                          currentProductionFiles=len(snapshot['production']), runtimeFiles=len(snapshot['runtime']))))
