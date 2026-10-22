"""Registered display-only attribution on the formal host and real combat route.

The five controls deliberately hide content. Results never authorize deployment
or performance acceptance; native reload gaps are recorded without forcing AI.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import math
import shutil
import statistics

B = Path(__file__).resolve().parent
OUT = B / 'generated/world-layers-20261022'
CONTROLS = ('all', 'no-fog', 'no-terrain', 'no-objects', 'no-world')
FORMAL_HOST = 'BEFCF0509E11FAC9FEF7AFB834708B8B93752A14AE3D5CD72B42AA6D42F9B82A'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


r = load('world_layer_runner_helpers', B / 'enemy-release.py')
m = r.motion


def source_hashes():
    return {p.relative_to(B.parent / 'src').as_posix(): r.sha(p)
            for p in (B.parent / 'src').rglob('*.as')}


def helper_hashes():
    paths = (Path(__file__), B / 'enemy-release.py', Path(r.enemy.__file__), Path(m.__file__))
    return {p.name: r.sha(p) for p in paths}


def metrics(rows):
    if not rows:
        return dict(frames=0)
    dt = [row['dt'] for row in rows]
    return dict(frames=len(rows), median=statistics.median(dt), mean=statistics.mean(dt),
                p95=sorted(dt)[math.ceil(len(dt) * .95) - 1], maximum=max(dt),
                over100=sum(value > 100 for value in dt),
                native=statistics.mean(row['currentNativeBand'] for row in rows),
                scriptBeforeProbe=statistics.mean(row['currentScriptBeforeProbe'] for row in rows),
                residualNotRenderCPU=statistics.mean(row['dt'] - row['currentScriptBeforeProbe'] for row in rows),
                playerShotFrames=sum(row['playerShot'] for row in rows),
                enemyShots=sum(row.get('enemyShots', 0) for row in rows),
                visibilityRewrites=sum(row['visibilityRewrites'] for row in rows),
                reassertWrites=sum(row['reassertCount'] for row in rows))


def summarize(name, effects, result):
    ds, frames, start = result['displaySummary'], result['displayFrames'], result['displayStart']
    assert ds['complete'] and not ds['aborted'] and ds['cleanup']['restored']
    assert ds['sampledFrames'] == ds['plannedFrames'] == 1500 and len(frames) == 1500
    assert ds['windows'] == 50 and ds['windowFrames'] == 30 and ds['invalidSamples'] == 0
    assert result['displayEmpty'] == 0 and result['displayMisses'] == 0
    assert tuple(start['controls']) == CONTROLS and len(start['layers']) == 12
    assert ds['cleanup']['finalOriginalLayerMask'] == start['originalVisibleMask']
    assert result['driver']['stableMotion'] and result['playerFire']['enabled']
    assert result['config']['combatRouteLength'] == 200 and result['config']['speed'] == 4
    assert result['playerFire']['shotFrames'] > 30
    assert all(row['frame'] == index and not row['issues'] for index, row in enumerate(frames))
    summary = dict(name=name, mode='worldlayers', effects=effects, diagnosticOnly=True,
                   performanceAcceptance=False, deployed=False, checks=len(result['assertions']),
                   driver=result['driver'], playerFire=result['playerFire'],
                   playerFireWarmup=result['playerFireWarmup'], combatRoute=result['combatRoute'],
                   displaySummary=ds, displayView=result['displayView'],
                   displayGroups={}, displayWindows=[], enemySilentWindows=[])
    for wi in range(50):
        window = frames[wi * 30:(wi + 1) * 30]
        assert all(row['window'] == wi and row['frameInWindow'] == index for index, row in enumerate(window))
        assert len({row['control'] for row in window}) == 1
        assert window[0]['transition'] and not any(row['transition'] for row in window[1:])
        populations = [row['encounter'] for row in window if 'encounter' in row]
        assert len(populations) == 2 and all(row['alive'] == 6 and row['armed'] == 6 for row in populations)
        player = sum(row['playerShot'] for row in window)
        enemy = sum(row.get('enemyShots', 0) for row in window)
        assert player > 0, ('Player did not shoot in window', wi)
        if enemy == 0:
            summary['enemySilentWindows'].append(wi)
        summary['displayWindows'].append(dict(window=wi, control=window[0]['control'],
            controlEffective=window[0]['controlEffective'], playerShotFrames=player, enemyShots=enemy,
            enemyTargets=sum(row.get('enemyTargets', 0) for row in window), population=populations,
            visibilityRewrites=sum(row['visibilityRewrites'] for row in window),
            metrics=metrics(window[1:])))
    for index, control in enumerate(CONTROLS):
        rows = [row for row in frames if row['control'] == control and not row['transition']]
        usable = [row for row in rows if row['eligible']]
        effective = bool(start['effectiveControls'][index])
        assert len(rows) == 290 and all(row['controlEffective'] == effective for row in rows)
        assert len(usable) == (290 if effective else 0), (control, len(usable), ds['negativeResidualSamples'])
        assert sum(row.get('enemyShots', 0) for row in rows) > 0, ('No enemy fire for control', control)
        summary['displayGroups'][control] = dict(attributionEligible=effective,
            reason=None if effective else 'Target group was hidden at the original baseline',
            eligible=metrics(usable), rawNonTransition=metrics(rows))
    summary['allWindowsHaveEnemyFire'] = not summary['enemySilentWindows']
    summary['loadLimitation'] = ('Natural enemy reload gaps are retained; compare per-control and per-window fire counts. '
                                 'Hidden content and timing residuals are attribution only, never renderer CPU or acceptance.')
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', required=True)
    parser.add_argument('--land', default='random_mane')
    parser.add_argument('--effects', choices=['off', 'full'], default='off')
    parser.add_argument('--compile-probe', action='store_true')
    parser.add_argument('--registry-wait', type=int, default=600)
    args = parser.parse_args()
    assert not (r.E / args.name).exists(), 'Never overwrite previous evidence'
    OUT.mkdir(parents=True, exist_ok=True)
    with m.Registration(owner='ContinuousScene / world display attribution / 01a13816',
            purpose=args.name, run_dir=m.RUNTIME, evidence=r.E / args.name, wait=args.registry_wait) as lease:
        assert not m.air_pids(), 'Other AIR present; untouched'
        baseline, helpers = r.baseline(), helper_hashes()
        assert baseline['pfe.swf'] == FORMAL_HOST
        if args.compile_probe:
            before = source_hashes()
            r.enemy.compile_as(B.parent / 'src', 'ContinuousSceneProbeDoc.as', OUT / 'ContinuousSceneProbe.swf')
            assert before == source_hashes(), 'Probe source changed during compile'
            r.save(OUT / 'probe-build.json', dict(sourceSHA256=before,
                probeSHA256=r.sha(OUT / 'ContinuousSceneProbe.swf')))
        probe = r.read(OUT / 'probe-build.json')
        assert probe['sourceSHA256'] == source_hashes(), 'Probe source changed; compile reviewed sources again'
        assert probe['probeSHA256'] == r.sha(OUT / 'ContinuousSceneProbe.swf')
        assert helpers == helper_hashes(), 'Runner helper drift before prepare'
        m.prepare()
        shutil.copy2(OUT / 'ContinuousSceneProbe.swf',
                     m.RUNTIME / 'mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf')
        options = ['--name', args.name, '--high-qos', '--land', args.land,
                   '--encounter', '--fixed-enemies', '--benchmark', 'scene', '--speed', '4', '--short',
                   '--stable-motion', '--player-fire', '--combat-route', '--combat-route-length', '200',
                   '--draw-control', 'worldlayers', '--window-width', '2048', '--window-height', '1123',
                   '--expect-no-signs']
        options += ['--no-lighting', '--no-wall'] if args.effects == 'off' else ['--vision']
        m.run_owned(m.parse_args(options), lease)
        result, inputs = r.result(args.name)
        assert source_hashes() == probe['sourceSHA256'], 'Probe sources changed during run'
        assert helpers == helper_hashes(), 'Runner helper drift during run'
        assert r.baseline() == baseline, 'Production dependency drift'
        for path, digest in baseline.items():
            if path not in ('application.xml', 'mods/loader-manifest.txt'):
                assert inputs[path] == digest, path
        assert inputs['mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf'] == probe['probeSHA256']
        assert not r.read(r.E / args.name / 'process-policy.json')['performanceEligible']
        r.save(r.E / args.name / 'probe-build.json', probe)
        r.save(r.E / args.name / 'runner-build.json', dict(helperSHA256=helpers))
        summary = summarize(args.name, args.effects, result)
        r.save(r.E / args.name / 'summary.json', summary)
        r.save(OUT / (args.name + '-summary.json'), summary)
        concise = {key: value for key, value in summary.items()
                   if key not in ('combatRoute', 'playerFireWarmup', 'displayWindows', 'displaySummary')}
        concise['reassertions'] = {key: summary['displaySummary'][key]
                                  for key in ('reassertFrames', 'reassertObservations', 'reassertWrites', 'reassertByLayer')}
        print(json.dumps(concise), flush=True)
        lease.outcome = 'passed'
        lease.note = 'Display attribution complete; raw load gaps retained, no performance acceptance or deployment'


if __name__ == '__main__':
    main()
