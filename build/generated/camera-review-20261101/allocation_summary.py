from pathlib import Path
from collections import Counter
import json
root=Path(__file__).resolve().parents[5]
evidence=root/'mods/ContinuousScene/knowledge/experiments/evidence/camera-review-current-alloc-r6-20261101'
r=json.loads((evidence/'storage/result.json').read_text('utf-8'))
f=r['frameCost'];windows=[w for w in f['windows'] if w['valid']]
def group(key):
    if 'FrameCostProbe' in key or 'ContinuousSceneMotionMod' in key:return 'probe'
    if 'UnitTurret/animate' in key:return 'turret-animation'
    if 'sceneNativeEnvironment' in key:return 'native-environment'
    if 'TdfcRuntime' in key:return 'tdfc'
    if 'addiction::' in key:return 'addiction'
    if 'rconnect' in key.lower() or 'NetHud' in key:return 'rconnect'
    if '[render]' in key or '[pre-render]' in key:return 'native-render'
    if key=='[]':return 'empty-stack'
    return 'other'
out={'valid':len(windows),'total':len(f['windows']),'errors':f['errors'],
     'scope':'One-interval sampling with internal allocations enabled; not frame-performance evidence. Live object getSize sums are incomplete and may include shared resources, not total allocated bytes.',
     'groups':{},'top':{}}
for kind in ['cpu','alloc','liveSizes']:
    all_rows=Counter();groups=Counter()
    for w in windows:
        all_rows.update(w[kind])
        for key,value in w[kind].items():groups[group(key)]+=value
    out['groups'][kind]=dict(groups.most_common())
    out['top'][kind]=all_rows.most_common(15)
with (evidence/'allocation-summary.json').open('x',encoding='utf-8') as stream:json.dump(out,stream,ensure_ascii=False,indent=2)
print(json.dumps({k:v for k,v in out.items() if k!='top'},ensure_ascii=False))
