package {
    import flash.display.DisplayObject;
    import flash.display.DisplayObjectContainer;
    import flash.display.Sprite;
    import flash.utils.Dictionary;
    import flash.utils.getQualifiedClassName;

    /** Isolated experiment: identity parents for contiguous exact Box roots.
     * No cached raster, visibility write, timeline stop or simulation change.
     * Native removal works through vis.parent. Baseline expands the groups at
     * their current position, preserving native removals and appended objects.
     */
    public class StaticObjectGroups {
        private var records:Array=[];
        private var active:Boolean=false;
        public var cellWidth:int=960,cellHeight:int=500;
        private var moved:int=0,created:int=0,restored:int=0,errors:int=0;
        public function setEnabled(w:*,enabled:Boolean):void {
            if(enabled==active)return;
            if(!enabled){clear();return;}
            var owners:Dictionary=new Dictionary(true),o:*=w.loc.firstObj,n:int=0;
            while(o && ++n<10000) {
                if(getQualifiedClassName(o)=="fe.loc::Box") {
                    if(o.vis)owners[o.vis]=o;
                    if("shad" in o && o.shad)owners[o.shad]=o;
                }
                o=o.nobj;
            }
            if(n>=10000)throw new Error("Unbounded object chain");
            active=true;
            try {
                for each(var layer:DisplayObjectContainer in w.grafon.visObjs) {
                    var original:Array=[],run:Array=[],cell:String="";
                    for(var i:int=0;i<layer.numChildren;++i)original.push(layer.getChildAt(i));
                    for each(var child:DisplayObject in original) {
                        var owner:*=owners[child];
                        var eligible:Boolean=owner && child.parent===layer && !child.mask && child.blendMode=="normal";
                        var key:String=eligible?int(Math.floor(owner.X/cellWidth))+":"+int(Math.floor(owner.Y/cellHeight)):"";
                        if(!eligible || key!=cell || run.length>=64){wrap(layer,run);run=[];cell=key;}
                        if(eligible)run.push(child);
                    }
                    wrap(layer,run);
                }
            }catch(e:*) {++errors;clear();throw e;}
        }
        private function wrap(layer:DisplayObjectContainer,children:Array):void {
            if(children.length<2)return;
            var group:Sprite=new Sprite();group.name="ContinuousSceneStaticGroupTrial";
            group.mouseEnabled=false;group.mouseChildren=true;
            var record:Object={parent:layer,group:group};records.push(record);
            layer.addChildAt(group,layer.getChildIndex(children[0]));++created;
            for each(var child:DisplayObject in children){group.addChild(child);++moved;}
        }
        public function clear():void {
            for each(var record:Object in records) {
                var group:Sprite=record.group,parent:DisplayObjectContainer=record.parent;
                if(group.parent!==parent){++errors;continue;}
                var index:int=parent.getChildIndex(group);
                while(group.numChildren){parent.addChildAt(group.getChildAt(0),index++);++restored;}
                parent.removeChild(group);
            }
            records=[];active=false;
        }
        public function stats():Object {return {cellWidth:cellWidth,cellHeight:cellHeight,active:active,groups:records.length,moved:moved,created:created,restored:restored,errors:errors};}
    }
}
