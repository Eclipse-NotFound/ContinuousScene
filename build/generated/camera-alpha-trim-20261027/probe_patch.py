"""Borrow the strict 13-view native presentation test; only tile extents change."""
from pathlib import Path
import importlib.util
import shutil
HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-native-light-crop-v2-20261027/probe_patch.py'
spec=importlib.util.spec_from_file_location('alpha_trim_seed',PATCH_SOURCE)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
ORIGINAL=base.HELPER
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
PRESENTER=HERE/'SceneTilePresentation.as'
CHANGED=base.CHANGED
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,PRESENTER,HERE/'prepare.py')

def helper_source():
    source=ORIGINAL.read_text('utf-8-sig');assert source==base.helper_source()
    source=source.replace('camera-native-light-crop-2','camera-alpha-trim-1').replace('lightcrop-','alphatrim-')
    source=source.replace('Native global darkness bitmap is cropped around the viewport; source lighting pixels and scale remain unchanged.',
        'Only proven transparent terrain margins are removed from native Bitmap display extents; source pixels unchanged.')
    source=source.replace('native light crop','transparent terrain crop').replace('Native light crop','Transparent terrain crop')
    old='require(saved.worldVisible===true,"World must start visible");'
    assert source.count(old)==1
    source=source.replace(old,old+'''
                require(w.mm!=null && !w.mm.active,"Main menu must be inactive");
                report.nativeMenuChildren=[];
                for(var menuChild:int=0;menuChild<w.main.numChildren;++menuChild) {
                    var className:String=getQualifiedClassName(w.main.getChildAt(menuChild));
                    report.nativeMenuChildren.push(className);require(className!="visMainMenu","Native menu display remains");
                }''')
    return source

def transform(source):
    source=base.transform(source)
    old='w.mm.active=false;w.newGame(-1,"Scene Motion",{propusk:true});phase=1;'
    new='w.mm.mainMenuOff();if(w.mm.active)throw new Error("Native menu shutdown failed");w.newGame(-1,"Scene Motion",{propusk:true});phase=1;'
    assert source.count(old)==1;return source.replace(old,new,1)

def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert not destination.exists() and not (source/'tests/SceneCameraRasterTrial.as').exists()
    shutil.copytree(source,destination)
    main=destination/'ContinuousSceneMotionProbe.as';main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/'tests/SceneCameraRasterTrial.as');shutil.copy2(PRESENTER,destination/'SceneTilePresentation.as')
