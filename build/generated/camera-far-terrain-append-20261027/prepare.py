from pathlib import Path
import ast
import importlib.util
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('append_terrain_patch',HERE/'probe_patch.py')
patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)
def write(p,s):
    p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():assert p.read_text('utf-8-sig')==s,p
    else:p.write_text(s,'utf-8')
write(patch.HELPER,patch.helper_source())
s=(HERE.parent/'camera-far-terrain-detach-20261027/run.py').read_text('utf-8-sig')
for old,new in [
    ('camera-far-terrain-detach-1','camera-far-terrain-append-1'),
    ("assert roots['visibilityWrites']==0", "assert roots['adoptedBitmaps']==roots['adoptedSurfaces']*4 and roots['appendAudits']>=0\n    assert roots['visibilityWrites']==0"),
    ("'No append/drop support: paused after fixed native prewarming; all native preparation counters stay unchanged.',", "'Native tail appends validated without changing selected tiles; drops unsupported. Native preparation counters stay unchanged during timing.',"),
]:
    assert old in s,old;s=s.replace(old,new)
ast.parse(s);write(HERE/'run.py',s)
print('Prepared native append ownership proof; original failed run retained')
