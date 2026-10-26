"""Single object group, unchanged alpha/restoration protocol."""
from pathlib import Path
import importlib.util
import shutil
HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-display-pixels-20261027/probe_patch.py'
spec=importlib.util.spec_from_file_location('binary_objects_seed',PATCH_SOURCE)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
ORIGINAL=base.HELPER
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
CHANGED=base.CHANGED
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,HERE/'prepare.py',HERE.parent/'camera-object-groups-20261027/generate.py')
VERSION='camera-upper-alpha-1'
INDICES=[3, 4, 5]

def helper_source():
    source=ORIGINAL.read_text('utf-8-sig');assert source==base.helper_source()
    targets='['+','.join('grafon.visObjs['+str(i)+']' for i in INDICES)+']'
    edits=[
      ('camera-display-pixels-1',VERSION),
      ('[grafon.visFon,grafon.visObjs[0],grafon.visObjs[1],grafon.visObjs[2],grafon.visObjs[3],grafon.visObjs[4],grafon.visObjs[5]]',targets),
      ('terrain.length==7','terrain.length=='+str(len(INDICES))),
      ('value.length!=7','value.length!='+str(len(INDICES))),
      ('i<7','i<'+str(len(INDICES))),
      ('[0,1,2,3,3,2,1,0]','[0,1,1,0]'),
      ('measurementFrames:960','measurementFrames:480'),
      ('mode<=3','mode<=1'),('condition<=3','condition<=1'),
      ('(i==0?(condition&1):(condition&2))','(condition&1)'),
      ('["native-moving","backdrop-zero-moving","objects-zero-moving","backdrop-objects-zero-moving"]','["native-moving","group-zero-moving"]'),
      ('Paused attribution only: native scenery backdrop and six object-layer parents use temporary alpha zero; all camera windows moving.',
       'Paused attribution only: object layers '+str(INDICES)+' use temporary alpha zero; all other parents remain native.')]
    for old,new in edits:
        assert old in source,old;source=source.replace(old,new)
    return source

def transform(source):return base.transform(source)

def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert not destination.exists() and not (source/CHANGED[1]).exists()
    shutil.copytree(source,destination)
    main=destination/CHANGED[0];main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/CHANGED[1])
