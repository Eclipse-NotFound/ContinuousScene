from pathlib import Path
import importlib.util
import ast
HERE=Path(__file__).resolve().parent
def save(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():assert path.read_text('utf-8-sig')==text,path
    else:path.write_text(text,'utf-8')
spec=importlib.util.spec_from_file_location('light_crop_patch',HERE/'probe_patch.py')
patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)
save(patch.HELPER,patch.helper_source())
source=(HERE.parent/'camera-backdrop-cache-20261026/run.py').read_text('utf-8-sig')
edits=[
    ('Paused camera motion versus whole-world visibility; diagnostic only.','Native globally enlarged darkness bitmap scissor; diagnostic only.'),
    ("VERSION = 'camera-backdrop-cache-1'","VERSION = 'camera-native-light-crop-1'"),
    ("row['presentation']['parents']==4","row['presentation']['parents']==1"),
    ("p['parents']==(4 if condition>=2 else 0)","p['parents']==(1 if condition>=2 else 0)"),
    ("['actualCache']","['cropActive']"),
    ("trial['pixelBitmapsDisposed'] == 15","trial['pixelBitmapsDisposed'] == 39"),
    ("len(trial['pixels']) == 5","len(trial['pixels']) == 13"),
    ("('native-static','native-moving','backdrop-static','backdrop-moving')",
     "('native-static','native-moving','lightcrop-static','lightcrop-moving')"),
    ('Only scenery backdrop native caching requested; CPU/GPU attribution and real combat performance are unproven.',
     'Only the native darkness bitmap display extent is cropped; light data and layers remain unchanged; real combat unproven.'),
    ('camera backdrop cache / 01a13816','camera native light crop / 01a13816'),
    ('960 native versus backdrop cache frames; diagnostic only, no deployment',
     '960 native versus light crop camera frames; diagnostic only, no deployment')
]
for old,new in edits:
    expected=2 if old=="['actualCache']" else 1
    assert source.count(old)==expected,(old,source.count(old))
    source=source.replace(old,new)
ast.parse(source);save(HERE/'run.py',source)
print('Prepared native darkness extent crop, 13 views, zero own bitmap/source pixel copies.')

