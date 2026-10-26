"""Isolate the remaining native light and world parents after proven warm-up."""
from pathlib import Path
import importlib.util
import shutil
HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-objects-warm-alpha-20261027/probe_patch.py'
spec=importlib.util.spec_from_file_location('native_light_attribution_seed',PATCH_SOURCE)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
ORIGINAL=base.HELPER
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
CHANGED=base.CHANGED
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,HERE/'prepare.py')

def helper_source():
    s=ORIGINAL.read_text('utf-8-sig');assert s==base.helper_source()
    for old,new in [
        ('camera-objects-warm-alpha-1','camera-native-light-attribution-1'),
        ('[grafon.visObjs[2],grafon.visObjs[3],grafon.visObjs[4],grafon.visObjs[5]]','[grafon.visLight,world.visual]'),
        ('terrain.length==4','terrain.length==2'),('value.length!=4','value.length!=2'),('i<4','i<2'),
        ('roles-upper-zero-moving','light-world-zero-moving'),('roles-zero-moving','light-zero-moving'),('upper-zero-moving','world-zero-moving'),
        ('role layer 2 and upper layers 3-5.','native light and its world parent. World alpha also suppresses light, so the fourth condition is a nested suppression consistency control.'),
    ]:
        # i<4 appears in native tile bookkeeping too: only change sameLayers below.
        if old=='i<4':
            old='for(var i:int=0;i<4;++i)if(value[i]';new='for(var i:int=0;i<2;++i)if(value[i]'
        assert old in s,old;s=s.replace(old,new)
    return s

def transform(source):return base.transform(source)

def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert not destination.exists() and not (source/CHANGED[1]).exists()
    shutil.copytree(source,destination)
    main=destination/CHANGED[0];main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/CHANGED[1])
