from pathlib import Path
import importlib.util,json
HERE=Path(__file__).resolve().parent
p=HERE.parent/'camera-visible-room-scout-20261027/verify_batch.py'
sp=importlib.util.spec_from_file_location('visible_reference_audit',p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
record,raw=m.verify('camera-visible-room-atlas-20261027-scene-r2',HERE,source_count=87)
assert record==m.read(HERE/'review.json')
assert (HERE/'ScenePersistentAtlas.as').read_bytes()==(HERE.parent/'camera-persistent-fullpage-20261027/ScenePersistentAtlas.as').read_bytes()
t=raw['cameraRaster'];expected=[False,True]*4+[True,False]*4
assert [w['cached'] for w in t['windows']]==expected
for i in range(0,16,2):
    a,b=t['windows'][i:i+2]
    for field in ['vx','vy','cameraX','cameraY']:assert a[field]==b[field],(i,field)
assert all(g['x']==6700 and g['y']==3640 and g['hp']>0 for w in t['windows'] for g in w['gg'])
failed=m.read(m.E/'camera-visible-room-atlas-20261027-scene-r1/runner-failure.json')
assert not failed['complete'] and not failed['deployed'] and 'memory_gate' in failed['traceback']
assert not (m.E/'camera-visible-room-atlas-20261027-scene-r1/probe-build.json').exists()
print(json.dumps(dict(checksPassed=True,reviewSHA256=m.sha(HERE/'review.json'),probeSHA256=record['probeSHA256'],
                     resultSHA256=record['resultSHA256'],preflightFailurePreserved=True)))
