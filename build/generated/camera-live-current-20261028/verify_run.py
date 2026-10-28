"""Validate retained current-dependency camera combat; no game launch or raw edits."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('camera_live_reuse_validation', HERE / 'verify_reuse.py')
reuse = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reuse)
silence = reuse.load('camera_live_retained_silence', HERE / 'silence.py')


def summarize(raw, name):
    assert raw['ok'] is True and not raw.get('error'), 'Original probe result failed'
    assert all(item['ok'] for item in raw['assertions']), 'Original probe assertion failed'
    summary = reuse.dense.summarize(raw, SimpleNamespace(mode='scene', name=name))
    camera = reuse.camera.camera_summary(raw)
    assert summary['qualification']['passed'] and camera['passed']
    arms = {}
    for held in (False, True):
        indices = (1, 2) if held else (0, 3)
        rows = [raw['samples'][i] for i in indices]
        frames = [f for i in indices for f in raw['cameraHold']['windows'][i]['frames']]
        enemy_moving = sum(any(abs(u['dx']) + abs(u['dy']) > .1 for u in f['actors']) for f in frames)
        native_sprint = sum(summary['samples'][i]['workload']['aboveWalkSpeedFrames'] for i in indices)
        fixture_bullets = [v for row in rows for v in row['denseFrames']['fixtureBullets']]
        player_bullets = [v for row in rows for v in row['denseFrames']['playerBullets']]
        assert enemy_moving > 0 and native_sprint > 0 and max(fixture_bullets) > 0 and max(player_bullets) > 0
        arms['held' if held else 'follow'] = dict(
            intervals=reuse.base.metrics([v for row in rows for v in row['continuousFramesMs']]),
            playerShots=sum(row['playerShotFrames'] for row in rows), enemyShots=sum(row['enemyShotFrames'] for row in rows),
            enemyMovingFrames=enemy_moving, actualNativeSprintFrames=native_sprint,
            liveFixtureBullets=reuse.base.metrics(fixture_bullets), livePlayerBullets=reuse.base.metrics(player_bullets),
            stagePriorityBand=reuse.base.metrics([v for row in rows for v in row['nativeBand']]))
    full_windows = []
    for index, row in enumerate(raw['samples']):
        previous_player, previous_enemy = row['playerShotStart'], row['enemyShotStart']
        windows = []
        for frame in range(29, 300, 30):
            ends = [x for x in row['combatWindows'] if x['frame'] == frame]
            assert len(ends) == 1
            end = ends[0]
            player, enemy = end['playerShots'], end['encounter']['actualShotFrames']
            windows.append(dict(first=frame-29, last=frame, playerShots=player-previous_player, enemyShots=enemy-previous_enemy))
            previous_player, previous_enemy = player, enemy
        assert sum(x['playerShots'] for x in windows) == row['playerShotFrames']
        assert sum(x['enemyShots'] for x in windows) == row['enemyShotFrames']
        full_windows.append(dict(index=index, windows=windows))
    summary.update(version=reuse.VERSION, cameraComparison=camera, arms=arms,
                   complete30FrameFireWindows=full_windows, historicalProbeReused=True,
                   probeSHA256=reuse.PROBE_SHA, complete=True, deployed=False)
    summary['limitations'] += [
        'Legacy combatWindows in inherited summary omit the first interval; use complete30FrameFireWindows for exact 30-frame firing counts.',
        'stagePriorityBand includes other ENTER_FRAME listeners; it is not exclusive World.step, GPU or renderer time.',
        'Original six-LMG fixture differs from the newer six-SMG10 fixture. No cross-fixture absolute performance claim.',
        'Follow versus held preserves simulation, but visibility, targeting and natural activity can differ; report both arms fire and movement.',
        'Cache prewarm is deliberate and separately reported; not natural exploration or first-load timing.',
        'RV, LightAndDarkness and WallBlend are disabled in this isolated run; installed current binaries are retained.',
        'Current CS 0.9.1 and its nativeAPI remain loaded. Ordinary six-LMG actors do not validate alicorn-alert behavior.',
    ]
    return summary


def verify(folder):
    folder = Path(folder).resolve()
    assert folder.parent == reuse.EVIDENCE.resolve()
    assert not (folder / 'runner-failure.json').exists(), 'Retained run failed'
    assert not (HERE / 'runs' / folder.name / 'runner-failure.json').exists(), 'Local run receipt failed'
    record = reuse.read(folder / 'runner-inputs.json')
    assert record['version'] == reuse.VERSION and record['prepared'] == reuse.prepared()
    assert record['preparedSHA256'] == reuse.sha(HERE / 'prepared.json')
    assert record['probeSHA256'] == reuse.PROBE_SHA and record['rebuilt'] is False
    raw, actual = reuse.r.result(folder.name)
    for path, digest in record['prepared']['production'].items():
        if path not in ('application.xml', 'mods/loader-manifest.txt'):
            assert actual[path] == digest, path
    assert actual[reuse.base.PROBE_PATH] == reuse.PROBE_SHA
    policy = reuse.read(folder / 'process-policy.json')
    assert policy['desktopPolicy'] == 'private' and not policy['performanceEligible']
    assert policy['appId'].startswith('pfe-modsettings-continuous-motion-') and policy['appId'] != 'pfe'
    seeded = record['nativeSilence']
    assert seeded['applicationID'] == policy['appId'] and seeded['writeOnce'] and seeded['decodedAfterWrite']
    assert seeded['nativeSndOnly'] and seeded['allAudioMuted'] is False
    assert seeded['sha256'] == '12CC4E62A459EAFDA8463F800F8E1E8388CC392AC6A5BDD882D14C572435B257'
    native_audio = silence.verify_retained(folder / 'storage/#SharedObjects/pfe.swf/config.sol')
    assert native_audio == seeded['snd']
    assert not policy.get('memoryAbort') and not policy.get('runFailure') and not policy.get('otherAirProcessIds')
    assert not record.get('executionError') and not record.get('error') and record.get('complete') is not False
    startup = record['startupPolicies']
    assert len(startup) == 1 and startup[0]['pid'] == policy['pid'] and startup[0]['policy'] is not None
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
    return dict(summarize(raw, folder.name), resultSHA256=reuse.sha(folder / 'storage/result.json'),
                actualInputsSHA256=reuse.sha(folder / 'inputs.json'), processPolicySHA256=reuse.sha(folder / 'process-policy.json'),
                loaderCheckSHA256=reuse.sha(folder / 'loader-check.json'), startupPolicyVerified=True,
                historicalReceiptSHA256=reuse.OLD_RECEIPT_SHA, currentInputsVerified=True,
                nativeAudioSettings=native_audio, audioLimit='Native Snd settings only; no runtime SoundMixer readback.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('name')
    args = parser.parse_args()
    assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
    report = verify(reuse.EVIDENCE / args.name)
    target = HERE / 'runs' / args.name
    target.mkdir(parents=True, exist_ok=True)
    reuse.save(target / 'independent-review.json', report)
    print(json.dumps(dict(verified=True, name=args.name, arms=report['arms'])))
