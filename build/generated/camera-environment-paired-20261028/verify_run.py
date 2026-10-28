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
    silence_source=HERE.parent/'camera-live-current-silent-20261028/silence.py'
    assert driver.SILENCE_SOURCE==silence_source and Path(driver.silence.__file__)==silence_source
    assert record['nativeSilenceSource']==dict(path=str(silence_source),sha256=sha(silence_source))
    assert record['runnerInputs'][str(silence_source)]==sha(silence_source)
    assert probe['runnerInputs'][str(silence_source)]==sha(silence_source)
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
    host_root=Path(record['hostRoot'])
    assert host_root in [HERE,HERE.parent/'camera-environment-paired-binary-20261028']
    host=read(host_root/'build.json');audit=read(host_root/'audit-proof.json')
    assert record['hostProducer']==host['version']
    assert host['diagnosticOnly'] and audit['diagnosticOnly'] and not host['deployed'] and not audit['deployed']
    assert host['candidate']==audit['candidateSHA256']==expected['pfe.swf']==sha(host_root/'pfe.swf')
    assert host['audit']==sha(host_root/'audit-proof.json') and audit['passed'] and audit['unchangedBodies']==5770 and audit['unchangedClasses']==1016
    assert audit['changed']==['fe.graph.Grafon::0:1:sceneNativeEnvironment']
    for path,digest in host['sourceInputs'].items():assert sha(Path(path))==digest,path
    policy=read(folder/'process-policy.json');loader=read(folder/'loader-check.json')
    assert policy['desktopPolicy']=='private' and not policy['performanceEligible']
    assert not any(policy.get(k) for k in ['otherAirProcessIds','memoryAbort','runFailure'])
    assert len(record['nativeSilence'])==1
    seeded=record['nativeSilence'][0]
    assert seeded['applicationID']==policy['appId'] and seeded['writeOnce'] and seeded['decodedAfterWrite']
    assert seeded['nativeSndOnly'] and seeded['allAudioMuted'] is False
    assert seeded['sha256']=='12CC4E62A459EAFDA8463F800F8E1E8388CC392AC6A5BDD882D14C572435B257'
    native_audio=driver.silence.verify_retained(folder/'storage/#SharedObjects/pfe.swf/config.sol')
    assert native_audio==seeded['snd']
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
        nativeCameraScheduling=summary['nativeCameraScheduling'],minimumAvailableCommit=policy['minimumAvailableCommit'],nativeAudioSettings=native_audio,
        limitation='Same-instance quiet active simulation; common selector and all intervals retained, no real combat or monitor-FPS acceptance.')
    result['movingMeanChangePercent']=(summary['moving']['cached']['mean']/summary['moving']['native']['mean']-1)*100
    args.out.write_text(json.dumps(result,indent=2),'utf-8')
    print(json.dumps(dict(verified=True,sha256=sha(args.out),moving=result['moving'],changePercent=result['movingMeanChangePercent'])),flush=True)

if __name__=='__main__':main()
