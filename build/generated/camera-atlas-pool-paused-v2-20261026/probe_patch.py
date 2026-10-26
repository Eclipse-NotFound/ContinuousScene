from pathlib import Path
import importlib.util
import shutil
import hashlib

HERE=Path(__file__).resolve().parent
PAGED=HERE.parent/'camera-atlas-paged-20261025'
POOL=HERE.parent/'camera-atlas-pool-20261026'
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
CHANGED=['ContinuousSceneMotionProbe.as','SceneRasterPresentation.as','tests/SceneCameraRasterTrial.as']
VERSION='camera-atlas-pool-paused-2'
PRESENTER_SHA='35956ECD2307521D7AEC2F0D6D62C45DE2E251E44AE799365C5DF9BCCBB20372'

def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
paged_patch=load('pool_paused_paged_patch',PAGED/'probe_patch.py')
pool_patch=load('pool_paused_pool_patch',POOL/'probe_patch.py')

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
    edits=[('version:"camera-atlas-paged-trial-2"','version:"camera-atlas-pool-paused-2",poolPreparation:[]'),
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

def prepare(source:Path,destination:Path):
    assert not destination.exists() and not (source/CHANGED[2]).exists()
    assert hashlib.sha256((POOL/'SceneRasterPresentation.as').read_bytes()).hexdigest().upper()==PRESENTER_SHA
    assert (POOL/'SceneRasterPresentation.as').read_text('utf-8-sig')==pool_patch.transform_presenter(
        (source/CHANGED[1]).read_text('utf-8-sig'))
    assert HELPER.read_text('utf-8-sig')==helper_source()
    shutil.copytree(source,destination)
    (destination/CHANGED[0]).write_text(transform_main((source/CHANGED[0]).read_text('utf-8-sig')),'utf-8',newline='\n')
    shutil.copy2(POOL/'SceneRasterPresentation.as',destination/CHANGED[1])
    shutil.copy2(HELPER,destination/CHANGED[2])

if __name__=='__main__':
    assert not HELPER.exists();HELPER.parent.mkdir(parents=True,exist_ok=True)
    HELPER.write_text(helper_source(),'utf-8',newline='\n')
    print('Prepared source only; no compiler, AIR, or deployment')
