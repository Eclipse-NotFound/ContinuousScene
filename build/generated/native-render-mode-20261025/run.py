"""One registered direct/cpu run of the exact measured 29AF native SMG probe.

No compilation, production descriptor change, presentation helper or automatic
second run. Render mode changes only in the owned, unique AIR descriptor.
"""
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
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
VERSION = 'native-render-mode-1'
SEED_SHA = '983727AEB832BC586AF3767613B7C9D61564D92DC9D8E2435F972EEBF1D1D5EE'
PROBE_SHA = '29AF34571E7181139C682AA32A160E2C217C1B02B295E6DCBD6931D8DB7F94E5'
FIXTURE = 'dense-sprint-smg10-1'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


old = load('native_render_smg_support', HERE.parent / 'camera-atlas-paged-combat-20261025/run.py')
control, dense, base, r, m, support = old.control, old.dense, old.base, old.r, old.m, old.support
SEED = r.E / 'camera-atlas-paged-combat-20261025-r1/probe-build.json'
PINS = dict(old.PINS)
digest = lambda value: hashlib.sha256(value).hexdigest().upper()


def verify_seed():
    """Validate the old receipt against its real inputs, never substitute new maps."""
    assert r.sha(SEED) == SEED_SHA
    receipt = r.read(SEED)
    assert receipt['probeSHA256'] == PROBE_SHA and len(receipt['frozenSourceSHA256']) == 85
    assert receipt['denseFixture'] == FIXTURE and receipt['observerFixtureSource'] == dense.VERSION
    for field in ('runnerInputs', 'compilerInputs', 'candidateInputs'):
        for path, expected in receipt[field].items():
            assert r.sha(Path(path)) == expected, ('Historical build input changed', field, path)
    # This verifier checks the genuine 39A -> 29AF three-file recipe, frozen
    # source/config/log/probe hashes and prior source-origin chain.
    original_receipt = Path(receipt['probePath']).parent / 'probe-build.json'
    assert r.sha(original_receipt) == SEED_SHA and r.read(original_receipt) == receipt
    verified = old.verify_probe(original_receipt, receipt['productionSHA256'], receipt['runnerInputs'],
                                receipt['compilerInputs'], receipt['candidateInputs'])
    assert verified == receipt and r.sha(Path(receipt['probePath'])) == PROBE_SHA
    return receipt


def runner_inputs():
    return dict(old.runner_inputs(), **{str(p): r.sha(p) for p in
        [Path(old.__file__), Path(m.__file__), HERE / 'run.py', HERE / 'README.md', SEED]})


def runtime_inputs():
    # The shared production map does not include the ADL/runtime binaries.
    # Freeze this exact runtime tree separately, outside measured gameplay.
    runtime = r.ROOT / 'runtimes/air/win64'
    files = [r.ROOT / 'adl64.exe'] + sorted(p for p in runtime.rglob('*') if p.is_file())
    assert files[0].is_file() and len(files) > 1
    return {p.relative_to(r.ROOT).as_posix(): r.sha(p) for p in files}


def options(name):
    value = old.options(name)
    assert value[-2:] == ['--draw-control', 'atlas']
    return value[:-1] + ['rcnative']


def render_change(text, mode):
    assert mode in ('direct', 'cpu')
    original = '<renderMode>direct</renderMode>'
    replacement = '<renderMode>' + mode + '</renderMode>'
    assert text.count(original) == 1 and text.count('<renderMode>') == 1
    changed = text.replace(original, replacement, 1)
    assert changed.replace(replacement, original, 1) == text
    root = ET.fromstring(changed)
    ns = {'a': root.tag[1:].split('}')[0]}
    windows = root.findall('a:initialWindow', ns); assert len(windows) == 1
    window = windows[0]
    assert window.findtext('a:content', namespaces=ns) == 'pfe.swf'
    assert window.findtext('a:renderMode', namespaces=ns) == mode
    assert window.findtext('a:transparent', default='false', namespaces=ns).lower() == 'false'
    return changed


def owned_adapter(mode, prepared_text, prepared_bytes):
    """Two local reversible anchors: save actual descriptor; check before unlink."""
    original = inspect.getsource(m.run_owned)
    before_write = "    descriptor.write_text(descriptor_text,encoding='utf-8')"
    after_write = ("    descriptor_text=native_render_before_write(descriptor_text,app,args,out)\n"
                   "    descriptor.write_text(descriptor_text,encoding='utf-8')\n"
                   "    native_render_after_write(descriptor,out)")
    before_cleanup = '        flag.unlink(missing_ok=True);descriptor.unlink(missing_ok=True)'
    after_cleanup = '        native_render_before_cleanup(descriptor,out)\n' + before_cleanup
    transformed = original
    for first, second in ((before_write, after_write), (before_cleanup, after_cleanup)):
        assert transformed.count(first) == 1 and second not in transformed
        transformed = transformed.replace(first, second, 1)
    restored = transformed.replace(after_cleanup, before_cleanup, 1).replace(after_write, before_write, 1)
    assert restored == original
    assert "current['availableCommit']<512*1024**2" in transformed
    tree = ast.parse(transformed)
    assert len(tree.body) == 1 and isinstance(tree.body[0], ast.FunctionDef) and tree.body[0].name == 'run_owned'
    observation = {}

    def before_write(text, app, args, folder):
        assert prepared_text.count('<id>pfe-modsettings-continuous-scene</id>') == 1
        expected = prepared_text.replace('<id>pfe-modsettings-continuous-scene</id>', '<id>' + app + '</id>', 1)
        if args.window_width > 0:
            expected, width_count = re.subn(r'<width>\d+</width>', '<width>' + str(args.window_width) + '</width>', expected)
            expected, height_count = re.subn(r'<height>\d+</height>', '<height>' + str(args.window_height) + '</height>', expected)
            assert width_count == height_count == 1
        assert text == expected, 'Unexpected stock descriptor transformation'
        changed = render_change(text, mode)
        (folder / 'application-after-prepare.xml').write_bytes(prepared_bytes)
        before_path = folder / 'application-before-mode.xml'
        before_path.write_text(text, 'utf-8')
        normal = changed.replace('<id>' + app + '</id>', '<id>OWNED-INSTANCE</id>', 1)
        normal = normal.replace('<renderMode>' + mode + '</renderMode>', '<renderMode>COMPARE-MODE</renderMode>', 1)
        observation.update(version=VERSION, requestedMode=mode, declaredMode=mode, appId=app,
            preparedSHA256=digest(prepared_bytes), preparedTextSHA256=digest(prepared_text.encode('utf-8')),
            beforeModeSHA256=r.sha(before_path), beforeModeTextSHA256=digest(text.encode('utf-8')),
            expectedActualSHA256=digest(changed.replace('\n', os.linesep).encode('utf-8')),
            normalizedIDAndModeSHA256=digest(normal.encode('utf-8')), onlyModeChange=True, reverseExact=True,
            modeDiff=list(difflib.unified_diff(text.splitlines(), changed.splitlines(), fromfile='parameterized-direct', tofile=mode, lineterm='')),
            prepareToActualDiff=list(difflib.unified_diff(prepared_text.splitlines(), changed.splitlines(), fromfile='after-prepare', tofile='actual', lineterm='')),
            expectedActualText=changed, cleanupChecked=False, effectiveHardwareBackendObserved=False)
        return changed

    def after_write(descriptor, folder):
        observation['descriptorPath'] = str(descriptor)
        assert r.sha(descriptor) == observation['expectedActualSHA256']
        assert descriptor.read_text('utf-8-sig') == observation['expectedActualText']
        shutil.copy2(descriptor, folder / 'application-used.xml')
        observation.update(actualSHA256=r.sha(descriptor), descriptorPath=str(descriptor),
            launchArgv=[str(r.ROOT / 'adl64.exe'), '-runtime', str(r.ROOT / 'runtimes/air/win64'), str(descriptor)])
        r.save(folder / 'descriptor-review.json', {k:v for k,v in observation.items() if k != 'expectedActualText'})

    def before_cleanup(descriptor, folder):
        # Do not raise inside the stock finally: retain cleanup of flags, lock
        # and descriptor even if this evidence check fails.
        try:
            observation['actualAfterSHA256'] = r.sha(descriptor)
            observation['cleanupChecked'] = observation['actualAfterSHA256'] == observation['actualSHA256']
        except BaseException as error:
            observation['cleanupCheckError'] = repr(error)
        try: r.save(folder / 'descriptor-review.json', {k:v for k,v in observation.items() if k != 'expectedActualText'})
        except BaseException as error: observation['receiptWriteError'] = repr(error)

    scope = dict(m.__dict__)
    scope.update(native_render_before_write=before_write, native_render_after_write=after_write,
                 native_render_before_cleanup=before_cleanup)
    exec(compile(tree, '<native-render-descriptor-adapter>', 'exec'), scope)
    assert scope['run_owned'] is not m.run_owned and scope['run_owned'].__globals__ is not m.__dict__
    proof = dict(originalSHA256=digest(original.encode('utf-8')), transformedSHA256=digest(transformed.encode('utf-8')),
        anchors=2, reverseExact=True, sharedModuleModified=False, noPerFrameHook=True,
        minimumStartCommitBytes=4*1024**3, minimumStartPhysicalBytes=2*1024**3, unchangedRunGuardBytes=512*1024**2)
    return scope['run_owned'], proof, observation


def summarize(result, name, mode):
    cfg, motion = result['config'], result['nativeInputMotion']
    assert result['ok'] and not result['error'] and len(result['assertions']) == 26 and all(x['ok'] for x in result['assertions'])
    assert cfg['benchmark'] == 'scene' and cfg['drawControl'] == 'rcnative' and not cfg['presentationCheck']
    assert cfg['nativeInputMotion'] and cfg['nativeSprint'] and cfg['stableMotion'] and cfg['playerFire']
    assert cfg['fixedEnemies'] and cfg['combatRoute'] and not cfg['localEnemies']
    assert cfg['noLighting'] and cfg['noWall'] and not cfg['vision']
    assert not any(cfg[k] for k in ('profile','culling','sleepingRootShort','bulletSegments','worldProfile',
        'locationProfile','guiWeaponProfile','playerStepProfile','playerAnimateProfile','impactABBA','fogABBA','fogTypedABBA'))
    assert not any(k in result for k in ('rcOfflineInitial','rcOfflineCleanup','atlasMotion','atlasMotionCleanup','terrainLayer'))
    assert result['denseFixture']['version'] == FIXTURE and result['denseFixture']['enemyWeapon'] == 'smg10'
    assert result['denseFixture']['actors'] == 6 and motion['version'] == 'native-input-dense-sprint-2'
    old.six_smg10(result['playerFireWarmup']['encounter'])
    assert result['observerPolicy'] == dict(version='dense-observer-lean-2',settingsDuringTiming=False,
        segmentProgressWrites=False,segmentCensus=False,finalCensus=True,heartbeatIntervalMs=5000,continuousFramesRetained=True)
    assert result['driver']['forcedPositionCalls'] == 0 and motion['spawn']['calls'] == 1
    assert motion['warmup']['ready'] and motion['warmup']['roundTrips'] >= 1 and motion['warmup']['groundContactRun'] >= 10
    assert motion['timingStart']['floorContact'] and motion['route']['terrainVerified']
    assert result['world']['layoutSeed'] == 20261019 and len(result['samples']) == 4
    assert result['viewport']['zoom'] == 1 and (result['world']['width'],result['world']['height']) == (240,125)
    rows=[]
    for index,row in enumerate(result['samples']):
        assert row['name'] == 'dense-native-' + str(index)
        assert row['empty'] == row['misses'] == 0 and row['playerShotFrames'] > 0 and row['enemyShotFrames'] > 0
        assert 'rcOffline' not in row and 'atlasMotion' not in row and 'activityCensus' not in row
        old.six_smg10(row['encounter'])
        for sample in row['combatWindows']: old.six_smg10(sample['encounter'])
        assert sum(row['probeTiming']['censusMs']) == sum(row['probeTiming']['progressSaveMs']) == 0
        rows.append(dict(index=index,renderMode=mode,continuous=base.metrics(row['continuousFramesMs']),
            withinSegment=base.metrics(row['frames']),playerShots=row['playerShotFrames'],enemyShots=row['enemyShotFrames'],
            combatWindows=base.combat_windows(row,300),workload=dense.workload(row,motion['route']),
            bands={k:base.metrics(row[k]) for k in ('nativeBand','wallBand','sceneBand','preBand','tailBand','totalScript','afterProbeBand')},
            activity=row['activity'],activityEnd=row.get('activityEnd'),warmed=sum(row['warm']),slices=row['slices'],
            forced=row['forced'],residentStart=row['residentStart'],residentEnd=row['residentEnd'],
            probeWorkMs=base.metrics(row['probeTiming']['workMs'])))
    census=result['finalActivityCensus']
    assert census['afterFinalSample'] and census['data']
    assert result['samples'][-1]['sampleAtMs'][-1] <= census['startedAtMs'] <= census['endedAtMs']
    qualification=dict(actualSprint=sum(x['workload']['aboveWalkSpeedFrames'] for x in rows)>=30,
        concurrentFixtureBullets=any(v>=3 for row in result['samples'] for v in row['denseFrames']['fixtureBullets']),
        observedNativePlayerBullets=any(v>0 for row in result['samples'] for v in row['denseFrames']['playerBullets']),
        playerShotFrames=sum(x['playerShots'] for x in rows),enemyShotFrames=sum(x['enemyShots'] for x in rows))
    qualification['passed']=all(qualification[k] for k in ('actualSprint','concurrentFixtureBullets','observedNativePlayerBullets'))
    return dict(version=VERSION,name=name,renderMode=mode,complete=True,diagnosticOnly=True,performanceEligible=False,
        visualAcceptance=False,gameplayAcceptance=False,deployed=False,qualification=qualification,
        continuous=dense.continuous(result),rows=rows,fixtureVersion=FIXTURE,observerFixtureSource=dense.VERSION,
        limitations=['The exact 29AF probe is reused without compilation or additional per-frame observation.',
            'rcnative is a no-op display/RC control; each native-input SMG/ASSR window has 300 frames and real fire gates.',
            'All four windows use the same descriptor mode. This is one arm, not a within-process render-mode ABBA.',
            'Declared descriptor mode and runtime files are verified; no effective renderer/backend introspection is added.',
            'Different processes have evolving unseeded AI/fire. Compare workload, prewarm and run order before attributing a difference.',
            'No layers, pixels, quality, actor logic or timing boundaries are deliberately changed; actual pixel equivalence is not tested here.',
            'Instrumentation remains present; frame-script residual is not GPU time. No production or visual acceptance.'])


def main():
    assert __debug__
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name',required=True);parser.add_argument('--mode',choices=['direct','cpu'],required=True)
    parser.add_argument('--registry-wait',type=int,default=600)
    args=parser.parse_args()
    assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
    folder=r.E/args.name;assert not folder.exists(),'Preserve prior evidence'
    record=dict(version=VERSION,requestedMode=args.mode,diagnosticOnly=True,performanceEligible=False,
                deployed=False,options=options(args.name),seedReceipt=str(SEED),seedReceiptSHA256=SEED_SHA)
    with m.Registration(owner='ContinuousScene / native render-mode comparison / 01a13816',purpose=args.name,
                        run_dir=m.RUNTIME,evidence=folder,resource='game',wait=args.registry_wait) as lease:
        try:
            assert not m.air_pids(),'Other AIR remains untouched'
            memory=control.memory_gate()
            seed=verify_seed();baseline,scripts,runtime=r.baseline(),runner_inputs(),runtime_inputs()
            assert len(baseline)==526,('Installed input inventory changed',len(baseline))
            for key,expected in PINS.items():assert baseline[key]==expected,key
            rv=r.read(old.RV_RECEIPT)
            assert rv['result']=='PASS' and rv['new'].upper()==old.RV_CURRENT and rv['before']['pfe.swf'].upper()==control.HOST
            record.update(baseline=baseline,runnerInputs=scripts,runtimeInputs=runtime,probeSHA256=PROBE_SHA,memoryBefore=memory)
            m.prepare();shutil.copy2(seed['probePath'],m.RUNTIME/base.PROBE_PATH)
            for key,expected in baseline.items():
                if key not in ('application.xml','mods/loader-manifest.txt'):assert r.sha(m.RUNTIME/key)==expected,key
            prepared_bytes=(m.RUNTIME/'application.xml').read_bytes()
            prepared_text=(m.RUNTIME/'application.xml').read_text('utf-8-sig')
            assert render_change(prepared_text,'direct')==prepared_text
            execute,adapter,observation=owned_adapter(args.mode,prepared_text,prepared_bytes)
            record.update(descriptorAdapter=adapter,preparedDescriptorSHA256=digest(prepared_bytes))
            launch=m.parse_args(record['options'])
            assert launch.draw_control=='rcnative' and not launch.profile and not launch.presentation_check
            assert baseline==r.baseline() and scripts==runner_inputs() and runtime==runtime_inputs()
            record['memoryBeforeAir']=control.memory_gate()
            try:execute(launch,lease)
            finally:
                # A descriptor evidence failure can occur before the stock
                # process try/finally. Remove only this invocation's unique file.
                app=observation.get('appId','')
                if re.fullmatch(r'pfe-modsettings-continuous-motion-[0-9a-f]{32}',app):
                    owned_descriptor=m.RUNTIME/(app+'.xml')
                    if owned_descriptor.exists():
                        observation['fallbackDescriptorCleanup']=True
                        owned_descriptor.unlink()
                if folder.exists():
                    shutil.copy2(SEED,folder/'probe-build.json')
                    r.save(folder/'runner-inputs.json',record)
            assert baseline==r.baseline() and scripts==runner_inputs() and runtime==runtime_inputs()
            assert verify_seed()==seed and r.sha(folder/'probe-build.json')==SEED_SHA
            assert (m.RUNTIME/'application.xml').read_bytes()==prepared_bytes
            assert observation['cleanupChecked'] and not observation.get('cleanupCheckError') and not observation.get('receiptWriteError')
            assert not Path(observation['descriptorPath']).exists()
            assert r.sha(folder/'application-used.xml')==observation['actualSHA256']==observation['expectedActualSHA256']
            result,actual=r.result(args.name)
            for key,expected in baseline.items():
                if key not in ('application.xml','mods/loader-manifest.txt'):assert actual[key]==expected,key
            assert actual[base.PROBE_PATH]==PROBE_SHA and actual['application.xml']==digest(prepared_bytes)
            policy=r.read(folder/'process-policy.json')
            assert policy['desktopPolicy']=='private' and not policy['performanceEligible']
            assert policy['diagnosticOnly']=='Independent RC binary comparison with native input and continuous timing; noop control, no RC probe API'
            assert not policy.get('runFailure') and not policy.get('memoryAbort') and not policy.get('otherAirProcessIds')
            summary=summarize(result,args.name,args.mode)
            summary.update(probeSHA256=PROBE_SHA,seedReceiptSHA256=SEED_SHA,hostSHA256=control.HOST,
                runtimeInputs=runtime,inputsUnchanged=True,checks=len(result['assertions']),
                resultSHA256=r.sha(folder/'storage/result.json'),descriptorReview=r.read(folder/'descriptor-review.json'),
                originalProcessPolicyReason=policy['diagnosticOnly'])
            r.save(folder/'summary.json',summary)
            assert summary['qualification']['passed'],'Native sprint/fire qualification failed; retained'
            lease.outcome='passed';lease.note='One native render-mode arm complete; no visual/deployment acceptance'
            print(json.dumps({k:summary[k] for k in ('name','renderMode','continuous','qualification','checks')},ensure_ascii=False),flush=True)
        except BaseException as error:
            lease.outcome='failed';lease.note=repr(error)
            folder.mkdir(parents=True,exist_ok=True)
            r.save(folder/'runner-failure.json',dict(record,error=repr(error),complete=False))
            raise


if __name__=='__main__':main()
