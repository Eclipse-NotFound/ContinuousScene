from pathlib import Path
import importlib.util
import shutil
import hashlib

HERE=Path(__file__).resolve().parent
PAGED=HERE.parent/'camera-atlas-paged-20261025'
POOL=HERE
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
CHANGED=['ContinuousSceneMotionProbe.as','SceneRasterPresentation.as','tests/SceneCameraRasterTrial.as']
VERSION='camera-atlas-pool-idle-2'
PRESENTER_SHA='6651CCFF07F244B09C67B3D5D6E61DE80791696C4BFF25607B4FE0F92B1D2D3A'

def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
paged_patch=load('pool_paused_paged_patch',PAGED/'probe_patch.py')
pool_patch=load('pool_paused_pool_patch',HERE.parent/'camera-atlas-pool-20261026'/'probe_patch.py')

def transform_main(source):
    value=paged_patch.transform(source)
    before='if(cfg.drawControl=="atlas") {\n                if(cfg.benchmark!="scene"'
    after='if(cfg.drawControl=="atlas" && !cfg.presentationCheck) {\n                if(cfg.benchmark!="scene"'
    assert value.count(before)==1
    changed=value.replace(before,after,1)
    assert changed.replace(after,before,1)==value
    return changed

def helper_source():
    value=(PAGED/'tests/SceneCameraRasterTrial.as').read_text('utf-8-sig')
    edits=[('version:"camera-atlas-paged-trial-2"','version:"camera-atlas-pool-idle-2",poolPreparation:[]'),
        ('report.prepareMs=getTimer()-prepareAt;report.prepareEnd=snapshot();',
         'report.prepareMs=getTimer()-prepareAt;report.prepareEnd=snapshot();preparePool("before-pixels");'),
        ('presenter.clear();applyCamera(views[0].x,views[0].y);',
         'presenter.clear();applyCamera(views[0].x,views[0].y);preparePool("before-timing");'),
        ('presenter.update(world,row.atlas);',
         'if(row.atlas)presenter.update(world,true);else presenter.useNativeForTest();'),
        ('        private function applyFrame():void {',
'''        private function preparePool(label:String):void {
            var item:Object={label:label,startedAtMs:getTimer(),before:presenter.snapshot(),memoryBefore:System.totalMemory};
            presenter.preallocate(world);
            item.endedAtMs=getTimer();item.after=presenter.snapshot();item.memoryAfter=System.totalMemory;
            report.poolPreparation.push(item);
        }

        private function applyFrame():void {''')]
    original=value
    for before,after in edits:
        assert value.count(before)==1,(before,value.count(before));value=value.replace(before,after,1)
    reverse=value
    for before,after in reversed(edits):
        assert reverse.count(after)==1;reverse=reverse.replace(after,before,1)
    assert reverse==original
    return value


original_helper_source=helper_source
def helper_source():
    source=original_helper_source()
    edits=[('row.atlasStates.push(pending.atlas);',
        'row.atlasStates.push(pending.atlas);row.cameraMs.push(pending.cameraMs);row.presenterMs.push(pending.presenterMs);row.guardMs.push(pending.guardMs);row.snapshotMs.push(pending.snapshotMs);'),
        ('workMs:[],presented:[],atlasStates:[],','workMs:[],presented:[],atlasStates:[],cameraMs:[],presenterMs:[],guardMs:[],snapshotMs:[],'),
        ('            if(row.atlas)presenter.update(world,true);else presenter.useNativeForTest();',
         '            var cameraEnd:int=getTimer();\n            if(row.atlas)presenter.update(world,true);else presenter.useNativeForTest();\n            var presenterEnd:int=getTimer();'),
        ('            checkTransform();guard();\n            pending=',
         '            checkTransform();guard();var guardEnd:int=getTimer();\n            pending='),
        ('atlas:presenter.snapshot(),workMs:getTimer()-at};',
         'atlas:presenter.snapshot(),workMs:getTimer()-at};\n            var end:int=getTimer();pending.workMs=end-at;\n            pending.cameraMs=cameraEnd-at;pending.presenterMs=presenterEnd-cameraEnd;\n            pending.guardMs=guardEnd-presenterEnd;pending.snapshotMs=end-guardEnd;')]
    result=source
    for before,after in edits:
        assert result.count(before)==1,(before,result.count(before));result=result.replace(before,after,1)
    reverse=result
    for before,after in reversed(edits):
        assert reverse.count(after)==1;reverse=reverse.replace(after,before,1)
    assert reverse==source
    return result


PRESENTER_EDITS=[
    ('        public var copies:int=0;', '        private var stationarySkips:int=0;\n        public var copies:int=0;'),
    ('            var view:Rectangle=g.sceneViewport();',
'            // beginFrame already restored native tiles. Nothing cached is shown\n            // at rest; native mutations remain visible immediately. Movement\n            // resumes through the complete revision/visibility synchronization.\n            if(!forcePresentation && poseValid && nextX==poseX && nextY==poseY && nextScale==poseScale){\n                ++stationarySkips;return;\n            }\n            var view:Rectangle=g.sceneViewport();'),
    ('return {version:"atlas-pool-1",', 'return {version:"atlas-pool-1",stationarySkips:stationarySkips,')]

stage_cost_helper=helper_source
def helper_source():
    value=stage_cost_helper()
    edits=[('    import flash.utils.getQualifiedClassName;',
        '    import flash.display.PNGEncoderOptions;\n    import flash.filesystem.File;\n    import flash.filesystem.FileMode;\n    import flash.filesystem.FileStream;\n    import flash.utils.getDefinitionByName;\n    import flash.utils.getQualifiedClassName;'),
        ('report.complete=true;report.passed=true;clear(w);',
        'report.stationaryRefresh=[];stationaryRefresh(false);stationaryRefresh(true);\n                            report.complete=true;report.passed=true;clear(w);'),
        ('        private function capture():BitmapData {',
        (HERE/'tests/StationaryRefresh.as.inc').read_text('utf-8-sig')+'\n        private function capture():BitmapData {')]
    original=value
    for before,after in edits:
        assert value.count(before)==1;value=value.replace(before,after,1)
    reverse=value
    for before,after in reversed(edits):reverse=reverse.replace(after,before,1)
    assert reverse==original
    return value

def prepare(source:Path,destination:Path):
    assert not destination.exists() and not (source/CHANGED[2]).exists()
    assert hashlib.sha256((POOL/'SceneRasterPresentation.as').read_bytes()).hexdigest().upper()==PRESENTER_SHA
    baseline=pool_patch.transform_presenter((source/CHANGED[1]).read_text('utf-8-sig'))
    current=(POOL/'SceneRasterPresentation.as').read_text('utf-8-sig')
    for before,after in reversed(PRESENTER_EDITS):
        assert current.count(after)==1
        current=current.replace(after,before,1)
    assert current==baseline
    assert HELPER.read_text('utf-8-sig')==helper_source()
    shutil.copytree(source,destination)
    (destination/CHANGED[0]).write_text(transform_main((source/CHANGED[0]).read_text('utf-8-sig')),'utf-8',newline='\n')
    shutil.copy2(POOL/'SceneRasterPresentation.as',destination/CHANGED[1])
    shutil.copy2(HELPER,destination/CHANGED[2])

if __name__=='__main__':
    assert not HELPER.exists();HELPER.parent.mkdir(parents=True,exist_ok=True)
    HELPER.write_text(helper_source(),'utf-8',newline='\n')
    print('Prepared source only; no compiler, AIR, or deployment')
