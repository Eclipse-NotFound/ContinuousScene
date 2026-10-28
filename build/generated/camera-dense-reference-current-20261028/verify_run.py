"""Independent retained-result verification; no AIR and no raw-result edits."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('dense_reference_reuse', HERE / 'verify_reuse.py')
reuse = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reuse)
silence = reuse.load('dense_reference_silence', reuse.SILENT / 'silence.py')


def evidence_name(name):
    assert name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in name)
    return name


def summarize(raw, name, mode):
    assert raw['ok'] is True and not raw.get('error') and all(x['ok'] for x in raw['assertions'])
    result = reuse.dense.summarize(raw, SimpleNamespace(name=name, mode=mode))
    assert result['qualification']['passed']
    fire, cache = [], []
    for index, row in enumerate(raw['samples']):
        assert row['empty'] == row['misses'] == row['forced'] == 0
        previous_player, previous_enemy = row['playerShotStart'], row['enemyShotStart']
        windows = []
        for frame in range(29, 300, 30):
            found = [x for x in row['combatWindows'] if x['frame'] == frame]
            assert len(found) == 1
            end = found[0]
            player, enemy = end['playerShots'], end['encounter']['actualShotFrames']
            assert player >= previous_player and enemy >= previous_enemy
            windows.append(dict(first=frame-29, last=frame, playerShots=player-previous_player,
                                enemyShots=enemy-previous_enemy))
            previous_player, previous_enemy = player, enemy
        assert sum(x['playerShots'] for x in windows) == row['playerShotFrames']
        assert sum(x['enemyShots'] for x in windows) == row['enemyShotFrames']
        fire.append(dict(index=index, windows=windows))
        cache.append(dict(index=index, warmed=sum(row['warm']), asyncSlices=row['slices'],
                          residentStart=row['residentStart'], residentEnd=row['residentEnd'],
                          misses=row['misses'], forced=row['forced'], empty=row['empty']))
    bands = {key: reuse.base.metrics([v for row in raw['samples'] for v in row[key]])
             for key in ('nativeBand', 'totalScript', 'preBand', 'wallBand', 'sceneBand',
                         'tailBand', 'afterProbeBand', 'renderBand', 'exitBand')}
    stable = all(x['warmed'] == x['asyncSlices'] == 0 and x['residentStart'] == x['residentEnd'] for x in cache)
    result.update(version=reuse.VERSION, complete=True, probeSHA256=reuse.PROBE_SHA,
                  complete30FrameFireWindows=fire, cacheWindows=cache, timedCacheStable=stable,
                  bands=bands, historicalProbeReused=True)
    result['limitations'] += [
        'This reference retains ordinary versus continuous native camera behavior; no held-camera condition.',
        'FA2B camera checks and its forced 177-tile prewarm are absent from the original 7F1F0B probe.',
        'Asynchronous tile warming remains in all intervals and is reported; nonzero warming prevents a steady-cache causal claim.',
        'totalScript is a previous-frame Stage ENTER_FRAME band (1199 entries), not whole-process or GPU time; do not subtract arrays index-for-index.',
        'renderBand/exitBand time event listeners, not full deferred rendering. No renderer or GPU attribution.',
        'Use complete30FrameFireWindows for exact 30-frame counts; inherited combatWindows omits the first interval.',
        'Current CS 0.9.1 supplies nativeAPI; this ordinary six-LMG fixture does not validate alicorn alerts.',
    ]
    return result


def verify(folder, allow_pair=True):
    folder = Path(folder).resolve()
    assert folder.parent == reuse.EVIDENCE.resolve()
    evidence_name(folder.name)
    assert not (folder / 'runner-failure.json').exists()
    assert not (HERE / 'runs' / folder.name / 'runner-failure.json').exists()
    record = reuse.read(folder / 'runner-inputs.json')
    assert record['version'] == reuse.VERSION and record['mode'] in ('normal', 'scene')
    assert record['prepared'] == reuse.prepared() and record['preparedSHA256'] == reuse.sha(HERE / 'prepared.json')
    assert record['probeSHA256'] == reuse.PROBE_SHA and record['rebuilt'] is False
    assert not record.get('executionError') and not record.get('error') and record.get('complete') is not False
    raw, actual = reuse.r.result(folder.name)
    for path, digest in record['prepared']['production'].items():
        if path not in ('application.xml', 'mods/loader-manifest.txt'):
            assert actual[path] == digest, path
    assert actual[reuse.base.PROBE_PATH] == reuse.PROBE_SHA
    policy = reuse.read(folder / 'process-policy.json')
    assert policy['desktopPolicy'] == 'private' and not policy['performanceEligible']
    assert policy['appId'].startswith('pfe-modsettings-continuous-motion-')
    assert not policy.get('memoryAbort') and not policy.get('runFailure') and not policy.get('otherAirProcessIds')
    seeded = record['nativeSilence']
    assert seeded['applicationID'] == policy['appId'] and seeded['writeOnce'] and seeded['decodedAfterWrite']
    assert seeded['nativeSndOnly'] and seeded['allAudioMuted'] is False
    assert seeded['sha256'] == '12CC4E62A459EAFDA8463F800F8E1E8388CC392AC6A5BDD882D14C572435B257'
    native_audio = silence.verify_retained(folder / 'storage/#SharedObjects/pfe.swf/config.sol')
    assert native_audio == seeded['snd']
    startup = record['startupPolicies']
    assert len(startup) == 1 and startup[0]['pid'] == policy['pid']
    applied = startup[0]['policy']
    assert applied['requested'] == 'test' and not applied['errors'] and not applied['after']['errors']
    assert applied['after']['cpuPriorityClass'] == 32 and applied['after']['memoryPriority'] == 5
    assert applied['after']['powerThrottling']['highQoS'] is True
    loader = reuse.read(folder / 'loader-check.json')
    assert len(loader['sessions']) == 1 and all(loader['loaded'].values())
    assert loader['loaded']['ContinuousSceneMod'] is True and loader['loaded']['ContinuousSceneMotionMod'] is True
    for key in ('memoryBefore', 'memoryBeforeAir', 'memoryImmediatelyBeforeCreate'):
        assert record[key]['availableCommit'] >= 4*1024**3 and record[key]['availablePhysical'] >= 2*1024**3
    assert policy['minimumAvailableCommit'] >= 512*1024**2
    summary = summarize(raw, folder.name, record['mode'])
    summary.update(resultSHA256=reuse.sha(folder / 'storage/result.json'),
                   actualInputsSHA256=reuse.sha(folder / 'inputs.json'),
                   processPolicySHA256=reuse.sha(folder / 'process-policy.json'),
                   loaderCheckSHA256=reuse.sha(folder / 'loader-check.json'),
                   historicalReceiptSHA256=reuse.OLD_RECEIPT_SHA, currentInputsVerified=True,
                   startupPolicyVerified=True, nativeAudioSettings=native_audio,
                   audioLimit='Native Snd configuration only; no runtime SoundMixer readback.')
    if record['pairedEvidence']:
        assert allow_pair and record['mode'] == 'scene'
        reference = verify(reuse.EVIDENCE / evidence_name(record['pairedEvidence']), allow_pair=False)
        assert reference['mode'] == 'normal' and reference['resultSHA256'] == record['pairedResultSHA256']
        assert all(summary[k] == reference[k] for k in
                   ('normalizedRoute', 'nativeRouteHash', 'selectedCombatCorridorTiles', 'viewport', 'probeSHA256', 'fixture'))
        summary['pairedComparison'] = dict(evidence=record['pairedEvidence'], matchedTerrainAndProbe=True,
            normal=reference['continuous'], scene=summary['continuous'],
            bothTimedCachesStable=reference['timedCacheStable'] and summary['timedCacheStable'],
            exactCausalAcceptance=False, limitation='Experience reference; natural population and camera bounds differ.')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('name')
    args = parser.parse_args()
    summary = verify(reuse.EVIDENCE / evidence_name(args.name))
    local = HERE / 'runs' / args.name
    local.mkdir(parents=True, exist_ok=True)
    reuse.save(local / 'independent-review.json', summary)
    print(json.dumps(dict(verified=True, mode=summary['mode'], continuous=summary['continuous'],
                          paired=summary.get('pairedComparison'))))
