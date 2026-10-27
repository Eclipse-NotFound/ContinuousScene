from pathlib import Path
import importlib.util,shutil
HERE=Path(__file__).resolve().parent;PATCH_SOURCE=HERE.parent/'camera-persistent-atlas-checks-20261027/probe_patch.py'
def load(name,p):
    sp=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
base=load('fullpage_patch_base',PATCH_SOURCE);generation=load('fullpage_generation',HERE/'prepare.py')
ORIGINAL=base.HELPER;HELPER=HERE/'tests/SceneCameraRasterTrial.as'
EXTRAS=[HERE/'SceneClassicAtlas.as',HERE/'ScenePersistentAtlas.as',HERE/'tests/ScenePersistentAtlasChecks.as']
CHANGED=base.CHANGED
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,generation.BASE/'prepare.py',HERE/'prepare.py',HERE/'summary.py',*EXTRAS)
def helper_source():return generation.helper_source()
def transform(source):return base.transform(source)
def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert (HERE/'run.py').read_text('utf-8-sig')==generation.runner_source()
    assert EXTRAS[0].read_text('utf-8-sig')==generation.classic_source()
    assert EXTRAS[1].read_text('utf-8-sig')==generation.persistent_source()
    assert EXTRAS[2].read_bytes()==base.EXTRAS[2].read_bytes()
    assert not destination.exists() and not (source/'tests/SceneCameraRasterTrial.as').exists()
    shutil.copytree(source,destination)
    p=destination/'ContinuousSceneMotionProbe.as';p.write_text(transform(p.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/'tests/SceneCameraRasterTrial.as')
    for p in EXTRAS:shutil.copy2(p,destination/p.relative_to(HERE))
