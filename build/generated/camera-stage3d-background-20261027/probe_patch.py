"""Terminal Stage3D background replacement; original foreground/objects unchanged."""
from pathlib import Path
import importlib.util
import shutil
HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-backdrop-cache-20261026/probe_patch.py'
spec=importlib.util.spec_from_file_location('stage3d_background_seed',PATCH_SOURCE)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
ORIGINAL=base.HELPER
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
PRESENTER=HERE/'SceneTilePresentation.as'
CHANGED=base.CHANGED
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,PRESENTER,HERE/'prepare.py')

def helper_source():
    source=ORIGINAL.read_text('utf-8-sig');assert source==base.helper_source()
    edits=[
      ('version:"camera-backdrop-cache-1"','version:"camera-stage3d-background-1"'),
      ('Only native scenery backdrop caching requested; actual internal allocation is not directly measured.',
       'Hardware backdrop and two background layers; native objects, foreground and light remain. GPU readback plus Stage.draw is not OS screenshot acceptance.'),
      ('["native-static","native-moving","backdrop-static","backdrop-moving"]',
       '["native-static","native-moving","gpu-static","gpu-moving"]'),
      ('prepareBaseline=counters();report.preparePasses=[];',
       'prepareBaseline=counters();report.preparePasses=[];presenter.prepareContext(w);'),
      ('if(phase==0) {','if(phase==0) {\n                    if(!presenter.ready())return false;'),
      ('if(grafon.sceneViewReady()) {++cursor;retries=0;}',
       'if(grafon.sceneViewReady()) {presenter.update(world,true);presenter.clear();++cursor;retries=0;}'),
      ('report.pixelMs=getTimer()-pixelAt;',
       '''var offsets:Array=[[0,1],[1,1],[1,0],[0,0],[5,7],[0,7],[5,0],[0,0]];
                        for(var micro:int=0;micro<offsets.length;++micro)
                            pixelCase({x:views[0].x+offsets[micro][0],y:views[0].y+offsets[micro][1]},5+micro);
                        report.pixelMs=getTimer()-pixelAt;'''),
      ('cleanup.presentation=presenter.snapshot();',
       'try {presenter.dispose();}catch(disposeError:Error){cleanup.errors.push("GPU disposal: "+disposeError.message);}\n            cleanup.presentation=presenter.snapshot();'),
      ('bitmap.draw(stage);return bitmap;',
       'if(presenter.active)presenter.capture(bitmap);else bitmap.draw(stage);return bitmap;'),
      ('Actual backdrop cache mismatch','Actual GPU background mismatch'),
      ('Backdrop cache not active','GPU background not active'),
      ('Backdrop cache pixels failed','GPU background pixels failed')
    ]
    for old,new in edits:
        assert source.count(old)==1,(old,source.count(old));source=source.replace(old,new,1)
    return source

def transform(source):return base.transform(source)

def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert not destination.exists() and not (source/'tests/SceneCameraRasterTrial.as').exists()
    shutil.copytree(source,destination)
    main=destination/'ContinuousSceneMotionProbe.as'
    main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/'tests/SceneCameraRasterTrial.as')
    shutil.copy2(PRESENTER,destination/'SceneTilePresentation.as')

