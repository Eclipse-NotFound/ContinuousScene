"""Immutable read-only review of current visibility experiments, including failures."""
from pathlib import Path
import hashlib
import json
HERE=Path(__file__).resolve().parent
MOD=HERE.parents[2];GAME=MOD.parents[1];E=MOD/'knowledge/experiments/evidence'
NAMES=['camera-world-alpha-visible-20261027-r1','camera-far-static-visibility-20261027-r1',
       'camera-far-static-warm-20261027-r1','camera-far-singleframe-20261027-r1',
       'camera-far-maskguard-20261027-r1','camera-object-alpha-visible-20261027-r1']
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
rows=[]
for name in NAMES:
    folder=E/name;rec=read(folder/'runner-inputs.json');probe=read(folder/'probe-build.json')
    raw=read(folder/'storage/result.json');policy=read(folder/'process-policy.json');trial=raw['cameraRaster']
    assert len(rec['baseline'])==526 and len(rec['runtimeInputs'])==13
    for k,v in rec['baseline'].items():assert sha(GAME/k)==v,k
    for group in ('runnerInputs','compilerInputs','fixtureInputs'):
        for k,v in rec[group].items():assert sha(Path(k))==v,(group,k)
    for k,v in rec['runtimeInputs'].items():assert sha(GAME/k)==v,k
    frozen=Path(probe['frozenSourcePath'])
    for k,v in probe['frozenSourceSHA256'].items():assert sha(frozen/k)==v,k
    assert sha(Path(probe['probePath']))==probe['probeSHA256']
    assert trial['pixelBitmapsCreated']==trial['pixelBitmapsDisposed'] and trial['cleanup']['pendingOwnedBitmaps']==0
    assert policy['desktopPolicy']=='private' and not policy.get('otherAirProcessIds')
    assert not policy.get('memoryAbort') and not policy.get('runFailure')
    summary_path=folder/'summary.json'
    summary=read(summary_path) if summary_path.exists() else None
    if summary:
        assert raw['ok'] and trial['passed'] and trial['cleanup']['restored'] and not trial['cleanup']['errors']
        assert summary['resultSHA256']==sha(folder/'storage/result.json') and summary['probeSHA256']==probe['probeSHA256']
    rows.append(dict(name=name,rawOK=raw['ok'],errors=trial['errors'],frames=len(trial['framesMs']),
        cleanup=trial['cleanup'],originalRunnerFailed=(folder/'runner-failure.json').exists(),pid=policy['pid'],
        screenshotsDisposed=trial['pixelBitmapsDisposed'],formalFiles=526,runtimeFiles=13,
        frozenSourceFiles=len(probe['frozenSourceSHA256']),inputsUnchanged=True,
        probeSHA256=probe['probeSHA256'],resultSHA256=sha(folder/'storage/result.json'),
        performanceAcceptance=False,deployed=False))
out=dict(complete=True,gameRuns=rows,limits=['Original failed checks retained; no deployment or gameplay acceptance.'])
path=HERE/'batch-review.json';assert not path.exists();path.write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(out,ensure_ascii=False))
