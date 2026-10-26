"""Viewport scroll alternative; original camera calculations remain, same image gates."""
from pathlib import Path
import importlib.util
import shutil
HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-world-alpha-visible-20261027/probe_patch.py'
spec=importlib.util.spec_from_file_location('world_scroll_seed',PATCH_SOURCE)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
ORIGINAL=base.HELPER
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
CHANGED=base.CHANGED
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,HERE/'prepare.py',HERE/'scroll-control.as.inc',HERE/'summarize.py')

def helper_source():
    s=ORIGINAL.read_text('utf-8-sig');assert s==base.helper_source()
    edits=[
        ('camera-world-alpha-visible-1','camera-world-scroll-1'),
        ('order:Array=[0,1,2,3,3,2,1,0]','order:Array=[0,1,2,2,1,0]'),
        ('measurementFrames:960','measurementFrames:720'),
        ('saved.stateFields=saved.state!=null',
         'saved.worldCache=world.visual.cacheAsBitmap;\n                require(world.visual.scrollRect==null && !saved.worldCache && world.visual.cacheAsBitmapMatrix==null && world.visual.mask==null && world.visual.filters.length==0,"Unsupported world effects/cache/clip");\n                saved.stateFields=saved.state!=null'),
        ('mode:["native-moving","alpha-zero-moving","invisible-moving","alpha-invisible-moving"][condition]','mode:["native-moving","scroll-moving","scroll-cached-moving"][condition]'),
        ('hidden:Boolean(condition&2),moving:true','hidden:false,moving:true'),
        ('require(world.visual.visible===((row.condition&2)==0),"World visibility condition changed");','require(world.visual.visible===true,"World visibility changed");'),
        ('for(var mode:int=1;mode<=3;++mode)','for(var mode:int=1;mode<=2;++mode)'),
        ('require(item.restored.equal,"Terrain visibility did not restore exact pixels");','require(item.changed.maxRGB<=2 && item.changed.maxAlpha==0 && item.restored.equal,"World scrolling changed pixels beyond accepted tolerance or failed exact restore");'),
        ('require(cam.X==x && cam.Y==y,"Native camera changed the supplied look target");\n            checkTransform();',
         'require(cam.X==x && cam.Y==y,"Native camera changed the supplied look target");\n            if(scrollCondition!=0)applyLayers(scrollCondition);\n            checkTransform();'),
        ('var m:Matrix=world.visual.transform.concatenatedMatrix;','var m:Matrix=world.visual.transform.matrix;'),
        ('require(sameMatrix(world.visual.transform.matrix,world.sats.vis.transform.matrix),"SATS camera transform differs");\n            require(world.visual.x==cam.vx && world.visual.y==cam.vy,"Native translation differs");',
         'if(scrollCondition==0){\n                require(sameMatrix(world.visual.transform.matrix,world.sats.vis.transform.matrix),"SATS camera transform differs");\n                require(world.visual.x==cam.vx && world.visual.y==cam.vy,"Native translation differs");\n            } else require(sameLayers(layerState(),scrollCondition),"Scroll state changed");'),
        ('The world parent alpha=0 and visible=false independently. The fourth condition combines both. Other callbacks may react to visibility, so this does not identify a pure renderer cost.',
         'Original camera calculation plus viewport scroll, without and with native cacheAsBitmap. Camera calculation still writes the original transform first; this is not an optimized host implementation. Delayed scrollRect coordinate conversion is not used to prove geometry.'),
    ]
    for old,new in edits:
        assert old in s,old;s=s.replace(old,new)
    start=s.index('        private function applyLayers(')
    end=s.index('        private function savePixel(',start)
    return s[:start]+(HERE/'scroll-control.as.inc').read_text('utf-8-sig')+'\n'+s[end:]

def transform(source):return base.transform(source)

def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert not destination.exists() and not (source/CHANGED[1]).exists()
    shutil.copytree(source,destination)
    main=destination/CHANGED[0];main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/CHANGED[1])
