from pathlib import Path
import importlib.util
import ast
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('warm_object_patch',HERE/'probe_patch.py')
patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)
def write(p,s):
    p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():assert p.read_text('utf-8-sig')==s,p
    else:p.write_text(s,'utf-8')
write(patch.HELPER,patch.helper_source())
s=(HERE.parent/'camera-lower-objects-20261027/run.py').read_text('utf-8-sig')
for old,new in [
    ('camera-lower-objects-1','camera-objects-warm-alpha-1'),
    ("trial['pixelBitmapsDisposed']==35","trial['pixelBitmapsDisposed']==75"),
    ("len(trial['terrainInitial'])==2","len(trial['terrainInitial'])==4"),
    ('objects01-zero-moving','roles-upper-zero-moving'),('objects0-zero-moving','roles-zero-moving'),('objects1-zero-moving','upper-zero-moving'),
    ('camera lower object layers / 01a13816','warmed object layer attribution / 01a13816'),
]:
    assert old in s,old;s=s.replace(old,new)
needle="    assert trial['pixelsValid'] and len(trial['pixels'])==5"
assert needle in s
s=s.replace(needle,needle+'''
    assert len(trial['nativeWarmups'])==5
    for warm in trial['nativeWarmups']:
        assert warm['passed'] and len(warm['checks'])==3
        assert all(check['pixels']['equal'] for check in warm['checks'])
''')
ast.parse(s);write(HERE/'run.py',s)
print('Prepared fixed native warm-up and strict natural/alpha restoration gates')
