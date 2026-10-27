from pathlib import Path
import ast
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-live-parking-window-20261027'
VERSION='camera-live-parking-math-1'
def one(s,a,b):
    assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
MATH='''        private function fastBounds(item:Object,parent:Matrix,out:Rectangle):void {
            var m:Matrix=item.root.transform.matrix,r:Rectangle=item.bounds;
            var a:Number=m.a*parent.a+m.b*parent.c,b:Number=m.a*parent.b+m.b*parent.d;
            var c:Number=m.c*parent.a+m.d*parent.c,d:Number=m.c*parent.b+m.d*parent.d;
            var x:Number=m.tx*parent.a+m.ty*parent.c+parent.tx,y:Number=m.tx*parent.b+m.ty*parent.d+parent.ty;
            var x1:Number=r.left*a,x2:Number=r.right*a,x3:Number=r.top*c,x4:Number=r.bottom*c;
            var y1:Number=r.left*b,y2:Number=r.right*b,y3:Number=r.top*d,y4:Number=r.bottom*d;
            out.x=Math.min(x1,x2)+Math.min(x3,x4)+x;out.y=Math.min(y1,y2)+Math.min(y3,y4)+y;
            out.width=Math.abs(x2-x1)+Math.abs(x4-x3);out.height=Math.abs(y2-y1)+Math.abs(y4-y3);
        }
        private function auditBounds(w:*):Object {
            var inverse:Matrix=w.visual.transform.concatenatedMatrix.clone();inverse.invert();
            var checks:int=0,maxError:Number=0,parents:Array=[];
            for each(var layer:DisplayObjectContainer in layers) {var pm:Matrix=layer.transform.concatenatedMatrix;pm.concat(inverse);parents.push(pm);}
            for each(var item:Object in entries)if(valid(item)) {
                var fast:Rectangle=new Rectangle();fastBounds(item,parents[item.layer],fast);
                var exact:Matrix=item.root.transform.concatenatedMatrix;exact.concat(inverse);
                var reference:Rectangle=project(item.bounds,exact);
                maxError=Math.max(maxError,Math.abs(fast.x-reference.x),Math.abs(fast.y-reference.y),Math.abs(fast.width-reference.width),Math.abs(fast.height-reference.height));
                ++checks;
            }
            require(checks>0 && maxError<0.00001,"Optimized bounds differ from native concatenated transforms");
            return {checks:checks,maxError:maxError,passed:true};
        }
'''
def generated():
    out={}
    for name in ['tests/SceneFarParkingTrial.as','probe_patch.py','summary.py','README.md','run.py']:
        s=(BASE/name).read_text('utf-8-sig').replace('camera-live-parking-window-1',VERSION)
        if name.endswith('.as'):
            s=one(s,'        public function update(w:*,on:Boolean):Object {',MATH+'        public function update(w:*,on:Boolean):Object {')
            s=one(s,'                for(var l:int=0;l<layers.length;++l) {','                var parents:Array=[],b:Rectangle=new Rectangle();\n                for(var l:int=0;l<layers.length;++l) {')
            s=one(s,'                    holders[l].transform.matrix=layers[l].transform.concatenatedMatrix;',
                '                    var parentWorld:Matrix=layers[l].transform.concatenatedMatrix;\n                    holders[l].transform.matrix=parentWorld;parentWorld=parentWorld.clone();parentWorld.concat(inverse);parents.push(parentWorld);')
            s=one(s,'                    var transform:Matrix=root.transform.matrix.clone();transform.concat(layers[item.layer].transform.concatenatedMatrix);transform.concat(inverse);\n                    var b:Rectangle=project(item.bounds,transform);',
                '                    fastBounds(item,parents[item.layer],b);')
            s=one(s,'                b.draw(stage);restoreAll();c.draw(stage);','                report.boundsAuditParked=auditBounds(w);\n                b.draw(stage);restoreAll();report.boundsAuditNative=auditBounds(w);c.draw(stage);')
        if name=='probe_patch.py':s=one(s,"EXTRA_INPUTS=(HERE/'prepare.py',HERE/'summary.py',", "EXTRA_INPUTS=(HERE/'prepare.py',HERE/'summary.py',HERE.parent/'camera-live-parking-window-20261027/tests/SceneFarParkingTrial.as',HERE.parent/'camera-live-parking-window-20261027/probe_patch.py',HERE.parent/'camera-live-parking-window-20261027/summary.py',HERE.parent/'camera-live-parking-window-20261027/README.md',HERE.parent/'camera-live-parking-window-20261027/run.py',")
        if name=='summary.py':s=one(s,"assert t['version']==VERSION and t['selected']>0 and t['maximumHeld']>0", "assert t['version']==VERSION and t['selected']>0 and t['maximumHeld']>0\n    assert all(t[k]['passed'] and t[k]['checks']>0 and t[k]['maxError']<0.00001 for k in ['boundsAuditParked','boundsAuditNative'])")
        if name=='README.md':s+='\n前驱20×60实战原生47.258→暂存49.658ms；管理本身5.875ms。本变体每层每帧只取一次父坐标，复用边界对象、直接合成数值，保持原生root矩阵读取以支持旋转/缩放/斜切。末尾对全部有效根在暂存/原生两种状态逐个核新旧完整矩阵边界，误差限1e-5。其他行为与窗口控制不变。\n'
        out[name]=s
    return out
if __name__=='__main__':
    for name,s in generated().items():
        p=HERE/name;p.parent.mkdir(exist_ok=True)
        if p.suffix=='.py':ast.parse(s)
        if p.exists():assert p.read_text('utf-8-sig')==s
        else:p.write_text(s,'utf-8')
    print('Prepared cached parent coordinates and exact scalar bounds audit')
