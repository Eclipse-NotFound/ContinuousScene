"""Read-only public-state comparison and changed-pixel node association."""
from collections import Counter
from pathlib import Path
import json
import sys
import numpy as np
from PIL import Image

folder=Path(sys.argv[1]).resolve()
raw=json.loads((folder/'storage/result.json').read_text('utf-8-sig'))
trial=raw['cameraRaster']
snapshots=trial['nodeSnapshots']
original=snapshots[0]
before={row['id']:row for row in original['nodes']}
comparisons=[]
for snapshot in snapshots[1:]:
    current={row['id']:row for row in snapshot['nodes']}
    changes=[]
    for key in sorted(before.keys()|current.keys()):
        a,b=before.get(key),current.get(key)
        if a!=b:
            fields={name:[a.get(name),b.get(name)] for name in a.keys()|b.keys() if a.get(name)!=b.get(name)} if a and b else {'presence':[bool(a),bool(b)]}
            changes.append(dict(id=key,className=(a or b)['className'],path=(a or b)['path'],changes=fields))
    comparisons.append(dict(label=snapshot['label'],changedNodes=len(changes),changes=changes))
pics=folder/'storage/display-pixels'
a=np.asarray(Image.open(pics/'original-0-2.png').convert('RGBA'),dtype=np.int16)
b=np.asarray(Image.open(pics/'restored-0-2.png').convert('RGBA'),dtype=np.int16)
delta=np.abs(a-b);changed=np.any(delta,axis=2)
associations=[]
for node in original['nodes']:
    bounds=node['bounds'];x,y=bounds['x'],bounds['y'];w,h=bounds['width'],bounds['height']
    left,top=max(0,int(np.floor(x))),max(0,int(np.floor(y)))
    right,bottom=min(a.shape[1],int(np.ceil(x+w))),min(a.shape[0],int(np.ceil(y+h)))
    if right<=left or bottom<=top:continue
    hits=int(changed[top:bottom,left:right].sum())
    if hits:
        associations.append(dict(id=node['id'],path=node['path'],className=node['className'],bounds=bounds,
            changedPixelsInBounds=hits,area=(right-left)*(bottom-top),blend=node['blend'],cache=node['cache'],filters=node['filters'],
            bitmap=node.get('bitmap'),text=node.get('text'),clip=node.get('clip')))
result=dict(nativeRepeat=trial['nativeRepeat'],errors=trial['errors'],snapshotCount=len(snapshots),
    publicComparisons=comparisons,rootsByLayer=dict(Counter(str(r['layer']) for r in original['roots'])),
    rootsByClass=dict(Counter(r['className'] for r in original['roots'])),
    nodesByClass=dict(Counter(r['className'] for r in original['nodes'])),
    cached=sum(n['cache'] for n in original['nodes']),filtered=sum(bool(n['filters']) for n in original['nodes']),
    textNodes=[n for n in original['nodes'] if 'text' in n],
    changedPixels=int(changed.sum()),maxRGB=int(delta[:,:,:3].max()),maxAlpha=int(delta[:,:,3].max()),
    associations=sorted(associations,key=lambda n:(n['area'],-n['changedPixelsInBounds'])),
    limits=['Geometric overlap does not prove which node caused a pixel difference.',
            'Public states and bitmap hashes do not expose internal renderer caches.'])
(folder/'display-state-analysis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps({k:result[k] for k in ('nativeRepeat','errors','rootsByLayer','rootsByClass','nodesByClass','cached','filtered','changedPixels','maxRGB','maxAlpha')},ensure_ascii=False))
print(json.dumps(dict(comparisons=[dict(label=c['label'],changedNodes=c['changedNodes'],changes=c['changes'][:3]) for c in comparisons],
    overlap=result['associations'][:30],textNodes=[dict(path=n['path'],text=n['text'],cache=n['cache'],visible=n['visible']) for n in result['textNodes']]),ensure_ascii=False))
