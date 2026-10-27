from pathlib import Path
import ast
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-live-parking-groups-20261027'
VERSION='camera-live-parking-safe-groups-1'
def one(s,a,b):
    assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
def generated():
    out={}
    for name in ['tests/SceneFarParkingTrial.as','probe_patch.py','summary.py','README.md','run.py']:
        s=(BASE/name).read_text('utf-8-sig').replace('camera-live-parking-groups-1',VERSION)
        if name.endswith('.as'):
            s=one(s,'            if(!on) {if(enabled)restoreAll();}', '            if(!on || w.gg.lurk>0) {if(enabled)restoreAll();}')
            s=one(s,'                    var tele:*=w.gg.teleObj,lurk:*=w.gg.lurkBox;\n                    if(tele || lurk)for each(var target:Object in group.items)if(!target.retired && (target.owner===tele || target.owner===lurk)){near=true;break;}',
                '                    var tele:*=w.gg.teleObj;\n                    if(tele)for each(var target:Object in group.items)if(!target.retired && target.owner===tele){near=true;break;}')
        if name=='probe_patch.py':s=one(s,"EXTRA_INPUTS=(HERE/'prepare.py',HERE/'summary.py',", "EXTRA_INPUTS=(HERE/'prepare.py',HERE/'summary.py',HERE.parent/'camera-live-parking-groups-20261027/tests/SceneFarParkingTrial.as',HERE.parent/'camera-live-parking-groups-20261027/probe_patch.py',HERE.parent/'camera-live-parking-groups-20261027/summary.py',HERE.parent/'camera-live-parking-groups-20261027/README.md',HERE.parent/'camera-live-parking-groups-20261027/run.py',")
        if name=='README.md':s+='\n前驱首次启用时读取不存在的公开lurkBox字段而失败，仅有一个原生窗口、0暂存写入。本修复沿旧SceneObjectCulling已使用的lurk状态，藏身时恢复全部原生根。当前纯跑动射击不会验证藏身分支。\n'
        out[name]=s
    return out
if __name__=='__main__':
    for name,s in generated().items():
        p=HERE/name;p.parent.mkdir(exist_ok=True)
        if p.suffix=='.py':ast.parse(s)
        if p.exists():assert p.read_text('utf-8-sig')==s
        else:p.write_text(s,'utf-8')
    print('Prepared native lurk-state fallback; failed runtime retained')
