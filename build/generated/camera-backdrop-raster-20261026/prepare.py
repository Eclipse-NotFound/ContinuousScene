"""Create a new candidate; never update a frozen source or prior receipt."""
from pathlib import Path
import importlib.util
import ast
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('screen_backdrop_patch',HERE/'probe_patch.py')
patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():assert path.read_text('utf-8-sig')==value,path
    else:path.write_text(value,'utf-8')

save(patch.HELPER,patch.helper_source())
source=(HERE.parent/'camera-backdrop-cache-20261026/run.py').read_text('utf-8-sig')
edits=[
    ('Paused camera motion versus whole-world visibility; diagnostic only.',
     'Paused camera motion versus exact-screen opaque backdrop; diagnostic only.'),
    ("VERSION = 'camera-backdrop-cache-1'","VERSION = 'camera-backdrop-raster-1'"),
    ("row['presentation']['parents']==4","row['presentation']['parents']==1"),
    ("p['parents']==(4 if condition>=2 else 0)","p['parents']==(1 if condition>=2 else 0)"),
    ("assert cleanup['presentation']['ownBitmapAllocations']==cleanup['presentation']['sourcePixelCopies']==0",
     """assert cleanup['presentation']['ownBitmapAllocations']==cleanup['presentation']['ownBitmapDisposals']==2
    assert cleanup['presentation']['liveBitmaps']==cleanup['presentation']['cacheBytes']==0
    assert cleanup['presentation']['sourcePixelCopies']==cleanup['presentation']['drawCalls']==1
    assert cleanup['presentation']['backdrop']['allOpaque']"""),
    ("assert row['endAtMs']==previous and row['copiesEnd']==row['copiesStart']==row['allocatedEnd']==row['allocatedStart']==0",
     "assert row['endAtMs']==previous and row['copiesEnd']==row['copiesStart']==1 and row['allocatedEnd']==row['allocatedStart']==2"),
    ('Only scenery backdrop native caching requested; CPU/GPU attribution and real combat performance are unproven.',
     'One opaque screen-sized copy of static scenery; real combat, changing backgrounds and full lifecycle are unproven.'),
    ('camera backdrop cache / 01a13816','camera backdrop raster / 01a13816'),
    ('960 native versus backdrop cache frames; diagnostic only, no deployment',
     '960 native versus screen backdrop frames; diagnostic only, no deployment')
]
for old,new in edits:
    assert source.count(old)==1,(old,source.count(old))
    source=source.replace(old,new,1)
save(HERE/'run.py',source)
ast.parse(source)
print('Prepared screen backdrop source, preserved native route and pixel gates.')

