"""Preserve both unsuccessful scroll diagnostics and audit their untouched inputs."""
from pathlib import Path
import hashlib
import json
from PIL import Image
import numpy as np
HERE=Path(__file__).resolve().parent
MOD=HERE.parents[2];GAME=MOD.parents[1];E=MOD/'knowledge/experiments/evidence'
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
rows=[]
for name in ['camera-world-scroll-20261027-r1','camera-world-scroll-cached-20261027-r1']:
    folder=E/name;rec=read(folder/'runner-inputs.json');probe=read(folder/'probe-build.json')
    raw=read(folder/'storage/result.json');policy=read(folder/'process-policy.json');t=raw['cameraRaster']
    assert len(rec['baseline'])==526 and len(rec['runtimeInputs'])==13
    for k,v in rec['baseline'].items():assert sha(GAME/k)==v,k
    for group in ('runnerInputs','compilerInputs','fixtureInputs'):
        for k,v in rec[group].items():assert sha(Path(k))==v,(group,k)
    for k,v in rec['runtimeInputs'].items():assert sha(GAME/k)==v,k
    for k,v in probe['frozenSourceSHA256'].items():assert sha(Path(probe['frozenSourcePath'])/k)==v,k
    assert sha(Path(probe['probePath']))==probe['probeSHA256']
    assert not raw['ok'] and not t['passed'] and not t['framesMs']
    assert t['cleanup']['restored'] and not t['cleanup']['errors'] and t['cleanup']['pendingOwnedBitmaps']==0
    assert t['pixelBitmapsCreated']==t['pixelBitmapsDisposed']
    assert policy['desktopPolicy']=='private' and not policy.get('otherAirProcessIds') and not policy.get('memoryAbort') and not policy.get('runFailure')
    rows.append(dict(name=name,errors=t['errors'],pid=policy['pid'],resultSHA256=sha(folder/'storage/result.json'),
        probeSHA256=probe['probeSHA256'],capturesDisposed=t['pixelBitmapsDisposed'],frames=0,inputsUnchanged=True,deployed=False))
p=E/'camera-world-scroll-20261027-r1/storage/display-pixels'
a_path=p/'original-0-1.png';b_path=p/'suppressed-0-1.png'
a=np.array(Image.open(a_path).convert('RGBA')).astype(np.int16)
b=np.array(Image.open(b_path).convert('RGBA')).astype(np.int16)
d=np.abs(a-b);m=d[:,:,:3].max(axis=2)
yy,xx=np.where(m==3)
assert int(m.max())==3 and int(d[:,:,3].max())==0 and len(xx)==1
out=dict(complete=True,gameRuns=rows,pixels=dict(originalSHA256=sha(a_path),candidateSHA256=sha(b_path),
    different=int((m>0).sum()),atLeast2=int((m>=2).sum()),maxRGB=3,alphaDifference=0,locationsAt3=[[int(x),int(y)] for x,y in zip(xx,yy)]),
    limits=['Both original failures retained. No timing or gameplay performance claim.'])
path=HERE/'batch-review.json';assert not path.exists();path.write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(out,ensure_ascii=False))
