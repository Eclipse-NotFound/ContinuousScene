package {
    import flash.display.DisplayObject;
    import flash.geom.Matrix;
    import flash.geom.Rectangle;
    /** Diagnostic only: request native cached scrolling on the four terrain parents. */
    public class SceneTilePresentation {
        private var saved:Array=[];
        private var world:*;
        private var location:*;
        public var copies:int=0;
        public var allocated:int=0;
        public var active:Boolean=false;
        public var updates:int=0;
        public var enables:int=0;
        public var restores:int=0;
        public var peakRequestedPixelBytes:Number=0;
        public function update(w:*,enabled:Boolean):void {
            ++updates;
            if(!enabled){clear();return;}
            require(w.grafon.sceneLarge && w.grafon.sceneChunkSide==320,"Native 320 scene required");
            var m:Matrix=w.visual.transform.concatenatedMatrix;
            require(m.a==1 && m.d==1 && m.b==0 && m.c==0 && m.tx==Math.floor(m.tx) && m.ty==Math.floor(m.ty),"Unit integer native transform required");
            require(w.cam.scaleV==1 && w.cam.quakeX==0 && w.cam.quakeY==0,"Unsupported zoom/shake");
            var width:int=w.main.stage.stageWidth,height:int=w.main.stage.stageHeight;
            require(width>0 && height>0 && width<=2560 && height<=2560,"Bounded native cache required");
            if(active)require(w===world && w.loc===location,"Identity changed while active");
            if(!active) {
                world=w;location=w.loc;
                var roots:Array=[w.grafon.visFront,w.grafon.visBack,w.grafon.visBack2,w.grafon.visVoda];
                for each(var root:DisplayObject in roots) {
                    var matrix:Matrix=root.transform.matrix;
                    require(root.parent===w.visual && matrix.a==1 && matrix.d==1 && matrix.b==0 && matrix.c==0 && matrix.tx==0 && matrix.ty==0,"Unexpected terrain parent transform");
                    require(root.scrollRect==null && !root.cacheAsBitmap && root.cacheAsBitmapMatrix==null && root.mask==null && root.filters.length==0 && root.blendMode=="normal","Unexpected terrain rendering state");
                    saved.push({root:root,matrix:matrix,cache:root.cacheAsBitmap,rect:root.scrollRect});
                }
                active=true;++enables;
            }
            var view:Rectangle=new Rectangle(-m.tx,-m.ty,width,height);
            peakRequestedPixelBytes=Math.max(peakRequestedPixelBytes,4*width*height*4);
            for each(var item:Object in saved) {
                root=item.root;
                // scrollRect removes its origin; this translation exactly compensates it.
                root.scrollRect=view;root.x=view.x;root.y=view.y;root.cacheAsBitmap=true;
                var actual:Rectangle=root.scrollRect;
                require(actual!=null && actual.equals(view) && root.x==view.x && root.y==view.y && root.cacheAsBitmap,"Scroll cache request did not apply");
            }
        }
        public function clear():void {
            var problem:String="";
            for each(var item:Object in saved) {
                try {
                    var root:DisplayObject=item.root;
                    root.cacheAsBitmap=item.cache;root.scrollRect=item.rect;root.transform.matrix=item.matrix;
                    var m:Matrix=root.transform.matrix,o:Matrix=item.matrix;
                    require(root.cacheAsBitmap===item.cache && root.scrollRect==null && m.a==o.a && m.b==o.b && m.c==o.c && m.d==o.d && m.tx==o.tx && m.ty==o.ty,"Terrain cache restoration mismatch");
                } catch(e:Error){problem+=e.message+";";}
            }
            if(saved.length)++restores;
            saved=[];active=false;world=null;location=null;
            require(problem=="",problem);
        }
        public function snapshot():Object {
            return {active:active,parents:saved.length,updates:updates,enables:enables,restores:restores,
                peakRequestedPixelBytes:peakRequestedPixelBytes,ownBitmapAllocations:allocated,
                runtimeCacheAllocationKnown:false};
        }
        private function require(value:Boolean,message:String):void{if(!value)throw new Error(message);}
    }
}
