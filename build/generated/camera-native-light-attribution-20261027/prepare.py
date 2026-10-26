from pathlib import Path
import importlib.util
import ast
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('native_light_attribution_patch',HERE/'probe_patch.py')
patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)
def write(p,s):
    p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():assert p.read_text('utf-8-sig')==s,p
    else:p.write_text(s,'utf-8')
write(patch.HELPER,patch.helper_source())
s=(HERE.parent/'camera-objects-warm-alpha-20261027/run.py').read_text('utf-8-sig')
for old,new in [
    ('camera-objects-warm-alpha-1','camera-native-light-attribution-1'),
    ("len(trial['terrainInitial'])==4","len(trial['terrainInitial'])==2"),
    ('roles-upper-zero-moving','light-world-zero-moving'),('roles-zero-moving','light-zero-moving'),('upper-zero-moving','world-zero-moving'),
    ('warmed object layer attribution / 01a13816','native light and world attribution / 01a13816'),
]:
    assert old in s,old;s=s.replace(old,new)
ast.parse(s);write(HERE/'run.py',s)
print('Prepared native light/world parent attribution with strict warmed restoration')
