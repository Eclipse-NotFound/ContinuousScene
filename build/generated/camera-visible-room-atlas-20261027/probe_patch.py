from pathlib import Path
import importlib.util,shutil
HERE=Path(__file__).resolve().parent;PATCH_SOURCE=HERE.parent/'camera-visible-room-scout-20261027/probe_patch.py'
def load(name,p):
    sp=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
base=load('room_atlas_patch_base',PATCH_SOURCE);generation=load('room_atlas_generator',HERE/'prepare.py')
ORIGINAL=base.HELPER;HELPER=HERE/'tests/SceneCameraRasterTrial.as';ATLAS=HERE/'ScenePersistentAtlas.as'
CHANGED=sorted([*base.CHANGED,'ScenePersistentAtlas.as'])
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,generation.BASE/'prepare.py',generation.BASE/'run.py',HERE/'prepare.py',HERE/'summary.py',HERE/'axis_summary.py',generation.ATLAS,ATLAS)
def helper_source():return generation.helper_source()
def transform(source):return base.transform(source)
def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert (HERE/'run.py').read_text('utf-8-sig')==generation.runner_source()
    assert ATLAS.read_bytes()==generation.ATLAS.read_bytes()
    assert not destination.exists() and not (source/'tests/SceneCameraRasterTrial.as').exists() and not (source/'ScenePersistentAtlas.as').exists()
    shutil.copytree(source,destination)
    p=destination/'ContinuousSceneMotionProbe.as';p.write_text(transform(p.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/'tests/SceneCameraRasterTrial.as');shutil.copy2(ATLAS,destination/'ScenePersistentAtlas.as')
