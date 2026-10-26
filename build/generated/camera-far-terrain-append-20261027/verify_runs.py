"""Retain the failed static-set test and independently audit the append-aware run."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;MOD=HERE.parents[2];GAME=MOD.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def read(p):return json.loads(p.read_text('utf-8-sig'))
rows=[]
for name in ('camera-far-terrain-detach-20261027','camera-far-terrain-append-20261027'):
    folder=MOD/'knowledge/experiments/evidence'/(name+'-r1');recipe=HERE.parent/name
    rec=read(folder/'runner-inputs.json');probe=read(folder/'probe-build.json');raw=read(folder/'storage/result.json')
    t=raw['cameraRaster'];policy=read(folder/'process-policy.json')
    assert len(rec['baseline'])==526 and len(rec['runtimeInputs'])==13
    for path,digest in rec['baseline'].items():assert sha(GAME/path)==digest,path
    for group in ('runnerInputs','compilerInputs','fixtureInputs'):
        for path,digest in rec[group].items():assert sha(Path(path))==digest,(group,path)
    for path,digest in rec['runtimeInputs'].items():assert sha(GAME/path)==digest,path
    assert len(probe['frozenSourceSHA256'])==86
    for path,digest in probe['frozenSourceSHA256'].items():assert sha(Path(probe['frozenSourcePath'])/path)==digest,path
    assert sha(Path(probe['probePath']))==probe['probeSHA256']
    assert policy['desktopPolicy']=='private' and not policy['performanceEligible']
    assert not any(policy.get(k) for k in ('otherAirProcessIds','memoryAbort','runFailure'))
    assert t['pixelBitmapsCreated']==t['pixelBitmapsDisposed'] and t['cleanup']['pendingOwnedBitmaps']==0
    row=dict(name=name,resultSHA256=sha(folder/'storage/result.json'),probeSHA256=probe['probeSHA256'],
        inputsUnchanged=True,pid=policy['pid'],samples=len(t['framesMs']),selection=t['rootSelection'],
        capturesDisposed=t['pixelBitmapsDisposed'],cleanup=t['cleanup'],errors=t['errors'])
    if 'detach-' in name:
        assert not raw['ok'] and not t['passed'] and not t['framesMs']
        assert t['errors']==['Prepared surface set changed','Cleanup failed']
        assert not t['cleanup']['restored'] and t['cleanup']['terrainRestored']
        assert t['rootSelection']['transitionWrites']==t['rootSelection']['selected']*2==408
        assert t['pixels'][0]['conditions'][0]['changed']['equal'] and t['pixels'][0]['conditions'][0]['restored']['equal']
        assert t['pixelBitmapsDisposed']==28
        row['originalFailureSHA256']=sha(folder/'runner-failure.json')
        row['originalFailureRetained']=True
    else:
        spec=importlib.util.spec_from_file_location('far_terrain_append_review',recipe/'run.py')
        runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
        summary=runner.summarize(raw);saved=read(folder/'summary.json')
        assert all(saved[k]==v for k,v in summary.items())
        assert t['cleanup']['restored'] and not t['errors'] and len(t['framesMs'])==480
        row.update(arms=summary['arms'],pairs=summary['pairs'],summarySHA256=sha(folder/'summary.json'))
    rows.append(row)
out=dict(complete=True,gameRuns=rows,diagnosticOnly=True,gameplayAcceptance=False,deployed=False)
path=HERE/'runs-review.json';assert not path.exists();path.write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(dict(review=str(path),runs=[dict(name=r['name'],samples=r['samples'],pid=r['pid']) for r in rows]),ensure_ascii=False))
