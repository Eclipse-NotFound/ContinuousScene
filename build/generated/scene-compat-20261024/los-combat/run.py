"""Registered 4 x 300 native combat LOS ABBA; isolated candidate only, no deployment."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys
import uuid

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
VERSION = 'tdfc-los-combat-1'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


env = load('los_environment_control', HERE.parent/'environment-control/run.py')
component = load('los_component_source', HERE.parent/'tdfc-los/run.py')
patcher = load('los_combat_patch', HERE/'probe_patch.py')
dense, base, r, m, support = env.dense, env.base, env.r, env.m, env.support
HOST, TDFC, TDFC_PATH = env.HOST, component.TDFC, component.TDFC_PATH
RC = '78C052AEA963F1689B705AE1E14D274916AE1A1F7E81933390CAF8D1A88F4699'
RC_BEFORE = 'DF0FA0E2CA952E77E5132E75D71E73558DC919C7B8CDEBA5DA05FC9E94DC01E7'
RC_RECEIPT = r.ROOT/'mods/RConnect/build/m52/recovery-room-user-deploy-01/deployment.json'
RC_RECEIPT_SHA = '16EF10BA4F2A5393FD41EFE0648EA55A051DD9D5DD7C9EFEAB722EE66D4EABE4'
LOADER_PATH = 'mods/ModLoader/release/ModLoaderMod.swf'
LOADER_BEFORE = 'BD71B6F31774B97841D4C158451DA0353B53BC46AC72F8E2A7FE2C3F3F4908B1'
LOADER = '2050E023205E87FDFDF7FBA4B54B9BAD7769868E51767D0BFBE1742CDC7542E2'
LOADER_RECEIPT = r.ROOT/'mods/ModLoader/build/out/debugger/20261024-122458-49ed085b/recorder-checks.json'
LOADER_RECEIPT_SHA = '9C624ECB717001F638A912C57491A402E41B219EF2D9FAF9408083E9E885E63D'
SEED_SHA, SEED_PROBE, SEED_RECEIPT = env.SEED_SHA, env.SEED_PROBE, env.SEED_RECEIPT
CHANGED = ['ContinuousSceneMotionProbe.as']


def seed():
    old = env.seed()
    pin = r.read(HERE/'source-pin.json')
    assert pin['receiptSHA256'] == SEED_SHA and pin['probeSHA256'] == SEED_PROBE
    assert pin['sourceFileCount'] == len(old['frozenSourceSHA256']) == 85
    assert pin['allowedChanges'] == CHANGED and not pin['currentSharedSourceAllowed']
    return old


def loader_receipt():
    assert r.sha(LOADER_RECEIPT)==LOADER_RECEIPT_SHA,'ModLoader deployment receipt changed'
    value=r.read(LOADER_RECEIPT);deployment=value['deployment']
    assert deployment['status']=='verified' and value['hostSha256'].upper()==HOST
    assert deployment['beforeSha256'].upper()==LOADER_BEFORE
    assert value['runtimeSha256'].upper()==deployment['afterSha256'].upper()==LOADER
    assert Path(deployment['target']).resolve()==(r.ROOT/LOADER_PATH).resolve()
    assert r.sha(Path(deployment['target']))==LOADER and r.sha(Path(deployment['backup']))==LOADER_BEFORE
    recorder=deployment['frameRecorder']
    assert recorder['active'] is True and recorder['samples']>0 and recorder['mode']=='memory-until-exit'
    assert not recorder['reason'] and not recorder['exportError']
    return dict(path=str(LOADER_RECEIPT),sha256=LOADER_RECEIPT_SHA,status='verified',
        beforeSHA256=LOADER_BEFORE,installedSHA256=LOADER,
        frameRecorderActiveInDeploymentSmoke=True,frameRecorderMode=recorder['mode'],
        recorderRuntimeSampledByThisProbe=False)


def rc_receipt(baseline=None):
    loader=loader_receipt()
    assert r.sha(RC_RECEIPT)==RC_RECEIPT_SHA,'RC deployment receipt changed; review the new evidence explicitly'
    value=r.read(RC_RECEIPT)
    assert value['status']=='user-requested-installed' and value['version']=='0.2.24-roomfix5'
    assert value['user_requested_deploy_before_final_validation'] and value['smoke_status']=='pending'
    assert value['before_sha256'].upper()==value['backup_sha256'].upper()==RC_BEFORE
    assert value['candidate_sha256'].upper()==value['release_sha256'].upper()==value['release_sha256_final'].upper()==RC
    before={key:digest.upper() for key,digest in value['installation_before'].items()}
    after={key:digest.upper() for key,digest in value['installation_after'].items()}
    assert after=={key:digest.upper() for key,digest in value['expected_installation_after'].items()}
    assert sorted(key for key in set(before)|set(after) if before.get(key)!=after.get(key))==[dense.RC]
    assert before[dense.RC]==RC_BEFORE and after[dense.RC]==RC
    assert Path(value['release']).resolve()==(r.ROOT/dense.RC).resolve()
    assert r.sha(Path(value['release']))==r.sha(Path(value['candidate']))==RC
    assert r.sha(Path(value['backup']))==RC_BEFORE
    if baseline is not None:
        differences=sorted(key for key,digest in after.items() if baseline[key]!=digest)
        assert differences==[LOADER_PATH],('Only the independently verified ModLoader update may follow the RC receipt',differences)
        assert after[LOADER_PATH]==LOADER_BEFORE and baseline[LOADER_PATH]==LOADER
    return dict(path=str(RC_RECEIPT),sha256=RC_RECEIPT_SHA,version=value['version'],
        status=value['status'],beforeSHA256=RC_BEFORE,installedSHA256=RC,rcSmokeVerified=False,
        smokeStatus='pending',rcPerformanceQualified=False,modLoaderDeployment=loader,
        scope='Current exact installed combination only; LOS results do not qualify RC behavior')


def runner_inputs():
    files = [HERE/'run.py', HERE/'probe_patch.py', HERE/'source-pin.json',
             HERE.parent/'environment-control/run.py', HERE.parent/'environment-control/probe_patch.py']
    return dict(dense.runner_inputs(), **component.runner_inputs(), **{str(p):r.sha(p) for p in files})


def fixture_inputs():
    old = seed(); env.deployment(); rc_receipt()
    files = [SEED_RECEIPT, Path(old['probePath']), HERE/'source-pin.json', HERE/'probe_patch.py',
             env.DEPLOYMENT, HERE.parent/'environment-control/probe_patch.py', RC_RECEIPT, LOADER_RECEIPT]
    return dict(component.candidate_inputs(), **{str(p):r.sha(p) for p in files})


def compile_probe(lease, baseline, scripts, compiler, fixture):
    old = seed(); staging = HERE/'source-staging'/uuid.uuid4().hex
    patcher.prepare(Path(old['frozenSourcePath']), staging/'src')
    after = base.tree_hashes(staging/'src')
    changed = sorted(k for k in set(old['frozenSourceSHA256'])|set(after)
        if old['frozenSourceSHA256'].get(k) != after.get(k))
    assert changed == CHANGED and len(after) == 85
    assert base.tree_hashes(Path(old['frozenSourcePath'])) == old['frozenSourceSHA256']
    origin = staging/'source-origin.json'
    r.save(origin, dict(version=VERSION,seedReceipt=str(SEED_RECEIPT),seedReceiptSHA256=SEED_SHA,
        seedProbeSHA256=SEED_PROBE,seedSource=old['frozenSourcePath'],seedSourceSHA256=old['frozenSourceSHA256'],
        stagedSHA256=after,changed=changed,fixtureInputs=fixture,componentsProbe=False))
    base.B = staging/'build'
    path = base.compile_frozen_probe(lease,baseline,scripts,compiler,fixture)
    value = r.read(path);value.update(losCombatVersion=VERSION,sourceOrigin=str(origin),sourceOriginSHA256=r.sha(origin))
    r.save(path,value);return path


def verify_probe(path,baseline,scripts,compiler,fixture):
    value = base.verify_probe(path,baseline,scripts,compiler,fixture)
    assert value['losCombatVersion'] == VERSION
    origin = Path(value['sourceOrigin']);assert r.sha(origin) == value['sourceOriginSHA256']
    original, old = r.read(origin), seed()
    assert original['version'] == VERSION and not original['componentsProbe']
    assert original['seedReceiptSHA256'] == SEED_SHA and original['seedProbeSHA256'] == SEED_PROBE
    assert original['seedSourceSHA256'] == old['frozenSourceSHA256'] and original['fixtureInputs'] == fixture
    assert original['stagedSHA256'] == value['frozenSourceSHA256']
    changed = sorted(k for k in set(old['frozenSourceSHA256'])|set(value['frozenSourceSHA256'])
        if old['frozenSourceSHA256'].get(k) != value['frozenSourceSHA256'].get(k))
    assert changed == original['changed'] == CHANGED and len(value['frozenSourceSHA256']) == 85
    source = (Path(old['frozenSourcePath'])/CHANGED[0]).read_text(encoding='utf-8-sig')
    assert (Path(value['frozenSourcePath'])/CHANGED[0]).read_text(encoding='utf-8-sig') == patcher.transform(source)
    return value


def component_gate(name,candidate,baseline):
    assert name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in name)
    folder = r.E/name
    result, inputs = r.result(name)
    summary, recorded = r.read(folder/'summary.json'), r.read(folder/'runner-inputs.json')
    assert summary['version'] == component.VERSION and summary['qualification']['passed'] and summary['componentsOnly']
    assert summary['hostSHA256'] == HOST and summary['candidateSHA256'] == candidate['candidateSHA256']
    assert summary['resultSHA256'] == r.sha(folder/'storage/result.json')
    assert summary['inputsSHA256'] == r.sha(folder/'inputs.json')
    assert recorded['baseline'] == baseline and inputs[TDFC_PATH] == candidate['candidateSHA256']
    assert r.read(folder/'candidate-build.json') == candidate
    c = result['tdfcLosComponents']
    assert c['passed'] and len(c['cases']) == 38 and c['nativeCalls'] == 76 and c['cacheHits'] > 0
    assert c['blockedCases'] >= 7 and c['fallbackCases'] == 10 and c['restore']['passed']
    assert not result['samples'] and not c['performanceEligible']
    return {str(folder/name):r.sha(folder/name) for name in
            ('summary.json','storage/result.json','inputs.json','runner-inputs.json','candidate-build.json','probe-build.json')}


def summarize(result,args):
    result_summary = dense.summarize(result,args)
    assert result_summary['qualification']['playerShotFrames'] == 400
    control = result['tdfcLos']
    assert control['version'] == VERSION and control['order'] == [False,True,True,False]
    assert control['initial']['enabled'] is False and control['boundaryOnly'] and not control['counterReset']
    assert not control['componentCalls'] and 'tdfcLosComponents' not in result
    cleanup = control['cleanup']
    assert cleanup['owned'] and cleanup['restored'] and cleanup['original'] is False and cleanup['after'] is False
    groups = {False:[],True:[]};counts={False:dict(calls=0,fallback=0,hits=0,lookups=0),True:dict(calls=0,fallback=0,hits=0,lookups=0)}
    previous = control['initial']; windows=[]
    for index,row in enumerate(result['samples']):
        value=row['tdfcLos'];enabled=index in (1,2)
        assert value['index']==index and value['enabled'] is enabled
        assert value['before']==previous
        assert value['after']['enabled'] is enabled and value['end']['enabled'] is enabled
        assert value['after']['version']==value['end']['version']=='tdfc-los-empty-cell-1'
        assert row['caseBeginAtMs'] <= value['switchBeginAtMs'] <= value['switchEndAtMs'] <= row['sampleAtMs'][0]
        assert value['switchMs']==value['switchEndAtMs']-value['switchBeginAtMs']
        assert row['sampleAtMs'][-1] <= value['observedEndAtMs']
        for key in counts[False]:
            assert value['before'][key]==value['after'][key]
            delta=value['end'][key]-value['after'][key]
            assert isinstance(delta,(int,float)) and delta>=0 and delta==int(delta)==value['delta'][key]
            assert enabled or delta==0
            counts[enabled][key]+=delta
        previous=value['end'];groups[enabled]+=row['continuousFramesMs']
        windows.append(dict(index=index,enabled=enabled,toggle=value,
            continuous=base.metrics(row['continuousFramesMs']),playerShots=row['playerShotFrames'],
            enemyShots=row['enemyShotFrames'],activity=row['activity'],activityEnd=row.get('activityEnd'),
            warmed=sum(row['warm']),slices=row.get('slices'),resident=row.get('resident'),
            workload=result_summary['samples'][index]['workload']))
    assert counts[True]['calls']>0 and counts[True]['hits']>0 and counts[True]['lookups']>0
    assert cleanup['before']==previous
    result_summary.update(losCombatVersion=VERSION,control=control,windows=windows,
        groups={('B' if enabled else 'A'):dict(continuous=base.metrics(groups[enabled]),counters=counts[enabled]) for enabled in (False,True)})
    result_summary['limitations'] += [
        'ABBA is four chronological 300-frame windows, not a claim that AI/fire/population loads are identical.',
        'No component calls, synthetic tile writes, camera hold, new prewarm, counter resets or per-frame LOS observer.',
        'All continuous intervals include boundary toggle/counter work; final counter read and cleanup occur after the final timestamp.',
        'A is the same diagnostic candidate with its switch false; candidate eligibility/counter instrumentation is not a production speed claim.',
        'Only B records optimized/fallback LOS calls; zero A counters do not mean no original LOS work.',
        'Candidate private class identity cache initializes on first eligible B call; that cost remains measured.',
        'This exact combination has RC roomfix5 and ModLoader 2.5.0 with an active frame recorder observed by its deployment smoke. It is not a causal comparison with earlier DF0F/BD71 runs; this probe does not sample recorder status.',
        'No numerical performance acceptance threshold is applied here; root reviews workload and repeat evidence.']
    return result_summary


def main():
    assert __debug__
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name',required=True)
    parser.add_argument('--candidate-build',type=Path,required=True)
    parser.add_argument('--component-evidence',required=True)
    parser.add_argument('--registry-wait',type=int,default=600)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--compile-probe',action='store_true');group.add_argument('--probe-build',type=Path)
    args=parser.parse_args();args.mode='scene'
    assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
    folder=r.E/args.name;assert not folder.exists()
    with m.Registration(owner='ContinuousScene / TDFC LOS combat / 01a13816',purpose=args.name,
            run_dir=m.RUNTIME,evidence=folder,wait=args.registry_wait) as lease:
        assert not m.air_pids()
        env.memory_gate()
        baseline,scripts,compiler,fixture=r.baseline(),runner_inputs(),support.compiler_inputs(),fixture_inputs()
        assert baseline['pfe.swf']==HOST and baseline[base.CS_PATH]==base.FORMAL_CS
        assert baseline[dense.RC]==RC and baseline[TDFC_PATH]==TDFC
        rc_source=rc_receipt(baseline)
        cp=args.candidate_build.resolve();candidate=component.verify_candidate(cp,baseline,compiler)
        components=component_gate(args.component_evidence,candidate,baseline)
        pp=compile_probe(lease,baseline,scripts,compiler,fixture) if args.compile_probe else args.probe_build.resolve()
        probe=verify_probe(pp,baseline,scripts,compiler,fixture)
        m.prepare();shutil.copy2(candidate['candidatePath'],m.RUNTIME/TDFC_PATH)
        shutil.copy2(probe['probePath'],m.RUNTIME/base.PROBE_PATH)
        for key,digest in baseline.items():
            if key not in ('application.xml','mods/loader-manifest.txt',TDFC_PATH):assert r.sha(m.RUNTIME/key)==digest,key
        assert r.sha(m.RUNTIME/TDFC_PATH)==candidate['candidateSHA256']
        assert not (m.RUNTIME/component.patch.CONTROL).exists(),'Terminal component control must be absent'
        options=['--name',args.name,'--high-qos','--land','random_mane','--encounter','--fixed-enemies',
            '--benchmark','scene','--short','--stable-motion','--native-input-motion','--native-sprint',
            '--player-fire','--combat-route','--combat-route-length','200','--window-width','2048',
            '--window-height','1123','--no-lighting','--no-wall','--draw-control','rcnative','--expect-no-signs']
        env.memory_gate();original_cpu=m.cpu_owned
        try:
            try:
                m.cpu_owned=env.aligned_cpu_owned(original_cpu)
                m.run_owned(m.parse_args(options),lease)
            finally:
                m.cpu_owned=original_cpu
                if folder.exists():
                    r.save(folder/'probe-build.json',probe);r.save(folder/'candidate-build.json',candidate)
                    r.save(folder/'runner-inputs.json',dict(version=VERSION,options=options,baseline=baseline,
                        runnerInputs=scripts,compilerInputs=compiler,fixtureInputs=fixture,
                        candidateBuildPath=str(cp),probeBuildPath=str(pp),componentEvidence=components,
                        overrideSources={TDFC_PATH:candidate['candidatePath'],base.PROBE_PATH:probe['probePath']},
                        hostSHA256=HOST,copiedActualInstalledHost=True,rcDeployment=rc_source))
            assert baseline==r.baseline() and scripts==runner_inputs() and fixture==fixture_inputs()
            assert compiler==support.compiler_inputs()
            component.verify_candidate(cp,baseline,compiler);verify_probe(pp,baseline,scripts,compiler,fixture)
            assert components==component_gate(args.component_evidence,candidate,baseline)
            result,inputs=r.result(args.name)
            for key,digest in baseline.items():
                if key not in ('application.xml','mods/loader-manifest.txt',TDFC_PATH):assert inputs[key]==digest,key
            assert inputs[TDFC_PATH]==candidate['candidateSHA256'] and inputs[base.PROBE_PATH]==probe['probeSHA256']
            assert 'cameraHold' not in result and 'cameraPrewarm' not in result
            policy=r.read(folder/'process-policy.json')
            assert policy['desktopPolicy']=='private' and not policy['performanceEligible']
            assert not policy.get('runFailure') and not policy.get('memoryAbort') and not policy.get('otherAirProcessIds')
            summary=summarize(result,args)
            summary.update(hostSHA256=HOST,candidateSHA256=candidate['candidateSHA256'],probeSHA256=probe['probeSHA256'],
                complete=True,incomplete=False,clockAlignment=env.alignment(result,policy),rcDeployment=rc_source)
            r.save(folder/'summary.json',summary)
            print(json.dumps(dict(name=args.name,qualification=summary['qualification'],groups=summary['groups'],
                clockAlignmentPassed=summary['clockAlignment']['passed']),ensure_ascii=False),flush=True)
            assert summary['qualification']['passed']
            lease.outcome='passed';lease.note='1200 real native combat frames / LOS ABBA captured; no performance acceptance or deployment'
        except Exception as error:
            if folder.exists() and not (folder/'summary.json').exists():
                raw=r.read(folder/'storage/result.json') if (folder/'storage/result.json').exists() else {}
                r.save(folder/'summary.json',dict(version=VERSION,name=args.name,complete=False,incomplete=True,
                    qualification=dict(passed=False),error=repr(error),diagnosticOnly=True,performanceEligible=False,
                    performanceAcceptance=False,deployed=False,completedWindows=len(raw.get('samples',[])),tdfcLos=raw.get('tdfcLos')))
            raise


base.OUT=HERE/'probe-builds'
base.runner_inputs=runner_inputs
base.candidate_inputs=fixture_inputs
if __name__=='__main__':main()
