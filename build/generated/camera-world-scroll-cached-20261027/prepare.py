from pathlib import Path
import importlib.util
import ast
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('world_scroll_cached_patch',HERE/'probe_patch.py')
patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)
def write(p,s):
    p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():assert p.read_text('utf-8-sig')==s,p
    else:p.write_text(s,'utf-8')
write(patch.HELPER,patch.helper_source())
s=(HERE.parent/'camera-world-scroll-20261027/run.py').read_text('utf-8-sig')
for old,new in [
    ('camera-world-scroll-1','camera-world-scroll-cached-1'),
    ("==65 and cleanup['terrainRestored']","==55 and cleanup['terrainRestored']"),
    ("len(row['conditions'])==2","len(row['conditions'])==1"),
    ("enumerate(row['conditions'],1)","enumerate(row['conditions'],2)"),
    ("len(trial['windows'])==6","len(trial['windows'])==4"),
    ("len(trial['sampleAtMs'])==720","len(trial['sampleAtMs'])==480"),
    ('(0,1,2,2,1,0)','(0,2,2,0)'),
    ('for name in modes}',"for name in ('native-moving','scroll-cached-moving')}"),
    ('((0,1),(0,2),(5,4),(5,3))','((0,1),(3,2))'),
    ('720 viewport-scrolling frames','480 cached viewport-scrolling frames'),
]:
    assert old in s,old;s=s.replace(old,new)
ast.parse(s);write(HERE/'run.py',s)
print('Prepared only the previously unexecuted cached viewport arm')
