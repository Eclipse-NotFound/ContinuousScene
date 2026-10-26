from pathlib import Path
import importlib.util
import ast
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('far_single_patch',HERE/'probe_patch.py')
patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)
def write(p,s):
    p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():assert p.read_text('utf-8-sig')==s,p
    else:p.write_text(s,'utf-8')
write(patch.HELPER,patch.helper_source())
s=(HERE.parent/'camera-far-static-warm-20261027/run.py').read_text('utf-8-sig')
assert 'camera-far-static-warm-1' in s
s=s.replace('camera-far-static-warm-1','camera-far-singleframe-1')
ast.parse(s);write(HERE/'run.py',s)
print('Prepared single-frame subtree eligibility; all bounds and pixel guards unchanged')
