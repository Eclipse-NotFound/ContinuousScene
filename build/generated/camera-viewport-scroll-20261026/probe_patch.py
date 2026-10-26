"""Frozen native camera fixture with a new four-buffer viewport renderer."""
from pathlib import Path
import importlib.util
import shutil
HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-backdrop-cache-20261026/probe_patch.py'
spec=importlib.util.spec_from_file_location('viewport_scroll_seed_patch',PATCH_SOURCE)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
ORIGINAL=base.HELPER
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
PRESENTER=HERE/'SceneTilePresentation.as'
CHANGED=base.CHANGED
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,PRESENTER,HERE/'prepare.py')
def helper_source():
    source=ORIGINAL.read_text('utf-8-sig');assert source==base.helper_source()
    edits=[
        ('version:"camera-backdrop-cache-1"','version:"camera-viewport-scroll-1"'),
        ('Only native scenery backdrop caching requested; actual internal allocation is not directly measured.',
         'Four screen buffers scroll existing pixels and refill exposed strips; no production lifecycle claim.'),
        ('try {if(presenter!=null)presenter.clear();} catch(e0:Error)',
         'try {if(presenter!=null)presenter.dispose();} catch(e0:Error)'),
        ('["native-static","native-moving","backdrop-static","backdrop-moving"]',
         '["native-static","native-moving","scroll-static","scroll-moving"]'),
        ('report.pixelMs=getTimer()-pixelAt;',
         '''var offsets:Array=[[0,1],[1,1],[1,0],[0,0],[5,7],[0,7],[5,0],[0,0]];
                        for(var micro:int=0;micro<offsets.length;++micro)
                            pixelCase({x:views[0].x+offsets[micro][0],y:views[0].y+offsets[micro][1]},5+micro);
                        report.pixelMs=getTimer()-pixelAt;'''),
        ('Actual backdrop cache mismatch','Actual viewport scroll mismatch'),
        ('Backdrop cache not active','Viewport scroll not active'),
        ('Backdrop cache pixels failed','Viewport scroll pixels failed')
    ]
    for old,new in edits:
        assert source.count(old)==1,(old,source.count(old));source=source.replace(old,new,1)
    return source

def transform(source):return base.transform(source)
def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert not destination.exists() and not (source/'tests/SceneCameraRasterTrial.as').exists()
    shutil.copytree(source,destination)
    main=destination/'ContinuousSceneMotionProbe.as'
    main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/'tests/SceneCameraRasterTrial.as')
    shutil.copy2(PRESENTER,destination/'SceneTilePresentation.as')

