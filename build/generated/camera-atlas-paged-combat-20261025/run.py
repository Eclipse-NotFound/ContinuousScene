"""Registered paged-atlas SMG10 combat ABBA; new workload, no production writes."""
from pathlib import Path
import argparse
import importlib.util
import json
import math
import shutil
import sys
import uuid

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
VERSION = 'camera-atlas-paged-smg10-combat-1'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


shared = load('motion_atlas_build_support', HERE.parent / 'camera-atlas-motion-native-size-20261025/run.py')
control, dense, base, r, m, support = shared.control, shared.dense, shared.base, shared.r, shared.m, shared.support
patch = load('motion_atlas_combat_patch', HERE / 'probe_patch.py')
RV_RECEIPT = HERE.parents[3] / 'RealisticVision/build/combat-render-output/deployment/receipt.json'
RV_CURRENT = '638E2D408E2CF46683C41114F75773829A1B4417D74BFFE9D08855A4FE343710'
PINS = dict(control.PINS)
PINS['mods/RealisticVision/release/RealisticVisionMod.swf'] = RV_CURRENT
PAGED_EVIDENCE = r.E / 'camera-atlas-paged-20261025-r2'
PAGED_RECEIPT_SHA = '359C581A5D9DE7FA5B90311A260F2443F1B5103031EA480A96A3FFC07E9EE02C'
PAGED_SUMMARY_SHA = '4A9386FE759D20CCA2D349492B733D2917EA1971C2557DDB1F75AD137A1CFFFD'


def tested_paging():
    receipt_path, summary_path = PAGED_EVIDENCE / 'probe-build.json', PAGED_EVIDENCE / 'summary.json'
    assert r.sha(receipt_path) == PAGED_RECEIPT_SHA and r.sha(summary_path) == PAGED_SUMMARY_SHA
    receipt, summary = r.read(receipt_path), r.read(summary_path)
    assert summary['complete'] and summary['version'] == 'camera-atlas-paged-2'
    assert summary['probeSHA256'] == receipt['probeSHA256']
    assert summary['atlasPixelToleranceRGB'] == 2 and summary['atlasPixelToleranceAlpha'] == 0
    assert receipt['frozenSourceSHA256']['SceneRasterPresentation.as'] == patch.PAGED_RAW_SHA
    assert r.sha(HERE / 'SceneRasterPresentation.as') == patch.PAGED_RAW_SHA
    return receipt


def runner_inputs():
    return dict(control.runner_inputs(), **{str(p): r.sha(p) for p in
        [Path(shared.__file__), HERE / 'run.py', HERE / 'probe_patch.py', HERE / 'presentation_transform.py',
         HERE / 'SceneRasterPresentation.as', patch.OLD / 'probe_patch.py', patch.OLD / 'presentation_transform.py',
         RV_RECEIPT, PAGED_EVIDENCE / 'probe-build.json', PAGED_EVIDENCE / 'summary.json']})


def fixture_inputs():
    old = control.seed(); tested_paging()
    return {str(p): r.sha(p) for p in [control.SEED_RECEIPT, Path(old['probePath']),
        Path(old['sourceOrigin']), HERE / 'probe_patch.py', HERE / 'presentation_transform.py',
        HERE / 'SceneRasterPresentation.as', patch.OLD / 'probe_patch.py', patch.OLD / 'presentation_transform.py',
        PAGED_EVIDENCE / 'probe-build.json', PAGED_EVIDENCE / 'summary.json',
        support.OUT / 'source-provenance.json']}


def compile_probe(lease, baseline, scripts, compiler, fixture):
    old = control.seed(); staging = HERE / 'source-staging' / uuid.uuid4().hex
    patch.prepare(Path(old['frozenSourcePath']), staging / 'src')
    after = base.tree_hashes(staging / 'src')
    changed = sorted(k for k in set(after) | set(old['frozenSourceSHA256'])
                     if after.get(k) != old['frozenSourceSHA256'].get(k))
    assert changed == patch.CHANGED and len(after) == 85
    origin = staging / 'source-origin.json'
    r.save(origin, dict(version=VERSION, seedReceiptSHA256=control.SEED_SHA,
        seedProbeSHA256=control.PROBE, seedSourceSHA256=old['frozenSourceSHA256'],
        stagedSHA256=after, changed=changed, fixtureInputs=fixture))
    path = shared.compile_frozen(lease, staging / 'src', baseline, scripts, compiler, fixture)
    value = r.read(path)
    value.update(motionAtlasCombatVersion=VERSION, denseFixture=patch.FIXTURE_VERSION, observerFixtureSource=dense.VERSION,
                 sourceOrigin=str(origin), sourceOriginSHA256=r.sha(origin))
    r.save(path, value); return path


def verify_probe(path, baseline, scripts, compiler, fixture):
    value = base.verify_probe(path, baseline, scripts, compiler, fixture)
    assert value['motionAtlasCombatVersion'] == VERSION and value['denseFixture'] == patch.FIXTURE_VERSION
    assert value['observerFixtureSource'] == dense.VERSION
    op = Path(value['sourceOrigin']); assert r.sha(op) == value['sourceOriginSHA256']
    origin, old = r.read(op), control.seed()
    assert origin['seedReceiptSHA256'] == control.SEED_SHA and origin['seedProbeSHA256'] == control.PROBE
    assert origin['seedSourceSHA256'] == old['frozenSourceSHA256'] and origin['changed'] == patch.CHANGED
    assert origin['stagedSHA256'] == value['frozenSourceSHA256'] and origin['fixtureInputs'] == fixture
    frozen, seed_source = Path(value['frozenSourcePath']), Path(old['frozenSourcePath'])
    assert (frozen / 'ContinuousSceneMotionProbe.as').read_text('utf-8-sig') == patch.transform(
        (seed_source / 'ContinuousSceneMotionProbe.as').read_text('utf-8-sig'))
    assert (frozen / 'SceneRasterPresentation.as').read_text('utf-8-sig') == patch.variant.transform(
        (seed_source / 'SceneRasterPresentation.as').read_text('utf-8-sig'))
    assert r.sha(frozen / 'SceneRasterPresentation.as') == patch.PAGED_RAW_SHA
    assert (frozen / 'tests/SceneEncounter.as').read_text('utf-8-sig') == patch.encounter_transform(
        (seed_source / 'tests/SceneEncounter.as').read_text('utf-8-sig'))
    return value


def options(name):
    return ['--name', name, '--high-qos', '--land', 'random_mane', '--encounter', '--fixed-enemies',
        '--benchmark', 'scene', '--short', '--stable-motion', '--native-input-motion', '--native-sprint',
        '--player-fire', '--combat-route', '--combat-route-length', '200', '--window-width', '2048',
        '--window-height', '1123', '--no-lighting', '--no-wall', '--expect-no-signs', '--draw-control', 'atlas']


def six_smg10(encounter):
    base.six_armed(encounter)
    for actor in encounter['actors']:
        gun, stats = actor['weapon'], actor['weaponStats']
        assert gun['id'] == stats['id'] == 'smg10' and stats['tip'] == 2
        assert stats['rapid'] == 3 and stats['knock'] == 3 and stats['holder'] == 24
        assert stats['reloadTicks'] == 35 and stats['speed'] == 150 and stats['damage'] == 2
        assert stats['knockMult'] == stats['ammoKnock'] == 1


def page_state(state):
    assert state['version'] == 'atlas-paged-1'
    assert state['pageSide'] == 1280 and state['cellSide'] == 320 and state['pageLimit'] == 8
    assert 0 <= state['livePages'] <= state['peakPages'] <= 8
    assert state['pagesCreated'] - state['pagesDisposed'] == state['livePages']
    assert state['allocations'] == state['pagesCreated'] * 4 and state['disposals'] == state['pagesDisposed'] * 4
    assert state['layers'] == state['attached'] == state['liveBitmaps'] == state['livePages'] * 4
    assert state['pixelStorageBytes'] == state['livePages'] * 1280 * 1280 * 4 * 4
    assert state['pixelStorageBytes'] <= state['peakPixelStorageBytes'] <= 8 * 1280 * 1280 * 4 * 4
    assert state['totalAllocatedPixelBytes'] == state['pagesCreated'] * 1280 * 1280 * 4 * 4
    assert len(state['residentPageKeys']) == len(set(state['residentPageKeys'])) == state['livePages']
    assert len(state['currentPageKeys']) == len(set(state['currentPageKeys'])) == state['requestedPages']
    assert set(state['visiblePageKeys']) <= set(state['currentPageKeys']) <= set(state['residentPageKeys'])
    if state['presented']:
        assert state['visiblePageKeys'] and state['pendingHidden'] > 0 and not state['fallbackReason']
    else:
        assert not state['visiblePageKeys'] and state['pendingHidden'] == 0


def summarize(result, name):
    cfg, motion = result['config'], result['nativeInputMotion']
    assert result['ok'] and not result['error'] and all(v['ok'] for v in result['assertions'])
    assert cfg['benchmark'] == 'scene' and cfg['drawControl'] == 'atlas' and not cfg['presentationCheck']
    assert cfg['nativeInputMotion'] and cfg['nativeSprint'] and cfg['stableMotion'] and cfg['playerFire']
    assert cfg['fixedEnemies'] and not cfg['localEnemies'] and cfg['noLighting'] and cfg['noWall'] and not cfg['vision']
    assert result['denseFixture']['version'] == patch.FIXTURE_VERSION and motion['version'] == 'native-input-dense-sprint-2'
    assert result['denseFixture']['enemyWeapon'] == 'smg10' and result['denseFixture']['actors'] == 6
    six_smg10(result['playerFireWarmup']['encounter'])
    assert result['observerPolicy'] == dict(version='dense-observer-lean-2', settingsDuringTiming=False,
        segmentProgressWrites=False, segmentCensus=False, finalCensus=True, heartbeatIntervalMs=5000,
        continuousFramesRetained=True)
    assert result['driver']['forcedPositionCalls'] == 0 and motion['spawn']['calls'] == 1
    assert motion['warmup']['ready'] and motion['warmup']['roundTrips'] >= 1 and motion['warmup']['groundContactRun'] >= 10
    assert motion['timingStart']['floorContact'] and motion['route']['terrainVerified']
    assert result['world']['layoutSeed'] == 20261019 and len(result['samples']) == 4
    assert result['viewport']['zoom'] == 1 and (result['world']['width'], result['world']['height']) == (240, 125)
    atlas_report = result['atlasMotion']
    assert atlas_report['version'] == VERSION and atlas_report['order'] == [False, True, True, False]
    assert atlas_report['diagnosticOnly'] and not atlas_report['performanceEligible'] and not atlas_report['visualAcceptance']
    cleanup = result['atlasMotionCleanup']
    assert cleanup['restored'] and cleanup['errors'] == []
    final = cleanup['after']
    page_state(final)
    assert final['pagesCreated'] == final['pagesDisposed'] and final['allocations'] == final['disposals']
    for key in ('presented', 'hasBounds', 'hasLocation', 'poseValid'): assert final[key] is False
    for key in ('layers', 'attached', 'liveBitmaps', 'pixelStorageBytes', 'pendingHidden'): assert final[key] == 0
    rows = []; pose = None; previous_enabled = previous_presented = False
    previous_copies = previous_rebuilds = 0
    for index, row in enumerate(result['samples']):
        assert row['name'] == ['draw-baseline-a', 'draw-control-b', 'draw-control-b-repeat', 'draw-baseline-a-repeat'][index]
        assert row['empty'] == row['misses'] == 0 and row['playerShotFrames'] > 0 and row['enemyShotFrames'] > 0
        six_smg10(row['encounter'])
        for observation in row['combatWindows']: six_smg10(observation['encounter'])
        assert 'activityCensus' not in row
        assert sum(row['probeTiming']['censusMs']) == sum(row['probeTiming']['progressSaveMs']) == 0
        atlas = row['atlasMotion']; enabled = index in (1, 2)
        assert atlas['version'] == VERSION
        names = ('enabled', 'presented', 'previousEnabled', 'previousPresented', 'vx', 'vy', 'scale',
                 'worldX', 'worldY', 'worldScaleX', 'worldScaleY', 'quakeX', 'quakeY', 'copies', 'rebuilds',
                 'matrixA', 'matrixB', 'matrixC', 'matrixD', 'matrixTX', 'matrixTY', 'chunkSide')
        assert all(len(atlas[k]) == 300 for k in names)
        assert all(len(atlas[k]) == 300 for k in ('states', 'worldOnStage', 'satsActive', 'satsVisible'))
        page_state(atlas['start'])
        assert atlas['start']['copies'] == previous_copies and atlas['start']['rebuilds'] == previous_rebuilds
        for j in range(300):
            for key in names[4:]: assert isinstance(atlas[key][j], (int, float)) and math.isfinite(atlas[key][j])
            current = tuple(atlas[k][j] for k in ('vx', 'vy', 'scale'))
            assert current[2] > 0
            geometry = (atlas['worldOnStage'][j] and current[2] == 1 and
                tuple(atlas[k][j] for k in ('matrixA', 'matrixB', 'matrixC', 'matrixD')) == (1, 0, 0, 1) and
                all(atlas[k][j] == math.floor(atlas[k][j]) for k in ('quakeX', 'quakeY', 'matrixTX', 'matrixTY')))
            reason = ('disabled-or-native-scene' if not enabled else
                'sats' if atlas['satsActive'][j] or atlas['satsVisible'][j] else
                'non-unit-or-fractional-geometry' if not geometry else
                'unsupported-native-cell-side' if atlas['chunkSide'][j] != 320 else '')
            state = atlas['states'][j]; page_state(state)
            assert state['fallbackReason'] == reason, ('Unexpected presentation fallback', index, j, state)
            expected = bool(not reason and pose is not None and current != pose)
            assert atlas['enabled'][j] is enabled and atlas['presented'][j] is expected
            assert state['presented'] is expected and state['poseValid'] is (not bool(reason))
            assert atlas['previousEnabled'][j] is previous_enabled and atlas['previousPresented'][j] is previous_presented
            assert atlas['copies'][j] >= previous_copies and atlas['rebuilds'][j] >= previous_rebuilds
            assert state['copies'] == atlas['copies'][j] and state['rebuilds'] == atlas['rebuilds'][j]
            pose = current if not reason else None
            previous_enabled, previous_presented = enabled, expected
            previous_copies, previous_rebuilds = atlas['copies'][j], atlas['rebuilds'][j]
        assert atlas['end'] == atlas['states'][-1]
        assert atlas['end']['copies'] == previous_copies == row['presentation']['copies']
        assert atlas['end']['rebuilds'] == previous_rebuilds == row['presentation']['rebuilds']
        assert sum(atlas['presented']) > 0 if enabled else sum(atlas['presented']) == 0
        if index == 1: assert previous_copies > 0 and previous_rebuilds > 0
        rows.append(dict(index=index, mode='atlas' if index in (1, 2) else 'native',
            continuous=base.metrics(row['continuousFramesMs']), withinSegment=base.metrics(row['frames']),
            nativeBand=base.metrics(row['nativeBand']), playerShots=row['playerShotFrames'], enemyShots=row['enemyShotFrames'],
            combatWindows=base.combat_windows(row, 300), workload=dense.workload(row, motion['route']),
            activity=row['activity'], activityEnd=row.get('activityEnd'), warmed=sum(row['warm']),
            slices=row['slices'], forced=row['forced'],
            probeWorkMs=base.metrics(row['probeTiming']['workMs']), presentation=row['presentation'],
            atlas=dict(presentedFrames=sum(atlas['presented']),
                fallbackFrames={reason: sum(s['fallbackReason'] == reason for s in atlas['states'])
                    for reason in sorted(set(s['fallbackReason'] for s in atlas['states']))},
                peakPages=max(s['peakPages'] for s in atlas['states']),
                peakPixelStorageBytes=max(s['peakPixelStorageBytes'] for s in atlas['states']),
                copies=atlas['end']['copies']-atlas['start']['copies'],
                rebuilds=atlas['end']['rebuilds']-atlas['start']['rebuilds'],
                pagesCreated=atlas['end']['pagesCreated']-atlas['start']['pagesCreated'],
                pagesDisposed=atlas['end']['pagesDisposed']-atlas['start']['pagesDisposed'],
                allocatedPixelBytes=atlas['end']['totalAllocatedPixelBytes']-atlas['start']['totalAllocatedPixelBytes'],
                fractionalWorldFrames=sum(any(atlas[k][j] != round(atlas[k][j]) for k in ('worldX', 'worldY')) for j in range(300)),
                quakeFrames=sum(atlas['quakeX'][j] != 0 or atlas['quakeY'][j] != 0 for j in range(300)),
                start=atlas['start'], end=atlas['end'])))
    final_census = result['finalActivityCensus']
    assert final_census['afterFinalSample'] and final_census['data']
    assert result['samples'][-1]['sampleAtMs'][-1] <= final_census['startedAtMs'] <= final_census['endedAtMs']
    qualification = dict(actualSprint=sum(x['workload']['aboveWalkSpeedFrames'] for x in rows) >= 30,
        concurrentFixtureBullets=any(v >= 3 for row in result['samples'] for v in row['denseFrames']['fixtureBullets']),
        observedNativePlayerBullets=any(v > 0 for row in result['samples'] for v in row['denseFrames']['playerBullets']),
        playerShotFrames=sum(x['playerShots'] for x in rows), enemyShotFrames=sum(x['enemyShots'] for x in rows))
    qualification['passed'] = all(qualification[k] for k in
        ('actualSprint', 'concurrentFixtureBullets', 'observedNativePlayerBullets'))
    grouped = {mode: base.metrics([v for i, row in enumerate(result['samples'])
        if (i in (1, 2)) == (mode == 'atlas') for v in row['continuousFramesMs']]) for mode in ('native', 'atlas')}
    return dict(version=VERSION, name=name, complete=True, diagnosticOnly=True, performanceEligible=False,
        performanceAcceptance=False, gameplayAcceptance=False, deployed=False, qualification=qualification,
        fixtureVersion=patch.FIXTURE_VERSION, observerFixtureSource=dense.VERSION,
        weaponStats=[a['weaponStats'] for a in result['samples'][0]['encounter']['actors']],
        continuous=dense.continuous(result), rows=rows, grouped=grouped, cleanup=cleanup,
        limitations=['All 1200 continuous intervals and initial allocation/transition costs are retained.',
            'Actual native input, acceleration, stamina and knockback; no jump input or per-frame teleport.',
            'Six native SMG10 shooters replace LMGs: this is a new workload, not comparable to old LMG arms as a performance delta. Original damage2/durable-HP fixture remains.',
            'Same-process ABBA has unseeded AI/fire and evolving scene content; inspect both pairs and workload.',
            'Camera vx/vy are native ints; actual world/quake transforms are recorded. Paging falls back on unsupported geometry; earlier paused pixels do not establish combat visual correctness.',
            'Recorded presentation is the display state set before each timestamp; its rendering contributes to the following interval.',
            'Lighting, vision and WallBlend are off; no long-route, zoom, SATS, multiplayer or all-effects qualification.',
            'No production deployment; favorable combat timing still requires separate visual and lifecycle checks.'])


def main():
    assert __debug__
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    parser.add_argument('--registry-wait', type=int, default=600)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--compile-probe', action='store_true')
    group.add_argument('--probe-build', type=Path)
    args = parser.parse_args()
    assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
    folder = r.E / args.name; assert not folder.exists(), 'Preserve prior evidence'
    record = dict(version=VERSION, diagnosticOnly=True, performanceEligible=False,
                  gameplayAcceptance=False, fixtureVersion=patch.FIXTURE_VERSION,
                  observerFixtureSource=dense.VERSION, options=options(args.name))
    with m.Registration(owner='ContinuousScene / paged atlas SMG10 combat / 01a13816', purpose=args.name,
                        run_dir=m.RUNTIME, evidence=folder, resource='game', wait=args.registry_wait) as lease:
        try:
            assert not m.air_pids(), 'Other AIR remains untouched'
            memory = control.memory_gate()
            baseline, scripts, compiler, fixture = r.baseline(), runner_inputs(), support.compiler_inputs(), fixture_inputs()
            rv_receipt = r.read(RV_RECEIPT)
            assert rv_receipt['result'] == 'PASS' and rv_receipt['new'].upper() == RV_CURRENT
            assert rv_receipt['before']['pfe.swf'].upper() == control.HOST
            for key, digest in PINS.items(): assert baseline[key] == digest, key
            record.update(baseline=baseline, runnerInputs=scripts, compilerInputs=compiler,
                          fixtureInputs=fixture, memoryBefore=memory, hostSHA256=control.HOST)
            path = compile_probe(lease, baseline, scripts, compiler, fixture) if args.compile_probe else args.probe_build.resolve()
            probe = verify_probe(path, baseline, scripts, compiler, fixture)
            m.prepare(); shutil.copy2(probe['probePath'], m.RUNTIME / base.PROBE_PATH)
            for key, digest in baseline.items():
                if key not in ('application.xml', 'mods/loader-manifest.txt'): assert r.sha(m.RUNTIME / key) == digest, key
            assert baseline == r.baseline() and scripts == runner_inputs()
            record.update(probeBuildPath=str(path), probeSHA256=probe['probeSHA256'], memoryBeforeAir=control.memory_gate())
            try: m.run_owned(m.parse_args(record['options']), lease)
            finally:
                if folder.exists():
                    r.save(folder / 'probe-build.json', probe); r.save(folder / 'runner-inputs.json', record)
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
            summary = summarize(result, args.name)
            summary.update(probeSHA256=probe['probeSHA256'], resultSHA256=r.sha(folder / 'storage/result.json'),
                           inputsUnchanged=True, checks=len(result['assertions']))
            r.save(folder / 'summary.json', summary)
            assert summary['qualification']['passed'], 'Sprint/concurrent-fire qualification failed; retained'
            lease.outcome='passed'; lease.note='Native combat ABBA complete; diagnostic only, visual/function qualification still required'
            print(json.dumps({k: summary[k] for k in ('name', 'continuous', 'grouped', 'qualification', 'checks')}, ensure_ascii=False), flush=True)
        except BaseException as error:
            lease.outcome='failed'; lease.note=repr(error)
            folder.mkdir(parents=True, exist_ok=True)
            r.save(folder / 'runner-failure.json', dict(record, error=repr(error), complete=False, deployed=False))
            raise


# Reuse only the previously reviewed compiler implementation, binding every
# output and input hash to this new recipe. Its paused-world driver is not used.
shared.HERE, shared.VERSION = HERE, VERSION
shared.runner_inputs, shared.fixture_inputs = runner_inputs, fixture_inputs
base.OUT = HERE / 'probe-builds'
base.runner_inputs, base.candidate_inputs = runner_inputs, fixture_inputs
if __name__ == '__main__': main()
