"""Prepare a bounded pool shortcut and terminal native-mutation verification."""
from pathlib import Path
import hashlib
import importlib.util

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'camera-atlas-pool-stage-cost-20261026'
POOL=HERE.parent/'camera-atlas-pool-20261026'
VERSION='camera-atlas-pool-idle-1'

def replace_once(source,before,after):
    assert source.count(before)==1,(before,source.count(before))
    value=source.replace(before,after,1)
    assert value.replace(after,before,1)==source
    return value

def save(name,source):
    target=HERE/name
    assert not target.exists(),target
    target.parent.mkdir(parents=True,exist_ok=True)
    if name.endswith('.py'):compile(source,name,'exec')
    target.write_text(source,'utf-8',newline='\n')

presenter=(POOL/'SceneRasterPresentation.as').read_text('utf-8-sig')
assert hashlib.sha256((POOL/'SceneRasterPresentation.as').read_bytes()).hexdigest().upper()=='35956ECD2307521D7AEC2F0D6D62C45DE2E251E44AE799365C5DF9BCCBB20372'
presenter=replace_once(presenter,'        public var copies:int=0;',
    '        private var stationarySkips:int=0;\n        public var copies:int=0;')
presenter=replace_once(presenter,'            var view:Rectangle=g.sceneViewport();',
'''            // beginFrame already restored native tiles. Nothing cached is shown
            // at rest; native mutations remain visible immediately. Movement
            // resumes through the complete revision/visibility synchronization.
            if(!forcePresentation && poseValid && nextX==poseX && nextY==poseY && nextScale==poseScale){
                ++stationarySkips;return;
            }
            var view:Rectangle=g.sceneViewport();''')
presenter=replace_once(presenter,'return {version:"atlas-pool-1",',
    'return {version:"atlas-pool-1",stationarySkips:stationarySkips,')
save('SceneRasterPresentation.as',presenter)
presenter_sha=hashlib.sha256((HERE/'SceneRasterPresentation.as').read_bytes()).hexdigest().upper()

patch=(OLD/'probe_patch.py').read_text('utf-8-sig').replace('camera-atlas-pool-stage-cost-1',VERSION)
patch=replace_once(patch,"POOL=HERE.parent/'camera-atlas-pool-20261026'","POOL=HERE")
patch=replace_once(patch,"pool_patch=load('pool_paused_pool_patch',POOL/'probe_patch.py')",
    "pool_patch=load('pool_paused_pool_patch',HERE.parent/'camera-atlas-pool-20261026'/'probe_patch.py')")
patch=replace_once(patch,"PRESENTER_SHA='35956ECD2307521D7AEC2F0D6D62C45DE2E251E44AE799365C5DF9BCCBB20372'",
    "PRESENTER_SHA='"+presenter_sha+"'")
patch=replace_once(patch,"    assert (POOL/'SceneRasterPresentation.as').read_text('utf-8-sig')==pool_patch.transform_presenter(\n        (source/CHANGED[1]).read_text('utf-8-sig'))",
'''    baseline=pool_patch.transform_presenter((source/CHANGED[1]).read_text('utf-8-sig'))
    current=(POOL/'SceneRasterPresentation.as').read_text('utf-8-sig')
    for before,after in reversed(PRESENTER_EDITS):
        assert current.count(after)==1
        current=current.replace(after,before,1)
    assert current==baseline''')
extra_patch='''
PRESENTER_EDITS=[
    ('        public var copies:int=0;', '        private var stationarySkips:int=0;\\n        public var copies:int=0;'),
    ('            var view:Rectangle=g.sceneViewport();',
''' + repr('''            // beginFrame already restored native tiles. Nothing cached is shown
            // at rest; native mutations remain visible immediately. Movement
            // resumes through the complete revision/visibility synchronization.
            if(!forcePresentation && poseValid && nextX==poseX && nextY==poseY && nextScale==poseScale){
                ++stationarySkips;return;
            }
            var view:Rectangle=g.sceneViewport();''') + '''),
    ('return {version:"atlas-pool-1",', 'return {version:"atlas-pool-1",stationarySkips:stationarySkips,')]

stage_cost_helper=helper_source
def helper_source():
    value=stage_cost_helper()
    edits=[('    import flash.utils.getQualifiedClassName;',
        '    import flash.utils.getDefinitionByName;\\n    import flash.utils.getQualifiedClassName;'),
        ('report.complete=true;report.passed=true;clear(w);',
        'report.stationaryRefresh=[];stationaryRefresh(false);stationaryRefresh(true);\\n                            report.complete=true;report.passed=true;clear(w);'),
        ('        private function capture():BitmapData {',
        (HERE/'tests/StationaryRefresh.as.inc').read_text('utf-8-sig')+'\\n        private function capture():BitmapData {')]
    original=value
    for before,after in edits:
        assert value.count(before)==1;value=value.replace(before,after,1)
    reverse=value
    for before,after in reversed(edits):reverse=reverse.replace(after,before,1)
    assert reverse==original
    return value

'''
patch=replace_once(patch,'def prepare(source:Path,destination:Path):',extra_patch+'def prepare(source:Path,destination:Path):')
save('probe_patch.py',patch)

run=(OLD/'run.py').read_text('utf-8-sig').replace('camera-atlas-pool-stage-cost-1',VERSION)
run=replace_once(run,"HERE/'README.md',HERE/'prepare.py',patch.HELPER,patch.PAGED/'tests/SceneCameraRasterTrial.as',",
    "HERE/'README.md',HERE/'prepare.py',HERE/'SceneRasterPresentation.as',HERE/'tests/StationaryRefresh.as.inc',patch.HELPER,patch.PAGED/'tests/SceneCameraRasterTrial.as',")
run=replace_once(run,"verify_scope=dict(paused.__dict__);exec(compile(verify_source,'<pool-paused-verified-checks>','exec'),verify_scope)",
    "assert verify_source.count(\"trial['pixelBitmapsDisposed'] == 19\")==1\nverify_source=verify_source.replace(\"trial['pixelBitmapsDisposed'] == 19\",\"trial['pixelBitmapsDisposed'] == 31\",1)\nverify_scope=dict(paused.__dict__);exec(compile(verify_source,'<pool-paused-verified-checks>','exec'),verify_scope)")
extra_summary='''
stage_cost_summary=summarize
def summarize(raw):
    value=stage_cost_summary(raw);trial=raw['cameraRaster']
    changes=trial['stationaryRefresh'];assert len(changes)==2
    for index,item in enumerate(changes):
        assert item['breakWall'] is bool(index) and item['passed']
        assert item['endedAtMs']>=item['startedAtMs']>=trial['timingEndAtMs']
        assert item['nativeChanged']['differentPixels']>0 and item['changedSurfaceRevisions']>0
        assert item['staticExact']['equal'] and item['restoreExact']['equal']
        assert item['movingPixels']['maxAlpha']==0 and item['movingPixels']['maxRGB']<=2
        before,skipped,moving=item['before'],item['skipped'],item['moving']
        assert skipped['stationarySkips']==before['stationarySkips']+1 and not skipped['presented']
        assert skipped['copies']==before['copies'] and skipped['rebuilds']==before['rebuilds']
        assert moving['presented'] and moving['copies']>skipped['copies']
        assert all(s['allocations']==64 and s['disposals']==32 for s in (before,skipped,moving))
        if index:assert item['nativeAction']['phis']==0
        else:assert item['nativeAction']['tilehit'] and item['nativeAction']['babah'] and item['nativeAction']['detached']
    for row in trial['windows']:
        if row['mode']=='atlas-static':
            states=row['atlasStates']
            assert states[-1]['stationarySkips']-states[0]['stationarySkips']==119
            for state in states[1:]:
                assert state['copies']==states[0]['copies'] and state['rebuilds']==states[0]['rebuilds']
                assert state['currentPageKeys']==[] and not state['presented']
    value['stationaryRefresh']=changes
    value['limits'].append('Native detached impact and wall-break checks run after timing; no player-fire or combat-performance claim.')
    return value

'''
run=replace_once(run,'original_main=inspect.getsource(framework.framework.framework.main)',
    extra_summary+'original_main=inspect.getsource(framework.framework.framework.main)')
save('run.py',run)
save('README.md',f'''# 固定池静止路径与恢复移动验证

仅候选、无部署。以35956ECD固定池为基线，保留所有场景/父层/SATS/几何门控。
镜头不动且非强制像素比较时，beginFrame已经恢复原生图，只跳过无用缓存扫描。
再次移动仍先完成原生surface revision/可见性同步，再展示合图。

呈现器 SHA256：{presenter_sha}。
复用stage-cost的960帧路线、五视口、两几何回退、池计数和四段墙钟观察。
新增两个计时后终态检查：原生独立子弹击墙、原生hitTile毁墙；静止时确有像素/版本变化，
必须直接显示原生变化；镜头移动4像素后同步合图须RGB≤2、alpha完全一致，恢复原生必须精确。
新增12张完整截图，总31张，均释放。模拟仍暂停，独立子弹明确不算玩家开火或实战收益。
静止计时段每段后119帧须不发生扫描复制/重建、完全走原生显示。
不修改正式文件、外部WIP、真实存档，私有桌面与共享登记/4GB预检沿原运行器。
''')

spec=importlib.util.spec_from_file_location('idle_patch',HERE/'probe_patch.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
save('tests/SceneCameraRasterTrial.as',module.helper_source())
print('Prepared source only; presenter SHA256 '+presenter_sha)
