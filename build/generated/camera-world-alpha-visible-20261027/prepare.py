from pathlib import Path
import importlib.util
import ast
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('world_visibility_patch',HERE/'probe_patch.py')
patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)
def write(p,s):
    p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():assert p.read_text('utf-8-sig')==s,p
    else:p.write_text(s,'utf-8')
write(patch.HELPER,patch.helper_source())
s=(HERE.parent/'camera-native-light-attribution-20261027/run.py').read_text('utf-8-sig')
for old,new in [
    ('camera-native-light-attribution-1','camera-world-alpha-visible-1'),
    ('light-world-zero-moving','alpha-invisible-moving'),('light-zero-moving','alpha-zero-moving'),('world-zero-moving','invisible-moving'),
    ("row['hidden'] is False","row['hidden'] is bool(condition & 2)"),
    ("assert all(v is True for v in row['worldVisible']+row['windowVisible'])", "assert all(v is True for v in row['windowVisible'])\n        assert all(v is (not bool(condition & 2)) for v in row['worldVisible'])"),
    ('native light and world attribution / 01a13816','world alpha versus visibility / 01a13816'),
    ('display alpha suppression is diagnostic, not a gameplay proposal.','world alpha/visibility suppression is diagnostic, not a gameplay proposal; other callbacks may react to visibility.'),
]:
    assert old in s,old;s=s.replace(old,new)
ast.parse(s);write(HERE/'run.py',s)
print('Prepared strict alpha/visible world comparison, same camera route in all conditions')
