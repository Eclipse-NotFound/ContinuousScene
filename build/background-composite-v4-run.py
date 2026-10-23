"""Formal BEFC/CS7F1F v4 background-composite early pixel diagnostic only.

Freeze and compile the ordinary probe source; do not inject a CS candidate.
Ten native held frames precede terminal same-frame pixels and full cleanup.
Pixel differences fail equivalence while retaining the complete raw evidence.
WB 14112 is pinned: only its disabled, hidden ordinary-room background residue
may accompany the native surfaces; private owner identity is not inferred.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import math
import shutil
import sys

sys.dont_write_bytecode = True
B = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('background_native_input_base', B / 'native-input-combat-run.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
r, m, support = base.r, base.m, base.support
OUT = B / 'generated/background-composite-v4-20261023'
HELPER = 'tests/SceneBackgroundCompositeProbe.as'
HELPER_SHA = '071A9D6FA2E8DCABC0D48236B343B9E37E9D3B5033CC93225D0D19A4F5CCA1E6'
VERSION = 'native-background-composite-diagnostic-4'
WB_PATH = 'mods/WallBlend/release/WallBlendMod.swf'
WB_SHA = '14112DA06214BCA51C6875D2527E73246DCB4C985CAADDA719EB4F77F1C0920D'
WB_VERSION = '0.5.9-scene'
R2_HELPER = B / 'generated/background-composite-20261023/probe-source/4739a6f139284ad7a33bbe30d3fdf34c/src' / HELPER
R2_HELPER_SHA = 'E900C41C9A27292B842749330D632D0AD5E0250B2E53D0F2D44EE8A8E5075F5C'
original_runner_inputs = base.runner_inputs


def runner_inputs():
    return dict(original_runner_inputs(), **{str(Path(__file__)): r.sha(Path(__file__))})


def helper_inputs():
    source = B.parent / 'src' / HELPER
    proof = support.OUT / 'source-provenance.json'
    assert r.sha(source) == HELPER_SHA, 'Background helper changed; review and pin explicitly'
    assert r.sha(proof) == support.PROVENANCE_SHA
    assert r.sha(R2_HELPER) == R2_HELPER_SHA, 'Preserve the rejected r2 source evidence'
    return {str(source): HELPER_SHA, str(proof): support.PROVENANCE_SHA, str(R2_HELPER): R2_HELPER_SHA}


# Reuse only the frozen-source compiler/receipt verification. Its unchanged r2
# helper guard still applies, but no sleeping-root native SWF is injected or run.
base.OUT = OUT
base.runner_inputs = runner_inputs
base.candidate_inputs = helper_inputs


def verify_probe(path, baseline, scripts, compiler, helpers):
    assert baseline[WB_PATH] == WB_SHA, 'Hidden-residue exception only reviewed for WB 14112'
    probe = base.verify_probe(path, baseline, scripts, compiler, helpers)
    frozen = Path(probe['frozenSourcePath'])
    assert probe['frozenSourceSHA256'][HELPER] == r.sha(frozen / HELPER) == HELPER_SHA
    source = (frozen / 'ContinuousSceneMotionProbe.as').read_text('utf-8-sig')
    for token in ('SceneBackgroundCompositeProbe', 'backgroundComposite.prepareFrame(w)',
                  'backgroundComposite.update(w,true)', 'backgroundComposite.verify(w)',
                  'phase==88', 'backgroundCompositeCleanup'):
        assert token in source, token
    return probe


def check_stats(stats, cleanup=False):
    assert stats['version'] == VERSION and stats['diagnosticOnly'] and not stats['performanceAcceptance']
    assert stats['requiredWallBlendVersion'] == WB_VERSION
    assert stats['trackedWallResidues'] in (0, 1) and not stats['residueIdentityInvalid']
    for key in ('updates', 'appliedUpdates', 'prepareCalls', 'restores', 'parentWrites', 'copies',
                'allocations', 'reuses', 'disposals', 'liveCopies', 'pool', 'heldParents',
                'attachedCompositeBitmaps', 'updateCost', 'copyCost', 'prepareCost', 'conflicts', 'errors'):
        value = stats[key]
        assert isinstance(value, (int, float)) and not isinstance(value, bool)
        assert math.isfinite(value) and value >= 0 and int(value) == value, (key, value)
    assert stats['errors'] == stats['conflicts'] == 0
    assert stats['liveCopies'] == stats['allocations'] - stats['disposals']
    if stats['last']['applied']:
        wall = stats['last']['wallBlend']
        assert wall['requiredBuildVersion'] == WB_VERSION and wall['enabled'] is False and wall['statusRead'] is False
        assert wall['source'] == 'public-enabled-setting-and-actual-display-tree'
        assert stats['last']['allowedWallResidues'] in (0, 1)
        if stats['last']['allowedWallResidues']:
            residue = stats['last']['wallResidue']
            assert residue == dict(name='WallBlendBackgroundLayer', width=1920, height=1000,
                visible=False, index=1, identityTracked=True, unchanged=True)
    if cleanup:
        assert stats['heldParents'] == stats['attachedCompositeBitmaps'] == stats['liveCopies'] == stats['pool'] == 0
        assert stats['trackedWallResidues'] == 0


def summarize(result, name):
    cfg, driver, motion = result['config'], result['driver'], result['nativeInputMotion']
    assert cfg['drawControl'] == 'backgrounds' and cfg['presentationCheck']
    assert cfg['benchmark'] == 'scene' and cfg['nativeInputMotion'] and cfg['stableMotion']
    assert cfg['noLighting'] and cfg['noWall'] and not cfg['vision']
    assert not cfg['sleepingRootCheck'] and not cfg['sleepingRootEarlyCheck'] and not cfg['sleepingRootShort']
    assert driver['nativeInputMotion'] and driver['forcedPositionCalls'] == 0 and motion['spawn']['calls'] == 1
    assert not result['samples'] and result.get('error') is None
    view = result['viewport']
    assert view['stageWidth'] == view['cameraWidth'] == 2032
    assert view['stageHeight'] == view['cameraHeight'] == 1084 and view['zoom'] == 1
    early = result['backgroundCompositeEarlyCheck']
    assert early['version'] == 'background-composite-early-check-1' and early['diagnosticOnly']
    assert early['groundContactRun'] >= 10 and early['startPose']['floorContact']
    assert early['requiredHoldFrames'] == early['nativeHeldFrames'] == len(early['holdSamples']) == 10
    base.check_motion_state(early['startPose'], motion['route'])
    check_stats(early['startSnapshot'])
    applied = early['startSnapshot']['last']['applied']
    for frame, sample in enumerate(early['holdSamples'], 1):
        assert sample['frame'] == frame
        base.check_motion_state(sample['pose'], motion['route'])
        check_stats(sample['snapshot'])
        assert sample['snapshot']['prepareCalls'] > early['startSnapshot']['prepareCalls']
        applied = applied and sample['snapshot']['last']['applied']
    verify, cleanup = result['backgroundCompositeVerification'], result['backgroundCompositeCleanup']
    assert verify['version'] == VERSION and verify['sameFrame'] and verify['diagnosticOnly']
    check_stats(verify['cleanup'], True)
    check_stats(cleanup, True)
    assert not verify.get('error')
    passed = bool(result['ok'] and applied and verify['applied'] and verify['equal'] and
                  verify['restored'] and verify['bindingsRestored'] and all(a['ok'] for a in result['assertions']))
    return dict(version='background-composite-early-summary-1', name=name, passed=passed,
        status='equal' if passed else 'pixel-difference' if verify['applied'] and not verify['equal'] else 'not-accepted',
        diagnosticOnly=True, performanceEligible=False, performanceAcceptance=False, deployed=False,
        helperSHA256=HELPER_SHA, appliedThroughoutHold=applied, driver=driver, viewport=view,
        requiredWallBlendSHA256=WB_SHA, requiredWallBlendVersion=WB_VERSION,
        priorRejectedHelperSHA256=R2_HELPER_SHA,
        allowedHiddenResidue='Only WB14112 lower index-1 hidden 1920x1000 WallBlendBackgroundLayer; stable node/data identity; never altered or composited',
        early=early, verification=verify, cleanup=cleanup, samples=[],
        limitations=['Only the current scale-1 camera and ten held native frames are covered.',
            'No combat timing, other scales, SATS, travel or enabled WB/RV/LAD acceptance.'])


def main():
    if not __debug__:
        raise RuntimeError('Assertions required; do not use -O')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--compile-probe', action='store_true')
    source.add_argument('--probe-build', type=Path)
    parser.add_argument('--registry-wait', type=int, default=600)
    args = parser.parse_args()
    assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
    folder = r.E / args.name
    assert not folder.exists(), 'Preserve existing evidence'
    with m.Registration(owner='ContinuousScene / background composite / 01a13816', purpose=args.name,
            run_dir=m.RUNTIME, evidence=folder, wait=args.registry_wait) as lease:
        assert not m.air_pids(), 'Other AIR present; untouched'
        baseline, scripts, compiler, helpers = r.baseline(), runner_inputs(), support.compiler_inputs(), helper_inputs()
        assert baseline['pfe.swf'] == base.FORMAL_HOST and baseline[base.CS_PATH] == base.FORMAL_CS
        assert baseline[WB_PATH] == WB_SHA
        build_path = base.compile_frozen_probe(lease, baseline, scripts, compiler, helpers) if args.compile_probe else args.probe_build.resolve()
        probe = verify_probe(build_path, baseline, scripts, compiler, helpers)
        m.prepare()
        shutil.copy2(probe['probePath'], m.RUNTIME / base.PROBE_PATH)
        assert r.sha(m.RUNTIME / 'pfe.swf') == base.FORMAL_HOST
        assert r.sha(m.RUNTIME / base.CS_PATH) == base.FORMAL_CS
        assert r.sha(m.RUNTIME / WB_PATH) == WB_SHA
        assert r.sha(m.RUNTIME / base.PROBE_PATH) == probe['probeSHA256']
        options = ['--name', args.name, '--high-qos', '--land', 'random_mane', '--encounter', '--fixed-enemies',
            '--benchmark', 'scene', '--speed', '4', '--short', '--stable-motion', '--native-input-motion', '--player-fire',
            '--combat-route', '--combat-route-length', '200', '--window-width', '2048', '--window-height', '1123',
            '--no-lighting', '--no-wall', '--expect-no-signs', '--draw-control', 'backgrounds', '--presentation-check']
        assert baseline == r.baseline() and scripts == runner_inputs() and compiler == support.compiler_inputs()
        assert helpers == helper_inputs()
        failure = None
        try:
            m.run_owned(m.parse_args(options), lease)
        except RuntimeError as error:
            if str(error) != 'Probe failed' or not (folder / 'storage/result.json').exists():
                raise
            failure = error  # Expected pixel rejection is still a failed check.
        finally:
            if folder.exists():
                r.save(folder / 'probe-build.json', probe)
                r.save(folder / 'runner-inputs.json', dict(options=options, baseline=baseline,
                    runnerInputs=scripts, compilerInputs=compiler, helperInputs=helpers, probeBuildPath=str(build_path),
                    requiredWallBlendSHA256=WB_SHA, requiredWallBlendVersion=WB_VERSION,
                    actualContinuousSceneSHA256=base.FORMAL_CS, candidateInjected=False))
        assert baseline == r.baseline() and scripts == runner_inputs() and compiler == support.compiler_inputs()
        assert helpers == helper_inputs()
        verify_probe(build_path, baseline, scripts, compiler, helpers)
        inputs = {k.replace('\\', '/'): v for k, v in r.read(folder / 'inputs.json').items()}
        for path, digest in baseline.items():
            if path not in ('application.xml', 'mods/loader-manifest.txt'):
                assert inputs[path] == digest, path
        assert inputs[base.PROBE_PATH] == probe['probeSHA256']
        expected = {line.split('|')[1] for line in (r.ROOT / 'mods/loader-manifest.txt').read_text('utf-8-sig').splitlines()
                    if len(line.split('|')) == 5 and line.split('|')[2] == '1'} | {'ContinuousSceneMotionMod'}
        loader = r.read(folder / 'loader-check.json')
        assert set(loader['loaded']) == expected and all(loader['loaded'].values()) and len(loader['sessions']) == 1
        policy = r.read(folder / 'process-policy.json')
        assert policy['performanceEligible'] is False
        assert not policy.get('runFailure') and not policy.get('memoryAbort') and not policy.get('otherAirProcessIds')
        result = r.read(folder / 'storage/result.json')
        summary = summarize(result, args.name)
        summary.update(probeBuildPath=str(build_path), hostSHA256=base.FORMAL_HOST, actualContinuousSceneSHA256=base.FORMAL_CS)
        r.save(folder / 'summary.json', summary)
        print(json.dumps({key: summary[key] for key in ('name', 'passed', 'status', 'appliedThroughoutHold', 'verification', 'cleanup')}), flush=True)
        if failure or not summary['passed']:
            lease.note = 'Background equivalence did not pass; pixels/restoration evidence retained; no deployment'
            raise RuntimeError('Background composite equivalence did not pass; inspect saved summary')
        lease.outcome = 'passed'
        lease.note = 'Early scale-1 pixels and cleanup passed; no performance acceptance or deployment'


if __name__ == '__main__':
    main()
