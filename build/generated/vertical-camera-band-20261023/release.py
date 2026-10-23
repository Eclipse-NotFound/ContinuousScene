"""Reviewed Camera.calc host-only release; check never writes or launches AIR.

The root reviewer supplies qualification JSON after reviewing real results. This
script never writes that approval. Deployment reuses the qualified component
probe and options against a copy of the actually installed file, not a build.
"""
from pathlib import Path
from datetime import datetime
from types import SimpleNamespace
import argparse
import importlib.util
import json
import os
import shutil
import sys
import uuid

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
BUILD, MOD = HERE.parents[1], HERE.parents[2]
ROOT = MOD.parents[1]
VERSION = 'vertical-camera-band-1'
SCHEMA = 'vertical-camera-band-release-qualification-1'
HOST = '80CFD8CF3138EE59CBF6EDA0A1824A9EC960F413BD95E4B90D41DD0322B4FD3D'
CANDIDATE = 'ABE2B65EDF3D0E4E0FA8ECA76A60E577D40E47F20B9ACECEBEC7730849A2602A'
XML = 'EE33CE0282C1DFBA7BF7AE03D1E7646383DCCF79EA1252F9792A57344E1208CF'
AUDIT = 'F8147E6F0E6939E65387F5A15FE9E80322EF925A306096F8816A490F401AE4B1'
RECEIPT = MOD / 'state/vertical-camera-band-deployment-20261023.json'
ROLES = ('components', 'jumpBaseline', 'jumpCandidate', 'combatBaseline', 'combatCandidate')
EVIDENCE_FILES = ('summary.json', 'storage/result.json', 'inputs.json', 'runner-inputs.json',
    'probe-build.json', 'process-policy.json', 'loader-check.json', 'storage/tdfc.log')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


t = load('camera_release_testing', HERE / 'testing/run.py')
c = load('camera_release_combat', HERE / 'combat/run.py')
r, m, base = t.r, t.m, t.base
assert ROOT == r.ROOT and BUILD == t.BUILD and MOD == r.MOD


def name_ok(value):
    assert isinstance(value, str) and value and all(ch in 'abcdefghijklmnopqrstuvwxyz0123456789-' for ch in value)


def hash_inputs(values):
    assert values
    for path, digest in values.items():
        assert r.sha(Path(path)) == digest, ('Input changed', path)


def product():
    selected = t.host_inputs(HERE / 'build.json')
    build = c.product()
    assert selected['sha256'] == build['candidate'] == CANDIDATE
    assert build['candidateXML'] == XML and build['audit'] == AUDIT
    return selected, build


def component_result(result):
    value = result['verticalCameraComponents']
    assert value['version'] == 'vertical-camera-components-1'
    assert value['passed'] and value['terminalOnly'] and value['expectCandidate']
    assert value['cases'] and all(case['passed'] for case in value['cases'])
    assert value['restore']['passed'] and not result.get('verticalMotion') and not result['samples']
    return value


def dependencies(inputs, baseline, host):
    # Isolated application id and launcher selection are intentionally different.
    for key, digest in baseline.items():
        if key not in ('application.xml', 'mods/loader-manifest.txt'):
            assert inputs[key] == (host if key == 'pfe.swf' else digest), key


def evidence(entry, role, installed, component_name, selected):
    name_ok(entry['name'])
    folder = r.E / entry['name']
    assert set(EVIDENCE_FILES) <= set(entry['hashes']), ('Missing evidence fingerprints', role)
    for relative, digest in entry['hashes'].items():
        path = (folder / relative).resolve()
        assert path.is_relative_to(folder.resolve()) and path.is_file(), relative
        assert r.sha(path) == digest, (role, relative)
    raw, inputs = r.result(entry['name'])
    summary, capture = r.read(folder / 'summary.json'), r.read(folder / 'runner-inputs.json')
    policy = r.read(folder / 'process-policy.json')
    assert not policy['performanceEligible'] and not policy.get('runFailure') and not policy.get('memoryAbort')
    assert not policy['otherAirProcessIds']
    candidate = role == 'components' or role.endswith('Candidate')
    kind, host = ('candidate', CANDIDATE) if candidate else ('baseline', HOST)
    assert summary['qualification']['passed'] and not summary['deployed']
    assert summary['hostKind'] == kind and summary['hostSHA256'] == host
    assert summary['installedHostSHA256'] == HOST and capture['baseline'] == installed
    dependencies(inputs, installed, host)
    for key in ('runnerInputs', 'compilerInputs', 'fixtureInputs'):
        hash_inputs(capture[key])
    path = Path(capture['probeBuildPath'])
    if role.startswith('combat'):
        assert capture['hostKind'] == kind and capture['hostSHA256'] == host
        assert capture['componentEvidence'] == summary['componentEvidence'] == component_name
        assert capture['runnerInputs'] == c.runner_inputs() and capture['fixtureInputs'] == c.fixture_inputs()
        assert capture['compilerInputs'] == c.support.compiler_inputs()
        probe = c.dense.verify_probe(path, installed, capture['runnerInputs'], capture['compilerInputs'], capture['fixtureInputs'])
        assert summary['cameraBandCombatVersion'] == c.VERSION and summary['productionHostWithoutCounters']
        recalculated = c.dense.summarize(raw, SimpleNamespace(name=entry['name'], mode='scene'))
        assert recalculated['qualification']['passed'] and recalculated['continuous']['count'] == 1200
    else:
        t.COMPONENT_MODE = role == 'components'
        assert capture['host'] == (selected if candidate else t.host_inputs(None))
        assert capture['runnerInputs'] == t.runner_inputs() and capture['fixtureInputs'] == t.fixture_inputs()
        assert capture['compilerInputs'] == base.support.compiler_inputs()
        probe = t.verify_probe(path, installed, capture['runnerInputs'], capture['compilerInputs'], capture['fixtureInputs'], False)
        control = dict(version='vertical-camera-band-test-controls-1', componentsOnly=t.COMPONENT_MODE,
            expectedCandidate=candidate, hostSHA256=host)
        assert capture['isolatedControl'] == summary['isolatedControl'] == raw['cameraBandHostControl'] == control
        assert inputs[t.CONTROL_NAME] == capture['isolatedControlSHA256']
        if t.COMPONENT_MODE:
            assert summary['componentsOnly'] and summary['verification'] == component_result(raw)
            recalculated = {}
        else:
            assert not summary.get('componentsOnly') and 'verticalCameraComponents' not in raw
            recalculated = t.summarize(raw, SimpleNamespace(name=entry['name'], mode='scene', grow=False))
            assert sum(row['frames']['count'] for row in recalculated['windows']) == 720
    # Recompute the raw timing/workload gates, retaining every primary interval.
    for key, value in recalculated.items():
        if key not in ('limitations', 'hostSHA256'):
            assert summary[key] == value, (role, key)
    assert r.read(folder / 'probe-build.json') == probe
    assert inputs[base.PROBE_PATH] == probe['probeSHA256']
    assert capture['options'].count('--name') == 1 and capture['options'][capture['options'].index('--name') + 1] == entry['name']
    return dict(name=entry['name'], role=role, hashes=entry['hashes'], summary=summary,
        capture=capture, probe=probe, raw=raw)


def paired(left, right, fields):
    assert left['probe']['probeSHA256'] == right['probe']['probeSHA256'], 'A/B probe differs'
    for key in ('baseline', 'runnerInputs', 'compilerInputs', 'fixtureInputs'):
        assert left['capture'][key] == right['capture'][key], ('A/B input differs', key)
    for key in fields:
        assert left['summary'][key] == right['summary'][key], ('A/B terrain or route differs', key)
    a, b = list(left['capture']['options']), list(right['capture']['options'])
    a[a.index('--name') + 1] = b[b.index('--name') + 1] = '<name>'
    assert a == b, 'A/B options differ'


def preflight(qualification_path):
    assert qualification_path is not None, '--qualification is required for check/deploy'
    qualification_path = qualification_path.resolve()
    q = r.read(qualification_path)
    assert q['schema'] == SCHEMA and q['version'] == VERSION and q['passed'] is True
    assert q['baselineHostSHA256'] == HOST and q['candidateHostSHA256'] == CANDIDATE
    assert q['sourceBuildSHA256'] == r.sha(HERE / 'build.json') and q['semanticAuditSHA256'] == AUDIT
    review = q['review']  # Authored by root after reviewing results, never synthesized here.
    assert all(review[key] is True for key in ('componentPassed', 'jumpBenefitAccepted', 'combatRegressionAccepted'))
    assert isinstance(review['limitations'], list) and review['limitations'] and all(isinstance(x, str) and x.strip() for x in review['limitations'])
    assert set(ROLES) <= set(q['evidence']), 'All five evidence roles required'
    assert '<content>pfe.swf</content>' in (ROOT / 'application.xml').read_text('utf-8-sig')
    selected, build = product()
    installed = r.baseline()
    assert installed['pfe.swf'] == HOST and installed[base.CS_PATH] == t.CS
    assert next(v for k, v in installed.items() if k.lower() == t.RC_PATH.lower()) == t.RC
    component_name = q['evidence']['components']['name']
    c.component(component_name, build, installed)  # Pins the actual component evidence in combat fixture inputs.
    checked = {}
    for key, entry in q['evidence'].items():
        role = entry.get('role', key)
        assert role in ROLES and (key not in ROLES or role == key), key
        checked[key] = evidence(entry, role, installed, component_name, selected)
    paired(checked['jumpBaseline'], checked['jumpCandidate'], ('normalizedTerrain', 'nativeRoute'))
    paired(checked['combatBaseline'], checked['combatCandidate'],
        ('normalizedRoute', 'nativeRouteHash', 'selectedCombatCorridorTiles', 'viewport'))
    assert installed == r.baseline() and selected == product()[0]
    assert q == r.read(qualification_path), 'Qualification changed while reading'
    return dict(installed=installed, selected=selected, build=build, checked=checked,
        qualification=q, qualificationPath=str(qualification_path), qualificationSHA256=r.sha(qualification_path))


def replace(source, destination, before, after):
    temporary = destination.with_name(destination.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        shutil.copy2(source, temporary)
        assert r.sha(temporary) == after
        assert r.sha(destination) == before, 'Concurrent host revision; do not overwrite'
        os.replace(temporary, destination)
        assert r.sha(destination) == after
    finally:
        temporary.unlink(missing_ok=True)


def rollback(receipt):
    assert receipt['version'] == VERSION and receipt['target'] == 'pfe.swf'
    assert receipt['before'] == HOST and receipt['after'] == CANDIDATE
    backup = Path(receipt['backup']).resolve()
    assert backup.is_relative_to((BUILD / 'backups').resolve()) and r.sha(backup) == HOST
    current = r.sha(ROOT / 'pfe.swf')
    if current not in (HOST, CANDIDATE):
        receipt.update(status='rollback-blocked', rollbackError='Third-party host revision: ' + current)
        r.save(RECEIPT, receipt)
        raise RuntimeError(receipt['rollbackError'])
    if current == CANDIDATE:
        replace(backup, ROOT / 'pfe.swf', CANDIDATE, HOST)
    receipt.update(status='rolled-back', rolledBackAt=datetime.now().astimezone().isoformat())
    r.save(RECEIPT, receipt)


def installed_smoke(state, name, lease):
    passed = state['checked']['components']
    capture, probe = passed['capture'], passed['probe']
    options = list(capture['options'])
    options[options.index('--name') + 1] = name
    installed = dict(state['installed'], **{'pfe.swf': CANDIDATE})
    assert r.baseline() == installed
    # No candidate copy here: prepare must copy the actual production pfe.swf.
    m.prepare()
    assert r.sha(m.RUNTIME / 'pfe.swf') == CANDIDATE
    shutil.copy2(probe['probePath'], m.RUNTIME / base.PROBE_PATH)
    assert r.sha(m.RUNTIME / base.PROBE_PATH) == probe['probeSHA256']
    control = m.RUNTIME / t.CONTROL_NAME
    assert not control.exists(), 'Stale isolated control; do not overwrite'
    r.save(control, capture['isolatedControl'])
    control_sha = r.sha(control)
    assert control_sha == capture['isolatedControlSHA256']
    try:
        m.run_owned(m.parse_args(options), lease)
    finally:
        folder = r.E / name
        if folder.exists():
            r.save(folder / 'probe-build.json', probe)
            r.save(folder / 'runner-inputs.json', dict(options=options, baseline=installed,
                probeBuildPath=capture['probeBuildPath'], qualifiedEvidence=passed['name'],
                qualifiedEvidenceHashes=passed['hashes'], probeProductionBaseline=state['installed'],
                runnerInputs=capture['runnerInputs'], compilerInputs=capture['compilerInputs'],
                fixtureInputs=capture['fixtureInputs'], installedCopy=True,
                releaseScriptSHA256=r.sha(Path(__file__)), qualificationSHA256=state['qualificationSHA256'],
                isolatedControl=capture['isolatedControl'], isolatedControlSHA256=control_sha))
        if control.exists():
            assert r.sha(control) == control_sha, 'External control edit; leave it untouched'
            control.unlink()
    raw, inputs = r.result(name)
    value = component_result(raw)
    assert raw['cameraBandHostControl'] == capture['isolatedControl']
    assert inputs[t.CONTROL_NAME] == control_sha and inputs[base.PROBE_PATH] == probe['probeSHA256']
    assert [x['name'] for x in value['cases']] == [x['name'] for x in passed['raw']['verticalCameraComponents']['cases']]
    dependencies(inputs, installed, CANDIDATE)
    policy = r.read(folder / 'process-policy.json')
    assert not policy.get('runFailure') and not policy['performanceEligible']
    assert not policy.get('memoryAbort') and not policy['otherAirProcessIds']
    assert r.baseline() == installed and state['selected'] == product()[0]
    for key in ('runnerInputs', 'compilerInputs', 'fixtureInputs'):
        hash_inputs(capture[key])
    t.COMPONENT_MODE = True
    t.verify_probe(Path(capture['probeBuildPath']), state['installed'], capture['runnerInputs'],
        capture['compilerInputs'], capture['fixtureInputs'], False)
    summary = dict(name=name, qualification=dict(passed=True), installedCopy=True,
        componentsOnly=True, verification=value, hostSHA256=CANDIDATE,
        probeSHA256=probe['probeSHA256'], performanceAcceptance=False)
    r.save(folder / 'summary.json', summary)
    return dict(name=name, checks=len(raw['assertions']), cases=len(value['cases']),
        hashes={relative: r.sha(folder / relative) for relative in EVIDENCE_FILES})


def main():
    assert __debug__, 'Run without -O; release assertions are mandatory'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('check', 'deploy', 'rollback'))
    parser.add_argument('--qualification', type=Path)
    parser.add_argument('--smoke-name', default='vertical-camera-band-20261023-installed-components-r1')
    parser.add_argument('--registry-wait', type=int, default=600)
    args = parser.parse_args()
    if args.mode == 'check':
        state = preflight(args.qualification)
        print(json.dumps(dict(passed=True, version=VERSION, candidate=CANDIDATE,
            unchangedDependencies=len(state['installed']) - 1,
            evidence=[v['name'] for v in state['checked'].values()]), ensure_ascii=False))
        return
    with m.Registration(owner='ContinuousScene / camera-band release / 01a13816',
            purpose=args.mode + ' ' + VERSION, resource='game', run_dir=m.RUNTIME,
            evidence=RECEIPT, wait=args.registry_wait) as lease:
        assert not m.air_pids(), 'Existing AIR remains untouched'
        if args.mode == 'rollback':
            rollback(r.read(RECEIPT)); lease.outcome = 'passed'; return
        assert not RECEIPT.exists(), 'Existing deployment receipt requires review'
        name_ok(args.smoke_name)
        assert not (r.E / args.smoke_name).exists(), 'Preserve previous smoke evidence'
        assert not (m.RUNTIME / t.CONTROL_NAME).exists(), 'Stale control requires review'
        state = preflight(args.qualification)
        folder = BUILD / 'backups' / ('vertical-camera-band-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8])
        folder.mkdir(parents=True, exist_ok=False)
        backup = folder / 'pfe_before_vertical_camera_band.swf'
        shutil.copy2(ROOT / 'pfe.swf', backup)
        assert r.sha(backup) == HOST
        receipt = dict(version=VERSION, status='backed-up', time=datetime.now().astimezone().isoformat(),
            target='pfe.swf', before=HOST, after=CANDIDATE, backup=str(backup), baseline=state['installed'],
            sourceBuild=str(HERE / 'build.json'), sourceBuildSHA256=r.sha(HERE / 'build.json'),
            semanticAuditSHA256=AUDIT, sourceInputs=state['selected']['inputs'],
            qualificationPath=state['qualificationPath'], qualificationSHA256=state['qualificationSHA256'],
            review=state['qualification']['review'], evidence=state['qualification']['evidence'],
            releaseScriptSHA256=r.sha(Path(__file__)), productionHasTelemetry=False,
            versionIdentity='Source recipe version, carrier state version, and actual host SHA256', wholeTaskComplete=False)
        r.save(RECEIPT, receipt)
        try:
            assert state['installed'] == r.baseline() and state['selected'] == product()[0]
            assert r.sha(Path(state['qualificationPath'])) == state['qualificationSHA256']
            replace(HERE / 'pfe.swf', ROOT / 'pfe.swf', HOST, CANDIDATE)
            receipt['status'] = 'installed-awaiting-smoke'; r.save(RECEIPT, receipt)
            smoke = installed_smoke(state, args.smoke_name, lease)
            assert r.sha(Path(state['qualificationPath'])) == state['qualificationSHA256']
            receipt.update(status='verified', installed=r.baseline(), smoke=smoke)
            r.save(RECEIPT, receipt)
        except BaseException as error:
            receipt['failure'] = repr(error)
            r.save(RECEIPT, receipt)
            rollback(receipt)
            raise
        lease.outcome = 'passed'; lease.note = 'Actual installed host component smoke passed; broader performance goal remains open'
        print(json.dumps(dict(status=receipt['status'], host=CANDIDATE, backup=str(backup), smoke=smoke), ensure_ascii=False))


if __name__ == '__main__':
    main()
