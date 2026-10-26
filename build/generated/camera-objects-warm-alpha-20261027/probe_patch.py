"""One fixed natural warm-up, three exact camera invariants, then alpha attribution."""
from pathlib import Path
import importlib.util
import shutil
HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-display-pixels-20261027/probe_patch.py'
spec=importlib.util.spec_from_file_location('warm_object_seed',PATCH_SOURCE)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
ORIGINAL=base.HELPER
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
CHANGED=base.CHANGED
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,HERE/'prepare.py',HERE/'warmup.as.inc')

def helper_source():
    source=ORIGINAL.read_text('utf-8-sig');assert source==base.helper_source()
    edits=[
        ('camera-display-pixels-1','camera-objects-warm-alpha-1'),
        ('[grafon.visFon,grafon.visObjs[0],grafon.visObjs[1],grafon.visObjs[2],grafon.visObjs[3],grafon.visObjs[4],grafon.visObjs[5]]',
         '[grafon.visObjs[2],grafon.visObjs[3],grafon.visObjs[4],grafon.visObjs[5]]'),
        ('terrain.length==7','terrain.length==4'),('value.length!=7','value.length!=4'),('i<7','i<4'),
        ('backdrop-objects-zero-moving','roles-upper-zero-moving'),
        ('backdrop-zero-moving','roles-zero-moving'),('objects-zero-moving','upper-zero-moving'),
        ('                var original:BitmapData=capture();','                var original:BitmapData=warmNative(point,index);'),
        ('        private function applyLayers(condition:int):void {',
         (HERE/'warmup.as.inc').read_text('utf-8-sig')+'\n        private function applyLayers(condition:int):void {'),
        ('Paused attribution only: native scenery backdrop and six object-layer parents use temporary alpha zero; all camera windows moving.',
         'Paused attribution only: role layer 2 and upper layers 3-5. One fixed native warm-up, then three exact natural camera invariants before alpha tests. Cold screenshot behavior remains separately recorded.')
    ]
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
