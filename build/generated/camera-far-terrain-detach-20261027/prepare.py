from pathlib import Path
import importlib.util
import ast
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('far_terrain_patch',HERE/'probe_patch.py')
patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)
def write(p,s):
    p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():assert p.read_text('utf-8-sig')==s,p
    else:p.write_text(s,'utf-8')
write(patch.HELPER,patch.helper_source())
s=(HERE.parent/'camera-far-maskguard-20261027/run.py').read_text('utf-8-sig')
for old,new in [
    ('camera-far-maskguard-1','camera-far-terrain-detach-1'),
    ('far-static-hidden-moving','far-terrain-detached-moving'),
    ("trial['pixelBitmapsDisposed']==55","trial['pixelBitmapsDisposed']==75"),
    ("assert roots['perFrameFullScans']==0", "assert roots['visibilityWrites']==0 and roots['surfaces']>0 and len(roots['byLayer'])==4\n    assert roots['perFrameFullScans']==0"),
    ("'Mask/effect/animation-bearing roots excluded, no wrapper or reparenting.',", "'Only original invisible native terrain Bitmap nodes outside the complete route plus 320px are detached.',\n                'No append/drop support: paused after fixed native prewarming; all native preparation counters stay unchanged.',"),
    ('far static root visibility','far native terrain detachment'),
]:
    assert old in s,old;s=s.replace(old,new)
ast.parse(s);write(HERE/'run.py',s)
print('Prepared fixed-residency terrain detach attribution; no new host patch')
