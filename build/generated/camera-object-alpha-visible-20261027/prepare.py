from pathlib import Path
import importlib.util
import ast
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('object_alpha_visible_patch',HERE/'probe_patch.py')
patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)
def write(p,s):
    p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():assert p.read_text('utf-8-sig')==s,p
    else:p.write_text(s,'utf-8')
write(patch.HELPER,patch.helper_source())
s=(HERE.parent/'camera-world-alpha-visible-20261027/run.py').read_text('utf-8-sig')
for old,new in [
    ('camera-world-alpha-visible-1','camera-object-alpha-visible-1'),
    ("row['hidden'] is bool(condition & 2)","row['hidden'] is False"),
    ("all(v is (not bool(condition & 2)) for v in row['worldVisible'])","all(v is True for v in row['worldVisible'])"),
    ("len(trial['terrainInitial'])==2","len(trial['terrainInitial'])==12"),
    ('1 if j==0 else 2','1 if j%2==0 else 2'),
    ('world alpha versus visibility / 01a13816','object layer alpha versus visibility / 01a13816'),
    ('world alpha/visibility suppression','object-layer alpha/visibility suppression'),
]:
    assert old in s,old;s=s.replace(old,new)
ast.parse(s);write(HERE/'run.py',s)
print('Prepared same-route six-object-layer alpha/visible diagnostic')
