package {
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.display.DisplayObjectContainer;
    import flash.geom.Point;
    import flash.geom.Rectangle;
    import flash.utils.Dictionary;

    /** Diagnostic only: row presentation has not passed native pixel equality. */
    public class SceneRasterRowsPresentation {
        private static const SIDE:int=320;
        private static const GUTTER:int=40;
        private static const NAMES:Array=["ContinuousSceneRowsFront","ContinuousSceneRowsBack",
            "ContinuousSceneRowsBack2","ContinuousSceneRowsWater"];
        private var layers:Array=[];
        private var parents:Array=[];
        private var hidden:Array=[];
        private var bounds:Rectangle;
        private var revisions:Dictionary=new Dictionary(true);
        private var location:*;
        public var copies:int=0;
        public var rebuilds:int=0;

        public function update(w:*,enabled:Boolean):void {
            if(!enabled || !w || !w.grafon || !w.grafon.sceneLarge){clear();return;}
            try {
                var g:*=w.grafon;
                var nextParents:Array=[g.visFront,g.visBack,g.visBack2,g.visVoda];
                if(location!==w.loc || !sameParents(nextParents))clear();
                location=w.loc;parents=nextParents;
                // The caller also invokes this before native ENTER_FRAME: V
                // must capture original native tiles, never the live rows.
                beginFrame();
                if(w.sats.active || g.visSats.visible)return;
                var surfaces:Array=g.sceneSurfaces();
                if(!surfaces.length || int(g.sceneChunkSide)!=SIDE)
                    throw new Error("Rows require resident native 320px surfaces");
                var view:Rectangle=g.sceneViewport();
                if(!view || view.isEmpty() || !isFinite(view.x) || !isFinite(view.y) ||
                    !isFinite(view.width) || !isFinite(view.height))
                    throw new Error("Rows require an active finite viewport");
                var needed:Rectangle=new Rectangle(Math.floor(view.x/SIDE)*SIDE,Math.floor(view.y/SIDE)*SIDE,
                    (Math.ceil(view.right/SIDE)-Math.floor(view.x/SIDE))*SIDE,
                    (Math.ceil(view.bottom/SIDE)-Math.floor(view.y/SIDE))*SIDE);
                if(!bounds || !bounds.containsRect(needed)) {
                    var next:Rectangle=needed.clone();next.inflate(SIDE,SIDE);
                    rebuild(next,surfaces);
                }
                for each(var surface:Object in surfaces) {
                    if(int(surface.side)!=SIDE || int(surface.gutter)!=GUTTER ||
                        Number(surface.x)+GUTTER!=Number(surface.cx)*SIDE ||
                        Number(surface.y)+GUTTER!=Number(surface.cy)*SIDE)
                        throw new Error("Rows surface disagrees with native geometry");
                    var x:Number=Number(surface.cx)*SIDE,y:Number=Number(surface.cy)*SIDE;
                    if(x<bounds.left || x>=bounds.right || y<bounds.top || y>=bounds.bottom)continue;
                    if(revisions[surface]!==surface.revision) {
                        copyCell(surface,int(x-bounds.x),int((y-bounds.y)/SIDE));
                        revisions[surface]=surface.revision;
                    }
                    for each(var native:Bitmap in surface.bitmaps)if(native.visible) {
                        hidden.push(native);native.visible=false;
                    }
                }
                for each(var row:Array in layers)for each(var bitmap:Bitmap in row)bitmap.visible=true;
            } catch(error:Error) {
                // A partially allocated row must not leave original tiles hidden.
                clear();throw error;
            }
        }

        private function sameParents(next:Array):Boolean {
            if(parents.length!=4)return false;
            for(var i:int=0;i<4;++i) {
                if(parents[i]!==next[i])return false;
                if(layers[i])for each(var bitmap:Bitmap in layers[i])if(bitmap.parent!==next[i])return false;
            }
            return true;
        }

        private function rebuild(next:Rectangle,surfaces:Array):void {
            removeRows();bounds=next;revisions=new Dictionary(true);
            var count:int=int(bounds.height/SIDE);
            for(var layer:int=0;layer<4;++layer) {
                var parent:DisplayObjectContainer=parents[layer];
                var anchor:Bitmap=nativeAnchor(parent,surfaces,layer);
                var depth:int=parent.getChildIndex(anchor),row:Array=[];
                layers.push(row);
                for(var i:int=0;i<count;++i) {
                    var bitmap:Bitmap=new Bitmap(null,anchor.pixelSnapping,anchor.smoothing);
                    row.push(bitmap);
                    bitmap.bitmapData=new BitmapData(int(bounds.width)+GUTTER*2,SIDE+GUTTER*2,true,0);
                    // Assigning bitmapData can reset smoothing in this runtime.
                    bitmap.smoothing=anchor.smoothing;
                    bitmap.name=NAMES[layer]+"-"+i;
                    bitmap.x=bounds.x;bitmap.y=bounds.y+i*SIDE;
                    bitmap.scrollRect=new Rectangle(GUTTER,GUTTER,bounds.width,SIDE);
                    bitmap.visible=false;
                    // Match the old atlas placement: replace the native base,
                    // keeping WallBlend and other later overlays above it.
                    parent.addChildAt(bitmap,depth+i);
                }
            }
            ++rebuilds;
        }

        private function copyCell(surface:Object,x:int,rowIndex:int):void {
            for(var layer:int=0;layer<4;++layer) {
                var source:BitmapData=surface.nativeBuffers[layer] as BitmapData;
                var native:Bitmap=surface.bitmaps[layer] as Bitmap;
                if(!source || !native || native.parent!==parents[layer] || native.bitmapData!==source ||
                    source.width!=SIDE+GUTTER*2 || source.height!=SIDE+GUTTER*2)
                    throw new Error("Rows require the current native 400px pixel store");
                var destination:BitmapData=Bitmap(layers[layer][rowIndex]).bitmapData;
                // Preserve this cell's own vertical gutters. A changed cell
                // copies only its slice, not the complete width of its row.
                destination.copyPixels(source,new Rectangle(GUTTER,0,SIDE,SIDE+GUTTER*2),
                    new Point(GUTTER+x,0));++copies;
                if(x==0) {
                    destination.copyPixels(source,new Rectangle(0,0,GUTTER,SIDE+GUTTER*2),new Point(0,0));
                    ++copies;
                }
                if(x+SIDE==bounds.width) {
                    destination.copyPixels(source,new Rectangle(GUTTER+SIDE,0,GUTTER,SIDE+GUTTER*2),
                        new Point(GUTTER+bounds.width,0));++copies;
                }
            }
        }

        private function nativeAnchor(parent:DisplayObjectContainer,surfaces:Array,index:int):Bitmap {
            var first:Bitmap=null,depth:int=parent.numChildren;
            for each(var surface:Object in surfaces) {
                var bitmap:Bitmap=surface.bitmaps[index];
                if(bitmap.parent===parent && parent.getChildIndex(bitmap)<depth) {
                    first=bitmap;depth=parent.getChildIndex(bitmap);
                }
            }
            if(!first)throw new Error("Rows native display anchor is missing");
            return first;
        }

        public function beginFrame():void {
            for each(var native:Bitmap in hidden)if(native.parent)native.visible=true;
            hidden=[];
            for each(var row:Array in layers)for each(var bitmap:Bitmap in row)bitmap.visible=false;
        }

        private function removeRows():void {
            for each(var row:Array in layers)for each(var bitmap:Bitmap in row) {
                if(bitmap.parent)bitmap.parent.removeChild(bitmap);
                var data:BitmapData=bitmap.bitmapData;bitmap.bitmapData=null;
                if(data)data.dispose();
            }
            layers=[];
        }

        public function clear():void {
            beginFrame();removeRows();
            parents=[];bounds=null;revisions=new Dictionary(true);location=null;
        }
    }
}
