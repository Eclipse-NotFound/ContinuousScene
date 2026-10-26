"""Isolate lower object layers; retain the exact alpha and restoration protocol."""
from pathlib import Path
import importlib.util
import shutil
HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-display-pixels-20261027/probe_patch.py'
spec=importlib.util.spec_from_file_location('lower_objects_seed',PATCH_SOURCE)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
ORIGINAL=base.HELPER
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
CHANGED=base.CHANGED
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,HERE/'prepare.py')

def helper_source():
    source=ORIGINAL.read_text('utf-8-sig');assert source==base.helper_source()
    source=source.replace('camera-display-pixels-1','camera-lower-objects-1')
    replacements=[
      ('[grafon.visFon,grafon.visObjs[0],grafon.visObjs[1],grafon.visObjs[2],grafon.visObjs[3],grafon.visObjs[4],grafon.visObjs[5]]','[grafon.visObjs[0],grafon.visObjs[1]]'),
      ('terrain.length==7','terrain.length==2'),('value.length!=7','value.length!=2'),
      ('i<7','i<2'),
      ('backdrop-zero-moving','objects0-zero-moving'),('objects-zero-moving','objects1-zero-moving'),
      ('backdrop-objects-zero-moving','objects01-zero-moving'),
      ('Paused attribution only: native scenery backdrop and six object-layer parents use temporary alpha zero; all camera windows moving.',
       'Paused attribution only: lower object parents visObjs[0] and visObjs[1] independently use alpha zero; other layers untouched.')]
    # Replace the longest mode name first, so it cannot be changed twice.
    replacements.sort(key=lambda pair:len(pair[0]),reverse=True)
    for old,new in replacements:
        assert old in source,old;source=source.replace(old,new)
    return source

def transform(source):return base.transform(source)

def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert not destination.exists() and not (source/CHANGED[1]).exists()
    shutil.copytree(source,destination)
    main=destination/CHANGED[0];main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/CHANGED[1])
