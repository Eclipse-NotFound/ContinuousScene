from pathlib import Path
import importlib.util,shutil
HERE=Path(__file__).resolve().parent;PATCH_SOURCE=HERE.parent/'camera-active-quiet-bands-20261027/probe_patch.py'
def load(name,p):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
base=load('persistent_bands_patch',PATCH_SOURCE);generation=load('persistent_trial_generation',HERE/'prepare.py')
ORIGINAL=base.HELPER;HELPER=HERE/'tests/SceneCameraRasterTrial.as';EXTRAS=[HERE/'SceneClassicAtlas.as',HERE/'ScenePersistentAtlas.as']
CHANGED=sorted([*base.CHANGED,*[p.name for p in EXTRAS]])
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,HERE/'prepare.py',HERE/'summary.py',HERE/'presentation.py',generation.presentation.SOURCE,*EXTRAS,generation.BASE/'prepare.py',HERE.parent/'camera-visible-tree-audit-20261027/prepare.py',HERE.parent/'camera-active-quiet-axis-20261027/run.py')
def helper_source():return generation.helper_source()
def transform(source):return base.transform(source)
def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert (HERE/'run.py').read_text('utf-8-sig')==generation.runner_source()
    assert EXTRAS[0].read_text('utf-8-sig')==generation.presentation.classic_source()
    assert EXTRAS[1].read_text('utf-8-sig')==generation.presentation.persistent_source()
    assert not destination.exists() and not (source/'tests/SceneCameraRasterTrial.as').exists()
    shutil.copytree(source,destination)
    p=destination/'ContinuousSceneMotionProbe.as';p.write_text(transform(p.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/'tests/SceneCameraRasterTrial.as')
    for p in EXTRAS:shutil.copy2(p,destination/p.name)
