from pathlib import Path
import importlib.util
import ast
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('world_scroll_patch',HERE/'probe_patch.py')
patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)
def write(p,s):
    p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():assert p.read_text('utf-8-sig')==s,p
    else:p.write_text(s,'utf-8')
write(patch.HELPER,patch.helper_source())
s=(HERE.parent/'camera-world-alpha-visible-20261027/run.py').read_text('utf-8-sig')
for old,new in [
    ('camera-world-alpha-visible-1','camera-world-scroll-1'),
    ('world alpha versus visibility / 01a13816','world viewport scrolling / 01a13816'),
    ('960 camera backdrop/object-layer alpha controls; diagnostic only, no deployment','720 viewport-scrolling frames; diagnostic only, no deployment'),
]:
    assert old in s,old;s=s.replace(old,new)
start=s.index('def summarize(raw):');end=s.index('\n\ndef main():',start)
s=s[:start]+(HERE/'summarize.py').read_text('utf-8-sig')+s[end:]
ast.parse(s);write(HERE/'run.py',s)
print('Prepared native / viewport-scroll / cached-viewport-scroll comparison')
