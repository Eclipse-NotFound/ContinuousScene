package tests {
    import flash.display.BitmapData;
    import flash.display.DisplayObject;
    import flash.display.DisplayObjectContainer;
    import flash.display.MovieClip;
    import flash.display.Sprite;
    import flash.geom.Matrix;
    import flash.geom.Rectangle;
    import flash.utils.Dictionary;
    import flash.utils.getQualifiedClassName;
    import flash.utils.getTimer;

    // Private terminal experiment. Native cache invalidation remains responsible
    // for child animation/content changes; no stop/play, replacement raster or AI edits.
    public final class SceneNativeGroupCache {
        public var report:Object={selected:0,groups:0,estimatedBytes:0,skips:{},classes:{},
            writes:0,restores:0,updates:0,workMs:0,playingClips:0,multiFrameClips:0,
            enabled:false,cleanup:null,diagnosticOnly:true};
        private var world:*,location:*;
        private var layers:Array=[],siblings:Array=[],groups:Array=[];
        private var masks:Dictionary=new Dictionary(true);
        private var filterProbe:BitmapData;
        private var ready:Boolean=false,closed:Boolean=false;
        private function require(ok:Boolean,message:String):void {if(!ok)throw new Error(message);}
        private function count(o:Object,key:String):void {o[key]=int(o[key])+1;}
        private function maskWalk(d:DisplayObject):void {
            if(d.mask)masks[d.mask]=true;
            var c:DisplayObjectContainer=d as DisplayObjectContainer;
            if(c)for(var i:int=0;i<c.numChildren;++i)maskWalk(c.getChildAt(i));
        }
        private function safe(d:DisplayObject):Boolean {
            if(d.mask || masks[d] || d.scrollRect || d.blendMode!="normal" || d.transform.matrix3D)return false;
            for each(var f:* in d.filters) {
                var type:String=getQualifiedClassName(f);
                if(type!="flash.filters::DropShadowFilter" && type!="flash.filters::GlowFilter" && type!="flash.filters::BlurFilter" && type!="flash.filters::ColorMatrixFilter")return false;
            }
            var c:DisplayObjectContainer=d as DisplayObjectContainer;
            if(c)for(var i:int=0;i<c.numChildren;++i)if(!safe(c.getChildAt(i)))return false;
            return true;
        }
        private function project(r:Rectangle,m:Matrix):Rectangle {
            var x1:Number=r.left*m.a,x2:Number=r.right*m.a,y1:Number=r.left*m.b,y2:Number=r.right*m.b;
            var x3:Number=r.top*m.c,x4:Number=r.bottom*m.c,y3:Number=r.top*m.d,y4:Number=r.bottom*m.d;
            return new Rectangle(Math.min(x1,x2)+Math.min(x3,x4)+m.tx,Math.min(y1,y2)+Math.min(y3,y4)+m.ty,
                Math.abs(x2-x1)+Math.abs(x4-x3),Math.abs(y2-y1)+Math.abs(y4-y3));
        }
        private function extent(d:DisplayObject):Rectangle {
            var b:Rectangle=d.getBounds(d),c:DisplayObjectContainer=d as DisplayObjectContainer;
            if(c)for(var i:int=0;i<c.numChildren;++i) {
                var child:DisplayObject=c.getChildAt(i),r:Rectangle=project(extent(child),child.transform.matrix);
                if(!r.isEmpty())b=b.isEmpty()?r:b.union(r);
            }
            for each(var f:* in d.filters)b=b.union(filterProbe.generateFilterRect(b,f));
            return b;
        }
        private function clipCounts(d:DisplayObject):void {
            var mc:MovieClip=d as MovieClip,c:DisplayObjectContainer=d as DisplayObjectContainer;
            if(mc){if(mc.totalFrames>1)++report.multiFrameClips;if(mc.isPlaying)++report.playingClips;}
            if(c)for(var i:int=0;i<c.numChildren;++i)clipCounts(c.getChildAt(i));
        }
        private function flush(items:Array,bounds:Rectangle,layer:int):void {
            if(items.length<2){if(items.length)count(report.skips,"singleton");return;}
            var bytes:Number=Math.ceil(bounds.width+4)*Math.ceil(bounds.height+4)*4;
            if(report.estimatedBytes+bytes>64*1024*1024){count(report.skips,"budget");return;}
            var holder:Sprite=new Sprite();holder.name="CSNativeNearGroup";
            holder.cacheAsBitmap=true;
            var group:Object={holder:holder,items:items.concat(),layer:layer,bounds:bounds.clone(),enabled:false};
            groups.push(group);++report.groups;report.selected+=items.length;report.estimatedBytes+=bytes;
            for each(var item:Object in items){count(report.classes,item.type);clipCounts(item.root);}
        }
        public function prepare(w:*,view:Rectangle):void {
            require(!ready && !closed,"Group cache single use");var at:int=getTimer();world=w;location=w.loc;
            require(w.grafon.sceneLarge && !w.onPause && w.allStat==1,"Group cache requires live scene");
            filterProbe=new BitmapData(1,1,true,0);maskWalk(w.main.stage);
            var owners:Dictionary=new Dictionary(true),obj:*=location.firstObj,n:int=0;
            while(obj) {
                require(++n<50000,"Object chain cycle");var type:String=getQualifiedClassName(obj);
                if(type=="fe.loc::Box" || type=="fe.loc::Bonus")for each(var field:String in ["vis","shad"])
                    if(field in obj && obj[field] is DisplayObject) {
                        var graphic:DisplayObject=obj[field];
                        owners[graphic]=owners[graphic]?{duplicate:true}:{owner:obj,field:field,type:type};
                    }
                obj=obj.nobj;
            }
            for(var l:int=0;l<w.grafon.visObjs.length;++l) {
                var parent:DisplayObjectContainer=w.grafon.visObjs[l],all:Array=[],items:Array=[],union:Rectangle=null;
                layers.push(parent);siblings.push(all);
                for(n=0;n<parent.numChildren;++n)all.push(parent.getChildAt(n));
                for(n=0;n<all.length;++n) {
                    graphic=all[n];var owned:Object=owners[graphic],b:Rectangle=null;
                    if(owned && !owned.duplicate && owned.owner.loc===location && owned.owner.in_chain && graphic.visible && safe(graphic))
                        b=project(extent(graphic),graphic.transform.matrix);
                    if(!b || b.isEmpty() || !isFinite(b.x+b.y+b.width+b.height) || b.width>768 || b.height>768 || !view.intersects(b)) {
                        flush(items,union,l);items=[];union=null;count(report.skips,"not-near-owned-safe");continue;
                    }
                    var next:Rectangle=union?union.union(b):b;
                    if(items.length>=16 || next.width>768 || next.height>768) {flush(items,union,l);items=[];union=null;next=b;}
                    items.push({root:graphic,owner:owned.owner,field:owned.field,type:owned.type,index:n});union=next;
                }
                flush(items,union,l);
            }
            filterProbe.dispose();filterProbe=null;ready=true;report.prepareMs=getTimer()-at;
            require(groups.length>0 && report.selected>=2,"No consecutive near-owned roots qualified");
            audit();
        }
        public function setEnabled(value:Boolean):void {
            if(closed)return;require(ready,"Groups not prepared");
            var at:int=getTimer();++report.updates;
            if(value==report.enabled)return;
            audit();var before:Array=flatten();
            for each(var group:Object in groups) {
                var parent:DisplayObjectContainer=layers[group.layer],holder:Sprite=group.holder;
                if(value) {
                    var first:int=parent.getChildIndex(group.items[0].root);
                    for(var k:int=0;k<group.items.length;++k)require(parent.getChildIndex(group.items[k].root)==first+k,"Group roots no longer consecutive");
                    parent.addChildAt(holder,first);
                    for each(var item:Object in group.items){holder.addChild(item.root);++report.writes;}
                } else {
                    var index:int=parent.getChildIndex(holder);
                    for each(item in group.items){parent.addChildAt(item.root,index++);++report.restores;}
                    parent.removeChild(holder);
                }
                group.enabled=value;
            }
            report.enabled=value;audit();
            var after:Array=flatten();require(before.length==after.length,"Logical display count changed");
            for(k=0;k<before.length;++k)require(before[k]===after[k],"Logical display order changed");
            report.workMs+=getTimer()-at;
        }
        public function audit():void {
            require(world.loc===location && world.allStat==1 && !world.onPause,"Group world changed");
            for each(var g:Object in groups) {
                require(g.holder.cacheAsBitmap && g.holder.x==0 && g.holder.y==0 && g.holder.scaleX==1 && g.holder.scaleY==1,"Group geometry/cache changed");
                for each(var item:Object in g.items) {
                    require(item.owner.in_chain && item.owner.loc===location && item.owner[item.field]===item.root,"Native group owner changed");
                    require(item.root.parent===(g.enabled?g.holder:layers[g.layer]),"Native group root reparented");
                }
            }
        }
        private function flatten():Array {
            var flat:Array=[];
            for(var l:int=0;l<layers.length;++l) {
                for(var i:int=0;i<layers[l].numChildren;++i) {
                    var node:DisplayObject=layers[l].getChildAt(i),found:Object=null;
                    for each(var g:Object in groups)if(g.holder===node){found=g;break;}
                    if(found)for(var j:int=0;j<found.holder.numChildren;++j)flat.push(found.holder.getChildAt(j));else flat.push(node);
                }
            }
            return flat;
        }
        public function clear():Object {
            if(closed)return report.cleanup;
            var result:Object={restored:false,errors:[],holders:groups.length};
            try {if(ready)setEnabled(false);if(ready)audit();result.restored=true;}
            catch(e:Error){result.errors.push(e.message);}
            for each(var g:Object in groups) {
                // On audit failure never resurrect native-removed/replaced roots.
                var p:DisplayObjectContainer=layers[g.layer],h:Sprite=g.holder;
                if(h.parent===p) {
                    var at:int=p.getChildIndex(h);
                    while(h.numChildren){
                        var d:DisplayObject=h.getChildAt(0),live:Boolean=false;
                        for each(var item:Object in g.items)if(item.root===d && item.owner.in_chain && item.owner.loc===location && item.owner[item.field]===d){live=true;break;}
                        if(live)p.addChildAt(d,at++);else h.removeChild(d);
                    }
                    p.removeChild(h);
                }
                h.cacheAsBitmap=false;
            }
            if(filterProbe){filterProbe.dispose();filterProbe=null;}
            result.pendingHolders=0;
            for each(g in groups)if(g.holder.parent || g.holder.numChildren)++result.pendingHolders;
            result.writes=report.writes;result.restores=report.restores;closed=true;report.cleanup=result;return result;
        }
    }
}
