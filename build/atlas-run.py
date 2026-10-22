"""Isolated atlas pixel checks and real-fire ABBA against the formal host.

This runner never writes a release or the formal host. Pixel checks are
terminal fixtures; timing excludes the first frame after each display switch.
Natural enemy reload gaps are retained and reported, never forced away.
"""
from pathlib import Path
import argparse, importlib.util, json, shutil, statistics

B = Path(__file__).resolve().parent
OUT = B/'generated/atlas-20261022'

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

r = load('atlas_runner_helpers', B/'enemy-release.py'); m = r.motion

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', required=True)
    parser.add_argument('--mode', choices=['pixels', 'combat'], default='pixels')
    parser.add_argument('--effects', choices=['off', 'full'], default='off')
    parser.add_argument('--land', default='random_mane')
    parser.add_argument('--compile-probe', action='store_true')
    parser.add_argument('--registry-wait', type=int, default=600)
    args = parser.parse_args(); OUT.mkdir(exist_ok=True)
    with m.Registration(owner='ContinuousScene / atlas investigation / 01a13816',
            purpose=args.name, run_dir=m.RUNTIME, evidence=r.E/args.name, wait=args.registry_wait) as lease:
        assert not m.air_pids(), 'Other AIR present; untouched'
        baseline = r.baseline()
        assert baseline['pfe.swf'] == 'BEFCF0509E11FAC9FEF7AFB834708B8B93752A14AE3D5CD72B42AA6D42F9B82A'
        hashes = lambda: {p.relative_to(B.parent/'src').as_posix():r.sha(p) for p in (B.parent/'src').rglob('*.as')}
        if args.compile_probe:
            before = hashes()
            r.enemy.compile_as(B.parent/'src', 'ContinuousSceneProbeDoc.as', OUT/'ContinuousSceneProbe.swf')
            assert before == hashes(), 'Probe source changed during compile'
            r.save(OUT/'probe-build.json', dict(sourceSHA256=before, probeSHA256=r.sha(OUT/'ContinuousSceneProbe.swf')))
        probe = r.read(OUT/'probe-build.json')
        assert probe['sourceSHA256'] == hashes(), 'Probe source changed; compile again'
        assert probe['probeSHA256'] == r.sha(OUT/'ContinuousSceneProbe.swf')
        m.prepare()
        shutil.copy2(OUT/'ContinuousSceneProbe.swf', m.RUNTIME/'mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf')
        options = ['--name', args.name, '--high-qos', '--land', args.land,
                   '--window-width', '2048', '--window-height', '1123',
                   '--expect-no-signs', '--draw-control', 'atlas']
        if args.mode == 'pixels': options += ['--presentation-check']
        else:
            options += ['--encounter', '--fixed-enemies', '--benchmark', 'scene',
                        '--speed', '4', '--short', '--stable-motion', '--player-fire',
                        '--combat-route', '--combat-route-length', '200']
        options += ['--no-lighting', '--no-wall'] if args.effects == 'off' else ['--vision']
        m.run_owned(m.parse_args(options), lease)
        result, inputs = r.result(args.name)
        assert r.baseline() == baseline, 'Production dependency drift'
        for path, digest in baseline.items():
            if path not in ('application.xml', 'mods/loader-manifest.txt'): assert inputs[path] == digest, path
        assert inputs['mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf'] == probe['probeSHA256']
        r.save(r.E/args.name/'probe-build.json', probe)
        summary = dict(name=args.name, mode=args.mode, effects=args.effects, land=args.land,
                       checks=len(result['assertions']), deployed=False,
                       acceptance=False, samples=[])
        if args.mode == 'pixels':
            assert not r.read(r.E/args.name/'process-policy.json')['performanceEligible']
            summary['presentation'] = result['presentation']
        else:
            assert not r.read(r.E/args.name/'process-policy.json')['performanceEligible']
            assert len(result['samples']) == 4
            summary['combatRoute'] = result['combatRoute']
            summary['playerFireWarmup'] = result['playerFireWarmup']
            for index, row in enumerate(result['samples']):
                assert len(row['frames']) == 300 and row['empty'] == 0 and row['misses'] == 0
                assert row['playerShotFrames'] > 0 and row['enemyShotFrames'] > 0
                assert row['encounter']['alive'] == 6 and row['encounter']['armed'] == 6
                windows = []
                for wi in range(10):
                    pair = [x for x in row['combatWindows'] if x['frame']//30 == wi]
                    assert len(pair) == 2 and all(x['encounter']['alive'] == 6 and x['encounter']['armed'] == 6 for x in pair)
                    player = pair[1]['playerShots'] - pair[0]['playerShots']
                    enemy = pair[1]['encounter']['actualShotFrames'] - pair[0]['encounter']['actualShotFrames']
                    assert player > 0
                    windows.append(dict(window=wi, playerShots=player, enemyShots=enemy, population=pair))
                frames = row['frames'][1:]  # switch frame belongs partly to the preceding control
                summary['samples'].append(dict(index=index, atlas=index in (1, 2), frames=len(frames),
                    median=statistics.median(frames), mean=statistics.mean(frames),
                    p95=sorted(frames)[int(len(frames)*.95)], maximum=max(frames), over100=sum(v>100 for v in frames),
                    native=statistics.mean(row['nativeBand'][1:]), script=statistics.mean(row['totalScript'][1:]),
                    playerShots=row['playerShotFrames'], enemyShots=row['enemyShotFrames'],
                    warmed=sum(row['warm']), presentation=row['presentation'], combatWindows=windows))
        r.save(OUT/(args.name+'-summary.json'), summary)
        concise = {k:v for k,v in summary.items() if k not in ('combatRoute', 'playerFireWarmup')}
        concise['samples'] = [{k:v for k,v in row.items() if k != 'combatWindows'} for row in summary['samples']]
        print(json.dumps(concise), flush=True)
        lease.outcome = 'passed'; lease.note = 'Isolated atlas check completed; overall optimization acceptance and deployment pending'

if __name__ == '__main__': main()
