"""Independent retained-input and full-clock review of the diagnostic A/B run."""
from pathlib import Path
import argparse,hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent;MOD=HERE.parents[2];ROOT=MOD.parents[1]

def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def load(name,p):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--name',required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    assert not args.out.exists()
    folder=MOD/'knowledge/experiments/evidence'/args.name
    assert not (folder/'runner-failure.json').exists()
    record=read(folder/'runner-inputs.json');probe=read(folder/'probe-build.json');raw=read(folder/'storage/result.json')
    assert len(record['baseline'])==526 and len(record['runtimeInputs'])==13 and len(probe['frozenSourceSHA256'])==86
    for field in ['baseline','runtimeInputs']:
        for path,digest in record[field].items():assert sha(ROOT/path)==digest,(field,path)
    for field in ['runnerInputs','compilerInputs','fixtureInputs','hostInputs']:
        for path,digest in record[field].items():assert sha(Path(path))==digest,(field,path)
    driver=load('paired_retained_driver',HERE/'run.py')
    verified=driver.verify_probe(Path(record['probeBuildPath']),record['baseline'],record['runnerInputs'],record['compilerInputs'],record['fixtureInputs'])
    assert verified==probe and record['probeSHA256']==probe['probeSHA256']
    if 'readinessReceipt' in record:
        receipt=record['readinessReceipt'];assert receipt['ready'] and sha(Path(receipt['path']))==receipt['sha256']
        readiness=read(Path(receipt['path']));recent=readiness['samples'][-3:]
        assert readiness['ready'] and readiness['stableChecks']>=3 and not readiness['launchedAir']
        assert len(recent)==3 and recent[-1]['elapsed']-recent[0]['elapsed']>=9.9
        assert all(s['good'] and not s['air'] and s['memory']['availableCommit']>=5*1024**3 and s['memory']['availablePhysical']>=2*1024**3 for s in recent)
    expected=record['expectedRuntime'];assert [p for p in expected if expected[p]!=record['baseline'][p]]==['pfe.swf']
    actual={p.replace('\\','/'):digest for p,digest in read(folder/'inputs.json').items()}
    for path,digest in expected.items():
        if path not in ['application.xml','mods/loader-manifest.txt']:assert actual[path]==digest,path
    assert actual[driver.base.PROBE_PATH]==probe['probeSHA256']
    host=read(HERE/'build.json');audit=read(HERE/'audit-proof.json')
    assert host['diagnosticOnly'] and audit['diagnosticOnly'] and not host['deployed'] and not audit['deployed']
    assert host['candidate']==audit['candidateSHA256']==expected['pfe.swf']==sha(HERE/'pfe.swf')
    assert host['audit']==sha(HERE/'audit-proof.json') and audit['passed'] and audit['unchangedBodies']==5770 and audit['unchangedClasses']==1016
    assert audit['changed']==['fe.graph.Grafon::0:1:sceneNativeEnvironment']
    for path,digest in host['sourceInputs'].items():assert sha(Path(path))==digest,path
    policy=read(folder/'process-policy.json');loader=read(folder/'loader-check.json')
    assert policy['desktopPolicy']=='private' and not policy['performanceEligible']
    assert not any(policy.get(k) for k in ['otherAirProcessIds','memoryAbort','runFailure'])
    assert len(loader['sessions'])==1 and all(loader['loaded'].values())
    assert record['memoryBeforeAir']['availableCommit']>=4*1024**3 and record['memoryBeforeAir']['availablePhysical']>=2*1024**3
    startup=record['startupResourcePolicies'];assert len(startup)==1 and startup[0]['pid']==policy['pid']
    applied=startup[0]['policy'];assert applied['requested']=='test' and not applied['errors'] and not applied['after']['errors']
    assert applied['after']['cpuPriorityClass']==32 and applied['after']['memoryPriority']==5 and applied['after']['powerThrottling']['highQoS']
    summary=load('paired_retained_summary',HERE/'summary.py').summarize(raw)
    summary.update(resultSHA256=sha(folder/'storage/result.json'),probeSHA256=probe['probeSHA256'],inputsUnchanged=True,runtimeInputsUnchanged=True)
    assert summary==read(folder/'summary.json')
    result=dict(verified=True,name=args.name,diagnosticOnly=True,deployed=False,pid=policy['pid'],hostSHA256=expected['pfe.swf'],
        probeSHA256=probe['probeSHA256'],resultSHA256=summary['resultSHA256'],moving=summary['moving'],arms=summary['arms'],pairs=summary['pairs'],
        nativeCameraScheduling=summary['nativeCameraScheduling'],minimumAvailableCommit=policy['minimumAvailableCommit'],
        limitation='Same-instance quiet active simulation; common selector and all intervals retained, no real combat or monitor-FPS acceptance.')
    result['movingMeanChangePercent']=(summary['moving']['cached']['mean']/summary['moving']['native']['mean']-1)*100
    args.out.write_text(json.dumps(result,indent=2),'utf-8')
    print(json.dumps(dict(verified=True,sha256=sha(args.out),moving=result['moving'],changePercent=result['movingMeanChangePercent'])),flush=True)

if __name__=='__main__':main()
