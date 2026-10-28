"""Independently verify retained range ABBA and the existing rc2 combat guards."""
from pathlib import Path
import argparse
import importlib.util
import json
import math
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('activity_range_review_build', HERE / 'build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)
CS_PATH = 'mods/ContinuousScene/release/ContinuousSceneMod.swf'


def range_summary(raw, metrics):
    assert 'cameraHold' not in raw and 'cameraPrewarm' not in raw
    assert raw['activityRange']['version'] == 'activity-camera-range-1'
    assert raw['activityRange']['order'] == [False, True, True, False]
    assert len(raw['samples']) == 4
    previous_tick, samples, windows = None, 0, []
    for index, row in enumerate(raw['samples']):
        enabled = index in (1, 2)
        switch = row['activityRangeSwitch']
        assert switch['index'] == index and switch['enabled'] is enabled
        assert switch['after']['enabled'] is enabled and switch['after']['requestedEnabled'] is enabled
        assert switch['before']['failed'] is False and switch['after']['failed'] is False
        assert switch['after']['configurationEpoch'] == switch['before']['configurationEpoch'] + (0 if index == 2 else 1)
        assert len(row['activityRange']) == len(row['continuousFramesMs']) == 300
        applied, old_only = 0, 0
        for item in row['activityRange']:
            samples += 1
            assert item['sample'] == samples and item['expectedEnabled'] is enabled
            check = item['verification']
            assert check['version'] == 'activity-camera-range-1' and check['ok'] is True and check['failed'] is False
            assert check['enabled'] is enabled and check['pending'] is False and check['checkComplete'] is True
            assert check['epoch'] == switch['after']['configurationEpoch']
            tick = check['tick']
            assert type(tick) in (int, float) and math.isfinite(tick) and tick == int(tick)
            assert previous_tick is None or tick > previous_tick
            previous_tick = tick
            assert check['visibleSleeping'] == 0 and check['errors'] == []
            assert check['visibleSleepingExamples'] == [] and check['unitsExamined'] > 0
            for rectangle in (check['planned'], check['actual']):
                assert all(type(rectangle[key]) in (int, float) and math.isfinite(rectangle[key])
                           for key in ('left', 'top', 'right', 'bottom'))
                assert rectangle['left'] <= rectangle['right'] and rectangle['top'] <= rectangle['bottom']
            if check['applied']:
                assert enabled and check['viewportContained'] is True
                outer, inner = check['planned'], check['actual']
                assert inner['left'] >= outer['left'] and inner['top'] >= outer['top']
                assert inner['right'] <= outer['right'] and inner['bottom'] <= outer['bottom']
                assert type(check['oldNearOnlySleeping']) is int and 0 <= check['oldNearOnlySleeping'] <= check['unitsExamined']
                applied += 1
                old_only += check['oldNearOnlySleeping']
            else:
                assert check['applied'] is False
        if enabled: assert applied > 0 and old_only > 0, 'Each B window must actually narrow sleeping population'
        else: assert applied == old_only == 0
        windows.append(dict(index=index, enabled=enabled, appliedFrames=applied, oldNearOnlySleepingSum=old_only))
    cleanup = raw['activityRangeCleanup']
    assert cleanup['started'] is True and cleanup['cleared'] is True and cleanup['errors'] == []
    assert cleanup['samples'] == samples == 1200
    assert cleanup['switches'] == [row['activityRangeSwitch'] for row in raw['samples']]
    assert cleanup['lastVerify'] == raw['samples'][-1]['activityRange'][-1]['verification']
    assert cleanup['after']['enabled'] is False and cleanup['after']['requestedEnabled'] is False
    assert cleanup['before']['failed'] is False and cleanup['after']['failed'] is False
    arms = {label: dict(intervals=metrics([v for i in indices for v in raw['samples'][i]['continuousFramesMs']]),
                        appliedFrames=sum(windows[i]['appliedFrames'] for i in indices),
                        oldNearOnlySleepingSum=sum(windows[i]['oldNearOnlySleepingSum'] for i in indices))
            for label, indices in (('original', (0, 3)), ('narrow', (1, 2)))}
    return windows, arms


def verify(folder):
    runtime = build.reference()
    reuse = runtime.reuse
    folder = Path(folder).resolve()
    assert folder.parent == reuse.EVIDENCE.resolve()
    build.name_ok(folder.name)
    assert not (folder / 'runner-failure.json').exists()
    record = build.read(folder / 'runner-inputs.json')
    assert record['version'] == build.VERSION and record['rebuilt'] is True and record['reusedOriginalCompilation'] is False
    assert not record.get('error') and record.get('complete') is not False
    assert record['referencePrepared'] == str(build.REFERENCE / 'prepared.json')
    assert record['referencePreparedSHA256'] == build.REFERENCE_PINS['prepared.json']
    assert record['scriptInputs'] == build.script_inputs()
    candidate = build.verify(record['buildReceipt'])
    assert build.sha(record['buildReceipt']) == record['buildReceiptSHA256']
    snapshot = reuse.prepared()
    expected = dict(snapshot['production'])
    expected[CS_PATH] = candidate['outputs']['carrier']['sha256']
    expected[reuse.base.PROBE_PATH] = candidate['outputs']['probe']['sha256']
    assert record['carrierSHA256'] == expected[CS_PATH] and record['probeSHA256'] == expected[reuse.base.PROBE_PATH]
    assert record['options'] == runtime.options(folder.name, 'scene')
    raw, actual = reuse.r.result(folder.name)
    for path, digest in expected.items():
        if path not in ('application.xml', 'mods/loader-manifest.txt'): assert actual[path] == digest, path
    policy, loader = build.read(folder / 'process-policy.json'), build.read(folder / 'loader-check.json')
    assert policy['desktopPolicy'] == 'private' and policy['performanceEligible'] is False
    assert not any(policy.get(key) for key in ('memoryAbort', 'runFailure', 'otherAirProcessIds'))
    assert policy['minimumAvailableCommit'] >= 512*1024**2
    for key in ('memoryBefore', 'memoryBeforeAir', 'memoryImmediatelyBeforeCreate'):
        assert record[key]['availableCommit'] >= 4*1024**3 and record[key]['availablePhysical'] >= 2*1024**3
    seeded = record['nativeSilence']
    assert seeded['applicationID'] == policy['appId'] and seeded['writeOnce'] and seeded['decodedAfterWrite']
    assert seeded['nativeSndOnly'] is True and seeded['allAudioMuted'] is False
    assert seeded['sha256'] == '12CC4E62A459EAFDA8463F800F8E1E8388CC392AC6A5BDD882D14C572435B257'
    assert runtime.silence.verify_retained(folder / 'storage/#SharedObjects/pfe.swf/config.sol') == seeded['snd']
    startup = record['startupPolicies']
    assert len(startup) == 1 and startup[0]['pid'] == policy['pid']
    applied = startup[0]['policy']
    assert applied['requested'] == 'test' and not applied['errors'] and not applied['after']['errors']
    assert applied['after']['cpuPriorityClass'] == 32 and applied['after']['memoryPriority'] == 5
    assert applied['after']['powerThrottling']['highQoS'] is True
    assert len(loader['sessions']) == 1 and all(loader['loaded'].values())
    assert loader['loaded']['ContinuousSceneMod'] and loader['loaded']['ContinuousSceneMotionMod']
    # Reuse interval conservation, native sprint, all 40 fire windows and cache guards.
    result = runtime.validation.summarize(raw, folder.name, 'scene')
    windows, arms = range_summary(raw, reuse.base.metrics)
    result.update(version=build.VERSION, probeSHA256=record['probeSHA256'], historicalProbeReused=False,
        sourceSeedProbeSHA256='39A1497BE832282CAC25E2A508A954432F9F31B15A2FBE5A650AB8C4D9C97E9E',
        rangeWindows=windows, rangeArms=arms, rangeRestored=True, currentInputsVerified=True,
        resultSHA256=build.sha(folder / 'storage/result.json'), buildReceiptSHA256=record['buildReceiptSHA256'],
        nativeAudioSettings=seeded['snd'], diagnosticOnly=True, performanceAccepted=False)
    result['limitations'] = [s for s in result['limitations'] if 'original 7F1F0B probe' not in s]
    result['limitations'] += ['New compilation of the 39A source plus range hooks; not reuse of the old probe binary.',
        'Every post-check, planning/scan/switch cost and boundary interval is retained; late-write failures invalidate the run.',
        'A restoration does not undo evolved combat state; narrowing counts and ABBA differences are not deployment acceptance.']
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('name')
    args = parser.parse_args()
    runtime = build.reference()
    summary = verify(runtime.reuse.EVIDENCE / build.name_ok(args.name))
    print(json.dumps(dict(verified=True, resultSHA256=summary['resultSHA256'],
                          buildReceiptSHA256=summary['buildReceiptSHA256'], arms=summary['rangeArms'])))
