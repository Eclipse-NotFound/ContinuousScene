"""Registered isolated FocusManager upper-bound control; never production."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys
import uuid

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
VERSION = 'focus-control-1'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


env = load('sampler_environment', HERE.parent/'environment-control/run.py')
dense, base, r, m, support = env.dense, env.base, env.r, env.m, env.support
HOST = env.HOST
RC = '78C052AEA963F1689B705AE1E14D274916AE1A1F7E81933390CAF8D1A88F4699'
RV = 'BF4AC9CD87272B03FAE7EC22EE67D045F037362F412EE801CAD3F9BA9FE3AFEF'
LOADER = '2050E023205E87FDFDF7FBA4B54B9BAD7769868E51767D0BFBE1742CDC7542E2'
TDFC = '7ACD45193109267DBBF875240528048AD6F1D09FA3B8B36BAA6F98EBB5FDDCE5'
RV_PATH = 'mods/RealisticVision/release/RealisticVisionMod.swf'
RV_RECEIPT = r.ROOT/'mods/RealisticVision/build/effect-load-v3-output/deployment/receipt.json'
CAPABILITY = HERE.parent/'sampler-capability/runs/sampler-capability-r2-e5eeb47418764e4a9bce2920051dcb6f'
CAPABILITY_RESULT_SHA = '42D539971AD4535CCC567036E66F019E5C1ADE3FFC5591BA6F74BD9E094CAC56'
CHANGED = ['ContinuousSceneMotionProbe.as', 'tests/SceneFocusControl.as']


def prerequisites(baseline=None):
    env.deployment(); env.seed()
    raw = CAPABILITY/'storage/result.json'
    assert r.sha(raw) == CAPABILITY_RESULT_SHA
    cap = r.read(raw)
    assert cap['supported'] and cap['counts']['knownHotLoopCPU'] == cap['counts']['cpu'] == 222
    assert cap['cleanup']['stopped'] and not cap['compilerDebug']
    deployment = r.read(RV_RECEIPT)
    assert deployment['result'] == 'PASS' and deployment['version'] == 'v0.33.9-effect-load'
    assert deployment['new'].upper() == RV
    assert r.sha(r.ROOT/RV_PATH) == RV
    assert r.sha(r.ROOT/'mods/RealisticVision'/deployment['backup']) == deployment['old'].upper()
    if baseline is not None:
        expected = dict(deployment['before']); expected[RV_PATH] = RV
        for key, value in expected.items(): assert baseline[key] == value.upper(), key
        assert baseline['pfe.swf'] == HOST and baseline[base.CS_PATH] == base.FORMAL_CS
        assert baseline[dense.RC] == RC and baseline['mods/ModLoader/release/ModLoaderMod.swf'] == LOADER
        assert baseline['mods/TDFC/release/TDFCMod.swf'] == TDFC


def runner_inputs():
    paths = [HERE/'run.py', HERE/'probe_patch.py', HERE/'tests/SceneFocusControl.as',
             HERE.parent/'environment-control/run.py']
    return dict(dense.runner_inputs(), **{str(p): r.sha(p) for p in paths})


def fixture_inputs():
    prerequisites()
    old = env.seed()
    paths = [env.SEED_RECEIPT, Path(old['probePath']), env.DEPLOYMENT, RV_RECEIPT,
             CAPABILITY/'summary.json', CAPABILITY/'storage/result.json',
             HERE/'probe_patch.py', HERE/'tests/SceneFocusControl.as']
    return {str(p): r.sha(p) for p in paths}


def compile_probe(lease, baseline, scripts, compiler, fixture, patch):
    old = env.seed(); staging = HERE/'source-staging'/uuid.uuid4().hex
    patch.prepare(Path(old['frozenSourcePath']), staging/'src')
    after = base.tree_hashes(staging/'src')
    changed = sorted(k for k in set(old['frozenSourceSHA256']) | set(after)
                     if old['frozenSourceSHA256'].get(k) != after.get(k))
    assert changed == CHANGED and len(after) == 86
    assert base.tree_hashes(Path(old['frozenSourcePath'])) == old['frozenSourceSHA256']
    origin = staging/'source-origin.json'
    r.save(origin, dict(version=VERSION, seedReceiptSHA256=env.SEED_SHA, seedProbeSHA256=env.SEED_PROBE,
        seedSource=old['frozenSourcePath'], seedSourceSHA256=old['frozenSourceSHA256'],
        changed=changed, stagedSHA256=after, fixtureInputs=fixture))
    base.B = staging/'build'
    path = base.compile_frozen_probe(lease, baseline, scripts, compiler, fixture)
    receipt = r.read(path); receipt.update(focusControlVersion=VERSION, denseFixture=dense.VERSION,
        sourceOrigin=str(origin), sourceOriginSHA256=r.sha(origin))
    r.save(path, receipt); return path


def verify_probe(path, baseline, scripts, compiler, fixture, patch):
    value = base.verify_probe(path, baseline, scripts, compiler, fixture)
    assert value['focusControlVersion'] == VERSION
    origin_path = Path(value['sourceOrigin']); assert r.sha(origin_path) == value['sourceOriginSHA256']
    origin, old = r.read(origin_path), env.seed()
    assert origin['seedReceiptSHA256'] == env.SEED_SHA and origin['seedProbeSHA256'] == env.SEED_PROBE
    assert origin['seedSourceSHA256'] == old['frozenSourceSHA256']
    assert origin['changed'] == CHANGED and origin['fixtureInputs'] == fixture
    assert origin['stagedSHA256'] == value['frozenSourceSHA256']
    frozen = Path(value['frozenSourcePath'])
    original = (Path(old['frozenSourcePath'])/'ContinuousSceneMotionProbe.as').read_text('utf-8-sig')
    assert (frozen/CHANGED[0]).read_text('utf-8-sig') == patch.transform(original)
    assert r.sha(frozen/CHANGED[1]) == r.sha(HERE/'tests/SceneFocusControl.as')
    return value


def verify_control(result):
    control = result['focusControl']
    assert control['version'] == VERSION and control['valid'] is True
    assert control['diagnosticOnly'] is True and control['performanceEligible'] is False
    assert control['errors'] == []
    q = control['qualification']
    assert q['passed'] is True and q['managerCount'] == 1 and q['existingControls']
    for field in ('containsVisual', 'initialActivated', 'initialStageFocusNull',
                  'initialLastFocusNull', 'initialDefButtonNull', 'initialDefaultButtonNull'):
        assert q[field] is True, field
    assert set(q['privateQNames']) == {'activated', 'lastFocus', 'defButton', '_defaultButton'}
    def state(value, active):
        assert value['activated'] is active
        for key in ('identity', 'containsVisual', 'stageFocusNull', 'lastFocusNull',
                    'defButtonNull', 'defaultButtonNull'):
            assert value[key] is True, key
    assert len(control['windows']) == len(result['samples']) == 4
    for i, row in enumerate(control['windows']):
        active = i in (0, 3)
        assert row == result['samples'][i]['focusControl']
        assert row['index'] == i and row['arm'] == ('active' if active else 'inactive')
        assert row['expectedActivated'] is active and row['frames'] == 300 and row['ended'] is True
        assert row['diagnosticOnly'] is True and row['performanceEligible'] is False
        assert row['transitionMs'] >= 0
        state(row['before'], i in (0, 1)); state(row['after'], active); state(row['end'], active)
        assert [s['age'] for s in row['states']] == list(range(0, 300, 30)) + [299]
        for s in row['states']:
            assert s['activated'] is active and s['identity'] is True and s['stageFocusNull'] is True
            assert s['menu'] is False and s['pip'] is False and s['sats'] is False
    cleanup = control['cleanup']
    assert cleanup['attempted'] is True and cleanup['restored'] is True and cleanup['error'] is None
    state(cleanup['state'], True)
    return control


def main():
    assert __debug__
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    parser.add_argument('--mode', choices=['normal', 'scene'], default='scene')
    parser.add_argument('--registry-wait', type=int, default=600)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--compile-probe', action='store_true')
    group.add_argument('--probe-build', type=Path)
    args = parser.parse_args()
    assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
    folder = r.E/args.name; assert not folder.exists()
    patch = load('focus_control_patch', HERE/'probe_patch.py')
    with m.Registration(owner='ContinuousScene / focus-manager upper-bound / 01a13816', purpose=args.name,
            run_dir=m.RUNTIME, evidence=folder, wait=args.registry_wait) as lease:
        assert not m.air_pids(), 'Other AIR remains untouched'
        memory = env.memory_gate()
        baseline, scripts, compiler, fixture = r.baseline(), runner_inputs(), support.compiler_inputs(), fixture_inputs()
        prerequisites(baseline)
        path = compile_probe(lease, baseline, scripts, compiler, fixture, patch) if args.compile_probe else args.probe_build.resolve()
        probe = verify_probe(path, baseline, scripts, compiler, fixture, patch)
        env.memory_gate(); m.prepare()
        shutil.copy2(probe['probePath'], m.RUNTIME/base.PROBE_PATH)
        assert baseline == r.baseline() and scripts == runner_inputs() and fixture == fixture_inputs()
        for key, digest in baseline.items():
            if key not in ('application.xml', 'mods/loader-manifest.txt'): assert r.sha(m.RUNTIME/key) == digest, key
        before_air = env.memory_gate()
        options = ['--name', args.name, '--high-qos', '--land', 'random_mane', '--encounter', '--fixed-enemies',
            '--benchmark', args.mode, '--short', '--stable-motion', '--native-input-motion', '--native-sprint',
            '--player-fire', '--combat-route', '--combat-route-length', '200', '--window-width', '2048',
            '--window-height', '1123', '--no-lighting', '--no-wall', '--draw-control', 'rcnative']
        if args.mode == 'normal':
            options += ['--native-room-x', '2', '--native-room-y', '4', '--native-route-x', '480', '--native-route-y', '119']
        else: options += ['--expect-no-signs']
        try:
            m.run_owned(m.parse_args(options), lease)
        finally:
            if folder.exists():
                r.save(folder/'probe-build.json', probe)
                r.save(folder/'runner-inputs.json', dict(options=options, baseline=baseline, runnerInputs=scripts,
                    compilerInputs=compiler, fixtureInputs=fixture, probeBuildPath=str(path),
                    focusControlVersion=VERSION, memoryBefore=memory, memoryBeforeAir=before_air,
                    diagnosticOnly=True, performanceEligible=False, actualInstalledGameBytes=True))
        assert baseline == r.baseline() and scripts == runner_inputs() and fixture == fixture_inputs()
        assert compiler == support.compiler_inputs()
        verify_probe(path, baseline, scripts, compiler, fixture, patch)
        result, inputs = r.result(args.name)
        for key, digest in baseline.items():
            if key not in ('application.xml', 'mods/loader-manifest.txt'): assert inputs[key] == digest, key
        assert inputs[base.PROBE_PATH] == probe['probeSHA256']
        policy = r.read(folder/'process-policy.json')
        assert not policy['performanceEligible'] and not policy.get('runFailure')
        assert not policy.get('memoryAbort') and not policy.get('otherAirProcessIds')
        summary = dense.summarize(result, args)

        control=result['focusControl']
        combined={}
        for arm,indices in [('A',[0,3]),('B',[1,2])]:
            combined[arm]=dict(continuous=base.metrics([dt for i in indices for dt in result['samples'][i]['continuousFramesMs']]),
                playerShots=sum(result['samples'][i]['playerShotFrames'] for i in indices),
                enemyShots=sum(result['samples'][i]['enemyShotFrames'] for i in indices))
        summary.update(version=VERSION,focusControl=control,arms=combined,
            hostSHA256=HOST,probeSHA256=probe['probeSHA256'],diagnosticOnly=True,
            performanceAcceptance=False,deployed=False,resultSHA256=r.sha(folder/'storage/result.json'))
        summary['limitations'] += ['B disables the whole existing FocusManager only inside this isolated test process.',
            'TAB, Enter and mouse focus/menu handling are affected: this is not a production candidate.',
            'Restoration rebuilds functional focus registration; dictionary identities and listener relative order are not preserved.',
            'Activation/deactivation and rebuild overhead remain in continuous intervals; no boundary or outlier removal.',
            'No call-stack sampler runs in this control. Whole-run native movement, bullets and combat still qualify separately.']
        r.save(folder/'summary.json',summary)
        assert summary['qualification']['passed']
        verify_control(result)
        lease.outcome='passed';lease.note='FocusManager whole-subsystem upper-bound diagnostic; no deployment'
        print(json.dumps(dict(name=args.name,qualification=summary['qualification'],arms=combined,
            controlValid=control['valid'],summary=str(folder/'summary.json')),ensure_ascii=False),flush=True)


base.OUT=HERE/'probe-builds'
base.runner_inputs=runner_inputs
base.candidate_inputs=fixture_inputs
if __name__=='__main__':main()
