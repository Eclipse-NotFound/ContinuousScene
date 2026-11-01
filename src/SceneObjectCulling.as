package {
    import flash.display.DisplayObject;
    import flash.display.DisplayObjectContainer;
    import flash.display.Sprite;
    import flash.geom.Rectangle;
    import flash.utils.Dictionary;

    /** Viewport visibility belongs to a transparent parent, so other mods keep
     * exclusive ownership of the actual object's alpha/visible/filter state. */
    public class SceneObjectCulling {
        private var entries:Dictionary=new Dictionary();
        private var tracked:Array=[];
        private var exclusions:Dictionary=new Dictionary(true);
        private var location:*;
        private var layers:*;
        public var hidden:int=0;
        private var suspended:Boolean=false;
        public function update(w:*,enabled:Boolean,unitsOnly:Boolean=false):void {
            if(!enabled || !w.grafon.sceneLarge){clear();return;}
            if(location!==w.loc || layers!==w.grafon.visObjs) {
                clear();location=w.loc;layers=w.grafon.visObjs;
                // Native hiding stores its chosen box in an internal field.
                // Keep all hiding boxes at their original display-list depth.
                for each(var box:* in w.loc.objs)if(box && "lurk" in box && box.lurk>0 && box.vis)exclusions[box.vis]=true;
            }
            suspended=false;
            var cam:*=w.cam,scale:Number=cam.scaleV;
            var view:Rectangle=new Rectangle(-cam.vx/scale-320,-cam.vy/scale-320,cam.screenX/scale+640,cam.screenY/scale+640);
            hidden=0;
            var selected:Array=unitsOnly?[layers[2]]:layers;
            for each(var layer:DisplayObjectContainer in selected) {
                var i:int=0;
                while(i<layer.numChildren) {
                    var child:DisplayObject=layer.getChildAt(i),e:Object=entries[child];
                    if(e && e.child.parent!==e.wrapper) {
                        layer.removeChild(e.wrapper);delete entries[e.wrapper];tracked.splice(tracked.indexOf(e),1);continue;
                    }
                    var actual:DisplayObject=e?e.child:child;
                    if((w.gg.teleObj && actual===w.gg.teleObj.vis) || exclusions[actual]) {
                        // Native telekinesis/hiding raises the direct child.
                        // Keep these targets direct children while manipulated.
                        if(e) {
                            layer.removeChild(e.wrapper);layer.addChild(actual);
                            delete entries[e.wrapper];tracked.splice(tracked.indexOf(e),1);continue;
                        }
                        ++i;continue;
                    }
                    if(!e) {
                        var wrapper:Sprite=new Sprite();wrapper.mouseEnabled=false;
                        e={child:child,wrapper:wrapper,bounds:child.getBounds(w.visual),x:child.x,y:child.y,
                            sx:child.scaleX,sy:child.scaleY,rotation:child.rotation,hidden:false};
                        layer.addChildAt(wrapper,i);wrapper.addChild(child);
                        entries[wrapper]=e;tracked.push(e);
                    }
                    child=e.child;
                    if(child.scaleX!=e.sx || child.scaleY!=e.sy || child.rotation!=e.rotation) {
                        e.bounds=child.getBounds(w.visual);e.x=child.x;e.y=child.y;e.sx=child.scaleX;e.sy=child.scaleY;e.rotation=child.rotation;
                    }
                    var b:Rectangle=e.bounds,dx:Number=child.x-e.x,dy:Number=child.y-e.y;
                    if(b.width<=0 && b.height<=0) {
                        // Empty bounds (not yet measured) must never hide content.
                        e.wrapper.visible=true;e.hidden=false;
                    } else {
                        // Extra room for frame-dependent animation and glows.
                        e.hidden=!(b.right+dx+240>=view.left && b.left+dx-240<=view.right
                            && b.bottom+dy+240>=view.top && b.top+dy-240<=view.bottom);
                        e.wrapper.visible=!e.hidden;
                    }
                    if(e.hidden)++hidden;
                    ++i;
                }
            }
        }
        /** SATS captures must draw the full resident tree. Returns true when
         * any wrapper was hidden and the caller must resumeFromCapture. */
        public function suspendForCapture():Boolean {
            if(suspended)return false;
            suspended=true;
            var had:Boolean=false;
            for each(var e:Object in tracked)if(e.hidden){e.wrapper.visible=true;had=true;}
            return had;
        }
        public function resumeFromCapture():void {
            if(!suspended)return;
            suspended=false;
            for each(var e:Object in tracked)if(e.hidden)e.wrapper.visible=false;
        }
        public function stats():Object {return {tracked:tracked.length,hidden:hidden,suspended:suspended};}
        public function clear():void {
            if(!tracked.length)return;
            for each(var e:Object in tracked) {
                var parent:DisplayObjectContainer=e.wrapper.parent;
                if(parent) {
                    var at:int=parent.getChildIndex(e.wrapper);parent.removeChild(e.wrapper);
                    if(e.child.parent===e.wrapper)parent.addChildAt(e.child,at);
                }
            }
            tracked=[];entries=new Dictionary();exclusions=new Dictionary(true);location=null;layers=null;hidden=0;suspended=false;
        }
    }
}
