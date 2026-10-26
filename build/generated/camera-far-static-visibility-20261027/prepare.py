from pathlib import Path
import importlib.util
import ast
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('far_static_patch',HERE/'probe_patch.py')
patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)

def write(p,s):
    p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():assert p.read_text('utf-8-sig')==s,p
    else:p.write_text(s,'utf-8')

write(patch.HELPER,patch.helper_source())
s=(HERE.parent/'camera-world-alpha-visible-20261027/run.py').read_text('utf-8-sig')
for old,new in [
    ('camera-world-alpha-visible-1','camera-far-static-visibility-1'),
    ('world alpha versus visibility / 01a13816','far static root visibility / 01a13816'),
    ('960 camera backdrop/object-layer alpha controls; diagnostic only, no deployment','480 direct-root visibility controls; diagnostic only, no deployment'),
]:
    assert old in s,old;s=s.replace(old,new)
begin=s.index('def summarize(raw):')
end=s.index('\n\ndef main():',begin)
s=s[:begin]+(HERE/'summarize.py').read_text('utf-8-sig')+s[end:]
ast.parse(s);write(HERE/'run.py',s)
print('Prepared conservative offscreen roots; 480 frames, 55 exact pixel captures')
