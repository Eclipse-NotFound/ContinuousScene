"""Native-only matched interior camera axes in ordinary and continuous rooms."""
from pathlib import Path
import importlib.util
import shutil
HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-axis-motion-20261025/probe_patch.py'
spec=importlib.util.spec_from_file_location('room_axis_seed_patch',PATCH_SOURCE)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
ORIGINAL=base.HELPER
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
CHANGED=base.CHANGED
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,HERE/'prepare.py')

def helper_source():
    source=ORIGINAL.read_text('utf-8-sig');assert source==base.helper_source()
    start=source.index('        private function makeRoute():void {')
    end=source.index('        private function startWindow():void {',start)
    route='''        private function makeRoute():void {
            require(stage.stageWidth==1280 && stage.stageHeight==720,"Matched camera baseline requires 1280x720 content");
            var offsetX:int=grafon.sceneLarge?3840:0,offsetY:int=grafon.sceneLarge?4000:0;
            require(grafon.sceneLarge?(location.spaceX==240 && location.spaceY==125):
                (location.spaceX==48 && location.spaceY==25),"Unexpected matched room dimensions");
            var x:int=offsetX+960,y:int=offsetY+600;
            views=[{x:x,y:y},{x:x+120,y:y},{x:x,y:y+48},{x:x-120,y:y-48},{x:x+120,y:y+48}];
            for(var leg:int=0;leg<5;++leg) {
                var a:Object=views[leg],b:Object=views[(leg+1)%5];
                for(var i:int=0;i<24;++i)route.push({x:a.x+(b.x-a.x)*i/24,y:a.y+(b.y-a.y)*i/24});
            }
            report.roomAxis={continuous:grafon.sceneLarge,offsetX:offsetX,offsetY:offsetY,
                localCenterX:960,localCenterY:600,roomGridX:2,roomGridY:4,roomWidth:1920,roomHeight:1000};
            report.routeTranslationOnly=true;report.playerMovedByHelper=false;report.prepareCalls=0;
        }

'''
    edits=[
        ('version:"camera-axis-motion-1"','version:"camera-room-axis-baseline-1"'),
        ('require(grafon.sceneLarge && cam.moved && grafon.sceneChunkSide==320,"Requires native 320px large scene");',
         'require(cam.moved && (!grafon.sceneLarge || grafon.sceneChunkSide==320),"Requires native camera and optional 320px scene");'),
        (source[start:end],route)
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

