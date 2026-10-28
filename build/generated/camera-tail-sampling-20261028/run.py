"""Extend the verified dense runner with one isolated diagnostic addon."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
UPSTREAM = HERE.parent / 'camera-dense-reference-rc2-20261028'
spec = importlib.util.spec_from_file_location('tail_dense_runner', UPSTREAM / 'run.py')
dense = importlib.util.module_from_spec(spec); spec.loader.exec_module(dense)
reuse, m = dense.reuse, dense.m
BASE_VERIFY = dense.validation.verify
ADDON = 'mods/ContinuousSceneTailSampler/release/ContinuousSceneTailSamplerMod.swf'
SCHEDULE = [100000, 110000, 120000, 130000]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def inputs():
    build = reuse.read(HERE / 'build.json')
    assert build['complete'] and not build['deployed'] and not build['runtimeVerified']
    assert build['sourceInputs'] == {p: sha(p) for p in build['sourceInputs']}
    assert build['directCompilerInputs'] == {p: sha(p) for p in build['directCompilerInputs']}
    assert sha(HERE / 'ContinuousSceneTailSamplerMod.swf') == build['outputSHA256']
    upstream = reuse.prepared()
    return dict(version='camera-tail-runner-1', diagnosticOnly=True, performanceEligible=False,
        addonSHA256=build['outputSHA256'], buildSHA256=sha(HERE / 'build.json'),
        runnerSHA256=sha(__file__), upstreamPreparedSHA256=sha(UPSTREAM / 'prepared.json'),
        upstreamInputs=upstream['successorInputs'], schedule=SCHEDULE,
        boundary='This Stage tail listener to next Stage head listener; no GPU-time attribution')


def verify(name):
    dense.validation.evidence_name(name)
    folder = reuse.EVIDENCE / name
    assert not (HERE / 'runs' / name / 'wrapper-failure.json').exists()
    base = BASE_VERIFY(folder)
    record = reuse.read(folder / 'runner-inputs.json')
    extension = record['tailSamplerExtension']
    assert extension['inputs'] == inputs()
    assert extension['plan']['tailAtMs'] == SCHEDULE
    assert extension['plan']['applicationID'] == reuse.read(folder / 'process-policy.json')['appId']
    assert sha(folder / 'tail-sampler-plan.json') == extension['planSHA256']
    assert reuse.read(folder / 'tail-sampler-plan.json') == extension['plan']
    assert sha(folder / 'tail-selection.json') == extension['selectionSHA256']
    actual = reuse.read(folder / 'inputs.json')
    assert actual.get(ADDON.replace('/', '\\'), actual.get(ADDON)) == extension['inputs']['addonSHA256']
    loader = reuse.read(folder / 'loader-check.json')
    assert loader['loaded']['ContinuousSceneTailSamplerMod'] is True
    report = reuse.read(folder / 'storage/tail-sampler.json')
    assert report['complete'] and report['valid'] and not report['errors']
    assert report['diagnosticOnly'] and not report['performanceEligible'] and not report['performanceAcceptance']
    assert report['listenersRemoved'] and not report['active'] and not report['callbackInstalled']
    assert report['applicationID'] == extension['plan']['applicationID'] and report['plan'] == extension['plan']
    assert len(report['windows']) == 4
    raw = reuse.read(folder / 'storage/result.json')
    selected, stacks = [], {}
    for window in report['windows']:
        assert window['valid'] and not window['errors'] and not window['overflow']
        assert window['headSequence'] == window['tailHeadSequence'] + 1
        assert window['cleanup'] == dict(stopped=True, cleared=True, callbackCleared=True)
        entries = window['entries']
        assert entries['unknown'] == 0
        assert entries['total'] == entries['cpu'] + entries['newObject'] + entries['deleteObject'] == window['reportedEntries']
        assert entries['cpu'] == sum(x['samples'] for x in window['stacks'])
        assert window['cpuNonMonotonic'] == window['cpuInvalidTimes'] == 0
        matches = [i for i, row in enumerate(raw['samples'])
            if row['caseBeginAtMs'] <= window['startAfterMs'] <= window['endBeforeMs'] <= row['caseEndAtMs']]
        assert len(matches) <= 1
        if not matches: continue
        row = raw['samples'][matches[0]]
        boundaries = [row['caseBeginAtMs']] + row['sampleAtMs']
        intervals = [i for i in range(len(boundaries) - 1) if
            boundaries[i] <= window['startAfterMs'] <= window['endBeforeMs'] <= boundaries[i+1]]
        assert len(intervals) == 1, 'Tail must fit one retained continuous interval'
        frame = intervals[0]
        selected.append(dict(index=window['index'], sample=matches[0], frame=frame,
            intervalStartMs=boundaries[frame], intervalEndMs=boundaries[frame+1], cpu=entries['cpu'],
            intervalMs=window['intervalMs'], ownMs=window['ownMs']))
        for item in window['stacks']:
            key = tuple(item['names']); stacks[key] = stacks.get(key, 0) + item['samples']
    # A structurally valid but uninformative capture stays explicitly inconclusive.
    cpu = sum(x['cpu'] for x in selected)
    return dict(version='camera-tail-review-1', name=name, diagnosticOnly=True,
        performanceEligible=False, deployed=False, workloadVerified=base['complete'],
        windowsInsideCompletedWorkload=selected, sampledCpuOccurrences=cpu,
        attributionReady=sum(x['cpu'] > 0 for x in selected) >= 2 and cpu >= 20,
        stacks=[dict(names=list(k), samples=v) for k, v in sorted(stacks.items(), key=lambda x: -x[1])],
        rawSHA256=sha(folder / 'storage/tail-sampler.json'), sourceInputs=inputs(),
        limitation='Occurrences in this Stage interval only; observer overhead changes frame times. No GPU milliseconds or exclusive renderer attribution.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    parser.add_argument('--registry-wait', type=int, default=900)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    dense.validation.evidence_name(args.name)
    if args.verify:
        result = verify(args.name)
        reuse.save(HERE / 'runs' / args.name / 'independent-review.json', result)
        print(json.dumps(result)); return
    evidence = reuse.EVIDENCE / args.name
    local = HERE / 'runs' / args.name
    assert not evidence.exists() and not local.exists()
    snapshot = inputs()
    extension = dict(inputs=snapshot)
    prepare_original, seed_original, save_original = m.prepare, dense.silence.seed, reuse.save

    def prepare(*positional, **keywords):
        prepare_original(*positional, **keywords)
        target = m.RUNTIME / ADDON
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists(): assert sha(target) == snapshot['addonSHA256'], 'Retain a different owned addon'
        else: shutil.copy2(HERE / 'ContinuousSceneTailSamplerMod.swf', target)
        catalog = m.RUNTIME / 'mods/ModLoader/supported-mods.txt'
        assert 'ContinuousSceneTailSampler|' not in catalog.read_text('utf-8-sig')
        with catalog.open('a', encoding='utf-8') as stream:
            stream.write('\nContinuousSceneTailSampler|ContinuousSceneTailSamplerMod|1|0|0\n')
        rows = [line.split('|') for line in (m.RUNTIME / 'mods/loader-manifest.txt').read_text('utf-8-sig').splitlines()]
        selected = [row[1] for row in rows if len(row) == 5 and row[2] == '1']
        assert 'ContinuousSceneMotionMod' in selected and 'ContinuousSceneMod' in selected
        selection = HERE / ('selection-' + args.name + '.json')
        assert not selection.exists()
        subprocess.run([str(m.ROOT / 'mods/ModLoader/RemainsModLauncher.exe'), '--root', str(m.RUNTIME),
            '--only', ','.join(selected + ['ContinuousSceneTailSamplerMod']), '--no-ui', '--report', str(selection)],
            capture_output=True, check=True)
        extension['selectionSHA256'] = sha(selection)
        extension['selectionPath'] = str(selection)

    def seed(descriptor, runtime):
        result = seed_original(descriptor, runtime)
        plan = dict(version='camera-tail-sampling-plan-1', applicationID=result['applicationID'], tailAtMs=SCHEDULE)
        path = m.RUNTIME / 'tail-sampler-plan.json'
        # The registered runtime is exclusively owned now; a stale plan has no valid new UUID.
        save_original(path, plan)
        extension.update(plan=plan, planSHA256=sha(path))
        return result

    def save(path, value):
        if Path(path).name == 'runner-inputs.json':
            value = dict(value, tailSamplerExtension=extension)
            if Path(path).parent == evidence and extension.get('plan') and extension.get('selectionPath'):
                shutil.copy2(m.RUNTIME / 'tail-sampler-plan.json', evidence / 'tail-sampler-plan.json')
                shutil.copy2(extension['selectionPath'], evidence / 'tail-selection.json')
        return save_original(path, value)

    def validate_inside_lease(folder, *positional, **keywords):
        # Tail errors must fail the same registration before it can say passed.
        base = BASE_VERIFY(folder, *positional, **keywords)
        assert inputs() == snapshot
        tail = verify(Path(folder).name)
        local.mkdir(parents=True, exist_ok=True)
        save_original(local / 'tail-review.json', tail)
        return dict(base, tailSamplerStructurallyVerified=True,
            tailSamplerAttributionReady=tail['attributionReady'], performanceEligible=False)

    old_argv, original_verify = sys.argv, dense.validation.verify
    m.prepare, dense.silence.seed, reuse.save = prepare, seed, save
    dense.validation.verify = validate_inside_lease
    sys.argv = [str(UPSTREAM / 'run.py'), '--name', args.name, '--mode', 'scene', '--registry-wait', str(args.registry_wait)]
    try:
        dense.main()
        assert inputs() == snapshot
        result = verify(args.name)
        local.mkdir(parents=True, exist_ok=True)
        save_original(local / 'tail-review.json', result)
        print(json.dumps(result))
    except BaseException as error:
        local.mkdir(parents=True, exist_ok=True)
        save_original(local / 'wrapper-failure.json', dict(error=repr(error), extension=extension, complete=False))
        raise
    finally:
        m.prepare, dense.silence.seed, reuse.save = prepare_original, seed_original, save_original
        dense.validation.verify = original_verify
        sys.argv = old_argv


if __name__ == '__main__':
    main()
