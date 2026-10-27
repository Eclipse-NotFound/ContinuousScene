"""RV candidate overrides are explicit; failed visual checks remain failed."""
from pathlib import Path
import hashlib,importlib.util,json,math,statistics
HERE=Path(__file__).resolve().parent;MOD=HERE.parents[2]
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def metric(v):
    a=sorted(v);return dict(count=len(a),mean=statistics.mean(a),median=statistics.median(a),p95=a[math.ceil(len(a)*.95)-1],maximum=max(a),over100=sum(x>100 for x in a))
def verify(name):
    recipe=HERE.parent/name;folder=MOD/'knowledge/experiments/evidence'/(name+'-r1')
    spec=importlib.util.spec_from_file_location('review_'+name.replace('-','_'),recipe/'run.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    r=read(folder/'runner-inputs.json');raw=read(folder/'storage/result.json');b=read(folder/'probe-build.json');rv=r['rvBuild']
    assert r['baseline']==m.r.baseline() and len(r['baseline'])==526
    assert r['runtimeInputs']==m.reference.runtime_inputs() and len(r['runtimeInputs'])==13
    assert r['runnerInputs']==m.runner_inputs() and r['fixtureInputs']==m.fixture_inputs() and r['compilerInputs']==m.support.compiler_inputs()
    verified=m.verify_probe(Path(r['probeBuildPath']),r['baseline'],r['runnerInputs'],r['compilerInputs'],r['fixtureInputs'])
    assert verified==b and len(b['frozenSourceSHA256'])==86
    m.rv_build.verify(rv,m.r,m.base)
    assert rv['sources']==m.base.tree_hashes(recipe/'rv-src') and len(rv['sources'])==6
    actual={p.replace('\\','/'):v for p,v in read(folder/'inputs.json').items()}
    for p,digest in r['baseline'].items():
        if p not in ['application.xml','mods/loader-manifest.txt','mods/RealisticVision/release/RealisticVisionMod.swf']:assert actual[p]==digest,p
    assert actual['mods/RealisticVision/release/RealisticVisionMod.swf']==rv['sha256']
    assert actual['mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf']==b['probeSHA256']==r['probeSHA256']
    policy=read(folder/'process-policy.json');loader=read(folder/'loader-check.json')
    assert policy['desktopPolicy']=='private' and not policy['performanceEligible']
    assert not any(policy.get(k) for k in ['otherAirProcessIds','memoryAbort','runFailure'])
    assert len(loader['sessions'])==1 and all(loader['loaded'].values())
    assert r['memoryBeforeAir']['availableCommit']>=4*1024**3 and r['memoryBeforeAir']['availablePhysical']>=2*1024**3
    passed=(folder/'summary.json').exists()
    result=dict(name=name,inputClosurePassed=True,originalRunPassed=passed,pid=policy['pid'],frozen=Path(b['frozenSourcePath']).parent.name,
        probeSHA256=b['probeSHA256'],resultSHA256=sha(folder/'storage/result.json'),rvCandidateSHA256=rv['sha256'],rvFrozen=Path(rv['source']).parent.name,
        rvBefore=raw.get('rvReaderBefore'),rvAfter=raw.get('rvReaderAfter'),pixels=raw.get('combatAtlasPixels'),deployed=False)
    if passed:
        assert not (folder/'runner-failure.json').exists()
        summary=m.summarize(raw);summary.update(resultSHA256=result['resultSHA256'],probeSHA256=b['probeSHA256'],inputsUnchanged=True,runtimeInputsUnchanged=True,rvCandidateSHA256=rv['sha256'])
        assert summary==read(folder/'summary.json');result['summary']=summary
    else:
        failed=read(folder/'runner-failure.json');assert not failed['complete']
        result.update(failurePreserved=True,measurementAccepted=False,failedChecks=[x for x in raw['assertions'] if not x['ok']],error=raw['error'])
    assert len(raw['samples'])==20
    result['diagnosticGrouped']={mode:metric([v for i,s in enumerate(raw['samples']) if (i%4 in (1,2))==(mode=='atlas') for v in s['continuousFramesMs']]) for mode in ['native','atlas']}
    assert all(v['count']==600 for v in result['diagnosticGrouped'].values())
    return result
def main():
    out=HERE/'review.json';assert not out.exists(),'Preserve prior audit'
    rows=[verify(n) for n in ['camera-persistent-rv-20261027','camera-persistent-rv-pixels-20261027']]
    out.write_text(json.dumps(dict(runs=rows,deployed=False,goalComplete=False),ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps(dict(sha256=sha(out),runs=[{k:r[k] for k in ['name','originalRunPassed','pid','probeSHA256','resultSHA256','rvCandidateSHA256','diagnosticGrouped']} for r in rows]),ensure_ascii=False))
if __name__=='__main__':main()
