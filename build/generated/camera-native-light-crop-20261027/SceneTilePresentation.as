package {
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.display.DisplayObjectContainer;
    import flash.geom.Matrix;
    import flash.geom.Rectangle;
    import flash.utils.getTimer;

    /** Bounded diagnosis: crop the native, globally enlarged darkness bitmap. */
    public class SceneTilePresentation {
        private var target:Bitmap;
        private var parent:DisplayObjectContainer;
        private var source:BitmapData;
        private var world:*;
        private var location:*;
        private var original:Object;
        private var crop:Rectangle;
        private var initial:Object;
        public var active:Boolean=false;
        public var copies:int=0,allocated:int=0,updates:int=0,enables:int=0,restores:int=0;
        public var cropChanges:int=0;
        public var setupMs:int=0;
        public function update(w:*,enabled:Boolean):void {
            ++updates;
            if(!enabled){clear();return;}
            require(w.grafon.sceneLarge && !w.sats.active && !w.grafon.visSats.visible,"Native light crop scene required");
            if(!active) {
                var at:int=getTimer();
                target=w.grafon.lightBitmap as Bitmap;parent=w.grafon.visLight;
                require(target!=null && target.parent===parent && parent.visible && target.visible &&
                    target.bitmapData===w.grafon.lightBmp && target.scrollRect==null,"Native light not eligible");
                require(target.scaleX==1 && target.scaleY==1 && target.rotation==0 &&
                    target.filters.length==0 && target.mask==null && target.transform.matrix3D==null,
                    "Unsupported native light bitmap effects");
                require(parent.filters.length==0 && parent.mask==null && parent.scrollRect==null &&
                    parent.transform.matrix3D==null,"Unsupported native light parent effects");
                world=w;location=w.loc;source=target.bitmapData;
                original={x:target.x,y:target.y,visible:target.visible,smoothing:target.smoothing,
                    pixelSnapping:target.pixelSnapping,blendMode:target.blendMode,color:target.transform.colorTransform};
                initial={width:source.width,height:source.height,sourcePixels:source.width*source.height,
                    nativeParentScaleX:parent.scaleX,nativeParentScaleY:parent.scaleY,
                    nativeParentBlend:parent.blendMode,nativeParentAlpha:parent.alpha,
                    smoothing:target.smoothing,originalX:target.x,originalY:target.y};
                active=true;++enables;setupMs+=getTimer()-at;
            }
            require(w===world && w.loc===location && w.grafon.lightBitmap===target &&
                w.grafon.lightBmp===source && target.bitmapData===source && target.parent===parent,
                "Native light identity changed");
            require(target.visible===original.visible && target.smoothing===original.smoothing &&
                target.pixelSnapping===original.pixelSnapping && target.blendMode===original.blendMode,
                "Native light appearance changed");
            var matrix:Matrix=parent.transform.concatenatedMatrix;
            require(matrix.a==40 && matrix.d==40 && matrix.b==0 && matrix.c==0 &&
                matrix.tx==Math.floor(matrix.tx) && matrix.ty==Math.floor(matrix.ty),
                "Trial requires native 40x light scale and integer camera");
            var left:int=Math.max(0,Math.floor(-matrix.tx/matrix.a-original.x)-2);
            var top:int=Math.max(0,Math.floor(-matrix.ty/matrix.d-original.y)-2);
            var right:int=Math.min(source.width,Math.ceil((w.main.stage.stageWidth-matrix.tx)/matrix.a-original.x)+2);
            var bottom:int=Math.min(source.height,Math.ceil((w.main.stage.stageHeight-matrix.ty)/matrix.d-original.y)+2);
            require(right>left && bottom>top,"Viewport misses native light bounds");
            if(crop==null || crop.x!=left || crop.y!=top || crop.right!=right || crop.bottom!=bottom) {
                crop=new Rectangle(left,top,right-left,bottom-top);
                target.scrollRect=crop;target.x=original.x+left;target.y=original.y+top;++cropChanges;
            }
            require(target.x==original.x+crop.x && target.y==original.y+crop.y &&
                target.scrollRect!=null && target.scrollRect.equals(crop),"Native crop did not apply");
        }
        public function clear():void {
            if(active) {
                target.scrollRect=null;target.x=original.x;target.y=original.y;
                require(target.scrollRect==null && target.x===original.x && target.y===original.y &&
                    target.bitmapData===source && target.parent===parent,"Native light restoration failed");
                active=false;++restores;
            }
            crop=null;target=null;parent=null;source=null;world=null;location=null;original=null;
        }
        public function snapshot():Object {
            return {active:active,parents:active?1:0,cropActive:active && target.scrollRect!=null,
                ownBitmapAllocations:allocated,sourcePixelCopies:copies,
                updates:updates,enables:enables,restores:restores,cropChanges:cropChanges,setupMs:setupMs,
                initial:initial,crop:crop==null?null:{x:crop.x,y:crop.y,width:crop.width,height:crop.height}};
        }
        private function require(value:Boolean,message:String):void{if(!value)throw new Error(message);}
    }
}

