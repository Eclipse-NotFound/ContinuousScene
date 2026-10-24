"""Registered isolated paused-world camera/presentation diagnosis, never gameplay acceptance."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import statistics
import subprocess
import sys
import uuid
from datetime import datetime
from xml.sax.saxutils import escape

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
VERSION = 'camera-atlas-size-compare-1'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


control = load('camera_raster_control', HERE.parent / 'scene-compat-20261024/shell-stop-candidate/combat_run.py')
dense, base, r, m = control.dense, control.base, control.r, control.m
support = dense.support
patch = load('camera_raster_patch', HERE / 'probe_patch.py')


def runner_inputs():
    return dict(control.runner_inputs(), **{str(p): r.sha(p) for p in
        [HERE / 'run.py', HERE / 'probe_patch.py', HERE / 'atlas_transform.py', patch.HELPER]})


def fixture_inputs():
    old = control.seed()
    return {str(p): r.sha(p) for p in [control.SEED_RECEIPT, Path(old['probePath']),
        Path(old['sourceOrigin']), patch.HELPER, HERE / 'probe_patch.py', HERE / 'atlas_transform.py',
        support.OUT / 'source-provenance.json']}


def compile_probe(lease, baseline, scripts, compiler, fixture):
    old = control.seed(); staging = HERE / 'source-staging' / uuid.uuid4().hex
    patch.prepare(Path(old['frozenSourcePath']), staging / 'src')
    after = base.tree_hashes(staging / 'src')
    changed = sorted(k for k in set(after) | set(old['frozenSourceSHA256'])
                     if after.get(k) != old['frozenSourceSHA256'].get(k))
    assert changed == patch.CHANGED and len(after) == 87
    origin = staging / 'source-origin.json'
    r.save(origin, dict(version=VERSION, seedReceiptSHA256=control.SEED_SHA,
        seedProbeSHA256=control.PROBE, seedSourceSHA256=old['frozenSourceSHA256'],
        stagedSHA256=after, changed=changed, fixtureInputs=fixture))
    path = compile_frozen(lease, staging / 'src', baseline, scripts, compiler, fixture)
    value = r.read(path)
    value.update(cameraRasterVersion=VERSION, denseFixture=dense.VERSION,
                 sourceOrigin=str(origin), sourceOriginSHA256=r.sha(origin))
    r.save(path, value); return path


def compile_frozen(lease, source, baseline, scripts, compiler, fixture):
    # This function builds one SWF only. It never prepares a game runtime or
    # launches AIR, so player windows may remain open during --compile-only.
    control.memory_gate()
    captured = base.tree_hashes(source)
    folder = HERE / 'probe-builds/probe-source' / uuid.uuid4().hex
    frozen = folder / 'src'; folder.mkdir(parents=True, exist_ok=False)
    shutil.copytree(source, frozen)
    assert captured == base.tree_hashes(source) == base.tree_hashes(frozen)
    assert r.sha(frozen / base.HELPER) == r.read(support.OUT / 'source-provenance.json')['probeHelperSHA256']
    stamp = datetime.now().astimezone().isoformat()
    r.save(folder / 'source-snapshot.json', dict(sharedSourcePath=str(source),
        sharedSourceSnapshotSHA256=captured, frozenSourcePath=str(frozen),
        frozenSourceSHA256=captured, capturedAt=stamp))
    output, config = folder / 'ContinuousSceneProbe.swf', folder / 'ContinuousSceneProbe.xml'
    config.write_text('''<flex-config><target-player>32.0</target-player><compiler>
<external-library-path><path-element>{air}</path-element></external-library-path>
<source-path><path-element>{source}</path-element></source-path><debug>false</debug><optimize>true</optimize><theme/>
</compiler></flex-config>'''.format(air=escape(str(r.enemy.TOOLS / 'airsdk/frameworks/libs/air/airglobal.swc')),
                                  source=escape(str(frozen))), encoding='utf-8')
    command = [str(r.enemy.JAVA), '-Xmx512m', '-Dfile.encoding=UTF-8', '-jar',
        str(r.enemy.TOOLS / 'flexsdk/lib/mxmlc.jar'), '+flexlib=' + str(r.enemy.TOOLS / 'flexsdk/frameworks'),
        '-load-config=' + str(config), '-swf-version=32', '-static-link-runtime-shared-libraries=true',
        '-output=' + str(output), str(frozen / 'ContinuousSceneProbeDoc.as')]
    process = None; lease.before_launch('Offline camera probe compiler; no AIR launch')
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        lease.child(process.pid); log, _ = process.communicate()
        (folder / 'compile.log').write_bytes(log)
        assert process.returncode == 0, 'Probe compiler failed: ' + str(folder / 'compile.log')
    finally:
        if process is not None:
            if process.poll() is None: process.kill(); process.wait(timeout=15)
            lease.child_stopped()
    assert captured == base.tree_hashes(frozen)
    assert scripts == runner_inputs() and compiler == support.compiler_inputs()
    assert fixture == fixture_inputs() and baseline == r.baseline()
    receipt = dict(version='native-input-combat-probe-1', capturedAt=stamp,
        sharedSourcePath=str(source), sharedSourceSnapshotSHA256=captured,
        frozenSourcePath=str(frozen), frozenSourceSHA256=captured,
        probePath=str(output), probeSHA256=r.sha(output), configPath=str(config), configSHA256=r.sha(config),
        command=command, compilerLogSHA256=r.sha(folder / 'compile.log'), runnerInputs=scripts,
        compilerInputs=compiler, candidateInputs=fixture, productionSHA256=baseline,
        diagnosticOnly=True, deployed=False, performanceAcceptance=False)
    path = folder / 'probe-build.json'; r.save(path, receipt)
    print(json.dumps(dict(frozenProbeBuild=str(path), compiled=True, launchedAir=False)), flush=True)
    return path


def verify_probe(path, baseline, scripts, compiler, fixture):
    value = base.verify_probe(path, baseline, scripts, compiler, fixture)
    assert value['cameraRasterVersion'] == VERSION and value['denseFixture'] == dense.VERSION
    op = Path(value['sourceOrigin']); assert r.sha(op) == value['sourceOriginSHA256']
    origin, old = r.read(op), control.seed()
    assert origin['seedReceiptSHA256'] == control.SEED_SHA and origin['seedProbeSHA256'] == control.PROBE
    assert origin['seedSourceSHA256'] == old['frozenSourceSHA256'] and origin['changed'] == patch.CHANGED
    assert origin['stagedSHA256'] == value['frozenSourceSHA256'] and origin['fixtureInputs'] == fixture
    frozen = Path(value['frozenSourcePath'])
    original = (Path(old['frozenSourcePath']) / 'ContinuousSceneMotionProbe.as').read_text(encoding='utf-8-sig')
    assert (frozen / 'ContinuousSceneMotionProbe.as').read_text(encoding='utf-8-sig') == patch.transform(original)
    assert r.sha(frozen / 'tests/SceneCameraRasterTrial.as') == r.sha(patch.HELPER)
    original_atlas = (Path(old['frozenSourcePath']) / 'SceneRasterPresentation.as').read_text('utf-8-sig')
    assert (frozen / 'SceneRasterPresentation.as').read_text('utf-8-sig') == patch.variant.transform(original_atlas)
    assert (frozen / 'SceneRasterLegacyPresentation.as').read_text('utf-8-sig') == original_atlas.replace('public class SceneRasterPresentation', 'public class SceneRasterLegacyPresentation')
    return value


def options(name):
    return ['--name', name, '--high-qos', '--land', 'random_mane', '--encounter', '--fixed-enemies',
        '--benchmark', 'scene', '--short', '--stable-motion', '--native-input-motion', '--native-sprint',
        '--player-fire', '--combat-route', '--combat-route-length', '200', '--window-width', '2048', '--window-height', '1123',
        '--no-lighting', '--no-wall', '--expect-no-signs', '--draw-control', 'atlas', '--presentation-check']


def verify_trial(trial, cleanup):
    assert trial['version'] == 'camera-atlas-size-compare-1'
    assert trial['pixelTolerance'] == dict(maxRGB=1, maxAlpha=0, restoreExact=True)
    assert trial['complete'] and trial['passed'] and trial['pixelsValid'] and trial['errors'] == []
    assert cleanup == trial['cleanup'] and cleanup['restored'] and cleanup['errors'] == []
    assert cleanup['pendingOwnedBitmaps'] == 0
    assert trial['pixelBitmapsCreated'] == trial['pixelBitmapsDisposed'] == 25
    assert trial['framesMs'] == trial['sampleAtMs'] == trial['windows'] == []
    assert trial['measurementFrames'] == 0 and len(trial['pixels']) == 5
    counterexamples = 0
    for row in trial['pixels']:
        legacy, padded = row['legacy'], row['atlas']
        assert legacy['maxAlpha'] == padded['maxAlpha'] == 0
        assert row['exactEqual'] == row['equal'] == padded['equal'] == (padded['differentPixels'] == 0)
        assert row['withinTolerance'] and row['passed'] and row['restored']
        assert padded['maxRGB'] <= 1
        for key in ('legacyRestore','restore'):
            restore = row[key]
            assert restore['equal'] and restore['differentPixels'] == restore['maxAlpha'] == restore['maxRGB'] == 0
        counterexamples += int(legacy['maxRGB'] > 1)
        assert len(row['atlasStorage']['layers']) == 4
        for layer in row['atlasStorage']['layers']:
            for key in ('width','height'):
                value = layer[key]
                assert value > 0 and value & (value-1) == 0
    assert counterexamples == trial['legacyCounterexampleCount']
    return dict(pixelViews=5, snapshots=25, legacyCounterexamples=counterexamples,
        sizeRemediationObserved=counterexamples>0,
        note='Same frame old/new comparison; zero counterexamples is inconclusive for remediation; no gameplay timing.')


def main():
    assert __debug__
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    parser.add_argument('--registry-wait', type=int, default=600)
    parser.add_argument('--compile-only', action='store_true')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--compile-probe', action='store_true')
    group.add_argument('--probe-build', type=Path)
    args = parser.parse_args()
    assert not args.compile_only or args.compile_probe, '--compile-only requires --compile-probe'
    assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
    folder = r.E / args.name; assert not folder.exists(), 'Preserve prior evidence'
    record = dict(version=VERSION, diagnosticOnly=True, performanceEligible=False,
                  gameplayAcceptance=False, options=options(args.name))
    with m.Registration(owner='ContinuousScene / camera raster / 01a13816', purpose=args.name,
                        run_dir=HERE if args.compile_only else m.RUNTIME, evidence=folder,
                        resource='offline' if args.compile_only else 'game', wait=args.registry_wait) as lease:
        try:
            if not args.compile_only: assert not m.air_pids(), 'Other AIR remains untouched'
            memory = control.memory_gate()
            baseline, scripts, compiler, fixture = r.baseline(), runner_inputs(), support.compiler_inputs(), fixture_inputs()
            for key, digest in control.PINS.items(): assert baseline[key] == digest, key
            record.update(baseline=baseline, runnerInputs=scripts, compilerInputs=compiler,
                          fixtureInputs=fixture, memoryBefore=memory, hostSHA256=control.HOST)
            path = compile_probe(lease, baseline, scripts, compiler, fixture) if args.compile_probe else args.probe_build.resolve()
            probe = verify_probe(path, baseline, scripts, compiler, fixture)
            if args.compile_only:
                folder.mkdir(parents=True, exist_ok=False)
                r.save(folder / 'probe-build.json', probe)
                r.save(folder / 'runner-inputs.json', record)
                r.save(folder / 'compile-only.json', dict(complete=True, compiled=True, launchedAir=False,
                    deployed=False, gameplayAcceptance=False, performanceEligible=False,
                    probeBuildPath=str(path), probeSHA256=probe['probeSHA256'], inputsUnchanged=baseline==r.baseline()))
                lease.outcome='passed'; lease.note='Offline compile only; player AIR untouched; no game test or performance acceptance'
                return
            m.prepare(); shutil.copy2(probe['probePath'], m.RUNTIME / base.PROBE_PATH)
            for key, digest in baseline.items():
                if key not in ('application.xml', 'mods/loader-manifest.txt'): assert r.sha(m.RUNTIME / key) == digest, key
            assert baseline == r.baseline() and scripts == runner_inputs()
            record.update(probeBuildPath=str(path), probeSHA256=probe['probeSHA256'], memoryBeforeAir=control.memory_gate())
            try: m.run_owned(m.parse_args(record['options']), lease)
            finally:
                if folder.exists():
                    r.save(folder / 'probe-build.json', probe)
                    r.save(folder / 'runner-inputs.json', record)
            assert baseline == r.baseline() and scripts == runner_inputs() and fixture == fixture_inputs()
            assert compiler == support.compiler_inputs()
            verify_probe(path, baseline, scripts, compiler, fixture)
            result, actual = r.result(args.name)
            for key, digest in baseline.items():
                if key not in ('application.xml', 'mods/loader-manifest.txt'): assert actual[key] == digest, key
            assert actual[base.PROBE_PATH] == probe['probeSHA256']
            policy = r.read(folder / 'process-policy.json')
            assert policy['desktopPolicy'] == 'private' and not policy['performanceEligible']
            assert not policy.get('runFailure') and not policy.get('memoryAbort') and not policy.get('otherAirProcessIds')
            trial = result['cameraRaster']
            rows = verify_trial(trial, result['cameraRasterCleanup'])
            assert not result['samples'], 'Paused diagnosis must not masquerade as gameplay samples'
            summary = dict(version=VERSION, name=args.name, complete=True, diagnosticOnly=True,
                performanceEligible=False, gameplayAcceptance=False, deployed=False,
                resultSHA256=r.sha(folder / 'storage/result.json'), probeSHA256=probe['probeSHA256'], pixelComparison=rows,
                atlasPixelToleranceRGB=1, atlasPixelToleranceAlpha=0, atlasPhysicalPaddingPowerOfTwo=True,
                exactEqual=all(row['exactEqual'] for row in trial['pixels']),
                pixels=trial['pixels'],
                elapsedMs=trial['elapsedMs'], originalFrameRate=trial['originalFrameRate'], testFrameRate=trial['testFrameRate'])
            r.save(folder / 'summary.json', summary)
            lease.outcome = 'passed'; lease.note = 'Five same-frame pixel comparisons completed; no performance/gameplay/release acceptance'
            print(json.dumps(dict(name=args.name, complete=True, pixelViews=5, timingFrames=0, deployed=False)), flush=True)
        except BaseException as error:
            lease.outcome = 'failed'; lease.note = repr(error)
            folder.mkdir(parents=True, exist_ok=True)
            r.save(folder / 'runner-failure.json', dict(record, error=repr(error), complete=False, deployed=False))
            raise


base.OUT = HERE / 'probe-builds'
base.runner_inputs = runner_inputs
base.candidate_inputs = fixture_inputs
if __name__ == '__main__': main()
