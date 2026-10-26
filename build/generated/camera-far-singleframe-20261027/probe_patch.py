"""Only single-frame subtrees; stopped multi-frame clips are not static proof."""
from pathlib import Path
import importlib.util
import shutil
HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-far-static-warm-20261027/probe_patch.py'
spec=importlib.util.spec_from_file_location('far_single_seed',PATCH_SOURCE)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
ORIGINAL=base.HELPER
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
CHANGED=base.CHANGED
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,HERE/'prepare.py')

def helper_source():
    s=ORIGINAL.read_text('utf-8-sig');assert s==base.helper_source()
    for old,new in [
        ('camera-far-static-warm-1','camera-far-singleframe-1'),
        ('clip.totalFrames>1 && clip.isPlaying)return "playing"','clip.totalFrames>1)return "multiframe"'),
    ]:
        assert old in s,old;s=s.replace(old,new)
    return s

def transform(source):return base.transform(source)

def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert not destination.exists() and not (source/CHANGED[1]).exists()
    shutil.copytree(source,destination)
    main=destination/CHANGED[0];main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/CHANGED[1])
