"""HIGH/LOW sensitivity with owned thread counters; no production acceptance."""
from pathlib import Path
import argparse
import ast
import difflib
import hashlib
import importlib.util
import inspect
import json
import os
import re
import shutil
import sys
import traceback
import types
import uuid
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
VERSION = 'stage-quality-native-1'
HELPER_SHA = '356D95B97654C6D84C78599E3957821B356E46D20B7984FECE838A01B315378F'
PATCH_SHA = '2B62D867E6A10EB9784292595AA98B412BE6F5625EDB7B1C1FF421B4EF5356B3'
ORDER = ('HIGH', 'LOW', 'LOW', 'HIGH')
HELPER = HERE / 'SceneStageQualityTrial.as'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


thread = load('stage_quality_thread_support', HERE.parent / 'thread-cpu-native-20261025/run.py')
w, old, shared, control, dense, base, r, m, support = (
    thread.w, thread.old, thread.shared, thread.control, thread.dense,
    thread.base, thread.r, thread.m, thread.support)
patch = load('stage_quality_patch', HERE / 'probe_patch.py')
digest = lambda data: hashlib.sha256(data).hexdigest().upper()


def imported_sources():
    """Pin imported workspace Python modules as well as the inherited manifest."""
    queue, seen, paths = [thread, patch], set(), set()
    while queue:
        module = queue.pop()
        if id(module) in seen: continue
        seen.add(id(module))
        path = getattr(module, '__file__', None)
        if not path: continue
        path = Path(path).resolve()
        if not path.is_relative_to(r.ROOT.resolve()) or path.suffix != '.py': continue
        paths.add(path)
        queue.extend(value for value in vars(module).values() if isinstance(value, types.ModuleType))
    return sorted(paths)


def runner_inputs():
    assert r.sha(HELPER) == HELPER_SHA and r.sha(HERE/'probe_patch.py') == PATCH_SHA
    assert r.sha(patch.CLOCK_PATCH) == patch.CLOCK_PATCH_SHA
    paths = imported_sources() + [HERE/'run.py', HERE/'README.md', HELPER, patch.CLOCK_PATCH,
        Path(inspect.getsourcefile(m.HiddenProcess)), Path(inspect.getsourcefile(m.Registration))]
    return dict(thread.runner_inputs(), **{str(path): r.sha(path) for path in paths})


def fixture_inputs():
    value = w.seed()
    return {str(path): r.sha(path) for path in [w.SEED, Path(value['probePath']), Path(value['configPath']),
        Path(value['sourceOrigin']), Path(value['probePath']).parent/'probe-build.json',
        HERE/'probe_patch.py', HELPER, patch.CLOCK_PATCH, support.OUT/'source-provenance.json']}


def compile_probe(lease, baseline, scripts, compiler, fixture):
    value = w.seed(); staging = HERE/'source-staging'/uuid.uuid4().hex
    patch.prepare(Path(value['frozenSourcePath']), staging/'src')
    after = base.tree_hashes(staging/'src')
    changed = sorted(k for k in set(after) | set(value['frozenSourceSHA256'])
        if after.get(k) != value['frozenSourceSHA256'].get(k))
    assert changed == patch.CHANGED and len(after) == 86
    origin = staging/'source-origin.json'
    r.save(origin, dict(version=VERSION, seedReceiptSHA256=w.SEED_SHA, seedProbeSHA256=w.PROBE_SHA,
        seedSourceSHA256=value['frozenSourceSHA256'], stagedSHA256=after, changed=changed, fixtureInputs=fixture))
    path = shared.compile_frozen(lease, staging/'src', baseline, scripts, compiler, fixture)
    receipt = r.read(path)
    receipt.update(stageQualityVersion=VERSION, denseFixture=w.FIXTURE,
        sourceOrigin=str(origin), sourceOriginSHA256=r.sha(origin))
    r.save(path, receipt); return path


def verify_probe(path, baseline, scripts, compiler, fixture):
    raw = r.read(path)
    assert path.resolve() == (Path(raw['probePath']).parent/'probe-build.json').resolve(), 'Use original build receipt beside compile.log'
    value = base.verify_probe(path, baseline, scripts, compiler, fixture)
    assert value['stageQualityVersion'] == VERSION and value['denseFixture'] == w.FIXTURE
    op = Path(value['sourceOrigin']); assert r.sha(op) == value['sourceOriginSHA256']
    origin, seed = r.read(op), w.seed()
    assert origin['seedReceiptSHA256'] == w.SEED_SHA and origin['seedProbeSHA256'] == w.PROBE_SHA
    assert origin['seedSourceSHA256'] == seed['frozenSourceSHA256'] and origin['changed'] == patch.CHANGED
    assert origin['stagedSHA256'] == value['frozenSourceSHA256'] and origin['fixtureInputs'] == fixture
    changed = sorted(k for k in set(value['frozenSourceSHA256']) | set(seed['frozenSourceSHA256'])
        if value['frozenSourceSHA256'].get(k) != seed['frozenSourceSHA256'].get(k))
    assert changed == patch.CHANGED and len(value['frozenSourceSHA256']) == 86
    frozen = Path(value['frozenSourcePath'])
    assert (frozen/'ContinuousSceneMotionProbe.as').read_text('utf-8-sig') == patch.transform(
        (Path(seed['frozenSourcePath'])/'ContinuousSceneMotionProbe.as').read_text('utf-8-sig'))
    assert r.sha(frozen/HELPER.name) == HELPER_SHA
    return value


def quality_descriptor(text):
    # r1 failed before AIR: prepare emits a single-line initialWindow. The
    # earlier static fixture used the formatted production XML and missed this.
    anchor = '<renderMode>direct</renderMode>'
    insertion = '<allowLowQuality>true</allowLowQuality>'
    assert text.count(anchor) == 1 and '<allowLowQuality' not in text
    changed = text.replace(anchor, insertion + anchor, 1)
    assert changed.replace(insertion, '', 1) == text
    root = ET.fromstring(changed); ns = {'a': 'http://ns.adobe.com/air/application/30.0'}
    assert root.tag == '{' + ns['a'] + '}application'
    windows = root.findall('a:initialWindow', ns); assert len(windows) == 1
    window = windows[0]
    assert window.findtext('a:allowLowQuality', namespaces=ns) == 'true'
    assert len(root.findall('.//a:allowLowQuality', ns)) == 1
    assert window.findtext('a:renderMode', namespaces=ns) == 'direct'
    assert window.findtext('a:content', namespaces=ns) == 'pfe.swf'
    return changed


def owned_adapter(prepared_text, prepared_bytes):
    """Local run_owned copy: one descriptor tag, retained evidence and CPU callback."""
    original = inspect.getsource(m.run_owned)
    first = "    descriptor.write_text(descriptor_text,encoding='utf-8')"
    inserted = ("    descriptor_text=quality_before_write(descriptor_text,app,args,out)\n" + first +
                "\n    try:\n        quality_after_write(descriptor,out)\n"
                "    except BaseException:\n        descriptor.unlink(missing_ok=True)\n        raise")
    cleanup = '        flag.unlink(missing_ok=True);descriptor.unlink(missing_ok=True)'
    cleanup_insert = '        quality_before_cleanup(descriptor,out)\n' + cleanup
    changed = original
    for before, after in ((first, inserted), (cleanup, cleanup_insert)):
        assert changed.count(before) == 1 and after not in changed
        changed = changed.replace(before, after, 1)
    assert changed.replace(cleanup_insert, cleanup, 1).replace(inserted, first, 1) == original
    assert "current['availableCommit']<512*1024**2" in changed
    assert 'HiddenProcess(' in changed and 'record.child(process.pid)' in changed
    tree = ast.parse(changed)
    assert len(tree.body) == 1 and isinstance(tree.body[0], ast.FunctionDef) and tree.body[0].name == 'run_owned'
    observation = {}

    def save(folder):
        r.save(folder/'descriptor-review.json', {key: value for key, value in observation.items() if key != 'expectedText'})

    def before_write(text, app, args, folder):
        expected = prepared_text.replace('<id>pfe-modsettings-continuous-scene</id>', '<id>'+app+'</id>', 1)
        assert prepared_text.count('<id>pfe-modsettings-continuous-scene</id>') == 1
        if args.window_width > 0:
            expected, wc = re.subn(r'<width>\d+</width>', '<width>'+str(args.window_width)+'</width>', expected)
            expected, hc = re.subn(r'<height>\d+</height>', '<height>'+str(args.window_height)+'</height>', expected)
            assert wc == hc == 1
        assert text == expected, 'Unexpected stock descriptor transformation'
        result = quality_descriptor(text)
        (folder/'application-after-prepare.xml').write_bytes(prepared_bytes)
        (folder/'application-before-quality.xml').write_text(text, 'utf-8')
        observation.update(version=VERSION, appId=app, namespace='30.0', requestedAllowLowQuality=True,
            preparedSHA256=digest(prepared_bytes), beforeTextSHA256=digest(text.encode('utf-8')),
            expectedText=result, expectedSHA256=digest(result.replace('\n', os.linesep).encode('utf-8')),
            onlyNewTagChange=True, reverseExact=True, cleanupChecked=False,
            actualQualityVerifiedByFrameReport=False, descriptorRuntimeAcceptanceNotAssumed=True,
            diff=list(difflib.unified_diff(text.splitlines(), result.splitlines(), fromfile='stock-owned', tofile='allow-low-quality', lineterm='')))
        return result

    def after_write(descriptor, folder):
        assert descriptor.read_text('utf-8-sig') == observation['expectedText']
        assert r.sha(descriptor) == observation['expectedSHA256']
        shutil.copy2(descriptor, folder/'application-used.xml')
        observation.update(actualSHA256=r.sha(descriptor), descriptorPath=str(descriptor))
        save(folder)

    def before_cleanup(descriptor, folder):
        # Never prevent the original finally from releasing process, flags and lock.
        try:
            observation['actualAfterSHA256'] = r.sha(descriptor)
            observation['cleanupChecked'] = observation['actualAfterSHA256'] == observation['actualSHA256']
        except BaseException as error: observation['cleanupCheckError'] = repr(error)
        try: save(folder)
        except BaseException as error: observation['receiptWriteError'] = repr(error)

    scope = dict(m.__dict__)
    scope.update(quality_before_write=before_write, quality_after_write=after_write,
        quality_before_cleanup=before_cleanup, cpu_owned=thread.sampled_cpu(m.cpu_owned))
    exec(compile(tree, '<stage-quality-owned-descriptor>', 'exec'), scope)
    assert scope['run_owned'].__globals__ is not m.__dict__
    return scope['run_owned'], observation, dict(reverseExact=True, sharedModuleModified=False,
        originalSHA256=digest(original.encode('utf-8')), transformedSHA256=digest(changed.encode('utf-8')),
        descriptorChange='initialWindow.allowLowQuality=true only; stock ID/dimensions retained',
        cpuSamplerSource=str(Path(thread.__file__)), threadSampleEveryProcessCalls=3, runGuardBytes=512*1024**2)


STATE_KEYS = ('visible', 'active', 'closed', 'applicationActiveWindowMatches', 'displayState',
    'stageWidth', 'stageHeight', 'frameRate', 'onPause', 'stageDisplayState', 'renderMode',
    'cameraScale', 'visualScaleX', 'visualScaleY', 'bounds')


def quality_review(raw):
    report = raw['stageQuality']; assert report['version'] == VERSION
    assert report['diagnosticOnly'] is True and report['performanceEligible'] is False and report['pixelAcceptance'] is False
    assert report['complete'] is True and report['observations'] == 1200 and report['errors'] == []
    cleanup = report['cleanup']; assert cleanup == raw['stageQualityCleanup']
    assert cleanup['initialized'] is True and cleanup['restored'] is True
    assert cleanup['pendingRestore'] == 0 and cleanup['errors'] == []
    initial = report['initial']; assert initial['normalizedQuality'] == 'HIGH'
    assert cleanup['originalQuality'] == initial['quality']
    switches = report['switches']; assert len(switches) == len(raw['samples']) == 4
    confounds, rows = {}, []

    def state(label, value):
        assert value['quality'].upper() == value['normalizedQuality']
        assert all(type(value[key]) is bool for key in ('visible', 'active', 'closed', 'applicationActiveWindowMatches', 'onPause'))
        assert value['closed'] is False
        assert all(base.finite(value[key]) and value[key] > 0 for key in
            ('stageWidth', 'stageHeight', 'frameRate', 'cameraScale', 'visualScaleX', 'visualScaleY'))
        assert all(base.finite(value['bounds'][key]) for key in ('x', 'y', 'width', 'height'))
        assert value['bounds']['width'] > 0 and value['bounds']['height'] > 0
        for key in STATE_KEYS:
            if value[key] != initial[key]:
                entry = confounds.setdefault(key, dict(initial=initial[key], observations=[]))
                entry['observations'].append(dict(at=label, value=value[key]))

    state('initial', initial)
    for index, row in enumerate(raw['samples']):
        segment = row['stageQuality']; expected = ORDER[index]
        assert row['name'] == 'dense-native-'+str(index)
        assert segment['index'] == index and segment['expectedQuality'] == expected
        assert segment['caseBeginAtMs'] == row['caseBeginAtMs']
        assert segment['caseBeginAtMs'] <= segment['switchBeginAtMs'] <= segment['switchEndAtMs'] <= row['sampleAtMs'][0]
        assert segment['switchMs'] == segment['switchEndAtMs']-segment['switchBeginAtMs']
        assert {key: value for key, value in segment.items() if key != 'frames'} == switches[index]
        state('case%d/before'%index, segment['before']); state('case%d/after'%index, segment['after'])
        assert segment['before']['normalizedQuality'] == (ORDER[index-1] if index else 'HIGH')
        assert segment['after']['normalizedQuality'] == expected
        assert len(segment['frames']) == 300
        for age, frame in enumerate(segment['frames']):
            assert frame['index'] == index and frame['frame'] == age
            assert frame['quality'].upper() == frame['normalizedQuality'] == expected
            assert type(frame['elapsedMs']) is int and frame['elapsedMs'] >= 0
        rows.append(dict(index=index, quality=expected, frames=300, switchMs=segment['switchMs'],
            observationCost=base.metrics([frame['elapsedMs'] for frame in segment['frames']])))
    state('finalBeforeRestore', report['finalBeforeRestore']); state('finalAfterRestore', report['finalAfterRestore'])
    assert report['finalBeforeRestore']['normalizedQuality'] == 'HIGH'
    assert report['finalAfterRestore']['quality'] == initial['quality']
    return dict(passed=True, observations=1200, rows=rows, initial=initial,
        finalBeforeRestore=report['finalBeforeRestore'], finalAfterRestore=report['finalAfterRestore'],
        switches=switches, cleanup=cleanup, boundaryStateConfounds=confounds,
        boundaryStateStableExceptQuality=not confounds, otherStateObservedEveryFrame=False)


def summarize(raw, policy):
    result = thread.summarize(raw, policy)
    quality = quality_review(raw)
    for index, row in enumerate(result['rows']):
        row.update(quality=ORDER[index], qualityObservation=quality['rows'][index],
            threadCpu=result['threads']['cases'][index])
    arms = {}
    for mode, indices in (('HIGH', (0, 3)), ('LOW', (1, 2))):
        cases = [result['threads']['cases'][index] for index in indices]
        elapsed = sum(case['coveredElapsedMs'] for case in cases)
        cpu = sum(case['matchedThreadCpuMs'] for case in cases)
        arms[mode] = dict(indices=list(indices), continuous=base.metrics(
            [dt for index in indices for dt in raw['samples'][index]['continuousFramesMs']]),
            playerShots=sum(result['rows'][index]['playerShots'] for index in indices),
            enemyShots=sum(result['rows'][index]['enemyShots'] for index in indices),
            warmed=sum(result['rows'][index]['warmed'] for index in indices),
            slices=sum(result['rows'][index]['slices'] for index in indices),
            switchMs=sum(quality['rows'][index]['switchMs'] for index in indices),
            matchedThreadCpuMs=cpu, threadCoveredElapsedMs=elapsed,
            summedThreadCoreEquivalent=cpu/elapsed if elapsed else None)
    pairs = [dict(highIndex=a, lowIndex=b, high=result['rows'][a]['continuous'], low=result['rows'][b]['continuous'],
        lowMinusHighMeanMs=result['rows'][b]['continuous']['mean']-result['rows'][a]['continuous']['mean'])
        for a, b in ((0, 1), (3, 2))]
    result.update(version=VERSION, stageQuality=quality, arms=arms, pairs=pairs,
        boundaryStateStableExceptQuality=quality['boundaryStateStableExceptQuality'],
        qualitySensitivityEligible=result['passed'] and quality['boundaryStateStableExceptQuality'],
        pureFinalPresentationAttribution=False, visualAcceptance=False, gameplayAcceptance=False)
    result['limits'] = result['limits'][:2] + [
        'All 1200 original intervals, quality-switch costs and thread-query disturbances are retained; boundary intervals can contain the previous quality presentation.',
        'LOW can change BitmapData.draw and newly rasterized decals/tiles permanently; the final HIGH arm is not a pixel-state rollback.',
        'AI, projectiles, prewarm and order change naturally; ABBA and matching boundary state do not eliminate workload confounding.',
        'Only quality is checked every frame. Other window/camera properties are checked at boundaries and termination.',
        'Private desktop, no pixels compared, no production performance or gameplay acceptance; no downgrade may be deployed from this experiment.']
    return result


def main():
    assert __debug__
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--name', required=True)
    parser.add_argument('--registry-wait', type=int, default=600)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--compile-probe', action='store_true'); group.add_argument('--probe-build', type=Path)
    args = parser.parse_args(); assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
    folder = r.E/args.name; assert not folder.exists(), 'Preserve prior evidence'
    options = old.options(args.name); assert options[-2:] == ['--draw-control', 'atlas']; options[-1] = 'rcnative'
    record = dict(version=VERSION, options=options, diagnosticOnly=True, performanceEligible=False)
    with m.Registration(owner='ContinuousScene / stage quality thread CPU / 01a13816', purpose=args.name,
                        run_dir=m.RUNTIME, evidence=folder, resource='game', wait=args.registry_wait) as lease:
        try:
            assert not m.air_pids(), 'Other AIR remains untouched'
            memory = control.memory_gate()
            baseline, scripts, compiler, fixture = r.baseline(), runner_inputs(), support.compiler_inputs(), fixture_inputs()
            runtime = w.runtime_inputs(); assert len(baseline) == 526
            for key, expected in old.PINS.items(): assert baseline[key] == expected, key
            rv = r.read(old.RV_RECEIPT); assert rv['result'] == 'PASS' and rv['new'].upper() == old.RV_CURRENT
            record.update(baseline=baseline, runnerInputs=scripts, compilerInputs=compiler, fixtureInputs=fixture,
                runtimeInputs=runtime, memoryBefore=memory)
            path = compile_probe(lease, baseline, scripts, compiler, fixture) if args.compile_probe else args.probe_build.resolve()
            probe = verify_probe(path, baseline, scripts, compiler, fixture)
            m.prepare(); shutil.copy2(probe['probePath'], m.RUNTIME/base.PROBE_PATH)
            for key, expected in baseline.items():
                if key not in ('application.xml', 'mods/loader-manifest.txt'): assert r.sha(m.RUNTIME/key) == expected, key
            assert baseline == r.baseline() and scripts == runner_inputs() and runtime == w.runtime_inputs()
            prepared_bytes = (m.RUNTIME/'application.xml').read_bytes()
            execute, descriptor, adapter = owned_adapter((m.RUNTIME/'application.xml').read_text('utf-8-sig'), prepared_bytes)
            record.update(probeBuildPath=str(path), probeSHA256=probe['probeSHA256'], ownedAdapter=adapter,
                memoryBeforeAir=control.memory_gate())
            launch = m.parse_args(options); assert launch.draw_control == 'rcnative'
            run_error = None
            try: execute(launch, lease)
            except BaseException as error:
                run_error = error
                record.update(executionError=repr(error), executionTraceback=traceback.format_exc())
            finally:
                if folder.exists():
                    r.save(folder/'probe-build.json', probe); r.save(folder/'runner-inputs.json', record)
                    if (folder/'storage/result.json').exists():
                        raw = r.read(folder/'storage/result.json')
                        r.save(folder/'component-status.json', dict(rawOK=raw.get('ok'), rawError=raw.get('error'),
                            stageQuality=raw.get('stageQuality'), stageQualityCleanup=raw.get('stageQualityCleanup'),
                            executionError=repr(run_error) if run_error else None,
                            executionTraceback=record.get('executionTraceback')))
            # Stock finally has already cleaned its owned resources. Preserve
            # the original failure before descriptor/result success assertions.
            if run_error: raise run_error
            assert baseline == r.baseline() and scripts == runner_inputs() and fixture == fixture_inputs()
            assert compiler == support.compiler_inputs() and runtime == w.runtime_inputs()
            assert (m.RUNTIME/'application.xml').read_bytes() == prepared_bytes, 'Prepared descriptor changed'
            verify_probe(path, baseline, scripts, compiler, fixture)
            assert descriptor.get('cleanupChecked') and not descriptor.get('cleanupCheckError') and not descriptor.get('receiptWriteError'), descriptor
            assert r.sha(folder/'application-used.xml') == descriptor['actualSHA256']
            assert not Path(descriptor['descriptorPath']).exists(), 'Owned descriptor was not cleaned'
            raw, actual = w.read_retained_result(folder)
            for key, expected in baseline.items():
                if key not in ('application.xml', 'mods/loader-manifest.txt'): assert actual[key] == expected, key
            assert actual[base.PROBE_PATH] == probe['probeSHA256']
            policy = r.read(folder/'process-policy.json')
            assert policy['desktopPolicy'] == 'private' and not policy['performanceEligible']
            assert not policy.get('runFailure') and not policy.get('memoryAbort') and not policy.get('otherAirProcessIds')
            try: summary = summarize(raw, policy)
            except Exception as validation_error:
                summary = dict(version=VERSION, passed=False, complete=False, diagnosticOnly=True,
                    performanceEligible=False, performanceAcceptance=False, visualAcceptance=False, deployed=False,
                    rawOK=raw.get('ok'), rawError=raw.get('error'), validationError=repr(validation_error),
                    retainedSampleCount=len(raw.get('samples', [])), stageQuality=raw.get('stageQuality'))
            summary.update(name=args.name, probeSHA256=probe['probeSHA256'], resultSHA256=r.sha(folder/'storage/result.json'),
                inputsUnchanged=True, runtimeInputsUnchanged=True, checks=len(raw['assertions']),
                descriptorReview=r.read(folder/'descriptor-review.json'), ownedAdapter=adapter)
            r.save(folder/'summary.json', summary)
            assert summary['passed'], 'Quality/thread diagnostic incomplete or invalid; original evidence retained'
            lease.outcome = 'passed'; lease.note = '1200 quality observations and aligned owned thread CPU; sensitivity only, no deployment acceptance'
            print(json.dumps(dict(name=args.name, passed=summary['passed'], continuous=summary['continuous'],
                qualitySensitivityEligible=summary['qualitySensitivityEligible'], arms=summary['arms'])), flush=True)
        except BaseException as error:
            lease.outcome = 'failed'; lease.note = repr(error); folder.mkdir(parents=True, exist_ok=True)
            r.save(folder/'runner-failure.json', dict(record, error=repr(error),
                runnerTraceback=traceback.format_exc(), complete=False, deployed=False)); raise


shared.HERE, shared.VERSION = HERE, VERSION
shared.runner_inputs, shared.fixture_inputs = runner_inputs, fixture_inputs
base.OUT = HERE/'probe-builds'
base.runner_inputs, base.candidate_inputs = runner_inputs, fixture_inputs
if __name__ == '__main__': main()
