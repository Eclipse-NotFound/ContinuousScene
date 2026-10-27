"""Use the same frozen allocation probe with one exact isolated host variant."""
from pathlib import Path
import argparse,importlib.util,json,shutil,sys,traceback
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
CANDIDATE=HERE.parent/'camera-environment-keycache-20261027'
def load(name,p):
    sp=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
source=load('environment_variant_fixture',HERE/'run.py')
r,m=source.r,source.m
PROBE=None
def inputs():return dict(source.runner_inputs(),**{str(p):r.sha(p) for p in [HERE/'run_variant.py',CANDIDATE/'source-equivalent.as.inc',CANDIDATE.parent/'camera-environment-clamp-20261027/audit.py',CANDIDATE/'build.py',CANDIDATE/'audit.py',HERE/'README.md',CANDIDATE/'build.json',CANDIDATE/'audit-proof.json',PROBE]})
def main():
    global PROBE
    parser=argparse.ArgumentParser();parser.add_argument('--name',required=True);parser.add_argument('--host',choices=['base','cache'],required=True);parser.add_argument('--probe-build',type=Path,required=True);args=parser.parse_args();PROBE=args.probe_build.resolve()
    assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
    folder=r.E/args.name;assert not folder.exists()
    record=dict(version='scene-native-once-variant-1',hostVariant=args.host,diagnosticOnly=True,deployed=False)
    with m.Registration(owner='ContinuousScene / environment allocations / 01a13816',purpose=args.name,run_dir=m.RUNTIME,evidence=folder,resource='game',wait=300) as lease:
        try:
            assert not m.air_pids();memory=source.control.memory_gate()
            baseline=r.baseline();scripts=inputs();compiler=source.support.compiler_inputs();fixture=source.fixture_inputs();runtime=source.reference.runtime_inputs()
            assert len(baseline)==526 and len(runtime)==13
            for key,digest in source.PINS.items():assert baseline[key]==digest,key
            build=r.read(CANDIDATE/'build.json');audit=r.read(CANDIDATE/'audit-proof.json')
            assert build['base']==baseline['pfe.swf'] and build['audit']==r.sha(CANDIDATE/'audit-proof.json')
            assert audit['passed'] and audit['changed']==['fe.graph.Grafon::0:1:sceneNativeEnvironment'] and audit['unchangedBodies']==5770
            assert audit['candidateSHA256']==build['candidate']==r.sha(CANDIDATE/'pfe.swf')
            probe=source.verify_probe(PROBE,baseline,source.runner_inputs(),compiler,fixture)
            expected=dict(baseline)
            if args.host=='cache':expected['pfe.swf']=build['candidate']
            record.update(baseline=baseline,expectedRuntime=expected,runnerInputs=scripts,compilerInputs=compiler,fixtureInputs=fixture,runtimeInputs=runtime,
                memoryBefore=memory,probeBuildPath=str(PROBE),probeSHA256=probe['probeSHA256'],candidateBuild=build)
            m.prepare();shutil.copy2(probe['probePath'],m.RUNTIME/source.base.PROBE_PATH)
            if args.host=='cache':shutil.copy2(CANDIDATE/'pfe.swf',m.RUNTIME/'pfe.swf')
            for key,digest in expected.items():
                if key not in ['application.xml','mods/loader-manifest.txt']:assert r.sha(m.RUNTIME/key)==digest,key
            assert baseline==r.baseline() and scripts==inputs() and runtime==source.reference.runtime_inputs()
            record['memoryBeforeAir']=source.control.memory_gate()
            options=source.options(args.name,'scene',3,3);record['options']=options
            run_error=None
            try:m.run_owned(m.parse_args(options),lease)
            except BaseException as error:run_error=error;record['executionError']=repr(error)
            finally:
                record['startupResourcePolicies']=source.STARTUP_POLICIES
                if folder.exists():r.save(folder/'runner-inputs.json',record);r.save(folder/'probe-build.json',probe)
            assert baseline==r.baseline() and scripts==inputs() and compiler==source.support.compiler_inputs() and fixture==source.fixture_inputs() and runtime==source.reference.runtime_inputs()
            raw,actual=source.reference.read_retained_result(folder)
            for key,digest in expected.items():
                if key not in ['application.xml','mods/loader-manifest.txt']:assert actual[key]==digest,key
            assert actual[source.base.PROBE_PATH]==probe['probeSHA256']
            policy=r.read(folder/'process-policy.json');assert not any(policy.get(k) for k in ['otherAirProcessIds','memoryAbort','runFailure'])
            assert policy['desktopPolicy']=='private' and not policy['performanceEligible']
            startup=source.STARTUP_POLICIES;assert len(startup)==1 and startup[0]['pid']==policy['pid']
            applied=startup[0]['policy'];assert not applied['errors'] and not applied['after']['errors']
            assert applied['after']['cpuPriorityClass']==32 and applied['after']['memoryPriority']==5 and applied['after']['powerThrottling']['highQoS']
            summary=source.summarize(raw)
            summary.update(resultSHA256=r.sha(folder/'storage/result.json'),probeSHA256=probe['probeSHA256'],hostSHA256=expected['pfe.swf'],inputsUnchanged=True)
            r.save(folder/'summary.json',summary)
            if run_error:raise run_error
            checks=raw['cameraRaster']['environmentChecks']
            assert checks['cachePresent']==(args.host=='cache')
            lease.outcome='passed';lease.note='Sampler-free camera route and environment checks complete; no deployment'
            print(json.dumps(dict(name=args.name,complete=True,arms=summary['arms'],environmentCases=len(checks['cases']),cachePresent=checks['cachePresent'])),flush=True)
        except BaseException as error:
            folder.mkdir(parents=True,exist_ok=True);r.save(folder/'runner-failure.json',dict(record,error=repr(error),traceback=traceback.format_exc(),complete=False,deployed=False))
            lease.outcome='failed';lease.note=repr(error);raise
if __name__=='__main__':main()
