"""Read-only comparison; incomplete metadata remains explicitly incomplete."""
from pathlib import Path
from collections import Counter
import json
import hashlib
import numpy as np
from PIL import Image
HERE=Path(__file__).resolve().parent
E=HERE.parents[2]/'knowledge/experiments/evidence/camera-native-roundtrip-v3-20261027-r1'
raw=json.loads((E/'storage/result.json').read_text('utf-8-sig'))
t=raw['cameraRaster'];snaps=t['nodeSnapshots']
before={n['id']:n for n in snaps[1]['nodes']}
comparisons=[]
for snap in snaps[2:]:
    after={n['id']:n for n in snap['nodes']};changes=[]
    for ident in before.keys()|after.keys():
        a,b=before.get(ident),after.get(ident)
        if a!=b:
            fields={k:[a.get(k),b.get(k)] for k in a.keys()|b.keys() if a.get(k)!=b.get(k)} if a and b else {'presence':[bool(a),bool(b)]}
            changes.append(dict(id=ident,path=(a or b)['path'],className=(a or b)['className'],fields=fields))
    comparisons.append(dict(label=snap['label'],count=len(changes),changes=changes))
pics=E/'storage/display-pixels'
names=['native-original.png','native-repeat.png']+[f'roundtrip-{k}-{state}.png' for k in range(3) for state in ('restored','repeat')]
images={n:np.asarray(Image.open(pics/n).convert('RGBA'),dtype=np.int16) for n in names}
native=images[names[0]]
pixels=[]
for n,im in images.items():
    diff=np.abs(native-im);changed=np.any(diff,axis=2);ys,xs=np.where(changed)
    pixels.append(dict(name=n,sha256=hashlib.sha256((pics/n).read_bytes()).hexdigest().upper(),
        changed=int(changed.sum()),maxRGB=int(diff[:,:,:3].max()),maxAlpha=int(diff[:,:,3].max()),
        bounds=None if len(xs)==0 else [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]))
restoresIdentical=all(np.array_equal(images['roundtrip-0-restored.png'],images[n]) for n in names[2:])
out=dict(errors=t['errors'],nativeRepeat=t['nativeRepeat'],frames=len(t['framesMs']),
    metadataComplete=all(s.get('complete',False) for s in snaps),metadataErrors=[dict(label=s['label'],errors=s['errors']) for s in snaps],
    comparisons=comparisons,pixels=pixels,allReturnedImagesIdentical=restoresIdentical,
    created=t['pixelBitmapsCreated'],disposed=t['pixelBitmapsDisposed'],cleanup=t['cleanup'],
    limits=['Public metadata is incomplete; equality of recorded nodes does not establish equality of all state or renderer caches.',
            'The first native round trip changed captured pixels without alpha/caching mutations; this is not a candidate performance result.'])
path=E/'roundtrip-analysis.json'
assert not path.exists(),'Preserve prior analysis'
path.write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(dict(metadataComplete=out['metadataComplete'],returnedImagesIdentical=restoresIdentical,
    recordedChanges=[dict(label=c['label'],count=c['count'],fields=dict(Counter(k for ch in c['changes'] for k in ch['fields']))) for c in comparisons],
    pixels=pixels),ensure_ascii=False))
