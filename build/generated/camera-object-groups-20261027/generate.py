"""Create independent binary layer-attribution fixtures from the checked seed.

Each instance starts from its own native combat state. Pixel restoration failure
terminates that instance before timing; another group never inherits its caches.
"""
from pathlib import Path
import ast

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PATCH_TEMPLATE = '''"""Single object group, unchanged alpha/restoration protocol."""
from pathlib import Path
import importlib.util
import shutil
HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-display-pixels-20261027/probe_patch.py'
spec=importlib.util.spec_from_file_location('binary_objects_seed',PATCH_SOURCE)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
ORIGINAL=base.HELPER
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
CHANGED=base.CHANGED
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,HERE/'prepare.py',HERE.parent/'camera-object-groups-20261027/generate.py')
VERSION=__VERSION__
INDICES=__INDICES__

def helper_source():
    source=ORIGINAL.read_text('utf-8-sig');assert source==base.helper_source()
    targets='['+','.join('grafon.visObjs['+str(i)+']' for i in INDICES)+']'
    edits=[
      ('camera-display-pixels-1',VERSION),
      ('[grafon.visFon,grafon.visObjs[0],grafon.visObjs[1],grafon.visObjs[2],grafon.visObjs[3],grafon.visObjs[4],grafon.visObjs[5]]',targets),
      ('terrain.length==7','terrain.length=='+str(len(INDICES))),
      ('value.length!=7','value.length!='+str(len(INDICES))),
      ('i<7','i<'+str(len(INDICES))),
      ('[0,1,2,3,3,2,1,0]','[0,1,1,0]'),
      ('measurementFrames:960','measurementFrames:480'),
      ('mode<=3','mode<=1'),('condition<=3','condition<=1'),
      ('(i==0?(condition&1):(condition&2))','(condition&1)'),
      ('["native-moving","backdrop-zero-moving","objects-zero-moving","backdrop-objects-zero-moving"]','["native-moving","group-zero-moving"]'),
      ('Paused attribution only: native scenery backdrop and six object-layer parents use temporary alpha zero; all camera windows moving.',
       'Paused attribution only: object layers '+str(INDICES)+' use temporary alpha zero; all other parents remain native.')]
    for old,new in edits:
        assert old in source,old;source=source.replace(old,new)
    return source

def transform(source):return base.transform(source)

def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert not destination.exists() and not (source/CHANGED[1]).exists()
    shutil.copytree(source,destination)
    main=destination/CHANGED[0];main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/CHANGED[1])
'''

PREPARE = '''from pathlib import Path
import importlib.util
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('binary_objects_patch',HERE/'probe_patch.py')
patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)
content=patch.helper_source();patch.HELPER.parent.mkdir(parents=True,exist_ok=True)
if patch.HELPER.exists():assert patch.HELPER.read_text('utf-8-sig')==content
else:patch.HELPER.write_text(content,'utf-8')
print('Prepared independent binary object-layer attribution')
'''

def write_new(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        assert path.read_text('utf-8-sig') == content, path
    else:
        path.write_text(content, 'utf-8')

for name, indices, label in (
    ('camera-roles-alpha-20261027', [2], '角色层'),
    ('camera-upper-alpha-20261027', [3, 4, 5], '上层效果与文字'),
):
    folder=ROOT/name
    version=name.replace('-20261027','-1')
    patch=PATCH_TEMPLATE.replace('__VERSION__',repr(version)).replace('__INDICES__',repr(indices))
    ast.parse(patch);ast.parse(PREPARE)
    write_new(folder/'probe_patch.py',patch)
    write_new(folder/'prepare.py',PREPARE)
    runner=(ROOT/'camera-lower-objects-20261027/run.py').read_text('utf-8-sig')
    edits=[
        ('camera-lower-objects-1',version),
        ("trial['pixelBitmapsDisposed']==35","trial['pixelBitmapsDisposed']==15"),
        ("len(row['conditions'])==3","len(row['conditions'])==1"),
        ('for i in range(3):','for i in range(1):'),
        ("len(trial['windows'])==8","len(trial['windows'])==4"),
        ("len(trial['sampleAtMs'])==960","len(trial['sampleAtMs'])==480"),
        ("('native-moving','objects0-zero-moving','objects1-zero-moving','objects01-zero-moving')","('native-moving','group-zero-moving')"),
        ('(0,1,2,3,3,2,1,0)','(0,1,1,0)'),
        ("len(trial['terrainInitial'])==2","len(trial['terrainInitial'])=="+str(len(indices))),
        ('(condition & (1 if j==0 else 2))','(condition & 1)'),
        ('((0,1),(0,2),(0,3),(7,6),(7,5),(7,4))','((0,1),(3,2))'),
        ('camera lower object layers / 01a13816',name+' / 01a13816'),
    ]
    for old,new in edits:
        assert old in runner,old
        runner=runner.replace(old,new)
    ast.parse(runner)
    write_new(folder/'run.py',runner)
    write_new(folder/'README.md',f'''# {label}独立归因

只把 visObjs{indices} 的父层临时设为 alpha=0，再恢复保存值。
它是缺失画面的归因诊断，不是优化候选。保持原来的精确恢复要求；
五视口恢复均相同后，才测 480 帧相同镜头路线的原生/隐藏/隐藏/原生。
每组独立启动，避免继承另一组隐藏后的内部缓存状态。主菜单走原生退出，
唯一 AIR ID/存储、独立桌面、共享登记、4GiB 提交余量与输入核验保持。
不修改产品、正式名单、用户存档或其他进程。任何恢复失败均停止计时。
''')
    print(name,indices)
