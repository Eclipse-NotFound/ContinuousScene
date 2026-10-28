"""Freeze the current CS carrier and the exact six-LMG activity-range probe.

Source preparation only: no compiler, AIR, deployment or production writes.
Default checks existing copies; --prepare creates missing files exclusively.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
MOD = HERE.parents[2]
OLD = HERE.parent / 'activity-camera-range-20261025'
BUILD = HERE.parent / 'alicorn-alerts-20261028/build.json'
SEED = MOD / 'knowledge/experiments/evidence/vertical-camera-band-20261023-combat-candidate-r3/probe-build.json'
FINAL = OLD / 'probe-prepared/9d862774fe044332bf8ad3614164bd61/source-proof.json'
HOST_SHA = '4E5FAB45D6F5A2634C83BE5E7EAF387443F9FB4E56B945CD2BF54880F1F73C75'
CS_SHA = '9A5E24E13AF2E2E211FAEAC038697D2CA2641CD6482766048BC3B9B4A506AA31'
PROBE_SHA = '39A1497BE832282CAC25E2A508A954432F9F31B15A2FBE5A650AB8C4D9C97E9E'
PINS = {
    BUILD: '9575560C129DE842FC404C61EEDA90F7CCA79746B01563768B64A48C729FAFFE',
    SEED: 'B7ED1EAB8BEE0DC1024D6EF0A56A965F311B97E8CED9A9F32A2BCDE35B35FF13',
    FINAL: 'EA15CFFC1A74E9A4A3B7796181F685B47192D3999C0645F88BAD98CEEDC74EBC',
    OLD / 'prepare_source.py': '7624E6C2763DF77B79436CBC92B30BB8BE249C82AEA2C995105F08EA3FB5EDE1',
    OLD / 'prepare_probe.py': 'DC3351E72E66752F3633BFEEABEF017E14AB4DE50FE16127A2D8162968AA5365',
    OLD / 'source-candidate/SceneActivityCameraRange.as': '898D0C6C260A49FC3DD5FF8B374933845A168948F3FACAA90A669FB903A99227',
    OLD / 'probe/SceneActivityRangeProbe.as': 'B119B70D49E42C241969B67CE14BBE19C0535AD97D8D436B5E7DECA64E63DF41',
}


def digest(data): return hashlib.sha256(data).hexdigest().upper()
def sha(path): return digest(path.read_bytes())
def read(path): return json.loads(path.read_text('utf-8-sig'))
def tree(path): return {p.relative_to(path).as_posix(): sha(p) for p in sorted(path.rglob('*')) if p.is_file()}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def keep(path, content, write):
    assert path.resolve().is_relative_to(HERE), path
    if path.exists():
        assert path.read_bytes() == content, ('Refuse overwrite', path)
    else:
        assert write, ('Prepared file missing; use --prepare', path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(content)


def prepare(write=False):
    assert __debug__, 'Assertions must remain enabled'
    for path, expected in PINS.items():
        assert sha(path) == expected, path
    prior = load('current_range_original_carrier', OLD / 'prepare_source.py')
    probe = load('current_range_original_probe', OLD / 'prepare_probe.py')
    build, seed, final = read(BUILD), read(SEED), read(FINAL)
    assert build['version'] == '0.9.1' and build['host'] == HOST_SHA and build['mod'] == CS_SHA
    assert seed['probeSHA256'] == PROBE_SHA and seed['denseFixture'] == 'dense-sprint-2'
    seed_root, seed_swf = Path(seed['frozenSourcePath']), Path(seed['probePath'])
    assert sha(seed_swf) == PROBE_SHA
    assert tree(seed_root) == seed['frozenSourceSHA256'] and len(seed['frozenSourceSHA256']) == 85
    assert final['compiled'] is False and final['changed'] == probe.CHANGED
    probe_helper = OLD / 'probe/SceneActivityRangeProbe.as'
    assert final['preparedSourceSHA256']['tests/SceneActivityRangeProbe.as'] == sha(probe_helper)

    names = [*prior.EXPECTED, 'SceneAlicornAlerts.as']
    original = {name: (MOD / 'src' / name).read_bytes() for name in names}
    assert all(digest(data) == build['source']['src\\' + name] for name, data in original.items())
    assert digest(original['NativeSceneActivity.as']) == prior.EXPECTED['NativeSceneActivity.as']
    candidate = dict(original)
    candidate['NativeSceneActivity.as'] = prior.transform('NativeSceneActivity.as', original['NativeSceneActivity.as'])
    assert prior.transform('NativeSceneActivity.as', candidate['NativeSceneActivity.as'], reverse=True) == original['NativeSceneActivity.as']
    protected = prior.protected_segments(original['NativeSceneActivity.as'], candidate['NativeSceneActivity.as'])
    # Reuse the four exact old API entries while retaining the current alicorn API.
    api = prior.MOD_EDITS[0][1].split('\n', 1)[1]
    assert api.endswith('};')
    api = api[:-2] + ',\n'
    anchor = '                alicornAllow:SceneAlicornAlerts.allow,alicornReceive:SceneAlicornAlerts.receive,'
    carrier = original['ContinuousSceneMod.as'].decode('utf-8')
    assert carrier.count(anchor) == 1
    changed_carrier = carrier.replace(anchor, api + anchor, 1)
    assert changed_carrier.replace(api + anchor, anchor, 1) == carrier
    candidate['ContinuousSceneMod.as'] = changed_carrier.encode('utf-8')
    candidate[prior.HELPER] = (OLD / 'source-candidate' / prior.HELPER).read_bytes()
    changed = sorted(name for name in original if candidate[name] != original[name])
    assert changed == ['ContinuousSceneMod.as', 'NativeSceneActivity.as'] and len(candidate) == 8

    main = (seed_root / 'ContinuousSceneMotionProbe.as').read_text('utf-8-sig')
    assert 'combatCamera' not in main and 'SceneCombatCameraHoldProbe' not in main
    assert 'weap:"lmg"' in (seed_root / 'tests/SceneEncounter.as').read_text('utf-8-sig')
    assert all(main.count(before) == 1 for before, after in probe.EDITS)
    probe_main = probe.transform(main)
    # The inherited guard's message named SMG; only its label follows this LMG seed.
    old_label = 'Activity range requires exact native SMG fixture with visual mods off'
    new_label = 'Activity range requires exact native LMG fixture with visual mods off'
    assert probe_main.count(old_label) == 1
    probe_main = probe_main.replace(old_label, new_label, 1)
    assert probe.reverse(probe_main.replace(new_label, old_label, 1)) == main
    probe_sources = {name: (seed_root / name).read_bytes() for name in seed['frozenSourceSHA256']}
    probe_sources['ContinuousSceneMotionProbe.as'] = probe_main.encode('utf-8')
    probe_sources['tests/SceneActivityRangeProbe.as'] = probe_helper.read_bytes()
    probe_hashes = {name: digest(data) for name, data in probe_sources.items()}
    assert sorted(name for name in set(probe_hashes) | set(seed['frozenSourceSHA256'])
                  if probe_hashes.get(name) != seed['frozenSourceSHA256'].get(name)) == probe.CHANGED
    assert len(probe_sources) == 86

    inputs = {str(path): expected for path, expected in PINS.items()}
    inputs.update({str(MOD / 'src' / name): digest(data) for name, data in original.items()})
    inputs.update({str(seed_root / name): expected for name, expected in seed['frozenSourceSHA256'].items()})
    inputs.update({str(path): sha(path) for path in (Path(__file__), HERE / 'README.md', seed_swf)})
    for folder, sources in (('source-original', original), ('source-candidate', candidate), ('probe-source', probe_sources)):
        target = HERE / folder
        for name, data in sources.items():
            keep(target / name, data, write)
        assert tree(target) == {name: digest(data) for name, data in sources.items()}
    assert all(sha(Path(path)) == expected for path, expected in inputs.items()), 'Inputs changed during preparation'
    manifest = dict(version='camera-activity-range-current-1', prepared=True, compiled=False, airRun=False,
        deployed=False, diagnosticOnly=True, performanceAccepted=False, sourceInputs=inputs,
        productionReference=dict(version='0.9.1', host=HOST_SHA, mod=CS_SHA, buildReceipt=str(BUILD)),
        carrier=dict(originalPath=str(HERE / 'source-original'), originalCount=7,
            originalSHA256={name: digest(data) for name, data in original.items()},
            candidatePath=str(HERE / 'source-candidate'), candidateCount=8,
            candidateSHA256={name: digest(data) for name, data in candidate.items()}, changed=changed,
            added=[prior.HELPER], reverseExact=True, protectedSegments=protected, alicornPreserved=True),
        probe=dict(seedReceipt=str(SEED), seedSHA256=PROBE_SHA, seedSourcePath=str(seed_root), seedSourceCount=85,
            seedSourceSHA256=seed['frozenSourceSHA256'], sourcePath=str(HERE / 'probe-source'), sourceCount=86,
            sourceSHA256=probe_hashes, changed=probe.CHANGED, reverseExact=True,
            inheritedAnchors=6, diagnosticLabelOnly='SMG -> LMG', cameraHoldIncluded=False,
            order=[False, True, True, False], framesPerWindow=300, finalLegacyPreparation=str(FINAL)),
        limitations=['Source preparation only; no runtime runner or compiled candidate exists here.',
            'Conditional geometry does not prove late player/quake/scale writes safe; per-frame post-check remains mandatory.',
            'All range planning, read-only scans, switching, observer work and boundary intervals remain in timing.',
            'Require actual B applications and oldNearOnlySleeping positives, complete post-checks and zero visible sleepers.',
            'Returning to A restores the switch, not evolved combat state; no performance or compatibility claim.'])
    keep(HERE / 'source-manifest.json', (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode('utf-8'), write)
    return dict(prepared=True, checked=True, carrier='7 -> 8', probe='85 -> 86', reverseExact=True,
                manifestSHA256=sha(HERE / 'source-manifest.json'), compiled=False, airRun=False, deployed=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true', help='Create missing source copies and manifest; never overwrite.')
    print(json.dumps(prepare(parser.parse_args().prepare), ensure_ascii=False, indent=2))
