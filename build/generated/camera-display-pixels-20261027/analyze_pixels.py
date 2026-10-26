"""Read-only comparison of retained restoration images; no image edits."""
from pathlib import Path
import hashlib
import json
from PIL import Image
import numpy as np
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
EVIDENCE=ROOT/'mods/ContinuousScene/knowledge/experiments/evidence/camera-display-pixels-20261027-r1/storage/display-pixels'
paths=[EVIDENCE/'original-0-2.png',EVIDENCE/'restored-0-2.png']
a,b=[np.asarray(Image.open(p).convert('RGBA')).astype(np.int16) for p in paths]
mask=np.any(a!=b,axis=2)
ys,xs=np.where(mask)
remaining=set((int(y),int(x)) for y,x in zip(ys,xs))
components=[]
while remaining:
    seed=remaining.pop();stack=[seed];points=[seed]
    while stack:
        y,x=stack.pop()
        for ny,nx in ((y-1,x),(y+1,x),(y,x-1),(y,x+1),(y-1,x-1),(y+1,x+1),(y-1,x+1),(y+1,x-1)):
            if (ny,nx) in remaining:
                remaining.remove((ny,nx));stack.append((ny,nx));points.append((ny,nx))
    py,px=zip(*points)
    components.append(dict(pixels=len(points),bounds=[min(px),min(py),max(px)+1,max(py)+1],
        maxRGB=int(np.abs(a[list(py),list(px),:3]-b[list(py),list(px),:3]).max())))
components.sort(key=lambda row:row['pixels'],reverse=True)
result=dict(inputs={str(p):hashlib.sha256(p.read_bytes()).hexdigest().upper() for p in paths},
    pixels=int(mask.sum()),bounds=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)],
    maxAlpha=int(np.abs(a[:,:,3]-b[:,:,3]).max()),
    maxRGB=int(np.abs(a[:,:,:3]-b[:,:,:3]).max()),components=components,
    note='Pixel differences only; component geometry alone does not establish a runtime cause.')
out=HERE/'pixel-analysis.json'
assert not out.exists(),'Preserve existing analysis'
out.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(dict(pixels=result['pixels'],bounds=result['bounds'],maxAlpha=result['maxAlpha'],
    maxRGB=result['maxRGB'],largest=components[:12]),ensure_ascii=False))

