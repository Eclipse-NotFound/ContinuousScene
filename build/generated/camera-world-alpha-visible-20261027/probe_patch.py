"""Compare alpha-zero and visibility-false with the same strict warm restoration."""
from pathlib import Path
import importlib.util
import shutil
HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-native-light-attribution-20261027/probe_patch.py'
spec=importlib.util.spec_from_file_location('world_visibility_seed',PATCH_SOURCE)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
ORIGINAL=base.HELPER
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
CHANGED=base.CHANGED
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,HERE/'prepare.py',HERE/'world-control.as.inc')

def helper_source():
    s=ORIGINAL.read_text('utf-8-sig');assert s==base.helper_source()
    edits=[
        ('camera-native-light-attribution-1','camera-world-alpha-visible-1'),
        ('[grafon.visLight,world.visual]','[world.visual]'),
        ('terrain.push({target:layer,parent:layer.parent,alpha:layer.alpha});','terrain.push({target:layer,parent:layer.parent,alpha:layer.alpha,visible:layer.visible});'),
        ('terrain.length==2','terrain.length==1'),
        ('light-world-zero-moving','alpha-invisible-moving'),('light-zero-moving','alpha-zero-moving'),('world-zero-moving','invisible-moving'),
        ('hidden:false,moving:true,startAtMs:previous,','hidden:Boolean(condition&2),moving:true,startAtMs:previous,'),
        ('require(world.visual.visible===true,"World visibility changed");',
         'require(world.visual.visible===((row.condition&2)==0),"World visibility condition changed");'),
        ('native light and its world parent. World alpha also suppresses light, so the fourth condition is a nested suppression consistency control.',
         'The world parent alpha=0 and visible=false independently. The fourth condition combines both. Other callbacks may react to visibility, so this does not identify a pure renderer cost.'),
    ]
    for old,new in edits:
        assert old in s,old;s=s.replace(old,new)
    begin=s.index('        private function applyLayers(')
    end=s.index('        private function savePixel(',begin)
    s=s[:begin]+(HERE/'world-control.as.inc').read_text('utf-8-sig')+'\n'+s[end:]
    return s

def transform(source):return base.transform(source)

def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert not destination.exists() and not (source/CHANGED[1]).exists()
    shutil.copytree(source,destination)
    main=destination/CHANGED[0];main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/CHANGED[1])
