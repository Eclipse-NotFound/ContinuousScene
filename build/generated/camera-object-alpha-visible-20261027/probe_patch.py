"""Six object-layer alpha and visibility controls, retaining terrain/light parents."""
from pathlib import Path
import importlib.util
import shutil
HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-world-alpha-visible-20261027/probe_patch.py'
spec=importlib.util.spec_from_file_location('object_alpha_visible_seed',PATCH_SOURCE)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
ORIGINAL=base.HELPER
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
CHANGED=base.CHANGED
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,HERE/'prepare.py',HERE/'object-control.as.inc')

def helper_source():
    s=ORIGINAL.read_text('utf-8-sig');assert s==base.helper_source()
    for old,new in [
        ('camera-world-alpha-visible-1','camera-object-alpha-visible-1'),
        ('[world.visual]','[grafon.visObjs[0],grafon.visObjs[1],grafon.visObjs[2],grafon.visObjs[3],grafon.visObjs[4],grafon.visObjs[5]]'),
        ('terrain.length==1','terrain.length==6'),
        ('hidden:Boolean(condition&2),moving:true','hidden:false,moving:true'),
        ('require(world.visual.visible===((row.condition&2)==0),"World visibility condition changed");','require(world.visual.visible===true,"World visibility changed");'),
        ('The world parent alpha=0 and visible=false independently. The fourth condition combines both.',
         'The six object parents alpha=0 and visible=false independently; terrain/background/native light retain their state. The fourth condition combines both.'),
    ]:
        assert old in s,old;s=s.replace(old,new)
    start=s.index('        private function applyLayers(')
    end=s.index('        private function savePixel(',start)
    return s[:start]+(HERE/'object-control.as.inc').read_text('utf-8-sig')+'\n'+s[end:]

def transform(source):return base.transform(source)

def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert not destination.exists() and not (source/CHANGED[1]).exists()
    shutil.copytree(source,destination)
    main=destination/CHANGED[0];main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/CHANGED[1])
