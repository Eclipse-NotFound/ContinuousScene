from pathlib import Path
import ast
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-live-parking-window-20261027'
VERSION='camera-live-parking-groups-1'
def one(s,a,b):
    assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
GROUPS='''        private var groups:Array=[];
        private function collectGroups():void {
            var keys:Object={};holders=[];
            for each(var item:Object in entries) {
                var b:Rectangle=project(item.bounds,item.root.transform.matrix);
                var key:String=item.layer+":"+Math.floor((b.x+b.width/2)/1920)+":"+Math.floor((b.y+b.height/2)/1000);
                var group:Object=keys[key];
                if(!group) {
                    group={layer:item.layer,holder:new Sprite(),items:[],bounds:null,filterPad:0,active:false,childCount:0};
                    groups.push(group);keys[key]=group;holders.push(group.holder);
                }
                group.items.push(item);item.group=group;
                group.bounds=group.bounds==null?b:group.bounds.union(b);
            }
            report.groups=groups.length;report.rootChecks=0;report.groupBoundsQueries=0;report.groupPreparations=0;
        }
        private function restoreGroup(group:Object):void {
            for(var i:int=group.items.length-1;i>=0;--i)if(valid(group.items[i]))restore(group.items[i]);
            group.active=false;group.childCount=group.holder.numChildren;
            require(group.childCount==0,"Group restoration left foreign graphics");
        }
        private function freshGroup(group:Object):Boolean {
            var all:Rectangle=null,geometry:Rectangle=null,countLive:int=0;
            ++report.groupPreparations;
            for each(var item:Object in group.items)if(valid(item)) {
                var root:DisplayObject=item.root;
                if(!safeTree(root)){retire(item,"changed-rendering-contract");continue;}
                item.bounds=localBounds(root);
                var full:Rectangle=project(item.bounds,root.transform.matrix);
                var geom:Rectangle=root.getBounds(layers[item.layer]);
                if(full.isEmpty())continue;
                all=all==null?full:all.union(full);geometry=geometry==null?geom:geometry.union(geom);++countLive;
            }
            if(countLive==0 || all==null || geometry==null)return false;
            group.bounds=all;
            group.filterPad=Math.max(0,geometry.left-all.left,geometry.top-all.top,all.right-geometry.right,all.bottom-geometry.bottom);
            require(isFinite(group.filterPad+all.x+all.y+all.width+all.height),"Non-finite group bounds");
            return true;
        }
        private function parkGroup(group:Object):void {
            for each(var item:Object in group.items)if(valid(item)) {
                group.holder.addChild(item.root);item.held=true;++held;++report.parked;
            }
            group.active=true;group.childCount=group.holder.numChildren;
        }
        public function update(w:*,on:Boolean):Object {
            prepare(w);var begin:int=getTimer();
            require(w.loc===location && w.allStat==1 && !w.onPause && w.t_exit==0,"Parking lost active world");
            require(w.main.stage.nativeWindow.visible,"Private native window became hidden");
            var previous:Boolean=enabled,heldGroups:int=0;
            if(!on) {if(enabled)restoreAll();}
            else {
                enabled=true;
                var inverse:Matrix=w.visual.transform.concatenatedMatrix.clone();inverse.invert();
                var view:Rectangle=project(new Rectangle(0,0,w.main.stage.stageWidth,w.main.stage.stageHeight),inverse);
                view.inflate(1024,1024);
                var parents:Array=[],globals:Array=[];
                for(var l:int=0;l<layers.length;++l) {
                    require(layers[l]===w.grafon.visObjs[l],"Object layer replaced");
                    var global:Matrix=layers[l].transform.concatenatedMatrix;
                    globals.push(global);var parentWorld:Matrix=global.clone();parentWorld.concat(inverse);parents.push(parentWorld);
                }
                for each(var group:Object in groups) {
                    // Child lists retain native visual removal. Only changed
                    // groups are reconciled; no per-frame full owner scan.
                    if(group.active && group.holder.numChildren!=group.childCount) {
                        for each(var changed:Object in group.items)valid(changed);
                        group.childCount=group.holder.numChildren;
                    }
                    var bound:Rectangle;
                    if(group.active) {
                        group.holder.transform.matrix=globals[group.layer];
                        bound=group.holder.getBounds(group.holder);++report.groupBoundsQueries;
                        bound.inflate(group.filterPad,group.filterPad);
                    } else bound=group.bounds;
                    var near:Boolean=bound==null || bound.isEmpty() || view.intersects(project(bound,parents[group.layer]));
                    // Native interaction targets are always restored, even if
                    // another system moves one a long distance in one frame.
                    var tele:*=w.gg.teleObj,lurk:*=w.gg.lurkBox;
                    if(tele || lurk)for each(var target:Object in group.items)if(!target.retired && (target.owner===tele || target.owner===lurk)){near=true;break;}
                    if(near) {if(group.active)restoreGroup(group);continue;}
                    if(!group.active) {
                        // Cached native bounds only select work. Actual roots
                        // are re-read before every park, so a moved/new state
                        // cannot be hidden using stale geometry.
                        if(!freshGroup(group) || view.intersects(project(group.bounds,parents[group.layer])))continue;
                        group.holder.transform.matrix=globals[group.layer];parkGroup(group);
                    }
                    if(group.active)++heldGroups;
                }
            }
            ++report.updates;report.maximumHeld=Math.max(report.maximumHeld,held);
            var elapsed:int=getTimer()-begin;report.workMs+=elapsed;
            return {enabled:on,previousEnabled:previous,held:held,heldGroups:heldGroups,retired:report.retired,workMs:elapsed,
                vx:w.cam.vx,vy:w.cam.vy,windowVisible:w.main.stage.nativeWindow.visible};
        }
'''
def generated():
    out={}
    for name in ['tests/SceneFarParkingTrial.as','probe_patch.py','summary.py','README.md','run.py']:
        s=(BASE/name).read_text('utf-8-sig').replace('camera-live-parking-window-1',VERSION)
        if name.endswith('.as'):
            s=one(s,'            ready=true;report.prepareMs=getTimer()-begin;report.initialLayers=layerCounts();',
                '            collectGroups();ready=true;report.prepareMs=getTimer()-begin;report.initialLayers=layerCounts();')
            s=one(s,'var root:DisplayObject=item.root,holder:Sprite=holders[item.layer];','var root:DisplayObject=item.root,holder:Sprite=item.group.holder;')
            s=one(s,'parent:DisplayObjectContainer=layers[item.layer],holder:Sprite=holders[item.layer];',
                'parent:DisplayObjectContainer=layers[item.layer],holder:Sprite=item.group.holder;')
            s=one(s,'        private function valid(item:Object):Boolean {', '        private function valid(item:Object):Boolean {\n            ++report.rootChecks;')
            s=one(s,'            enabled=false;require(held==0,"Parking cleanup left owned roots");',
                '            for each(var group:Object in groups){group.active=false;group.childCount=group.holder.numChildren;}\n            enabled=false;require(held==0,"Parking cleanup left owned roots");')
            start=s.index('        public function update(w:*,on:Boolean):Object {');end=s.index('        private function compare(',start)
            s=s[:start]+GROUPS+s[end:]
        if name=='probe_patch.py':s=one(s,"EXTRA_INPUTS=(HERE/'prepare.py',HERE/'summary.py',", "EXTRA_INPUTS=(HERE/'prepare.py',HERE/'summary.py',HERE.parent/'camera-live-parking-window-20261027/tests/SceneFarParkingTrial.as',HERE.parent/'camera-live-parking-window-20261027/probe_patch.py',HERE.parent/'camera-live-parking-window-20261027/summary.py',HERE.parent/'camera-live-parking-window-20261027/README.md',HERE.parent/'camera-live-parking-window-20261027/run.py',")
        if name=='summary.py':s=one(s,"assert t['version']==VERSION and t['selected']>0 and t['maximumHeld']>0", "assert t['version']==VERSION and t['selected']>0 and t['maximumHeld']>0\n    assert t['groups']>0 and t['groupBoundsQueries']>0 and t['groupPreparations']>0")
        if name=='README.md':s='''# 按区域暂存箱子和掉落物图像

沿已通过像素/销毁检查的live-parking-window闭包，保持相同20×60实际跑动、六射手交战、早显示私有窗口、完整连续计时。逐物体候选管理5.875ms且平均慢5.1%，停止沿用每帧全根检查。

本候选按1920×1000空间区域及原绘制层建立少量离屏容器。每帧只检查区域边界；原生移除导致子数变化时核该区域归属。临时移出前重新核所有真实物体边界，进入1024世界像素提前区时按原兄弟锚点放回。新物体保持原生。念力/藏身目标恢复；敌人、武器、子弹保持原生。原生图像销毁仍能从容器移除，不复活对象。

边界沿用Flash原生getBounds并额外包含收集时的滤镜外延。没有冻结/重放动画。动态滤镜突然扩大、所有跨模组、长期生命周期尚未验；仅隔离候选。像素和原生Box移除在计时后检查，全部计时/切换/区域管理成本保留，不部署。

526正式/13运行库/86源前后核验；共享game登记，唯一AIR ID与存储，独立桌面与原4GB提交内存门槛。
'''
        out[name]=s
    return out
if __name__=='__main__':
    for name,s in generated().items():
        p=HERE/name;p.parent.mkdir(exist_ok=True)
        if p.suffix=='.py':ast.parse(s)
        if p.exists():assert p.read_text('utf-8-sig')==s
        else:p.write_text(s,'utf-8')
    print('Prepared sparse spatial groups; prior per-root variants preserved')
