from pathlib import Path
import importlib.util
import ast
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('cached_native_scroll_patch',HERE/'probe_patch.py')
patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)

def write(p,s):
    p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():assert p.read_text('utf-8-sig')==s,p
    else:p.write_text(s,'utf-8')

write(patch.HELPER,patch.helper_source())
s=(HERE.parent/'camera-world-scroll-native-20261027/run.py').read_text('utf-8-sig')
for old,new in [
    ('camera-world-scroll-native-1','camera-world-scroll-native-cached-1'),
    ('HERE = Path(__file__).resolve().parent', "HERE = Path(__file__).resolve().parent\nHOST_HOME=HERE.parent/'camera-world-scroll-native-20261027'"),
    ("enumerate(row['conditions'],1)","enumerate(row['conditions'],2)"),
    ("zip(trial['windows'],(0,1,1,0))","zip(trial['windows'],(0,2,2,0))"),
    ("for name in ('native-moving','scroll-moving')", "for name in ('native-moving','scroll-cached-moving')"),
    ("HERE/'host-build.json'", "HOST_HOME/'host-build.json'"),
    ("HERE/'pfe.swf'", "HOST_HOME/'pfe.swf'"),
    ("HERE/'audit-proof.json'", "HOST_HOME/'audit-proof.json'"),
    ("480 isolated-host scroll intervals;", "480 isolated-host cached scroll intervals;"),
]:
    assert old in s,old;s=s.replace(old,new)
ast.parse(s);write(HERE/'run.py',s)
print('Prepared previously untimed cached condition with unchanged visual rejection')
