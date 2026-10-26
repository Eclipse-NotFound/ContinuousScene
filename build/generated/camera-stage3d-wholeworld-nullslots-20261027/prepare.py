"""Record actual empty display-list slots; never silently skip non-display values."""
from pathlib import Path
import importlib.util
import ast
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-stage3d-wholeworld-late-20261027'
spec=importlib.util.spec_from_file_location('wholeworld_null_base',BASE/'prepare.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
one=base.one
def helper_source():return base.helper_source().replace('camera-stage3d-wholeworld-late-1','camera-stage3d-wholeworld-nullslots-1')
def renderer_source():
    s=base.renderer_source()
    s=one(s,'private var timelineChanges:Array=[];',
        'private var timelineChanges:Array=[];\n        private var emptySlots:Array=[],walkedNodes:int=0;')
    s=one(s,'var seen:Dictionary=new Dictionary(),stack:Array=[root,backdrop];',
        'var seen:Dictionary=new Dictionary(),stack:Array=[{node:root,path:"world"},{node:backdrop,path:"backdrop"}];')
    s=one(s,'var node:DisplayObject=stack.pop() as DisplayObject;\n                require(node!=null,"Null display node during timeline inventory");',
        'var visit:Object=stack.pop(),node:DisplayObject=visit.node as DisplayObject;\n                require(node!=null,"Invalid queued display node: "+visit.path);++walkedNodes;')
    s=one(s,'className:getQualifiedClassName(mc),name:mc.name};','className:getQualifiedClassName(mc),name:mc.name,path:visit.path};')
    s=one(s,'if(container)for(var i:int=0;i<container.numChildren;++i)stack.push(container.getChildAt(i));', '''if(container)for(var i:int=0;i<container.numChildren;++i) {
                    var child:DisplayObject=container.getChildAt(i);
                    if(child==null) {
                        // A second immediate read must also be empty; no renderer object exists here.
                        require(container.getChildAt(i)==null,"Transient child disappeared during inventory");
                        emptySlots.push({parent:visit.path,parentClass:getQualifiedClassName(container),index:i,count:container.numChildren});
                    } else stack.push({node:child,path:visit.path+"/"+i+":"+getQualifiedClassName(child)});
                }''')
    s=one(s,'className:item.className,name:item.name,','className:item.className,name:item.name,path:item.path,')
    s=one(s,'timelineChanges:timelineChanges};','timelineChanges:timelineChanges,emptySlots:emptySlots,walkedNodes:walkedNodes};')
    return s
def runner_source():return base.runner_source().replace('camera-stage3d-wholeworld-late-1','camera-stage3d-wholeworld-nullslots-1')
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    (HERE/'tests/SceneCameraRasterTrial.as').write_text(helper_source(),'utf-8')
    (HERE/'SceneTilePresentation.as').write_text(renderer_source(),'utf-8')
    s=runner_source();ast.parse(s);(HERE/'run.py').write_text(s,'utf-8')
    print('Generated explicit empty-slot diagnostic; no build or launch')
