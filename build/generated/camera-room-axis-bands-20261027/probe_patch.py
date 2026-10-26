"""Read existing event clocks; distinguish script spans from the unlabelled inter-frame gap."""
from pathlib import Path
import importlib.util
import shutil
HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-room-axis-baseline-v2-20261027/probe_patch.py'
spec=importlib.util.spec_from_file_location('room_axes_clock_seed',PATCH_SOURCE)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
ORIGINAL=base.HELPER
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
CHANGED=base.CHANGED
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,HERE/'prepare.py')
def helper_source():
    source=ORIGINAL.read_text('utf-8-sig');assert source==base.helper_source()
    edits=[
      ('version:"camera-room-axis-baseline-2"','version:"camera-room-axis-bands-1"'),
      ('public function step(w:*):Boolean','public function step(w:*,clocks:Object):Boolean'),
      ('                    var interval:int=now-previous;previous=now;',
       '''                    require(clocks!=null && previous<=clocks.previousEnd &&
                        clocks.previousEnd<=clocks.first && clocks.first<=clocks.start &&
                        clocks.start<=clocks.nativeEnd && clocks.nativeEnd<=clocks.wallEnd &&
                        clocks.wallEnd<=clocks.sceneEnd && clocks.sceneEnd<=clocks.beforeProbe &&
                        clocks.beforeProbe<=now,"Frame event clock ordering changed");
                    row.eventClocks.push(clocks);
                    row.previousTailMs.push(clocks.previousEnd-previous);
                    row.interFrameGapMs.push(clocks.first-clocks.previousEnd);
                    row.scriptToSampleMs.push(now-clocks.first);
                    var interval:int=now-previous;previous=now;'''),
      ('                framesMs:[],sampleAtMs:[],vx:[],vy:[],cameraX:[],cameraY:[],gg:[],scene:[],workMs:[],',
       '                eventClocks:[],previousTailMs:[],interFrameGapMs:[],scriptToSampleMs:[],framesMs:[],sampleAtMs:[],vx:[],vy:[],cameraX:[],cameraY:[],gg:[],scene:[],workMs:[],')
    ]
    for old,new in edits:
        assert source.count(old)==1,(old,source.count(old));source=source.replace(old,new,1)
    return source
def transform(source):
    out=base.transform(source)
    before='if(cameraRaster.step(w))'
    after='''if(cameraRaster.step(w,{first:absoluteStart,start:startFrame,nativeEnd:band50,wallEnd:band150,
                        sceneEnd:band250,beforeProbe:getTimer(),previousEnd:lastEnd,
                        renderListenerMs:renderMs,renderCalls:renderCalls,exitListenerMs:exitMs,exitCalls:exitCalls}))'''
    assert out.count(before)==1
    return out.replace(before,after,1)
def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert not destination.exists() and not (source/'tests/SceneCameraRasterTrial.as').exists()
    shutil.copytree(source,destination)
    main=destination/'ContinuousSceneMotionProbe.as'
    main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/'tests/SceneCameraRasterTrial.as')

