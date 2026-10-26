"""Attribute remaining moving-camera display costs without changing gameplay code."""
from pathlib import Path
import importlib.util
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'camera-terrain-layers-20261025'
VERSION='camera-display-contribution-1'

def once(value,before,after,count=1):
    assert value.count(before)==count,(before,value.count(before))
    return value.replace(before,after)
def save(name,value):
    target=HERE/name
    if target.exists():
        assert target.read_text('utf-8-sig')==value
        return
    target.parent.mkdir(parents=True,exist_ok=True)
    if name.endswith('.py'):compile(value,name,'exec')
    target.write_text(value,'utf-8',newline='\n')

patch=r'''"""Only temporary alpha controls for a paused moving-camera attribution."""
from pathlib import Path
import importlib.util
import shutil
import hashlib

HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-terrain-layers-20261025/probe_patch.py'
ORIGINAL=HERE.parent/'camera-terrain-layers-20261025/tests/SceneCameraRasterTrial.as'
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
CHANGED=['ContinuousSceneMotionProbe.as','tests/SceneCameraRasterTrial.as']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
s=importlib.util.spec_from_file_location('display_contribution_terrain_patch',PATCH_SOURCE)
base=importlib.util.module_from_spec(s);s.loader.exec_module(base)
EXTRA_INPUTS=(base.ORIGINAL,base.PATCH_SOURCE,*base.EXTRA_INPUTS)

def helper_source():
    source=ORIGINAL.read_text('utf-8-sig');assert source==base.helper_source()
    edits=[
        ('version:"camera-terrain-layers-1"','version:"camera-display-contribution-1"'),
        ('[grafon.visBack,grafon.visBack2,grafon.visFront,grafon.visVoda]','[grafon.visFon,grafon.visObjs[0],grafon.visObjs[1],grafon.visObjs[2],grafon.visObjs[3],grafon.visObjs[4],grafon.visObjs[5]]'),
        ('require(layer!=null && layer.parent===world.visual,"Terrain parent identity mismatch");','require(layer!=null && layer.parent!=null && isFinite(layer.alpha),"Display parent identity mismatch");'),
        ('terrain.push({target:layer,visible:layer.visible});','terrain.push({target:layer,parent:layer.parent,alpha:layer.alpha});'),
        ('World stays visible; only native terrain parents are temporarily suppressed, all camera windows moving.',
         'Paused attribution only: native scenery backdrop and six object-layer parents use temporary alpha zero; all camera windows moving.'),
        ('["native-moving","back-hidden-moving","front-hidden-moving","terrain-hidden-moving"]',
         '["native-moving","backdrop-zero-moving","objects-zero-moving","backdrop-objects-zero-moving"]'),
        ('if(terrain.length==4)','if(terrain.length==7)'),
        ('item.target.visible=item.visible && !(i<2?(condition&1):(condition&2));',
         'require(item.target.parent===item.parent,"Display parent changed during attribution");\n                item.target.alpha=(i==0?(condition&1):(condition&2))?0:item.alpha;'),
        ('value.push(item.target.visible)','value.push(item.target.alpha)'),
        ('if(value.length!=4)return false;','if(value.length!=7)return false;'),
        ('for(var i:int=0;i<4;++i)if(value[i]!==Boolean(terrain[i].visible && !(i<2?(condition&1):(condition&2))))return false;',
         'for(var i:int=0;i<7;++i)if(value[i]!==Number((i==0?(condition&1):(condition&2))?0:terrain[i].alpha))return false;')]
    value=source
    for before,after in edits:
        assert value.count(before)==1,(before,value.count(before));value=value.replace(before,after,1)
    reverse=value
    for before,after in reversed(edits):reverse=reverse.replace(after,before,1)
    assert reverse==source
    return value

def transform(source):return base.transform(source)

def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert not destination.exists() and not (source/CHANGED[1]).exists()
    shutil.copytree(source,destination)
    main=destination/CHANGED[0];main.write_text(transform(main.read_text('utf-8-sig')),'utf-8',newline='\n')
    shutil.copy2(HELPER,destination/CHANGED[1])
'''
save('probe_patch.py',patch)
run=(OLD/'run.py').read_text('utf-8-sig').replace('camera-terrain-layers-1',VERSION)
run=once(run,"LINEAGE = HERE/'lineage.py'","LINEAGE = HERE.parent/'camera-terrain-layers-20261025/lineage.py'") if "LINEAGE = HERE/'lineage.py'" in run else run
# Preserve the exact repaired registry adapter, without copying or weakening it.
run=once(run,"HERE/'lineage.py'","HERE.parent/'camera-terrain-layers-20261025/lineage.py'",3) if "HERE/'lineage.py'" in run else run
run=once(run,"HERE/'prepare_runner.py'","HERE/'prepare.py'")
run=once(run,'Paused camera motion versus whole-world visibility; diagnostic only.','Paused moving-camera backdrop/object alpha attribution; diagnostic only.')
run=once(run,"('native-moving','back-hidden-moving','front-hidden-moving','terrain-hidden-moving')",
    "('native-moving','backdrop-zero-moving','objects-zero-moving','backdrop-objects-zero-moving')")
run=once(run,"expected=[bool(initial_visible and not (condition & (1 if j<2 else 2))) for j,initial_visible in enumerate(trial['terrainInitial'])]",
    "assert len(trial['terrainInitial'])==7\n        expected=[0 if (condition & (1 if j==0 else 2)) else initial_alpha for j,initial_alpha in enumerate(trial['terrainInitial'])]")
run=once(run,'Terrain suppression is diagnostic, not a gameplay proposal.','Display alpha suppression is diagnostic, not a gameplay proposal.') if 'Terrain suppression is diagnostic, not a gameplay proposal.' in run else run
run=once(run,'terrain suppression is diagnostic, not a gameplay proposal.','display alpha suppression is diagnostic, not a gameplay proposal.')
run=once(run,'camera terrain layers / 01a13816','camera display contribution / 01a13816')
run=once(run,'960 moving camera terrain-layer controls; diagnostic only, no deployment','960 camera backdrop/object-layer alpha controls; diagnostic only, no deployment')
# This file's source is part of the frozen recipe.
run=once(run,"HERE/'run.py',HERE/'probe_patch.py',HERE/'README.md',","HERE/'run.py',HERE/'prepare.py',HERE/'probe_patch.py',HERE/'README.md',") if "HERE/'run.py',HERE/'probe_patch.py',HERE/'README.md'," in run else run
save('run.py',run)
save('README.md','''# 移动镜头的远景与对象层开销归因

页合图在暂停路线约15%改善，实战首轮仅6%。本轮不加优化，用同一960帧/五视口路线确认剩余绘制成本在哪。
四种条件全程相同镜头移动：完整画面；仅远景alpha=0；仅六个对象父层alpha=0；两组均0。世界visible、模拟对象、地形、碰撞不改。
World.onPause为诊断暂停，六对象层包含人物/物品/效果；不能当真实无敌人游戏帧率，更不是产品隐藏画面的方案。
不调用失败的整世界visible切换。逐一保存原alpha/父级，五视口的15次恢复必须像素完全相同，才进入计时。
每帧核对全部七个alpha、原生八项地形计数、同路线与玩家状态，35张截图释放，终态恢复alpha/矩阵/帧率/暂停。
保留所有切换、观测和长帧；严格冻结现有宿主/模组，私有桌面、共享登记、4GB预检及本轮所有者清理不变。无部署。
''')
spec=importlib.util.spec_from_file_location('display_contribution_patch',HERE/'probe_patch.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
save('tests/SceneCameraRasterTrial.as',m.helper_source())
print('Prepared attribution source only; no compiler, AIR or deployment')

