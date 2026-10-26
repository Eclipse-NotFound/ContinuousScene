"""Read-only final fingerprint review for this four-run investigation."""
from pathlib import Path
import hashlib
import json

HERE=Path(__file__).resolve().parent
MOD=HERE.parents[2]
GAME=MOD.parents[1]
EVIDENCE=MOD/'knowledge/experiments/evidence'
NAMES=['camera-display-state-20261027-r1','camera-display-settled-20261027-r1',
       'camera-alpha-trim-20261027-r1','camera-lower-objects-20261027-r1']

def read(path):return json.loads(path.read_text('utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest().upper()

results=[]
for name in NAMES:
    folder=EVIDENCE/name
    receipt=read(folder/'runner-inputs.json')
    probe=read(folder/'probe-build.json')
    raw=read(folder/'storage/result.json')
    policy=read(folder/'process-policy.json')
    assert len(receipt['baseline'])==526 and len(receipt['runtimeInputs'])==13
    for key,digest in receipt['baseline'].items():assert sha(GAME/key)==digest,key
    for group in ('runnerInputs','compilerInputs','fixtureInputs'):
        for key,digest in receipt[group].items():assert sha(Path(key))==digest,(group,key)
    for key,digest in receipt['runtimeInputs'].items():assert sha(GAME/key)==digest,key
    frozen=Path(probe['frozenSourcePath'])
    for key,digest in probe['frozenSourceSHA256'].items():assert sha(frozen/key)==digest,key
    assert sha(Path(probe['probePath']))==probe['probeSHA256']
    trial=raw['cameraRaster']
    assert trial['cleanup']['restored'] and not trial['cleanup']['errors']
    assert trial['cleanup']['pendingOwnedBitmaps']==0
    assert trial['pixelBitmapsCreated']==trial['pixelBitmapsDisposed']
    assert policy['desktopPolicy']=='private' and not policy.get('otherAirProcessIds')
    assert not policy.get('memoryAbort') and not policy.get('runFailure')
    results.append(dict(name=name,formalFiles=526,runtimeFiles=13,sourceFiles=len(probe['frozenSourceSHA256']),
        rawOK=raw['ok'],errors=trial['errors'],frames=len(trial['framesMs']),
        nativeRepeat=trial.get('nativeRepeat'),screenshotsDisposed=trial['pixelBitmapsDisposed'],
        pid=policy['pid'],probeSHA256=probe['probeSHA256'],resultSHA256=sha(folder/'storage/result.json'),
        inputsUnchanged=True,scalarCleanupPassed=True,performanceAcceptance=False,deployed=False))
output=HERE/'batch-review.json'
assert not output.exists(),'Keep earlier review'
output.write_text(json.dumps(dict(complete=True,runs=results),ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(results,ensure_ascii=False))
