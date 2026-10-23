"""Release only the reviewed 80CF host; preserve every installed mod and setting.

The source recipe version plus the exact installed SWF fingerprint identify this
host-only patch. No diagnostic marker, fields, timers or counters are added to
the game. A failed installed-file smoke rolls back only our own host revision.
"""
from pathlib import Path
from datetime import datetime
import argparse
import importlib.util
import json
import os
import shutil
import sys
import uuid

sys.dont_write_bytecode = True
B = Path(__file__).resolve().parent
MOD, ROOT = B.parent, B.parents[2]
PERF = B/'generated/combat-near-native-20261023/logic-profile-audit/fog-last-blocker-production-performance'
RECEIPT = MOD/'state/fog-last-blocker-deployment-20261023.json'
VERSION = 'fog-last-blocker-production-minimal-1'
PREFIX = 'fog-blocker-product-20261023-'
RUNS = ('scene-baseline-r2', 'scene-baseline-r4', 'scene-candidate-r1',
        'scene-candidate-r2', 'normal-baseline-r1', 'normal-candidate-r1')
PROBE_RECEIPT = PERF/'probe-builds/probe-source/9c16fb0212c34197bd1bafcf34b76990/probe-build.json'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


p = load('blocker_release_performance', PERF/'run.py')
r, m, base, dense = p.r, p.m, p.base, p.dense


def replace(source, destination, expected):
    temporary = destination.with_name(destination.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        shutil.copy2(source, temporary)
        assert r.sha(temporary) == expected
        os.replace(temporary, destination)
        assert r.sha(destination) == expected
    finally:
        temporary.unlink(missing_ok=True)


def preflight():
    assert '<content>pfe.swf</content>' in (ROOT/'application.xml').read_text('utf-8-sig')
    build = p.product()
    assert build['version'] == VERSION
    component = p.component(PREFIX+'candidate-check-r1')
    installed = r.baseline()
    assert installed['pfe.swf'] == base.FORMAL_HOST
    probe = dense.verify_probe(PROBE_RECEIPT, installed, p.runner_inputs(),
                               p.support.compiler_inputs(), p.fixture_inputs())
    checked = []
    for suffix in RUNS:
        name = PREFIX+suffix
        result, inputs = r.result(name)
        folder = r.E/name
        summary = r.read(folder/'summary.json')
        capture = r.read(folder/'runner-inputs.json')
        assert summary['productPerformanceVersion'] == p.VERSION
        assert summary['qualification']['passed'] and summary['continuous']['count'] == 1200
        assert summary['productionHostWithoutCounters']
        expected = p.HOST if 'candidate' in suffix else base.FORMAL_HOST
        assert summary['hostSHA256'] == inputs['pfe.swf'] == expected
        assert capture['baseline'] == installed
        assert capture['runnerInputs'] == p.runner_inputs()
        assert capture['fixtureInputs'] == p.fixture_inputs()
        assert r.read(folder/'probe-build.json')['probeSHA256'] == probe['probeSHA256']
        assert inputs[base.PROBE_PATH] == probe['probeSHA256']
        for key, digest in installed.items():
            if key not in ('application.xml', 'mods/loader-manifest.txt', 'pfe.swf'):
                assert inputs[key] == digest, (name, key)
        checked.append(dict(name=name, summarySHA256=r.sha(folder/'summary.json'),
                            hostSHA256=expected, checks=len(result['assertions'])))
    return installed, build, probe, checked


def rollback(receipt):
    backup = Path(receipt['backup'])
    assert r.sha(backup) == base.FORMAL_HOST
    current = r.sha(ROOT/'pfe.swf')
    assert current in (base.FORMAL_HOST, p.HOST), 'Concurrent host change; do not overwrite'
    if current == p.HOST:
        replace(backup, ROOT/'pfe.swf', base.FORMAL_HOST)
    receipt['status'] = 'rolled-back'
    r.save(RECEIPT, receipt)


def main():
    assert __debug__
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['check', 'deploy', 'rollback'])
    args = parser.parse_args()
    if args.mode == 'check':
        installed, build, probe, checked = preflight()
        print(json.dumps(dict(passed=True, version=VERSION, target=p.HOST,
            unchangedDependencies=len(installed)-1, checked=checked), ensure_ascii=False))
        return
    with m.Registration(owner='ContinuousScene / last blocker release / 01a13816',
            purpose=args.mode+' '+VERSION, run_dir=m.RUNTIME, evidence=RECEIPT, wait=600) as lease:
        assert not m.air_pids(), 'AIR present; leave all existing processes untouched'
        if args.mode == 'rollback':
            rollback(r.read(RECEIPT)); lease.outcome = 'passed'; return
        assert not RECEIPT.exists(), 'Existing receipt requires review'
        installed, build, probe, checked = preflight()
        folder = B/'backups'/('fog-last-blocker-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
        folder.mkdir(parents=True, exist_ok=False)
        backup = folder/'pfe_before_ContinuousScene_fog_last_blocker_20261023.swf'
        shutil.copy2(ROOT/'pfe.swf', backup)
        assert r.sha(backup) == base.FORMAL_HOST
        receipt = dict(version=VERSION, status='backed-up', time=datetime.now().astimezone().isoformat(),
            backup=str(backup), target='pfe.swf', before=base.FORMAL_HOST, after=p.HOST,
            baseline=installed, checked=checked, candidateBuild=str(p.PRODUCT/'build.json'),
            candidateBuildSHA256=r.sha(p.PRODUCT/'build.json'), semanticAuditSHA256=p.AUDIT,
            componentEvidence=PREFIX+'candidate-check-r1', productionHasTelemetry=False,
            versionIdentity='Source recipe version plus actual installed/runtime host SHA256',
            wholeTaskComplete=False, limitations=[
                'Small lighting algorithm improvement; no near-native or fixed whole-frame percentage claim.',
                'Separate-process combat has varying AI, fire, activity and prewarming.',
                'Unexplained 820ms candidate spike and both failed baseline attempts remain in evidence.',
                'Pixel/state checks include 91 exact pairs; current tests do not cover every game state.'])
        r.save(RECEIPT, receipt)
        try:
            assert r.baseline() == installed and p.product() == build
            replace(p.PRODUCT/'pfe.swf', ROOT/'pfe.swf', p.HOST)
            receipt['status'] = 'installed-awaiting-smoke'; r.save(RECEIPT, receipt)
            expected_installed = dict(installed, **{'pfe.swf': p.HOST})
            assert r.baseline() == expected_installed
            # prepare copies the actually installed host; never substitute a build here.
            m.prepare()
            assert r.sha(m.RUNTIME/'pfe.swf') == p.HOST
            shutil.copy2(probe['probePath'], m.RUNTIME/base.PROBE_PATH)
            smoke = PREFIX+'installed-native-r1'
            m.run_owned(m.parse_args(['--name', smoke, '--suite', 'native', '--high-qos']), lease)
            result, inputs = r.result(smoke)
            assert r.baseline() == expected_installed
            assert inputs[base.PROBE_PATH] == probe['probeSHA256']
            for key, digest in expected_installed.items():
                if key not in ('application.xml', 'mods/loader-manifest.txt'):
                    assert inputs[key] == digest, key
            receipt.update(status='verified', installed=expected_installed,
                smoke=dict(name=smoke, checks=len(result['assertions']),
                    resultSHA256=r.sha(r.E/smoke/'storage/result.json'),
                    inputsSHA256=r.sha(r.E/smoke/'inputs.json')))
            r.save(RECEIPT, receipt)
        except BaseException:
            rollback(receipt)
            raise
        lease.outcome = 'passed'; lease.note = 'Actual installed host smoke passed; near-native task remains open'
        print(json.dumps(dict(status=receipt['status'], version=VERSION,
            host=p.HOST, backup=str(backup), smoke=receipt['smoke']), ensure_ascii=False))


if __name__ == '__main__': main()
