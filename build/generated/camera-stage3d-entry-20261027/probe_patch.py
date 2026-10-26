"""Use the actual native menu shutdown before newGame; previous renderer preserved."""
from pathlib import Path
import importlib.util
import shutil
HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-stage3d-pixels-20261027/probe_patch.py'
spec=importlib.util.spec_from_file_location('stage3d_entry_seed',PATCH_SOURCE)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
ORIGINAL=base.HELPER
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
PRESENTER=HERE/'SceneTilePresentation.as'
CHANGED=base.CHANGED
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,PRESENTER,HERE/'prepare.py')

def renderer_source():
    source=base.PRESENTER.read_text('utf-8-sig');assert source==base.renderer_source()
    assert source.count('if(captures<=13)savePixel')==1
    return source.replace('if(captures<=13)savePixel','if(captures==1)savePixel',1)

def helper_source():
    source=ORIGINAL.read_text('utf-8-sig');assert source==base.helper_source()
    edits=[
      ('version:"camera-stage3d-pixels-1"','version:"camera-stage3d-entry-1"'),
      ('require(saved.worldVisible===true,"World must start visible");','''require(saved.worldVisible===true,"World must start visible");
                require(w.mm!=null && w.mm.active===false,"Main menu must be inactive");
                report.nativeMenuChildren=[];
                for(var menuChild:int=0;menuChild<w.main.numChildren;++menuChild) {
                    var className:String=getQualifiedClassName(w.main.getChildAt(menuChild));
                    report.nativeMenuChildren.push({className:className,visible:w.main.getChildAt(menuChild).visible});
                    require(className!="visMainMenu","Native mainMenuOff must remove the main menu display");
                }''')
    ]
    for old,new in edits:
        assert source.count(old)==1;source=source.replace(old,new,1)
    return source

def transform(source):
    source=base.transform(source)
    old='w.mm.active=false;w.newGame(-1,"Scene Motion",{propusk:true});phase=1;'
    new='w.mm.mainMenuOff();if(w.mm.active)throw new Error("Native menu shutdown failed");w.newGame(-1,"Scene Motion",{propusk:true});phase=1;'
    assert source.count(old)==1
    return source.replace(old,new,1)

def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert PRESENTER.read_text('utf-8-sig')==renderer_source()
    assert not destination.exists() and not (source/'tests/SceneCameraRasterTrial.as').exists()
    shutil.copytree(source,destination)
    main=destination/'ContinuousSceneMotionProbe.as'
    main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/'tests/SceneCameraRasterTrial.as')
    shutil.copy2(PRESENTER,destination/'SceneTilePresentation.as')

