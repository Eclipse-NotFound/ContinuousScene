"""Post-hoc version-constant correction only; original failed recipe/result preserved."""
from pathlib import Path
import hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent;MOD=HERE.parents[2];ROOT=MOD.parents[1]
F=MOD/'knowledge/experiments/evidence/camera-persistent-combat-imports-20261027-r1'
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def main():
    r=read(F/'runner-inputs.json');b=read(F/'probe-build.json');raw=read(F/'storage/result.json');failed=read(F/'runner-failure.json')
    assert not failed['complete'] and '<pool-atlas-summary>' in failed['traceback'] and not (F/'summary.json').exists()
    assert len(r['baseline'])==526 and len(r['runtimeInputs'])==13
    for key in ['baseline','runtimeInputs']:
        for p,d in r[key].items():assert sha(ROOT/p)==d,p
    for key in ['runnerInputs','fixtureInputs','compilerInputs']:
        for p,d in r[key].items():assert sha(Path(p))==d,p
    assert len(b['frozenSourceSHA256'])==86
    for p,d in b['frozenSourceSHA256'].items():assert sha(Path(b['frozenSourcePath'])/p)==d,p
    assert sha(Path(b['probePath']))==b['probeSHA256']==r['probeSHA256']
    for p,k in [('sourceOrigin','sourceOriginSHA256'),('configPath','configSHA256')]:assert sha(Path(b[p]))==b[k]
    actual={p.replace('\\','/'):d for p,d in read(F/'inputs.json').items()}
    for p,d in r['baseline'].items():
        if p not in ['application.xml','mods/loader-manifest.txt']:assert actual[p]==d,p
    assert actual['mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf']==b['probeSHA256']
    policy=read(F/'process-policy.json');loader=read(F/'loader-check.json')
    assert policy['desktopPolicy']=='private' and not policy['performanceEligible']
    assert not any(policy.get(k) for k in ['otherAirProcessIds','memoryAbort','runFailure'])
    assert len(loader['sessions'])==1 and all(loader['loaded'].values())
    assert r['memoryBeforeAir']['availableCommit']>=4*1024**3 and r['memoryBeforeAir']['availablePhysical']>=2*1024**3
    sp=importlib.util.spec_from_file_location('combat_failed_summary_review',HERE/'summary.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
    assert m.base.pool_summary.__globals__ is m.base.scope
    assert m.VERSION=='camera-persistent-combat-imports-1'
    assert m.base.scope['VERSION']=='camera-atlas-merged-combat-1'
    m.base.scope['VERSION']='camera-persistent-combat-imports-1'
    # No timing threshold, row, source, pixel, workload or cleanup rule changes.
    summary=m.summarize(raw)
    result=dict(originalSummaryPassed=False,originalFailurePreserved=True,retainedChecksPassedAfterConstantCorrection=True,
        correction={'before':'camera-atlas-merged-combat-1','after':'camera-persistent-combat-imports-1','field':'pool_summary.__globals__[VERSION]'},
        sourceCount=86,frozen=Path(b['frozenSourcePath']).parent.name,probeSHA256=b['probeSHA256'],resultSHA256=sha(F/'storage/result.json'),pid=policy['pid'],
        summary=summary,deployed=False,gameplayAcceptance=False)
    out=HERE/'review.json';assert not out.exists(),'Preserve previous audit'
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps(dict(sha256=sha(out),originalSummaryPassed=False,retainedChecksPassed=True,grouped=summary['grouped'],qualification=summary['qualification']),ensure_ascii=False))
if __name__=='__main__':main()
