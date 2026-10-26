from pathlib import Path
import importlib.util
import ast
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('world_routewarm_patch',HERE/'probe_patch.py')
patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)
def write(p,s):
    p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():assert p.read_text('utf-8-sig')==s,p
    else:p.write_text(s,'utf-8')
write(patch.HELPER,patch.helper_source())
s=(HERE.parent/'camera-world-scroll-cached-20261027/run.py').read_text('utf-8-sig')
for old,new in [
    ('camera-world-scroll-cached-1','camera-world-scroll-routewarm-1'),
    ("==55 and cleanup['terrainRestored']","==75 and cleanup['terrainRestored']"),
    ("assert warm['passed'] and len(warm['checks'])==3", "assert len(warm['preparationReturns'])==3\n        assert warm['passed'] and len(warm['checks'])==3"),
]:
    assert old in s,old;s=s.replace(old,new)
ast.parse(s);write(HERE/'run.py',s)
print('Prepared fixed full-offset native preparation and failure PNG retention')
