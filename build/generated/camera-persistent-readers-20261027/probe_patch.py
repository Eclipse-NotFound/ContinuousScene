from pathlib import Path
import importlib.util,shutil
HERE=Path(__file__).resolve().parent;PATCH_SOURCE=HERE.parent/'camera-persistent-fullpage-20261027/probe_patch.py'
def load(name,p):
    sp=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
base=load('reader_patch_base',PATCH_SOURCE);generation=load('reader_generation',HERE/'prepare.py')
ORIGINAL=base.HELPER;HELPER=HERE/'tests/SceneCameraRasterTrial.as'
EXTRAS=[HERE/p for p in ['SceneClassicAtlas.as','ScenePersistentAtlas.as','tests/ScenePersistentAtlasChecks.as','SceneLegacyRVWallSurface.as','SceneNativeRVWallSurface.as','tests/SceneNativeReaderChecks.as']]
CHANGED=sorted(base.CHANGED+['SceneLegacyRVWallSurface.as','SceneNativeRVWallSurface.as','tests/SceneNativeReaderChecks.as'])
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,generation.BASE/'prepare.py',generation.RV,HERE/'prepare.py',HERE/'summary.py',*EXTRAS)
def helper_source():return generation.helper_source()
def transform(source):return base.transform(source)
def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert (HERE/'run.py').read_text('utf-8-sig')==generation.runner_source()
    for p,s in [(EXTRAS[0],generation.classic_source()),(EXTRAS[1],generation.persistent_source()),(EXTRAS[2],generation.fixture_source()),(EXTRAS[3],generation.rv_source(False)),(EXTRAS[4],generation.rv_source(True))]:assert p.read_text('utf-8-sig')==s
    assert not destination.exists() and not (source/'tests/SceneCameraRasterTrial.as').exists()
    shutil.copytree(source,destination)
    p=destination/'ContinuousSceneMotionProbe.as';p.write_text(transform(p.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/'tests/SceneCameraRasterTrial.as')
    for p in EXTRAS:shutil.copy2(p,destination/p.relative_to(HERE))
