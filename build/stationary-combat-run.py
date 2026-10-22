"""Real-fire ABBA for the already audited stopped-projectile candidate.

Only compiles the current diagnostic probe, into a separate output directory.
Never rebuilds the candidate, patches the host, deploys, or touches user storage.
The first 60 frames of EACH 300-frame segment are excluded from timing because
the scheduling grace lasts 45 ticks. Natural reload gaps remain in the evidence.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import statistics
import sys

sys.dont_write_bytecode = True
B = Path(__file__).resolve().parent
MOD = B.parent
OUT = B / 'generated/stationary-combat-20261022'
OLD = B / 'generated/stationary-threat-20261021'
HOST_SHA = 'BEFCF0509E11FAC9FEF7AFB834708B8B93752A14AE3D5CD72B42AA6D42F9B82A'
BASE_SHA = '7F1F2961C6E299D949423591F3C65C610C2EAEFA7FC72E8A583A402770D6B51F'
CANDIDATE_SHA = '738F634A2B7E12EC625CD0E4C13BCE222934B07AA36F356556C9B8CC79310546'
AUDIT_SHA = 'C2FEF9121D065BE4618C3F70491DB7784320975C78511820FE58AF032C0F04F7'
BUILD_SHA = '2DECD3955DD17EEE75AE2A60E500F2CDD59A321F457CADD768A2DD9D0BD5DA55'
METHODS = {'NativeSceneActivity::1:1:stats', 'NativeSceneActivity::1:1:update'}
DROP = 60


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


r = load('stationary_combat_helpers', B / 'enemy-release.py')
m = r.motion


def source_hashes():
    return {p.relative_to(MOD / 'src').as_posix(): r.sha(p)
            for p in sorted((MOD / 'src').rglob('*.as'))}


def reviewed_artifacts():
    """Bind the existing two-method audit to its exact old inputs and exports."""
    assert r.sha(OLD / 'audit.json') == AUDIT_SHA, 'Reviewed stationary audit changed'
    assert r.sha(OLD / 'build.json') == BUILD_SHA, 'Reviewed stationary build changed'
    audit = r.read(OLD / 'audit.json')
    build = r.read(OLD / 'build.json')
    assert audit['passed'] and build['deployed'] is False
    assert set(audit['allowedChangedMethods']) == set(audit['actualChangedBodies']) == METHODS
    assert not audit['addedFields'] and not audit['addedMethods']
    assert audit['originalConstantPoolPreserved'] and audit['nonABCSWFEnvelopePreserved']
    assert audit['totalBaseMethods'] == audit['totalCandidateMethods'] == 57
    assert audit['unchangedNamedMethods'] == 47 and audit['unchangedClassLayouts'] == 6
    assert audit['unchangedScriptInitializers'] == 6 and audit['equivalentAnonymousMethods'] == 2
    assert build['host'] == HOST_SHA
    assert r.sha(B / 'large-map/ContinuousSceneMod.swf') == build['base'] == audit['baseSHA256'] == BASE_SHA
    assert r.sha(OLD / 'ContinuousSceneMod.swf') == build['candidate'] == audit['candidateSHA256'] == CANDIDATE_SHA
    assert r.sha(OLD / 'baseline.xml') == audit['baseXMLSHA256']
    assert r.sha(OLD / 'candidate.xml') == audit['candidateXMLSHA256']
    assert r.sha(OLD / 'source/NativeSceneActivity.as') == build['source']
    assert r.sha(B / 'native-crop-audit.py') == audit['semanticComparatorSHA256']
    paths = [OLD / 'ContinuousSceneMod.swf', OLD / 'audit.json', OLD / 'build.json',
             OLD / 'baseline.xml', OLD / 'candidate.xml', OLD / 'source/NativeSceneActivity.as',
             B / 'large-map/ContinuousSceneMod.swf', B / 'stationary-threat-audit.py',
             B / 'native-crop-audit.py', B / 'enemy-release.py', B / 'enemy-speed.py',
             B / 'motion-test.py', Path(__file__)]
    return {p.relative_to(B).as_posix(): r.sha(p) for p in paths}


def summarize(result):
    assert result['driver']['stableMotion']
    assert result['driver']['perFrameMethod'] == 'Unit.setPos (position/bounds/target only)'
    assert result['playerFire']['enabled'] and result['playerFire']['shotFrames'] > 0
    assert result['combatRoute']['path'] == 200
    assert result['path']['speed'] == 4 and result['path']['endX'] - result['path']['startX'] == 200
    warm = result['playerFireWarmup']
    assert warm['frames'] >= 100 and warm['quietWarmFrames'] >= 100 and warm['shotFrames'] >= 5
    assert len(result['samples']) == 4
    output = []
    for index, row in enumerate(result['samples']):
        enabled = index in (1, 2)
        assert len(row['frames']) == len(row['nativeBand']) == len(row['warm']) == 300
        assert len(row['totalScript']) in (299, 300)
        assert row['empty'] == 0 and row['misses'] == 0
        assert row['playerShotFrames'] > 0 and row['enemyShotFrames'] > 0
        assert row['encounter']['alive'] == row['encounter']['armed'] == 6
        assert len(row['combatWindows']) == 20 and len(row['activity']) == 10
        windows = []
        for wi in range(10):
            pair = sorted((x for x in row['combatWindows'] if x['frame'] // 30 == wi), key=lambda x: x['frame'])
            assert len(pair) == 2 and [x['frame'] % 30 for x in pair] == [0, 29]
            assert all(x['encounter']['alive'] == x['encounter']['armed'] == 6 for x in pair)
            player = pair[1]['playerShots'] - pair[0]['playerShots']
            enemy = pair[1]['encounter']['actualShotFrames'] - pair[0]['encounter']['actualShotFrames']
            assert player > 0, ('No actual player fire', index, wi)
            # Zero-shot enemy windows from native reload/AI are recorded, not
            # rejected or compensated by changing enemies or weapon cadence.
            windows.append(dict(window=wi, retained=wi >= 2, playerShots=player,
                                enemyShots=enemy, population=pair))
        before = windows[1]['population'][1]  # frame 59, immediately before retained range
        after = windows[9]['population'][1]   # frame 299
        player = after['playerShots'] - before['playerShots']
        enemy = after['encounter']['actualShotFrames'] - before['encounter']['actualShotFrames']
        assert player > 0 and enemy > 0, ('No real two-sided fire after grace exclusion', index)
        activity = row['activity'][2:]  # samples at ages 60, 90, ..., 270
        assert all(x['version'] == 'stationary-threats-1' and x['stationaryThreats'] is enabled for x in activity)
        frames = row['frames'][DROP:]
        # totalScript is recorded one tick late. A 299-entry first segment starts
        # at age 0; later 300-entry arrays start with the preceding segment's tail.
        # Both slices below cover ages 60..298, not an off-by-one 59..298 range.
        script = row['totalScript'][DROP + (len(row['totalScript']) == 300):]
        assert len(frames) == 240 and len(script) == 239
        output.append(dict(index=index, name=row['name'], stationary=enabled,
            rawFrames=300, excludedFrames=DROP, retainedFrameRange=[60, 299], frames=len(frames),
            median=statistics.median(frames), mean=statistics.mean(frames),
            p95=sorted(frames)[int(len(frames) * .95)], maximum=max(frames), over100=sum(x > 100 for x in frames),
            native=statistics.mean(row['nativeBand'][DROP:]), script=statistics.mean(script),
            scriptFrames=len(script), scriptFrameRange=[60, 298],
            playerShots=row['playerShotFrames'], enemyShots=row['enemyShotFrames'],
            retainedPlayerShots=player, retainedEnemyShots=enemy,
            warmed=sum(row['warm'][DROP:]), activity=activity,
            awakeMin=min(x['awake'] for x in activity), awakeMax=max(x['awake'] for x in activity),
            awakeMean=statistics.mean(x['awake'] for x in activity), combatWindows=windows))
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', required=True)
    parser.add_argument('--land', default='random_mane')
    parser.add_argument('--effects', choices=['off', 'full'], default='off')
    parser.add_argument('--compile-probe', action='store_true')
    parser.add_argument('--registry-wait', type=int, default=600)
    args = parser.parse_args()
    assert Path(args.name).name == args.name and args.name not in ('.', '..'), 'Use a single evidence directory name'
    assert not (r.E / args.name).exists(), 'Never overwrite prior evidence'
    OUT.mkdir(parents=True, exist_ok=True)
    with m.Registration(owner='ContinuousScene / real-fire stationary ABBA / 01a13816',
            purpose=args.name, run_dir=m.RUNTIME, evidence=r.E / args.name, wait=args.registry_wait) as lease:
        assert not m.air_pids(), 'Other AIR present; untouched'
        baseline = r.baseline()
        assert baseline['pfe.swf'] == HOST_SHA
        assert baseline['mods/ContinuousScene/release/ContinuousSceneMod.swf'] == BASE_SHA
        frozen = reviewed_artifacts()
        probe_source = MOD / 'src/ContinuousSceneMotionProbe.as'
        assert 'initialActivityAPI.stationaryThreatsEnabled=false;' in probe_source.read_text('utf-8-sig'), 'Baseline stationary mode must be set before warmup'
        if args.compile_probe:
            before = source_hashes()
            r.enemy.compile_as(MOD / 'src', 'ContinuousSceneProbeDoc.as', OUT / 'ContinuousSceneProbe.swf')
            assert before == source_hashes(), 'Probe source changed during compilation'
            assert frozen == reviewed_artifacts(), 'Audited artifact/helper changed during compilation'
            r.save(OUT / 'probe-build.json', dict(sourceSHA256=before,
                probeSHA256=r.sha(OUT / 'ContinuousSceneProbe.swf'), artifactsSHA256=frozen))
        probe = r.read(OUT / 'probe-build.json')
        assert probe['sourceSHA256'] == source_hashes(), 'Probe source changed; compile again'
        assert probe['artifactsSHA256'] == frozen, 'Frozen candidate/audit/helper changed; review before reuse'
        assert probe['probeSHA256'] == r.sha(OUT / 'ContinuousSceneProbe.swf')
        m.prepare()
        shutil.copy2(OUT / 'ContinuousSceneProbe.swf', m.RUNTIME / 'mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf')
        shutil.copy2(OLD / 'ContinuousSceneMod.swf', m.RUNTIME / 'mods/ContinuousScene/release/ContinuousSceneMod.swf')
        assert r.sha(m.RUNTIME / 'pfe.swf') == HOST_SHA
        assert r.sha(m.RUNTIME / 'mods/ContinuousScene/release/ContinuousSceneMod.swf') == CANDIDATE_SHA
        options = ['--name', args.name, '--high-qos', '--land', args.land,
            '--window-width', '2048', '--window-height', '1123', '--expect-no-signs',
            '--draw-control', 'stationary', '--encounter', '--fixed-enemies', '--benchmark', 'scene',
            '--speed', '4', '--short', '--stable-motion', '--player-fire', '--combat-route', '--combat-route-length', '200']
        options += ['--no-lighting', '--no-wall'] if args.effects == 'off' else ['--vision']
        m.run_owned(m.parse_args(options), lease)
        result, inputs = r.result(args.name)
        assert r.baseline() == baseline, 'Production dependency drift'
        assert frozen == reviewed_artifacts() and probe['sourceSHA256'] == source_hashes(), 'Frozen inputs changed during run'
        assert probe['probeSHA256'] == r.sha(OUT / 'ContinuousSceneProbe.swf')
        for path, digest in baseline.items():
            if path not in ('application.xml', 'mods/loader-manifest.txt'):
                assert inputs[path] == (CANDIDATE_SHA if path == 'mods/ContinuousScene/release/ContinuousSceneMod.swf' else digest), path
        assert inputs['mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf'] == probe['probeSHA256']
        policy = r.read(r.E / args.name / 'process-policy.json')
        assert policy['performanceEligible'] and not policy['otherAirProcessIds'] and not policy.get('memoryAbort')
        summary = dict(name=args.name, candidate=CANDIDATE_SHA, host=HOST_SHA, land=args.land, effects=args.effects,
            deployed=False, acceptance=False, sequence='ABBA', excludedFramesPerSegment=DROP,
            checks=len(result['assertions']), driver=result['driver'], playerFireWarmup=result['playerFireWarmup'],
            combatRoute=result['combatRoute'], samples=summarize(result))
        r.save(r.E / args.name / 'probe-build.json', probe)
        r.save(r.E / args.name / 'stationary-combat-summary.json', summary)
        r.save(OUT / (args.name + '-summary.json'), summary)
        concise = {k: v for k, v in summary.items() if k not in ('combatRoute', 'playerFireWarmup')}
        concise['samples'] = [{k: v for k, v in row.items() if k not in ('combatWindows', 'activity')} for row in summary['samples']]
        print(json.dumps(concise), flush=True)
        lease.outcome = 'passed'
        lease.note = 'Audited stationary candidate real-fire ABBA completed; grace excluded; no deployment or overall acceptance'


if __name__ == '__main__':
    main()
