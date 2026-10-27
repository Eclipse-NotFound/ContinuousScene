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
import uuid

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
VERSION = 'camera-native-visible-groups-1'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


reference = load('camera_world_reference', HERE.parent/'window-visibility-native-20261025/run.py')
old, shared, control, dense, base, r, m, support = (reference.old, reference.shared, reference.control,
    reference.dense, reference.base, reference.r, reference.m, reference.support)
patch = load('camera_world_patch', HERE/'probe_patch.py')
lineage = load('terrain_registry_lineage', HERE.parent/'camera-terrain-layers-20261025/lineage.py')
PINS = dict(reference.PINS)
RC_RECEIPT=HERE.parents[4]/'mods/RConnect/build/m52/a-live-animation-deploy-01/verified.json'
RC_CURRENT='2C49DFD05D524085EA43FB8FFA537D1A9359FEBD52FB13D6A19FAAE6E2563621'
PINS['mods/Rconnect/release/RConnectMod.swf']=RC_CURRENT


def runner_inputs():
    assert r.sha(RC_RECEIPT)=='5446D95AAA1552622CF1E691BBDE5C962875897014CF5C06A452A95037ACBC3B'
    rc=r.read(RC_RECEIPT)
    assert rc['status']=='verified' and rc['version']=='0.2.24-animfix1' and rc['release_sha256'].upper()==RC_CURRENT
    assert patch.HELPER.read_text('utf-8-sig') == patch.helper_source()
    return dict(reference.runner_inputs(), **{str(p): r.sha(p) for p in
        (Path(reference.__file__), HERE/'run.py', HERE/'README.md', HERE/'probe_patch.py', HERE/'prepare.py', HERE.parent/'camera-terrain-layers-20261025/lineage.py', RC_RECEIPT,
         patch.HELPER, patch.ORIGINAL, patch.PATCH_SOURCE, *patch.EXTRA_INPUTS)})


def fixture_inputs():
    return dict(lineage.fixture_inputs(reference), **{str(p): r.sha(p) for p in
        (HERE/'probe_patch.py', HERE.parent/'camera-terrain-layers-20261025/lineage.py', patch.HELPER, patch.ORIGINAL, patch.PATCH_SOURCE, *patch.EXTRA_INPUTS)})


def compile_probe(lease, baseline, scripts, compiler, fixture):
    seed = lineage.read_seed(reference)
    staging = HERE/'source-staging'/uuid.uuid4().hex
    patch.prepare(Path(seed['frozenSourcePath']), staging/'src')
    after = base.tree_hashes(staging/'src')
    changed = sorted(k for k in set(after)|set(seed['frozenSourceSHA256']) if after.get(k)!=seed['frozenSourceSHA256'].get(k))
    assert changed == patch.CHANGED and len(after) == 87
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
    assert changed == patch.CHANGED and len(value['frozenSourceSHA256']) == 87
    frozen, source = Path(value['frozenSourcePath']), Path(seed['frozenSourcePath'])
    assert (frozen/'ContinuousSceneMotionProbe.as').read_text('utf-8-sig') == patch.transform((source/'ContinuousSceneMotionProbe.as').read_text('utf-8-sig'))
    assert r.sha(frozen/'tests/SceneCameraRasterTrial.as') == r.sha(patch.HELPER)
    return value


def options(name,mode):
    values=reference.options(name)+['--draw-control','tilecrop','--presentation-check']
    for flag,value in [('--benchmark',mode),('--window-width','1296'),('--window-height','759')]:
        i=values.index(flag);values[i+1]=value
    if mode=='normal':
        values=[v for v in values if v!='--expect-no-signs']
        values+=['--native-room-x','2','--native-room-y','4','--native-route-x','480','--native-route-y','119']
    return values


def metric(values):
    ordered = sorted(values)
    return dict(count=len(values), mean=statistics.mean(values), median=statistics.median(values),
                p95=ordered[math.ceil(len(ordered)*.95)-1], maximum=max(values))


summary_module=load('active_quiet_summary',HERE/'summary.py')
summarize=summary_module.summarize


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',required=True,choices=['normal','scene']);parser.add_argument('--name',required=True);parser.add_argument('--registry-wait',type=int,default=300)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--compile-probe',action='store_true');group.add_argument('--probe-build',type=Path)
    args=parser.parse_args()
    assert __debug__ and args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
    folder=r.E/args.name;assert not folder.exists(),'Keep prior evidence'
    record=dict(version=VERSION,options=options(args.name,args.mode),diagnosticOnly=True,deployed=False)
    with m.Registration(owner='ContinuousScene / visible native cache groups / 01a13816',purpose=args.name,
            run_dir=m.RUNTIME,evidence=folder,resource='game',wait=args.registry_wait) as lease:
        try:
            assert not m.air_pids(),'Other AIR remains untouched'
            memory=control.memory_gate()
            baseline,scripts,compiler,fixture=r.baseline(),runner_inputs(),support.compiler_inputs(),fixture_inputs()
            runtime=reference.runtime_inputs();assert len(baseline)==526 and len(runtime)==13
            for key,digest in PINS.items():assert baseline[key]==digest,key
            record.update(baseline=baseline,runnerInputs=scripts,compilerInputs=compiler,fixtureInputs=fixture,runtimeInputs=runtime,memoryBefore=memory)
            path=compile_probe(lease,baseline,scripts,compiler,fixture) if args.compile_probe else args.probe_build.resolve()
            probe=verify_probe(path,baseline,scripts,compiler,fixture)
            m.prepare();shutil.copy2(probe['probePath'],m.RUNTIME/base.PROBE_PATH)
            for key,digest in baseline.items():
                if key not in ('application.xml','mods/loader-manifest.txt'):assert r.sha(m.RUNTIME/key)==digest,key
            assert baseline==r.baseline() and scripts==runner_inputs() and runtime==reference.runtime_inputs()
            record.update(probeBuildPath=str(path),probeSHA256=probe['probeSHA256'],memoryBeforeAir=control.memory_gate())
            run_error=None
            try:m.run_owned(m.parse_args(record['options']),lease)
            except BaseException as error:
                run_error=error;record.update(executionError=repr(error),executionTraceback=traceback.format_exc())
            finally:
                if folder.exists():
                    r.save(folder/'probe-build.json',probe);r.save(folder/'runner-inputs.json',record)
            assert baseline==r.baseline() and scripts==runner_inputs() and compiler==support.compiler_inputs()
            assert fixture==fixture_inputs() and runtime==reference.runtime_inputs()
            verify_probe(path,baseline,scripts,compiler,fixture)
            if not (folder/'storage/result.json').is_file():
                if run_error:raise run_error
                raise RuntimeError('No retained result; original process evidence preserved')
            raw,actual=reference.read_retained_result(folder)
            for key,digest in baseline.items():
                if key not in ('application.xml','mods/loader-manifest.txt'):assert actual[key]==digest,key
            assert actual[base.PROBE_PATH]==probe['probeSHA256']
            policy=r.read(folder/'process-policy.json')
            assert policy['desktopPolicy']=='private' and not policy['performanceEligible']
            assert not policy.get('otherAirProcessIds') and not policy.get('memoryAbort') and not policy.get('runFailure')
            summary=summarize(raw)
            summary.update(resultSHA256=r.sha(folder/'storage/result.json'),probeSHA256=probe['probeSHA256'],inputsUnchanged=True,runtimeInputsUnchanged=True)
            r.save(folder/'summary.json',summary)
            if run_error:raise run_error
            lease.outcome='passed';lease.note='1920 active quiet native/cached camera intervals; no deployment'
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
