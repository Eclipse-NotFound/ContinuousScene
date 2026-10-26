"""GPU static terrain attribution; preserve native translucent water rendering."""
from pathlib import Path
import importlib.util
import shutil
HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-stage3d-terrain-attribution-20261027/probe_patch.py'
spec=importlib.util.spec_from_file_location('static_terrain_gpu_seed',PATCH_SOURCE)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
ORIGINAL=base.HELPER
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
PRESENTER=HERE/'SceneTilePresentation.as'
CHANGED=base.CHANGED
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,base.PRESENTER,PRESENTER,HERE/'prepare.py')

def renderer_source():
    s=base.PRESENTER.read_text('utf-8-sig');assert s==base.renderer_source()
    for old,new in [
        ('for(var layer:int=0;layer<4;++layer)','for(var layer:int=0;layer<3;++layer)'),
        ('parentIndex<=4','parentIndex<=3'),('[-1,1,2,0,3]','[-1,1,2,0]'),
        ('parents=[backdrop,g.visBack,g.visBack2,g.visFront,g.visVoda];','parents=[backdrop,g.visBack,g.visBack2,g.visFront];'),
        ('world.visual.getChildIndex(g.visFront),world.visual.getChildIndex(g.visVoda)','world.visual.getChildIndex(g.visFront)'),
        ('static backdrop, native back, native back2','static backdrop, native back/back2/front; water remains native'),
    ]:
        assert old in s,old;s=s.replace(old,new)
    return s

def helper_source():
    s=ORIGINAL.read_text('utf-8-sig');assert s==base.helper_source()
    return s.replace('camera-stage3d-terrain-attribution-1','camera-stage3d-static-terrain-1')

def transform(source):return base.transform(source)

def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source() and PRESENTER.read_text('utf-8-sig')==renderer_source()
    assert not destination.exists() and not (source/'tests/SceneCameraRasterTrial.as').exists()
    shutil.copytree(source,destination)
    main=destination/'ContinuousSceneMotionProbe.as';main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/'tests/SceneCameraRasterTrial.as')
    shutil.copy2(PRESENTER,destination/'SceneTilePresentation.as')
