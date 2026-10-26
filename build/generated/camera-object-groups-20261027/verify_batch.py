"""Final read-only fingerprints, resources and outcomes for the camera batch."""
from pathlib import Path
import hashlib
import json
HERE=Path(__file__).resolve().parent
MOD=HERE.parents[2];GAME=MOD.parents[1];E=MOD/'knowledge/experiments/evidence'
NAMES=['camera-roles-alpha-20261027-r1','camera-upper-alpha-20261027-r1',
       'camera-native-roundtrip-20261027-r1','camera-native-roundtrip-v2-20261027-r1',
       'camera-native-roundtrip-v3-20261027-r1','camera-objects-warm-alpha-20261027-r1',
       'camera-stage3d-terrain-attribution-20261027-r1','camera-stage3d-static-terrain-20261027-r1',
       'camera-native-light-attribution-20261027-r1']
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
rows=[]
for name in NAMES:
    folder=E/name;rec=read(folder/'runner-inputs.json');probe=read(folder/'probe-build.json')
    raw=read(folder/'storage/result.json');policy=read(folder/'process-policy.json');t=raw['cameraRaster']
    assert len(rec['baseline'])==526 and len(rec['runtimeInputs'])==13
    for k,v in rec['baseline'].items():assert sha(GAME/k)==v,k
    for group in ('runnerInputs','compilerInputs','fixtureInputs'):
        for k,v in rec[group].items():assert sha(Path(k))==v,(group,k)
    for k,v in rec['runtimeInputs'].items():assert sha(GAME/k)==v,k
    frozen=Path(probe['frozenSourcePath'])
    for k,v in probe['frozenSourceSHA256'].items():assert sha(frozen/k)==v,k
    assert sha(Path(probe['probePath']))==probe['probeSHA256']
    assert t['cleanup']['restored'] and not t['cleanup']['errors'] and t['cleanup']['pendingOwnedBitmaps']==0
    assert t['pixelBitmapsCreated']==t['pixelBitmapsDisposed']
    p=t['cleanup'].get('presentation')
    if p and 'texturesCreated' in p:
        assert p['texturesCreated']==p['texturesDisposed'] and p['contextCreates']==p['contextDisposals'] and p['gpuBytes']==0
    assert policy['desktopPolicy']=='private' and not policy.get('otherAirProcessIds')
    assert not policy.get('memoryAbort') and not policy.get('runFailure')
    rows.append(dict(name=name,rawOK=raw['ok'],errors=t['errors'],frames=len(t['framesMs']),
        originalRunnerFailed=(folder/'runner-failure.json').exists(),pid=policy['pid'],
        screenshotsDisposed=t['pixelBitmapsDisposed'],formalFiles=526,runtimeFiles=13,
        frozenSourceFiles=len(probe['frozenSourceSHA256']),inputsUnchanged=True,scalarCleanupPassed=True,
        probeSHA256=probe['probeSHA256'],resultSHA256=sha(folder/'storage/result.json'),
        performanceAcceptance=False,deployed=False))
solo=MOD/'build/generated/alpha-restore-repro-20261027/runs/786977a376d1419984e203ff64ec0c26/runner-result.json'
s=read(solo)
assert s['diagnosticCompleted'] and s['inputChanges']==[] and s['cleanup']['ownedHandlesClosed'] and s['cleanup']['exitCode']==0
for k,v in s['inputs'].items():assert sha(Path(k))==v,k
assert len(s['airResult']['cases'])==16 and all(row['restored']['equal'] for row in s['airResult']['cases'])
out=dict(complete=True,gameRuns=rows,synthetic=dict(path=str(solo),resultSHA256=sha(solo),
    cases=16,restorationFailures=0,allocations=s['airResult']['allocations'],disposals=s['airResult']['disposals'],
    inputsUnchanged=True),limits=['No product change or deployment; unsuccessful checks remain unsuccessful.'])
path=HERE/'batch-review.json';assert not path.exists();path.write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(out,ensure_ascii=False))
