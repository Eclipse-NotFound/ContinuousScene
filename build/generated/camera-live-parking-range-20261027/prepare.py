from pathlib import Path
import ast
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-live-parking-groups-20261027'
VERSION='camera-live-parking-range-1'
def one(s,a,b):
    assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
def generated():
    out={}
    for name in ['tests/SceneFarParkingTrial.as','probe_patch.py','summary.py','README.md','run.py']:
        s=(BASE/name).read_text('utf-8-sig').replace('camera-live-parking-groups-1',VERSION)
        if name.endswith('.as'):
            s=one(s,'                view.inflate(1024,1024);', '                view.inflate(1024,1024);\n                var playerArea:Rectangle=new Rectangle(w.gg.X-1024,w.gg.Y-1024,2048,2048);')
            s=one(s,'                    var near:Boolean=bound==null || bound.isEmpty() || view.intersects(project(bound,parents[group.layer]));',
                '                    var projected:Rectangle=bound==null?null:project(bound,parents[group.layer]);\n                    var near:Boolean=projected==null || projected.isEmpty() || view.intersects(projected) || playerArea.intersects(projected);')
            s=one(s,'                    var tele:*=w.gg.teleObj,lurk:*=w.gg.lurkBox;\n                    if(tele || lurk)for each(var target:Object in group.items)if(!target.retired && (target.owner===tele || target.owner===lurk)){near=true;break;}',
                '                    var tele:*=w.gg.teleObj;\n                    if(tele)for each(var target:Object in group.items)if(!target.retired && target.owner===tele){near=true;break;}')
            s=one(s,'                        if(!freshGroup(group) || view.intersects(project(group.bounds,parents[group.layer])))continue;',
                '                        if(!freshGroup(group))continue;\n                        projected=project(group.bounds,parents[group.layer]);\n                        if(view.intersects(projected) || playerArea.intersects(projected))continue;')
        if name=='probe_patch.py':s=one(s,"EXTRA_INPUTS=(HERE/'prepare.py',HERE/'summary.py',", "EXTRA_INPUTS=(HERE/'prepare.py',HERE/'summary.py',HERE.parent/'camera-live-parking-groups-20261027/tests/SceneFarParkingTrial.as',HERE.parent/'camera-live-parking-groups-20261027/probe_patch.py',HERE.parent/'camera-live-parking-groups-20261027/summary.py',HERE.parent/'camera-live-parking-groups-20261027/README.md',HERE.parent/'camera-live-parking-groups-20261027/run.py',")
        if name=='README.md':
            s=s.replace('念力/藏身目标恢复；','念力目标恢复；玩家周边物体留在原生显示中；')
            s+='\n前驱groups读取lurkBox、safe-groups读取lurk，运行时均证实玩家无此公开字段，两者只完成1个原生窗口、0暂存。改为始终保留镜头提前区及玩家周围1024世界像素物体；不再访问这两个未知字段。实际藏身、远距离念力及镜头脱离玩家的组合尚未验证。\n'
        out[name]=s
    return out
if __name__=='__main__':
    for name,s in generated().items():
        p=HERE/name;p.parent.mkdir(exist_ok=True)
        if p.suffix=='.py':ast.parse(s)
        if p.exists():assert p.read_text('utf-8-sig')==s
        else:p.write_text(s,'utf-8')
    print('Prepared player/viewport range retention without unknown player fields')
