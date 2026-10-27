from pathlib import Path
import importlib.util,shutil
HERE=Path(__file__).resolve().parent;PATCH_SOURCE=HERE.parent/'camera-persistent-combat-imports-20261027/probe_patch.py'
def load(name,p):
    sp=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
generation=load('persistent_repeated_recipe',HERE/'prepare.py');base=load('persistent_repeated_patch_base',PATCH_SOURCE)
ORIGINAL=base.HELPER;HELPER=HERE/'tests/SceneCombatAtlasPixels.as';CHANGED=base.CHANGED
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,generation.BASE/'prepare.py',HERE/'prepare.py',HERE/'summary.py',HERE/'SceneRasterPresentation.as')
def helper_source():return generation.helper_source()
def transform(source):return generation.transform(source)
def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert (HERE/'run.py').read_text('utf-8-sig')==generation.runner_source()
    assert (HERE/'SceneRasterPresentation.as').read_text('utf-8-sig')==generation.presenter_source()
    assert (HERE/'SceneRasterPresentation.as').read_bytes()==(generation.BASE/'SceneRasterPresentation.as').read_bytes()
    assert not destination.exists() and not (source/'tests/SceneCombatAtlasPixels.as').exists()
    shutil.copytree(source,destination)
    p=destination/'ContinuousSceneMotionProbe.as';p.write_text(transform(p.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HERE/'SceneRasterPresentation.as',destination/'SceneRasterPresentation.as')
    shutil.copy2(HELPER,destination/'tests/SceneCombatAtlasPixels.as')
