from pathlib import Path
import importlib.util
import shutil
HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-stage3d-wholeworld-cost-20261027/probe_patch.py'
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
base=load('wholeworld_settle_patch_seed',PATCH_SOURCE)
generation=load('wholeworld_settle_generation',HERE/'prepare.py')
ORIGINAL=base.HELPER;HELPER=HERE/'tests/SceneCameraRasterTrial.as';PRESENTER=HERE/'SceneTilePresentation.as'
CHANGED=base.CHANGED
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,base.PRESENTER,HERE/'prepare.py',PRESENTER,
    HERE.parents[4]/'game-reference/decompiled/1.02/src102/scripts/pfe_fla/bloat_bulk_896.as')
def helper_source():return generation.helper_source()
def renderer_source():return generation.renderer_source()
def transform(source):return base.transform(source)
def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source() and PRESENTER.read_text('utf-8-sig')==renderer_source()
    assert (HERE/'run.py').read_text('utf-8-sig')==generation.runner_source()
    assert not destination.exists() and not (source/'tests/SceneCameraRasterTrial.as').exists()
    shutil.copytree(source,destination)
    main=destination/'ContinuousSceneMotionProbe.as';main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/'tests/SceneCameraRasterTrial.as');shutil.copy2(PRESENTER,destination/'SceneTilePresentation.as')
