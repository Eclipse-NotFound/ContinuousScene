"""Matched native camera axes with active quiet simulation; diagnostic only."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import math
import shutil
import statistics
import sys
import traceback
import time
import uuid

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
VERSION = 'camera-environment-paired-1'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


reference = load('camera_world_reference', HERE.parent/'window-visibility-native-20261025/run.py')
old, shared, control, dense, base, r, m, support = (reference.old, reference.shared, reference.control,
    reference.dense, reference.base, reference.r, reference.m, reference.support)
patch = load('camera_world_patch', HERE/'probe_patch.py')
lineage = load('terrain_registry_lineage', HERE/'lineage.py')
PINS = dict(reference.PINS)
STARTUP_POLICIES=[]
original_hidden_process=m.HiddenProcess
def recorded_hidden_process(*args,**kwargs):
    process=original_hidden_process(*args,**kwargs)
    STARTUP_POLICIES.append(dict(pid=process.pid,policy=getattr(process,'resource_policy',None)))
    return process
m.HiddenProcess=recorded_hidden_process

RC_RECEIPT=HERE.parents[4]/'mods/RConnect/build/m52/a-live-animation-deploy-01/verified.json'
RC_CURRENT='2C49DFD05D524085EA43FB8FFA537D1A9359FEBD52FB13D6A19FAAE6E2563621'
PINS['mods/Rconnect/release/RConnectMod.swf']=RC_CURRENT


def runner_inputs():
    assert r.sha(RC_RECEIPT)=='5446D95AAA1552622CF1E691BBDE5C962875897014CF5C06A452A95037ACBC3B'
    rc=r.read(RC_RECEIPT)
    assert rc['status']=='verified' and rc['version']=='0.2.24-animfix1' and rc['release_sha256'].upper()==RC_CURRENT
    assert patch.HELPER.read_text('utf-8-sig') == patch.helper_source()
    return dict(reference.runner_inputs(), **{str(p): r.sha(p) for p in
        (Path(reference.__file__), HERE/'run.py', HERE/'README.md', HERE/'probe_patch.py', HERE/'prepare.py', HERE/'lineage.py',HERE/'prepare_host.py',HERE/'audit.py',HERE/'build.py',HERE/'source-equivalent.as.inc', RC_RECEIPT,
         patch.HELPER, patch.ORIGINAL, patch.PATCH_SOURCE, *patch.EXTRA_INPUTS, *lineage.tool_paths(reference))})


def fixture_inputs():
    return dict(lineage.fixture_inputs(reference), **{str(p): r.sha(p) for p in
        (HERE/'probe_patch.py', HERE/'lineage.py', patch.HELPER, patch.ORIGINAL, patch.PATCH_SOURCE, *patch.EXTRA_INPUTS, *lineage.tool_paths(reference))})


def compile_probe(lease, baseline, scripts, compiler, fixture):
    seed = lineage.read_seed(reference)
    staging = HERE/'source-staging'/uuid.uuid4().hex
    patch.prepare(Path(seed['frozenSourcePath']), staging/'src')
    after = base.tree_hashes(staging/'src')
    changed = sorted(k for k in set(after)|set(seed['frozenSourceSHA256']) if after.get(k)!=seed['frozenSourceSHA256'].get(k))
    assert changed == patch.CHANGED and len(after) == 86
    origin = staging/'source-origin.json'
    r.save(origin, dict(version=VERSION, seedReceiptSHA256=reference.SEED_SHA,
        seedProbeSHA256=reference.PROBE_SHA, seedSourceSHA256=seed['frozenSourceSHA256'],
        stagedSHA256=after, changed=changed, fixtureInputs=fixture))
    path = shared.compile_frozen(lease, staging/'src', baseline, scripts, compiler, fixture)
    value = r.read(path)
    value.update(cameraWorldVersion=VERSION, sourceOrigin=str(origin), sourceOriginSHA256=r.sha(origin))
    r.save(path, value)
    return path


def verify_probe(path, baseline, scripts, compiler, fixture):
    value = base.verify_probe(path, baseline, scripts, compiler, fixture)
    assert value['cameraWorldVersion'] == VERSION
    seed = lineage.read_seed(reference)
    origin_path = Path(value['sourceOrigin'])
    assert r.sha(origin_path) == value['sourceOriginSHA256']
    origin = r.read(origin_path)
    assert origin['seedReceiptSHA256'] == reference.SEED_SHA and origin['seedProbeSHA256'] == reference.PROBE_SHA
    assert origin['seedSourceSHA256'] == seed['frozenSourceSHA256'] and origin['changed'] == patch.CHANGED
    assert origin['fixtureInputs'] == fixture and origin['stagedSHA256'] == value['frozenSourceSHA256']
    changed = sorted(k for k in set(value['frozenSourceSHA256'])|set(seed['frozenSourceSHA256'])
        if value['frozenSourceSHA256'].get(k) != seed['frozenSourceSHA256'].get(k))
    assert changed == patch.CHANGED and len(value['frozenSourceSHA256']) == 86
    frozen, source = Path(value['frozenSourcePath']), Path(seed['frozenSourcePath'])
    assert (frozen/'ContinuousSceneMotionProbe.as').read_text('utf-8-sig') == patch.transform((source/'ContinuousSceneMotionProbe.as').read_text('utf-8-sig'))
    assert r.sha(frozen/'tests/SceneCameraRasterTrial.as') == r.sha(patch.HELPER)
    return value


def options(name,mode,room_x,room_y):
    values=reference.options(name)+['--draw-control','tilecrop','--presentation-check']
    for flag,value in [('--benchmark',mode),('--window-width','1296'),('--window-height','759')]:
        i=values.index(flag);values[i+1]=value
    values=[v for v in values if v not in ('--encounter','--fixed-enemies','--native-input-motion','--native-sprint','--player-fire','--combat-route')]
    i=values.index('--combat-route-length');del values[i:i+2]
    if mode=='normal':
        values=[v for v in values if v!='--expect-no-signs']
        values+=['--native-room-x',str(room_x),'--native-room-y',str(room_y),'--native-route-x','480','--native-route-y','119']
    return values


def metric(values):
    ordered = sorted(values)
    return dict(count=len(values), mean=statistics.mean(values), median=statistics.median(values),
                p95=ordered[math.ceil(len(ordered)*.95)-1], maximum=max(values))


summary_module=load('active_quiet_summary',HERE/'summary.py')
summarize=summary_module.summarize


def wait_ready(seconds):
    assert 0<=seconds<=300
    if not seconds:return None
    started=time.monotonic();deadline=started+seconds;samples=[];stable=0;reported=-30
    while True:
        elapsed=time.monotonic()-started;memory=m.memory_status();air=m.air_pids()
        good=memory['availableCommit']>=5*1024**3 and memory['availablePhysical']>=2*1024**3 and not air
        stable=stable+1 if good else 0
        samples.append(dict(elapsed=elapsed,memory=memory,air=air,good=good))
        if stable>=3 or time.monotonic()>=deadline:
            value=dict(ready=stable>=3,samples=samples,stableChecks=stable,waitLimitSeconds=seconds,
                requiredCommit=5*1024**3,requiredPhysical=2*1024**3,launchedAir=False)
            path=HERE/'readiness'/(uuid.uuid4().hex+'.json');path.parent.mkdir(exist_ok=True)
            r.save(path,value)
            receipt=dict(path=str(path),sha256=r.sha(path),ready=value['ready'])
            print(json.dumps(dict(readiness=receipt,lastMemory=memory)),flush=True)
            return receipt
        if elapsed-reported>=30:
            print(json.dumps(dict(waitingForStableMemory=True,elapsed=round(elapsed),memory=memory,air=air)),flush=True)
            reported=elapsed
        time.sleep(min(5,max(0,deadline-time.monotonic())))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',required=True,choices=['scene']);parser.add_argument('--name',required=True);parser.add_argument('--registry-wait',type=int,default=300)
    parser.add_argument('--room-x',type=int,default=2);parser.add_argument('--room-y',type=int,default=3)
    parser.add_argument('--wait-ready-seconds',type=int,default=0)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--compile-probe',action='store_true');group.add_argument('--probe-build',type=Path)
    args=parser.parse_args()
    assert __debug__ and args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
    folder=r.E/args.name;assert not folder.exists(),'Keep prior evidence'
    readiness=wait_ready(args.wait_ready_seconds)
    if readiness is not None and not readiness['ready']:return
    record=dict(version=VERSION,options=options(args.name,args.mode,args.room_x,args.room_y),diagnosticOnly=True,deployed=False)
    if readiness is not None:record['readinessReceipt']=readiness
    with m.Registration(owner='ContinuousScene / visible ordinary room reference / 01a13816',purpose=args.name,
            run_dir=m.RUNTIME,evidence=folder,resource='game',wait=args.registry_wait) as lease:
        try:
            assert not m.air_pids(),'Other AIR remains untouched'
            memory=control.memory_gate()
            baseline,scripts,compiler,fixture=r.baseline(),runner_inputs(),support.compiler_inputs(),fixture_inputs()
            runtime=reference.runtime_inputs();assert len(baseline)==526 and len(runtime)==13
            for key,digest in PINS.items():assert baseline[key]==digest,key
            host_build=r.read(HERE/'build.json');host_audit=r.read(HERE/'audit-proof.json')
            assert host_build['base']==baseline['pfe.swf'] and host_build['diagnosticOnly'] and host_audit['diagnosticOnly']
            assert host_build['audit']==r.sha(HERE/'audit-proof.json') and host_audit['passed']
            assert host_audit['changed']==['fe.graph.Grafon::0:1:sceneNativeEnvironment'] and host_audit['unchangedBodies']==5770
            assert host_build['candidate']==host_audit['candidateSHA256']==r.sha(HERE/'pfe.swf')
            host_inputs={str(HERE/p):r.sha(HERE/p) for p in ['build.json','audit-proof.json','pfe.swf']}
            expected=dict(baseline);expected['pfe.swf']=host_build['candidate']
            record.update(baseline=baseline,expectedRuntime=expected,hostInputs=host_inputs,runnerInputs=scripts,compilerInputs=compiler,fixtureInputs=fixture,runtimeInputs=runtime,memoryBefore=memory)
            path=compile_probe(lease,baseline,scripts,compiler,fixture) if args.compile_probe else args.probe_build.resolve()
            probe=verify_probe(path,baseline,scripts,compiler,fixture)
            m.prepare();shutil.copy2(probe['probePath'],m.RUNTIME/base.PROBE_PATH)
            shutil.copy2(HERE/'pfe.swf',m.RUNTIME/'pfe.swf')
            for key,digest in expected.items():
                if key not in ('application.xml','mods/loader-manifest.txt'):assert r.sha(m.RUNTIME/key)==digest,key
            assert baseline==r.baseline() and scripts==runner_inputs() and runtime==reference.runtime_inputs()
            record.update(probeBuildPath=str(path),probeSHA256=probe['probeSHA256'],memoryBeforeAir=control.memory_gate())
            run_error=None
            try:m.run_owned(m.parse_args(record['options']),lease)
            except BaseException as error:
                run_error=error;record.update(executionError=repr(error),executionTraceback=traceback.format_exc())
            finally:
                record['startupResourcePolicies']=STARTUP_POLICIES
                if folder.exists():
                    r.save(folder/'probe-build.json',probe);r.save(folder/'runner-inputs.json',record)
            assert baseline==r.baseline() and scripts==runner_inputs() and compiler==support.compiler_inputs()
            assert fixture==fixture_inputs() and runtime==reference.runtime_inputs()
            verify_probe(path,baseline,scripts,compiler,fixture)
            assert host_inputs=={p:r.sha(Path(p)) for p in host_inputs}
            if not (folder/'storage/result.json').is_file():
                if run_error:raise run_error
                raise RuntimeError('No retained result; original process evidence preserved')
            raw,actual=reference.read_retained_result(folder)
            for key,digest in expected.items():
                if key not in ('application.xml','mods/loader-manifest.txt'):assert actual[key]==digest,key
            assert actual[base.PROBE_PATH]==probe['probeSHA256']
            policy=r.read(folder/'process-policy.json')
            assert policy['desktopPolicy']=='private' and not policy['performanceEligible']
            assert not policy.get('otherAirProcessIds') and not policy.get('memoryAbort') and not policy.get('runFailure')
            assert len(STARTUP_POLICIES)==1 and STARTUP_POLICIES[0]['pid']==policy['pid']
            applied=STARTUP_POLICIES[0]['policy']
            assert applied['requested']=='test' and not applied['errors'] and not applied['after']['errors']
            assert applied['after']['cpuPriorityClass']==0x20 and applied['after']['memoryPriority']==5
            assert applied['after']['powerThrottling']['highQoS']
            summary=summarize(raw)
            summary.update(resultSHA256=r.sha(folder/'storage/result.json'),probeSHA256=probe['probeSHA256'],inputsUnchanged=True,runtimeInputsUnchanged=True)
            r.save(folder/'summary.json',summary)
            if run_error:raise run_error
            lease.outcome='passed';lease.note='1920 same-instance native/cached intervals, selector restored; diagnostic host not deployed'
            print(json.dumps(dict(name=args.name,complete=True,arms=summary['arms'],pairs=summary['pairs'])),flush=True)
        except BaseException as error:
            folder.mkdir(parents=True,exist_ok=True)
            r.save(folder/'runner-failure.json',dict(record,error=repr(error),traceback=traceback.format_exc(),complete=False,deployed=False))
            lease.outcome='failed';lease.note=repr(error);raise


shared.HERE,shared.VERSION=HERE,VERSION
shared.runner_inputs,shared.fixture_inputs=runner_inputs,fixture_inputs
base.OUT=HERE/'probe-builds'
base.runner_inputs,base.candidate_inputs=runner_inputs,fixture_inputs
if __name__=='__main__':main()
