package {
    import flash.display.DisplayObject;
    import flash.display.DisplayObjectContainer;
    import flash.display.Sprite;
    import flash.events.Event;
    import flash.geom.Matrix;
    import flash.geom.Rectangle;
    import flash.utils.Dictionary;

    /** Own wrapper visibility; never overwrite native objects' own visibility. */
    public class SceneObjectCulling {
        /** Below this the unit-scale base box would divide by ~0; measure instead. */
        private static const MIN_SCALE:Number=1e-3;
        private var entries:Dictionary=new Dictionary();
        private var tracked:Vector.<SceneCullEntry>=new Vector.<SceneCullEntry>();
        private var exclusions:Dictionary=new Dictionary(true),layerSet:Dictionary=new Dictionary();
        private var layers:Vector.<DisplayObjectContainer>=new Vector.<DisplayObjectContainer>();
        private var added:Array=[],removed:Array=[],queued:Dictionary=new Dictionary();
        private var location:*,visual:*,tele:DisplayObject;
        private var unitsMode:Boolean=false,mutating:Boolean=false,suspended:Boolean=false,fastPath:Boolean=true;
        private var lastLeft:Number=NaN,lastTop:Number=NaN,lastRight:Number=NaN,lastBottom:Number=NaN;
        private var visits:int=0,changes:int=0,discoveries:int=0,boundsReads:int=0,scans:int=0,age:int=0;
        private var scaleSkips:int=0,baseRefreshes:int=0,refreshCursor:int=0;
        public var hidden:int=0;

        public function update(w:*,enabled:Boolean,unitsOnly:Boolean=false):void {
            if(!enabled || !w.grafon.sceneLarge){clear();return;}
            var selected:Array=unitsOnly?[w.grafon.visObjs[2]]:w.grafon.visObjs;
            var changed:Boolean=location!==w.loc || visual!==w.visual || unitsMode!=unitsOnly || layers.length!=selected.length;
            var i:int;
            if(!changed)for(i=0;i<layers.length;++i)if(layers[i]!==selected[i]){changed=true;break;}
            if(changed)bind(w,selected,unitsOnly);
            visits=changes=boundsReads=0;scaleSkips=0;baseRefreshes=0;
            var nextTele:DisplayObject=w.gg.teleObj?w.gg.teleObj.vis as DisplayObject:null;
            if(nextTele!==tele) {
                var oldTele:DisplayObject=tele;tele=nextTele;
                if(tele && entries[tele])forget(entries[tele],true);
                if(oldTele && layerSet[oldTele.parent])enqueue(oldTele);
            }
            // Audit unusual edits occasionally; undiscovered roots remain visible.
            if(++age%120==0)audit();
            flush();
            if(suspended)resumeFromCapture();
            refreshBase();
            var cam:*=w.cam,scale:Number=cam.scaleV;
            var left:Number=-cam.vx/scale-320,top:Number=-cam.vy/scale-320;
            var right:Number=left+cam.screenX/scale+640,bottom:Number=top+cam.screenY/scale+640;
            var viewChanged:Boolean=left!=lastLeft || top!=lastTop || right!=lastRight || bottom!=lastBottom;
            var count:int=tracked.length,e:SceneCullEntry,child:DisplayObject;
            var x:Number,y:Number,sx:Number,sy:Number,rot:Number,transformed:Boolean;
            for(var index:int=0;index<count;++index) {
                e=tracked[index];++visits;
                child=e.child;
                // Property changes and teleports do not emit ADDED/REMOVED.
                x=child.x;y=child.y;sx=child.scaleX;sy=child.scaleY;rot=child.rotation;
                transformed=sx!=e.sx || sy!=e.sy || rot!=e.rotation;
                if(transformed) {
                    // A pure non-zero scale change at rotation 0 is an exact map
                    // of the cached unit-scale box: arithmetic instead of a
                    // bounds traversal. Rotation (own or on the layer chain)
                    // keeps the transform off-axis, so those still measure.
                    if(fastPath && e.rotation==0 && canFastScale(rot,sx,sy) && e.baseValid)
                        applyScale(e,sx,sy);
                    else measure(e,x,y,sx,sy,rot);
                }
                if(!viewChanged && !transformed && x==e.x && y==e.y && e.checked)continue;
                e.x=x;e.y=y;e.checked=true;
                var hide:Boolean=!e.empty && !(e.right+x+240>=left && e.left+x-240<=right
                    && e.bottom+y+240>=top && e.top+y-240<=bottom);
                if(hide!=e.hidden) {
                    e.hidden=hide;e.wrapper.visible=!hide;hidden+=hide?1:-1;++changes;
                }
            }
            lastLeft=left;lastTop=top;lastRight=right;lastBottom=bottom;
        }
        private function bind(w:*,selected:Array,unitsOnly:Boolean):void {
            clear();location=w.loc;visual=w.visual;unitsMode=unitsOnly;
            for each(var box:* in w.loc.objs)if(box && "lurk" in box && box.lurk>0 && box.vis)exclusions[box.vis]=true;
            fastPath=true;
            for each(var layer:DisplayObjectContainer in selected) {
                layers.push(layer);layerSet[layer]=true;
                layer.addEventListener(Event.ADDED,onAdded,false,0,true);
                layer.addEventListener(Event.REMOVED,onRemoved,false,0,true);
                scan(layer);
                // The cached unit-scale box is only frame-independent while the
                // layer chain applies no translation, rotation or skew (uniform
                // scale is absorbed by the base). Guard once per bind instead of
                // trusting the caller: any violation falls back to measuring.
                var m:Matrix=layer.transform.matrix;
                if(layer.parent!==visual || m.b!=0 || m.c!=0 || m.tx!=0 || m.ty!=0 || m.a==0 || m.d==0)
                    fastPath=false;
            }
        }
        private static function canFastScale(rot:Number,sx:Number,sy:Number):Boolean {
            return rot==0 && sx!=0 && sy!=0 && Math.abs(sx)>=MIN_SCALE && Math.abs(sy)>=MIN_SCALE
                && isFinite(sx) && isFinite(sy);
        }
        private function scan(layer:DisplayObjectContainer):void {
            ++scans;
            for(var i:int=0;i<layer.numChildren;++i) {
                var child:DisplayObject=layer.getChildAt(i);
                if(!entries[child])enqueue(child);
            }
        }
        private function audit():void {
            for each(var e:SceneCullEntry in tracked)if(!e.pending && (e.child.parent!==e.wrapper || e.wrapper.parent!==e.layer)) {
                e.pending=true;removed.push(e);
            }
            for each(var layer:DisplayObjectContainer in layers)scan(layer);
        }
        private function enqueue(child:DisplayObject):void {
            if(!queued[child]){queued[child]=true;added.push(child);}
        }
        private function onAdded(event:Event):void {
            if(mutating)return;
            var child:DisplayObject=event.target as DisplayObject;
            if(child && layerSet[child.parent])enqueue(child);
        }
        private function onRemoved(event:Event):void {
            if(mutating)return;
            var e:SceneCullEntry=entries[event.target];
            if(e && !e.pending){e.pending=true;removed.push(e);}
        }
        private function flush():void {
            for each(var e:SceneCullEntry in removed) {
                e.pending=false;
                if(e.index>=0 && (e.child.parent!==e.wrapper || e.wrapper.parent!==e.layer))forget(e,true);
            }
            removed.length=0;
            for each(var child:DisplayObject in added) {
                delete queued[child];
                if(entries[child] || child===tele || exclusions[child] || !layerSet[child.parent])continue;
                var layer:DisplayObjectContainer=child.parent,wrapper:Sprite=new Sprite();wrapper.mouseEnabled=false;
                e=new SceneCullEntry();e.child=child;e.wrapper=wrapper;e.layer=layer;e.index=tracked.length;
                measure(e,child.x,child.y,child.scaleX,child.scaleY,child.rotation);
                mutating=true;
                try {var at:int=layer.getChildIndex(child);layer.addChildAt(wrapper,at);wrapper.addChild(child);}
                finally {mutating=false;}
                entries[child]=entries[wrapper]=e;tracked.push(e);++discoveries;
            }
            added.length=0;
        }
        private function measure(e:SceneCullEntry,x:Number,y:Number,sx:Number,sy:Number,rot:Number):void {
            var b:Rectangle=e.child.getBounds(visual);++boundsReads;
            storeMeasured(e,b,x,y,sx,sy,rot);
            e.x=x;e.y=y;e.sx=sx;e.sy=sy;e.rotation=rot;
        }
        /** Single place that turns measured bounds into the cached unit-scale
         * box. Descendants' own scaling or rotation is part of the measured box
         * and does not matter; what matters is the root's rotation (which makes
         * the mapping off-axis) and a degenerate axis (which makes dividing by
         * the scale meaningless). */
        private function storeMeasured(e:SceneCullEntry,b:Rectangle,x:Number,y:Number,
                                       sx:Number,sy:Number,rot:Number):void {
            e.left=b.left-x;e.right=b.right-x;e.top=b.top-y;e.bottom=b.bottom-y;
            e.empty=b.width<=0 && b.height<=0;
            if(canFastScale(rot,sx,sy)) {
                storeBase(e,e.left/sx,e.right/sx,e.top/sy,e.bottom/sy);
                e.baseValid=true;
            } else e.baseValid=false;
        }
        private function storeBase(e:SceneCullEntry,left:Number,right:Number,top:Number,bottom:Number):void {
            e.baseLeft=left<right?left:right;e.baseRight=left<right?right:left;
            e.baseTop=top<bottom?top:bottom;e.baseBottom=top<bottom?bottom:top;
        }
        /** Exact axis-aligned map of the cached unit-scale box for a pure scale
         * change (rotation unchanged at 0). Mirrors are the swap of the two
         * scaled edges, so sign flips cost no bounds traversal either. */
        private function applyScale(e:SceneCullEntry,sx:Number,sy:Number):void {
            ++scaleSkips;
            var l:Number=e.baseLeft*sx,r:Number=e.baseRight*sx;
            e.left=l<r?l:r;e.right=l<r?r:l;
            var t:Number=e.baseTop*sy,b:Number=e.baseBottom*sy;
            e.top=t<b?t:b;e.bottom=t<b?b:t;
            e.sx=sx;e.sy=sy;
        }
        /** Amortised cache refresh: one tracked child per frame re-reads its
         * exact box, so animation inside a child (which changes its extent
         * without touching the root transform) cannot leave the cache stale
         * for longer than one full sweep. Two invariants:
         *  - it never writes e.x/e.y/e.sx/e.sy/e.rotation, because the main loop
         *    owns those and uses "position changed" to decide whether to
         *    re-evaluate; adopting them here would swallow a same-frame move;
         *  - it clears e.checked so the refreshed box is used in this same
         *    frame instead of waiting for the next camera or transform change. */
        private function refreshBase():void {
            var count:int=tracked.length;
            if(!count)return;
            if(++refreshCursor>=count)refreshCursor=0;
            var e:SceneCullEntry=tracked[refreshCursor],child:DisplayObject=e.child;
            var sx:Number=child.scaleX,sy:Number=child.scaleY,rot:Number=child.rotation;
            if(!canFastScale(rot,sx,sy)) {e.baseValid=false;e.checked=false;return;}
            var b:Rectangle=child.getBounds(visual);++boundsReads;++baseRefreshes;
            storeMeasured(e,b,child.x,child.y,sx,sy,rot);
            e.checked=false;
        }
        private function forget(e:SceneCullEntry,restore:Boolean):void {
            if(e.index<0)return;
            delete entries[e.child];delete entries[e.wrapper];
            var tail:SceneCullEntry=tracked.pop();
            if(tail!==e){tracked[e.index]=tail;tail.index=e.index;}
            e.index=-1;
            if(e.hidden){--hidden;e.hidden=false;e.wrapper.visible=true;}
            if(restore && e.wrapper.parent) {
                var parent:DisplayObjectContainer=e.wrapper.parent,at:int=parent.getChildIndex(e.wrapper);
                mutating=true;
                try {parent.removeChild(e.wrapper);if(e.child.parent===e.wrapper)parent.addChildAt(e.child,at);}
                finally {mutating=false;}
            }
        }
        public function suspendForCapture():Boolean {
            if(suspended)return false;
            suspended=true;var had:Boolean=false;
            for each(var e:SceneCullEntry in tracked)if(e.hidden){e.wrapper.visible=true;had=true;}
            return had;
        }
        public function resumeFromCapture():void {
            if(!suspended)return;suspended=false;
            for each(var e:SceneCullEntry in tracked)if(e.hidden)e.wrapper.visible=false;
        }
        public function stats():Object {
            return {version:"event-tracked-3",tracked:tracked.length,hidden:hidden,suspended:suspended,
                visits:visits,visibilityChanges:changes,discoveries:discoveries,boundsReads:boundsReads,
                layerScans:scans,scaleSkips:scaleSkips,baseRefreshes:baseRefreshes,fastPath:fastPath};
        }
        public function clear():void {
            if(!location && !layers.length && !tracked.length)return;
            for each(var layer:DisplayObjectContainer in layers) {
                layer.removeEventListener(Event.ADDED,onAdded);layer.removeEventListener(Event.REMOVED,onRemoved);
            }
            while(tracked.length)forget(tracked[tracked.length-1],true);
            entries=new Dictionary();exclusions=new Dictionary(true);layerSet=new Dictionary();
            layers.length=0;added.length=0;removed.length=0;queued=new Dictionary();
            location=null;visual=null;tele=null;hidden=0;suspended=false;age=0;fastPath=true;
            scaleSkips=0;baseRefreshes=0;refreshCursor=0;
            lastLeft=lastTop=lastRight=lastBottom=NaN;
        }
    }
}
