"""Isolate only the reversible backdrop control; never touch object-layer opacity."""
from pathlib import Path
import importlib.util

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'camera-display-contribution-20261026'

def once(value,before,after):
    assert value.count(before)==1,(before,value.count(before))
    return value.replace(before,after,1)
def save(name,value):
    target=HERE/name;assert not target.exists()
    target.parent.mkdir(parents=True,exist_ok=True)
    if name.endswith('.py'):compile(value,name,'exec')
    target.write_text(value,'utf-8',newline='\n')

patch=r'''from pathlib import Path
import importlib.util
import shutil
import hashlib

HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-display-contribution-20261026/probe_patch.py'
ORIGINAL=HERE.parent/'camera-display-contribution-20261026/tests/SceneCameraRasterTrial.as'
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
CHANGED=['ContinuousSceneMotionProbe.as','tests/SceneCameraRasterTrial.as']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
s=importlib.util.spec_from_file_location('backdrop_display_patch',PATCH_SOURCE)
base=importlib.util.module_from_spec(s);s.loader.exec_module(base)
EXTRA_INPUTS=(base.ORIGINAL,base.PATCH_SOURCE,*base.EXTRA_INPUTS)

def helper_source():
    source=ORIGINAL.read_text('utf-8-sig');assert source==base.helper_source()
    edits=[
        ('version:"camera-display-contribution-1"','version:"camera-backdrop-contribution-1"'),
        ('private var order:Array=[0,1,2,3,3,2,1,0];','private var order:Array=[0,1,1,0,0,1,1,0];'),
        ('[grafon.visFon,grafon.visObjs[0],grafon.visObjs[1],grafon.visObjs[2],grafon.visObjs[3],grafon.visObjs[4],grafon.visObjs[5]]','[grafon.visFon]'),
        ('if(terrain.length==7)','if(terrain.length==1)'),
        ('for(var mode:int=1;mode<=3;++mode)','for(var mode:int=1;mode<=1;++mode)'),
        ('require(condition>=0 && condition<=3,"Invalid terrain condition");','require(condition>=0 && condition<=1,"Invalid backdrop condition");'),
        ('if(value.length!=7)return false;','if(value.length!=1)return false;'),
        ('for(var i:int=0;i<7;++i)','for(var i:int=0;i<1;++i)'),
        ('["native-moving","backdrop-zero-moving","objects-zero-moving","backdrop-objects-zero-moving"]','["native-moving","backdrop-zero-moving"]'),
        ('Paused attribution only: native scenery backdrop and six object-layer parents use temporary alpha zero; all camera windows moving.',
         'Paused attribution only: native scenery backdrop temporarily uses alpha zero; object layers remain untouched; every window moves the camera.')]
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
run=(OLD/'run.py').read_text('utf-8-sig').replace('camera-display-contribution-1','camera-backdrop-contribution-1')
edits=[
    ('Paused moving-camera backdrop/object alpha attribution; diagnostic only.','Paused moving-camera backdrop-only alpha attribution; diagnostic only.'),
    ("trial['pixelBitmapsDisposed']==35","trial['pixelBitmapsDisposed']==15"),
    ("len(row['conditions'])==3","len(row['conditions'])==1"),
    ('for i in range(3):','for i in range(1):'),
    ("('native-moving','backdrop-zero-moving','objects-zero-moving','backdrop-objects-zero-moving')","('native-moving','backdrop-zero-moving')"),
    ('(0,1,2,3,3,2,1,0)','(0,1,1,0,0,1,1,0)'),
    ("len(trial['terrainInitial'])==7","len(trial['terrainInitial'])==1"),
    ('((0,1),(0,2),(0,3),(7,6),(7,5),(7,4))','((0,1),(3,2),(4,5),(7,6))'),
    ('camera display contribution / 01a13816','camera backdrop contribution / 01a13816'),
    ('960 camera backdrop/object-layer alpha controls; diagnostic only, no deployment','960 camera backdrop-only alpha controls; diagnostic only, no deployment')]
for before,after in edits:run=once(run,before,after)
save('run.py',run)
save('README.md','''# 仅远景的镜头移动归因

前一display-contribution的对象层alpha恢复出现1567像素差，0性能样本，停止该控制。远景在首视口恢复精确，单独隔离验证。
本轮只读/临时写grafon.visFon.alpha，不读写任何visObjs父层alpha或visible。原版视觉/逻辑对象保持运行状态；世界仍处于诊断暂停。
八窗120帧按原生/远景零透明/远景零透明/原生重复两次，总960帧；每窗都沿同一路线移动，所有长帧保留。
五视口原生/远景抑制/恢复共15图，恢复必须完全一致；八地形计数逐帧不变、玩家状态/父级/镜头/帧率与清理全部验证。
这里只测成本构成，不把省略远景作为产品方案，不声称游戏帧率或CPU/GPU原因。正式文件、存档不变。
''')
spec=importlib.util.spec_from_file_location('backdrop_contribution_patch',HERE/'probe_patch.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
save('tests/SceneCameraRasterTrial.as',m.helper_source())
print('Prepared backdrop-only attribution; no compiler, AIR or deployment')

