"""One-time conservative direct-root culling; no wrappers or per-frame tree scan."""
from pathlib import Path
import importlib.util
import shutil
HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-world-alpha-visible-20261027/probe_patch.py'
spec=importlib.util.spec_from_file_location('far_static_seed',PATCH_SOURCE)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
ORIGINAL=base.HELPER
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
CHANGED=base.CHANGED
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,HERE/'prepare.py',HERE/'root-control.as.inc',HERE/'summarize.py')

def helper_source():
    s=ORIGINAL.read_text('utf-8-sig');assert s==base.helper_source()
    edits=[
        ('camera-world-alpha-visible-1','camera-far-static-visibility-1'),
        ('    import flash.display.Stage;','    import flash.display.Stage;\n    import flash.display.DisplayObjectContainer;\n    import flash.display.MovieClip;\n    import flash.utils.Dictionary;'),
        ('order:Array=[0,1,2,3,3,2,1,0]','order:Array=[0,1,1,0]'),
        ('measurementFrames:960','measurementFrames:480'),
        ('[world.visual]','[grafon.visObjs[0],grafon.visObjs[1],grafon.visObjs[2],grafon.visObjs[3],grafon.visObjs[4],grafon.visObjs[5]]'),
        ('applyCamera(point.x,point.y);\n                    ++report.prepareCalls;', 'applyCamera(point.x,point.y);collectViewport();\n                    ++report.prepareCalls;'),
        ('phase=1;pixelAt=getTimer();','collectRoots();phase=1;pixelAt=getTimer();'),
        ('try {if(terrain.length==1){applyLayers(0);cleanup.terrainRestored=sameLayers(layerState(),0);}}',
         'try {restoreRoots();cleanup.terrainRestored=sameLayers(layerState(),0);if(rootsReady)auditRoots();}'),
        ('mode:["native-moving","alpha-zero-moving","invisible-moving","alpha-invisible-moving"][condition]','mode:["native-moving","far-static-hidden-moving"][condition]'),
        ('hidden:Boolean(condition&2),moving:true','hidden:false,moving:true'),
        ('require(world.visual.visible===((row.condition&2)==0),"World visibility condition changed");','require(world.visual.visible===true,"World visibility changed");'),
        ('for(var mode:int=1;mode<=3;++mode)','for(var mode:int=1;mode<=1;++mode)'),
        ('require(item.restored.equal,"Terrain visibility did not restore exact pixels");','require(item.changed.equal && item.restored.equal,"Offscreen root culling changed pixels");'),
        ('report.timingEnd=row.end;report.timingRasterDelta={};','auditRoots();report.timingEnd=row.end;report.timingRasterDelta={};'),
        ('The world parent alpha=0 and visible=false independently. The fourth condition combines both. Other callbacks may react to visibility, so this does not identify a pure renderer cost.',
         'Only qualified static direct roots outside the whole route plus 320px are hidden. No wrappers or per-frame full tree scans. End/switch audits do not prove every intermediate callback state.'),
    ]
    for old,new in edits:
        assert old in s,old;s=s.replace(old,new)
    begin=s.index('        private function applyLayers(')
    end=s.index('        private function savePixel(',begin)
    return s[:begin]+(HERE/'root-control.as.inc').read_text('utf-8-sig')+'\n'+s[end:]

def transform(source):return base.transform(source)

def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert not destination.exists() and not (source/CHANGED[1]).exists()
    shutil.copytree(source,destination)
    main=destination/CHANGED[0];main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/CHANGED[1])
