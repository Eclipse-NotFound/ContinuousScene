"""Measure the previously untimed cached condition; visual rejection stays explicit."""
from pathlib import Path
import importlib.util
import shutil
HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-world-scroll-native-20261027/probe_patch.py'
spec=importlib.util.spec_from_file_location('cached_native_scroll_seed',PATCH_SOURCE)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
ORIGINAL=base.HELPER
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
CHANGED=base.CHANGED
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,HERE/'prepare.py')

def helper_source():
    s=ORIGINAL.read_text('utf-8-sig');assert s==base.helper_source()
    for old,new in [
        ('camera-world-scroll-native-1','camera-world-scroll-native-cached-1'),
        ('private var order:Array=[0,1,1,0];','private var order:Array=[0,2,2,0];'),
        ('for(var mode:int=1;mode<=1;++mode)', 'for(var mode:int=2;mode<=2;++mode)'),
    ]:
        assert s.count(old)==1,old;s=s.replace(old,new)
    return s

def transform(source):return base.transform(source)

def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert not destination.exists() and not (source/CHANGED[1]).exists()
    shutil.copytree(source,destination)
    main=destination/CHANGED[0];main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/CHANGED[1])
