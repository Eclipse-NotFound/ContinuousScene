"""Generate the bounded trial without altering any previous test source."""
from pathlib import Path
import importlib.util
import ast
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('viewport_scroll_patch',HERE/'probe_patch.py')
patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():assert path.read_text('utf-8-sig')==value,path
    else:path.write_text(value,'utf-8')
save(patch.HELPER,patch.helper_source())
source=(HERE.parent/'camera-backdrop-cache-20261026/run.py').read_text('utf-8-sig')
edits=[
    ('Paused camera motion versus whole-world visibility; diagnostic only.',
     'Paused camera motion versus a four-buffer incremental viewport cache; diagnostic only.'),
    ("VERSION = 'camera-backdrop-cache-1'","VERSION = 'camera-viewport-scroll-1'"),
    ("    assert cleanup['presentation']['actualCache'] is False\n    assert cleanup['presentation']['ownBitmapAllocations']==cleanup['presentation']['sourcePixelCopies']==0",
     """    assert cleanup['presentation']['ownBitmapAllocations']==cleanup['presentation']['ownBitmapDisposals']==4
    assert cleanup['presentation']['liveBitmaps']==cleanup['presentation']['cacheBytes']==cleanup['presentation']['nativeRecords']==0
    assert cleanup['presentation']['sourcePixelCopies']>0 and cleanup['presentation']['scrolls']>0"""),
    ("trial['pixelBitmapsDisposed'] == 15","trial['pixelBitmapsDisposed'] == 39"),
    ("len(trial['pixels']) == 5","len(trial['pixels']) == 13"),
    ("('native-static','native-moving','backdrop-static','backdrop-moving')",
     "('native-static','native-moving','scroll-static','scroll-moving')"),
    ("        assert all(p['parents']==(1 if condition>=2 else 0) and p['actualCache'] is (condition>=2) for p in row['presentation'])",
     "        assert all(p['liveBitmaps']==p['ownBitmapAllocations']==4 and p['ownBitmapDisposals']==0 for p in row['presentation'])"),
    ("assert row['endAtMs']==previous and row['copiesEnd']==row['copiesStart']==row['allocatedEnd']==row['allocatedStart']==0",
     """assert row['endAtMs']==previous and row['copiesEnd']>=row['copiesStart'] and row['allocatedEnd']==row['allocatedStart']==4
        if condition<2:assert row['copiesEnd']==row['copiesStart']
        if condition==3:assert row['copiesEnd']>row['copiesStart']"""),
    ('Only scenery backdrop native caching requested; CPU/GPU attribution and real combat performance are unproven.',
     'Four viewport buffers with incremental pixel scrolling; no real combat or dynamic revision acceptance yet.'),
    ('camera backdrop cache / 01a13816','camera viewport scroll / 01a13816'),
    ('960 native versus backdrop cache frames; diagnostic only, no deployment',
     '960 native versus viewport scroll frames; diagnostic only, no deployment')
]
for old,new in edits:
    assert source.count(old)==1,(old,source.count(old));source=source.replace(old,new,1)
save(HERE/'run.py',source);ast.parse(source)
print('Prepared viewport scrolling and 13 view/one-pixel checks.')

