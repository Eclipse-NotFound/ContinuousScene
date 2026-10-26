from pathlib import Path
import importlib.util
import ast
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('static_terrain_gpu_patch',HERE/'probe_patch.py')
patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)
def write(p,s):
    p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():assert p.read_text('utf-8-sig')==s,p
    else:p.write_text(s,'utf-8')
write(patch.HELPER,patch.helper_source());write(patch.PRESENTER,patch.renderer_source())
s=(HERE.parent/'camera-stage3d-terrain-attribution-20261027/run.py').read_text('utf-8-sig')
for old,new in [
    ('camera-stage3d-terrain-attribution-1','camera-stage3d-static-terrain-1'),
    ("row['presentation']['parents']==5","row['presentation']['parents']==4"),
    ('(5 if condition>=2 else 0)','(4 if condition>=2 else 0)'),
    ('All terrain on GPU below native objects:','Static terrain on GPU below native objects, water unchanged:'),
]:
    assert old in s,old;s=s.replace(old,new)
ast.parse(s);write(HERE/'run.py',s)
print('Prepared static terrain attribution; translucent water remains native')
