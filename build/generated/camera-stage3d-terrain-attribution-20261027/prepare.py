from pathlib import Path
import importlib.util
import ast
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('all_terrain_gpu_patch',HERE/'probe_patch.py')
patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)
def write(p,s):
    p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():assert p.read_text('utf-8-sig')==s,p
    else:p.write_text(s,'utf-8')
write(patch.HELPER,patch.helper_source());write(patch.PRESENTER,patch.renderer_source())
s=(HERE.parent/'camera-stage3d-entry-20261027/run.py').read_text('utf-8-sig')
for old,new in [
    ('camera-stage3d-entry-1','camera-stage3d-terrain-attribution-1'),
    ("trial['pixelBitmapsDisposed'] == 39","trial['pixelBitmapsDisposed'] == 143"),
    ("assert row['passed'] and row['candidate']['maxRGB']<=2 and row['candidate']['maxAlpha']==0","assert row['passed']  # Candidate draw order differs intentionally; never a visual acceptance."),
    ("row['presentation']['parents']==3","row['presentation']['parents']==5"),
    ('(3 if condition>=2 else 0)','(5 if condition>=2 else 0)'),
    ('camera Stage3D backgrounds / 01a13816','camera GPU terrain attribution / 01a13816'),
    ('Hardware backgrounds only; native remaining display list, readback composition not OS screenshot acceptance.',
     'All terrain on GPU below native objects: wrong foreground occlusion is intentional for attribution, not a product. No visual acceptance or OS mixed-presentation claim.'),
]:
    assert old in s,old;s=s.replace(old,new)
needle="    assert trial['pixelsValid'] and len(trial['pixels']) == 13"
assert needle in s
s=s.replace(needle,needle+'''
    assert trial['drawOrderIntentionallyDifferent'] and not trial['candidateVisualEquivalent']
    assert len(trial['nativeWarmups'])==13
    assert all(w['passed'] and len(w['checks'])==3 and all(c['pixels']['equal'] for c in w['checks']) for w in trial['nativeWarmups'])
    assert end['initial']['diagnosticWrongOcclusion']
''')
ast.parse(s);write(HERE/'run.py',s)
print('Prepared all-terrain GPU attribution: native restoration strict, object occlusion explicitly non-equivalent')
