package {
    import flash.display.DisplayObject;
    import flash.display.DisplayObjectContainer;
    import flash.display.MovieClip;
    import flash.geom.Rectangle;
    import flash.utils.getQualifiedClassName;

    /** Trial: cache only the native scenery backdrop, never terrain or actors. */
    public class SceneTilePresentation {
        private var target:DisplayObject;
        private var parent:DisplayObjectContainer;
        private var world:*;
        private var location:*;
        private var original:Boolean;
        private var initial:Object;
        public var copies:int=0;
        public var allocated:int=0;
        public var active:Boolean=false;
        public var updates:int=0;
        public var enables:int=0;
        public var restores:int=0;

        public function update(w:*,enabled:Boolean):void {
            ++updates;
            if(!enabled){clear();return;}
            if(!active) {
                require(w.grafon.sceneLarge,"Continuous scene required");
                var candidate:DisplayObject=w.grafon.visFon as DisplayObject;
                require(candidate!=null && candidate.parent!=null && candidate.visible,"Visible native backdrop required");
                require(!candidate.cacheAsBitmap && candidate.cacheAsBitmapMatrix==null,"Backdrop already cached");
                require(candidate.filters.length==0 && candidate.mask==null,"Backdrop has external rendering changes");
                var bounds:Rectangle=candidate.getBounds(w.main.stage);
                require(bounds.width>0 && bounds.height>0 && bounds.width<=4096 && bounds.height<=4096 && bounds.width*bounds.height<=8388608,"Backdrop cache outside bounded trial");
                target=candidate;parent=target.parent;world=w;location=w.loc;original=target.cacheAsBitmap;
                initial={className:getQualifiedClassName(target),width:bounds.width,height:bounds.height,
                    x:bounds.x,y:bounds.y,children:target is DisplayObjectContainer?DisplayObjectContainer(target).numChildren:0,
                    totalFrames:target is MovieClip?MovieClip(target).totalFrames:0};
                target.cacheAsBitmap=true;active=true;++enables;
            }
            require(w===world && w.loc===location && w.grafon.visFon===target && target.parent===parent,"Backdrop identity changed");
            require(target.cacheAsBitmap && target.visible,"Backdrop cache setting changed");
        }
        public function clear():void {
            if(active) {
                target.cacheAsBitmap=original;
                require(target.cacheAsBitmap===original && target.parent===parent,"Backdrop cache restore failed");
                ++restores;
            }
            active=false;target=null;parent=null;world=null;location=null;
        }
        public function snapshot():Object {
            return {active:active,parents:active?1:0,actualCache:target!=null?target.cacheAsBitmap:false,
                updates:updates,enables:enables,restores:restores,backdrop:initial,
                ownBitmapAllocations:allocated,sourcePixelCopies:copies,runtimeCacheAllocationKnown:false};
        }
        private function require(value:Boolean,message:String):void{if(!value)throw new Error(message);}
    }
}
