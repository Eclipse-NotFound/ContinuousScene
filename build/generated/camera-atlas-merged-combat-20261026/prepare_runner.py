"""Keep the native short combat fixture; substitute the verified page compositor."""
from pathlib import Path
import hashlib

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'camera-atlas-pool-20261026'
CANDIDATE=HERE.parent/'camera-atlas-pool-merged-20261026'
VERSION='camera-atlas-merged-combat-1'

def once(value,before,after):
    assert value.count(before)==1,(before,value.count(before))
    result=value.replace(before,after,1)
    assert result.replace(after,before,1)==value
    return result

def save(name,text):
    target=HERE/name;assert not target.exists()
    target.parent.mkdir(parents=True,exist_ok=True)
    if name.endswith('.py'):compile(text,name,'exec')
    target.write_text(text,'utf-8',newline='\n')

candidate=(CANDIDATE/'SceneRasterPresentation.as').read_text('utf-8-sig')
assert hashlib.sha256((CANDIDATE/'SceneRasterPresentation.as').read_bytes()).hexdigest().upper()=='BC0BCA76989B2C2A323D723BD4240F79A1EA48B5F69316A00F9F5D75C1B91E63'
save('SceneRasterPresentation.as',candidate)
save('probe_patch.py',r'''from pathlib import Path
import importlib.util
import hashlib
import shutil

HERE=Path(__file__).resolve().parent
VERSION='camera-atlas-merged-combat-1'
CHANGED=['ContinuousSceneMotionProbe.as','SceneRasterPresentation.as','tests/SceneCombatAtlasPixels.as']
CANDIDATE=HERE.parent/'camera-atlas-pool-merged-20261026'
PRESENTER_SOURCE=HERE.parent/'camera-atlas-paged-combat-20261025/SceneRasterPresentation.as'
PRESENTER_SHA='AD472C796A8006227C5523E51C5803511C2F3904AE0E970D08136BB37C02AD48'
CANDIDATE_SHA='BC0BCA76989B2C2A323D723BD4240F79A1EA48B5F69316A00F9F5D75C1B91E63'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
pool=load('merged_combat_pool_patch',HERE.parent/'camera-atlas-pool-20261026/probe_patch.py')
candidate=load('merged_combat_candidate_patch',CANDIDATE/'probe_patch.py')

def transform_main(source):
    value=pool.transform_main(source)
    assert value.count('camera-atlas-pool-combat-1')==2
    value=value.replace('camera-atlas-pool-combat-1',VERSION)
    before='    import tests.SceneAtlasChecks;'
    assert value.count(before)==1
    value=value.replace(before,before+'\n    import tests.SceneCombatAtlasPixels;',1)
    before='            closeProbeTiming(true);\n            if(cfg.drawControl=="atlas") {'
    after='            closeProbeTiming(true);\n            if(error==null && cfg.drawControl=="atlas" && report.samples.length==4) {\n                report.combatAtlasPixels=SceneCombatAtlasPixels.run(w,rasterPresentation);\n                check("combat-terminal-atlas-pixels",report.combatAtlasPixels.passed,report.combatAtlasPixels);\n            }\n            if(cfg.drawControl=="atlas") {'
    assert value.count(before)==1;value=value.replace(before,after,1)
    return value

def transform_presenter(source):
    value=pool.transform_presenter(source);baseline=value
    for before,after in candidate.PRESENTER_EDITS:
        assert value.count(before)==1,(before,value.count(before))
        value=value.replace(before,after,1)
    reverse=value
    for before,after in reversed(candidate.PRESENTER_EDITS):reverse=reverse.replace(after,before,1)
    assert reverse==baseline
    assert hashlib.sha256(value.encode('utf-8')).hexdigest().upper()==CANDIDATE_SHA
    return value

def prepare(source:Path,destination:Path):
    assert not destination.exists() and not (source/CHANGED[2]).exists()
    assert hashlib.sha256((source/CHANGED[1]).read_bytes()).hexdigest().upper()==PRESENTER_SHA
    shutil.copytree(source,destination)
    (destination/CHANGED[0]).write_text(transform_main((source/CHANGED[0]).read_text('utf-8-sig')),'utf-8',newline='\n')
    presenter=transform_presenter((source/CHANGED[1]).read_text('utf-8-sig'))
    assert presenter==(HERE/CHANGED[1]).read_text('utf-8-sig')
    (destination/CHANGED[1]).write_text(presenter,'utf-8',newline='\n')
    shutil.copy2(HERE/CHANGED[2],destination/CHANGED[2])
''')
run=(OLD/'run.py').read_text('utf-8-sig').replace('camera-atlas-pool-combat-1',VERSION)
run=once(run,"HERE/'README.md',HERE/'SceneRasterPresentation.as',HERE/'prepare_runner.py')",
    "HERE/'README.md',HERE/'SceneRasterPresentation.as',HERE/'prepare_runner.py',HERE/'tests/SceneCombatAtlasPixels.as',\n        patch.CANDIDATE/'probe_patch.py',patch.CANDIDATE/'SceneRasterPresentation.as',HERE.parent/'camera-atlas-pool-20261026/probe_patch.py')")
run=once(run,'changed==patch.CHANGED and len(after)==85','changed==patch.CHANGED and len(after)==86')
run=once(run,"len(value['frozenSourceSHA256'])==85","len(value['frozenSourceSHA256'])==86")
run=once(run,"    return value\n\ndef options(name):", "    assert r.sha(frozen/patch.CHANGED[2])==r.sha(HERE/patch.CHANGED[2])\n    return value\n\ndef options(name):")
run=once(run,"assert set(state['visiblePageKeys'])==set(state['currentPageKeys'])",
    "assert set(state['visiblePageKeys'])=={p['key'] for p in state['pages'] if p['key'] in state['currentPageKeys'] and any(p['layerHasPixels'])}")
extra='''
pool_verified_summary=summarize
def summarize(raw):
    value=pool_verified_summary(raw);pixels=raw['combatAtlasPixels']
    assert pixels['passed'] and pixels['error'] is None and pixels['presented']
    assert pixels['created']==pixels['disposed']==3 and pixels['stateRestored']
    assert pixels['atlas']['maxRGB']<=2 and pixels['atlas']['maxAlpha']==0 and pixels['restore']['equal']
    assert pixels['startedAtMs']>=raw['samples'][-1]['sampleAtMs'][-1]
    displayed=[];omitted=[]
    for row in raw['samples']:
        for state in row['atlasMotion']['states']:
            for page in state['pages']:
                content,shown=page['layerHasPixels'],page['layerVisible']
                assert len(content)==len(shown)==4 and all(type(x) is bool for x in content+shown)
                assert not content[1] and not shown[1]
                assert shown==[bool(state['presented'] and page['key'] in state['currentPageKeys'] and b) for b in content]
            if state['presented']:
                pages=[p for p in state['pages'] if p['key'] in state['currentPageKeys']]
                displayed.append(sum(sum(p['layerVisible']) for p in pages))
                omitted.append(sum(sum(not b for b in p['layerHasPixels']) for p in pages))
    assert displayed and max(omitted)>0
    value['combatTerminalPixels']=pixels
    value['layerCounts']=dict(displayed=base.metrics(displayed),omitted=base.metrics(omitted))
    value['limitations'].append('Three synchronous terminal combat screenshots are excluded from timing; one view does not cover all effects or every combat frame.')
    return value

'''
run=once(run,'original_main=inspect.getsource(framework.framework.main)',extra+'original_main=inspect.getsource(framework.framework.main)')
save('run.py',run)
save('README.md','''# 页级背景合成：真实移动与战斗对照

呈现器严格复用BC0BCA76，与已通过960帧/36截图/击墙毁墙/效果回退的候选同字节。
沿用35956池实战的六名原生SMG10、玩家原生移动/冲刺/开火/击退/碰撞/四段120帧夹具，不减少战斗负载。
原85源仅Main、Presenter变化并新增终态截图helper为86源；编译前反向核对候选与Main变换。
结束480帧计时后、正式清理前，同步拍原生/候选/恢复三张完整Stage图；RGB≤2、alpha0，恢复精确。
没有暂停/传送/隐藏对象/修改任何战斗状态，截图全部释放；单视口像素不能代表所有战斗帧与完整模组组合。
对照原生臂仍保留不可见固定池，无像素更新；预留200MiB耗时单列，不据此声称生产加载已整合。
全部前置输入、共享登记、独立桌面/存储、4GB余量及终态清理保持。无部署。
''')
print('Prepared combat runner only; candidate BC0BCA76 and original gameplay fixture retained')

