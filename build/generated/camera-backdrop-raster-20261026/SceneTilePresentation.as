package {
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.display.DisplayObject;
    import flash.display.DisplayObjectContainer;
    import flash.display.MovieClip;
    import flash.display.Stage;
    import flash.geom.ColorTransform;
    import flash.geom.Matrix;
    import flash.geom.Point;
    import flash.geom.Rectangle;
    import flash.utils.getQualifiedClassName;
    import flash.utils.getTimer;

    /** Bounded paused-camera experiment. No production integration or dynamic graphics claim. */
    public class SceneTilePresentation {
        private var target:DisplayObject;
        private var parent:DisplayObjectContainer;
        private var stage:Stage;
        private var world:*;
        private var location:*;
        private var bitmap:Bitmap;
        private var pixels:BitmapData;
        private var records:Array=[];
        private var originalVisible:Boolean;
        private var width:int=0;
        private var height:int=0;
        private var initial:Object;
        private var atIndex:int=0;
        public var copies:int=0;
        public var allocated:int=0;
        public var disposed:int=0;
        public var active:Boolean=false;
        public var updates:int=0;
        public var enables:int=0;
        public var restores:int=0;
        public var prepareMs:int=0;
        public var drawCalls:int=0;

        public function update(w:*,enabled:Boolean):void {
            ++updates;
            if(!enabled){clear();return;}
            if(target==null)prepare(w);
            verify(w);
            if(!active) {
                target.visible=false;bitmap.visible=true;
                active=true;++enables;
            }
            require(!target.visible && bitmap.visible && bitmap.parent===parent,"Backdrop presentation changed");
        }

        private function prepare(w:*):void {
            var started:int=getTimer();
            require(w.grafon.sceneLarge,"Continuous scene required");
            var candidate:DisplayObject=w.grafon.visFon as DisplayObject;
            require(candidate!=null && candidate.parent!=null && candidate.visible,"Visible native backdrop required");
            target=candidate;parent=target.parent;world=w;location=w.loc;stage=w.main.stage;
            width=stage.stageWidth;height=stage.stageHeight;originalVisible=target.visible;
            atIndex=parent.getChildIndex(target);
            require(width>0 && height>0 && width<=4096 && height<=4096 && width*height<=8388608,"Unbounded screen");
            var ancestor:DisplayObject=parent;
            while(ancestor!==stage) {
                require(ancestor!=null && neutral(ancestor),"Backdrop ancestors are not neutral");
                ancestor=ancestor.parent;
            }
            remember(target);
            initial={className:getQualifiedClassName(target),width:width,height:height,nodes:records.length,
                bounds:target.getBounds(stage),tree:[],allOpaque:false};
            for each(var record:Object in records)initial.tree.push({className:getQualifiedClassName(record.target),
                children:record.children,frames:record.frames});
            var scratch:BitmapData;
            try {
                scratch=new BitmapData(width,height,true,0);++allocated;
                scratch.draw(target,target.transform.matrix,target.transform.colorTransform,null,scratch.rect,true);++drawCalls;
                var nonOpaque:Rectangle=scratch.getColorBoundsRect(0xFF000000,0xFF000000,false);
                initial.nonOpaque={x:nonOpaque.x,y:nonOpaque.y,width:nonOpaque.width,height:nonOpaque.height};
                require(nonOpaque.isEmpty(),"Native visible backdrop has transparency");
                initial.allOpaque=true;
                pixels=new BitmapData(width,height,false,0);++allocated;
                pixels.copyPixels(scratch,scratch.rect,new Point());++copies;
                bitmap=new Bitmap(pixels,"always",false);
                bitmap.name="ContinuousSceneScreenBackdropTrial";
                bitmap.visible=false;
                parent.addChildAt(bitmap,atIndex);
            } finally {
                if(scratch!=null){scratch.dispose();++disposed;}
                prepareMs+=getTimer()-started;
            }
        }

        private function remember(node:DisplayObject):void {
            require(records.length<256 && node.filters.length==0 && node.mask==null &&
                node.scrollRect==null && node.transform.matrix3D==null && node.blendMode=="normal" &&
                !node.cacheAsBitmap,"Unsupported backdrop subtree");
            var container:DisplayObjectContainer=node as DisplayObjectContainer;
            var clip:MovieClip=node as MovieClip;
            require(clip==null || clip.totalFrames==1,"Animated backdrop subtree");
            records.push({target:node,parent:node.parent,matrix:node.transform.matrix,
                color:node.transform.colorTransform,visible:node.visible,
                children:container!=null?container.numChildren:0,frames:clip!=null?clip.totalFrames:0,
                data:node is Bitmap?Bitmap(node).bitmapData:null});
            if(container!=null)for(var i:int=0;i<container.numChildren;++i)remember(container.getChildAt(i));
        }

        private function verify(w:*):void {
            require(w===world && w.loc===location && w.grafon.visFon===target &&
                target.parent===parent && stage.stageWidth==width && stage.stageHeight==height,
                "Backdrop identity or viewport changed");
            var ancestor:DisplayObject=parent;
            while(ancestor!==stage){require(ancestor!=null && neutral(ancestor),"Backdrop ancestor changed");ancestor=ancestor.parent;}
            require(bitmap!=null && pixels!=null && parent.getChildIndex(bitmap)+1==parent.getChildIndex(target),
                "Backdrop display order changed");
            for each(var row:Object in records) {
                var node:DisplayObject=row.target;
                var container:DisplayObjectContainer=node as DisplayObjectContainer;
                require(node.parent===row.parent && sameMatrix(node.transform.matrix,row.matrix) &&
                    sameColor(node.transform.colorTransform,row.color) &&
                    (node===target?node.visible==!active:node.visible==row.visible) &&
                    (container!=null?container.numChildren:0)==row.children &&
                    node.filters.length==0 && node.mask==null && node.scrollRect==null &&
                    node.transform.matrix3D==null && node.blendMode=="normal" && !node.cacheAsBitmap,
                    "Backdrop subtree state changed");
                if(node is Bitmap)require(Bitmap(node).bitmapData===row.data,"Backdrop bitmap replaced");
            }
        }

        public function clear():void {
            if(active) {
                target.visible=originalVisible;bitmap.visible=false;
                active=false;++restores;
            }
        }

        public function dispose():void {
            clear();
            if(bitmap!=null && bitmap.parent!=null)bitmap.parent.removeChild(bitmap);
            if(bitmap!=null)bitmap.bitmapData=null;
            if(pixels!=null){pixels.dispose();++disposed;}
            bitmap=null;pixels=null;target=null;parent=null;world=null;location=null;stage=null;records=[];
        }

        public function snapshot():Object {
            return {active:active,parents:active?1:0,actualCache:active && bitmap!=null && bitmap.visible,
                updates:updates,enables:enables,restores:restores,backdrop:initial,
                ownBitmapAllocations:allocated,ownBitmapDisposals:disposed,liveBitmaps:allocated-disposed,
                sourcePixelCopies:copies,drawCalls:drawCalls,prepareMs:prepareMs,
                cacheBytes:pixels!=null?width*height*4:0};
        }

        private function neutral(node:DisplayObject):Boolean {
            var matrix:Matrix=node.transform.matrix;
            var color:ColorTransform=node.transform.colorTransform;
            return node.visible && matrix.a==1 && matrix.d==1 && matrix.b==0 && matrix.c==0 &&
                matrix.tx==0 && matrix.ty==0 && sameColor(color,new ColorTransform()) &&
                node.filters.length==0 && node.mask==null && node.scrollRect==null &&
                node.transform.matrix3D==null && node.blendMode=="normal" && !node.cacheAsBitmap;
        }
        private function sameMatrix(a:Matrix,b:Matrix):Boolean {
            return a.a==b.a && a.b==b.b && a.c==b.c && a.d==b.d && a.tx==b.tx && a.ty==b.ty;
        }
        private function sameColor(a:ColorTransform,b:ColorTransform):Boolean {
            return a.redMultiplier==b.redMultiplier && a.greenMultiplier==b.greenMultiplier &&
                a.blueMultiplier==b.blueMultiplier && a.alphaMultiplier==b.alphaMultiplier &&
                a.redOffset==b.redOffset && a.greenOffset==b.greenOffset &&
                a.blueOffset==b.blueOffset && a.alphaOffset==b.alphaOffset;
        }
        private function require(value:Boolean,message:String):void{if(!value)throw new Error(message);}
    }
}

