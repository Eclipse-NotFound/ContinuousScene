package {
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.display.DisplayObjectContainer;
    import flash.geom.Point;
    import flash.geom.Rectangle;
    import flash.utils.Dictionary;

    /** Experimental viewport atlas; full native surfaces remain authoritative. */
    public class SceneRasterPresentation {
        private var layers:Array=[];
        private var bounds:Rectangle;
        private var revisions:Dictionary=new Dictionary(true);
        private var hidden:Array=[];
        private var location:*;
        private var side:int=0;
        private static const NAMES:Array=["ContinuousSceneAtlasFront","ContinuousSceneAtlasBack","ContinuousSceneAtlasBack2","ContinuousSceneAtlasWater"];
        public var copies:int=0;
        public var rebuilds:int=0;
        public function update(w:*,enabled:Boolean):void {
            if(!enabled || !w.grafon.sceneLarge){clear();return;}
            var g:*=w.grafon,parents:Array=[g.visFront,g.visBack,g.visBack2,g.visVoda];
            if(location!==w.loc)clear();
            for(var i:int=0;i<layers.length;++i)if(layers[i].parent!==parents[i]){clear();break;}
            location=w.loc;
            // The ENTER_FRAME beginFrame hook restores native tiles before V
            // captures them. Never place a live atlas over the frozen overlay.
            if(w.sats.active || g.visSats.visible){beginFrame();return;}
            var surfaces:Array=g.sceneSurfaces();
            if(!surfaces.length)throw new Error("Atlas requires resident native surfaces");
            var actualSide:int=int(surfaces[0].side);
            if((actualSide!=320 && actualSide!=640) || actualSide!=int(g.sceneChunkSide) || (side && side!=actualSide))
                throw new Error("Atlas native chunk geometry changed or is unsupported");
            side=actualSide;
            var view:Rectangle=g.sceneViewport();
            if(!view || view.isEmpty() || !isFinite(view.x) || !isFinite(view.y) || !isFinite(view.width) || !isFinite(view.height))
                throw new Error("Atlas requires an active finite viewport");
            var needed:Rectangle=new Rectangle(Math.floor(view.x/side)*side,Math.floor(view.y/side)*side,
                (Math.ceil(view.right/side)-Math.floor(view.x/side))*side,
                (Math.ceil(view.bottom/side)-Math.floor(view.y/side))*side);
            if(!bounds || !bounds.containsRect(needed)) {
                beginFrame();
                var next:Rectangle=needed.clone();next.inflate(side,side);
                var old:Rectangle=bounds;
                for(i=0;i<4;++i){
                    var data:BitmapData=new BitmapData(next.width,next.height,true,0);
                    if(!layers[i]){
                        var anchor:Bitmap=nativeAnchor(parents[i],surfaces,i);
                        layers[i]=new Bitmap(null,anchor.pixelSnapping,anchor.smoothing);
                        layers[i].name=NAMES[i];
                        // Replace the native base at its original depth. WB
                        // overlays remain above it, including later new tiles.
                        parents[i].addChildAt(layers[i],parents[i].getChildIndex(anchor));
                    }
                    var bitmap:Bitmap=layers[i];
                    if(bitmap.bitmapData){
                        data.copyPixels(bitmap.bitmapData,bitmap.bitmapData.rect,new Point(old.x-next.x,old.y-next.y));
                        bitmap.bitmapData.dispose();
                    }
                    bitmap.bitmapData=data;bitmap.x=next.x;bitmap.y=next.y;
                }
                // Keep only cells copied wholly from the preceding atlas.
                for(var prior:Object in revisions)
                    if(!old || !old.containsRect(new Rectangle(prior.cx*side,prior.cy*side,side,side)))delete revisions[prior];
                bounds=next;++rebuilds;
            }
            beginFrame();
            for each(var s:Object in surfaces) {
                if(int(s.side)!=side || Number(s.x)+Number(s.gutter)!=s.cx*side || Number(s.y)+Number(s.gutter)!=s.cy*side)
                    throw new Error("Atlas surface disagrees with native chunk geometry");
                if(!bounds.intersects(new Rectangle(s.cx*side,s.cy*side,side,side)))continue;
                if(revisions[s]!==s.revision){
                    for(i=0;i<4;++i){
                        Bitmap(layers[i]).bitmapData.copyPixels(s.nativeBuffers[i],
                            new Rectangle(s.gutter,s.gutter,s.side,s.side),new Point(s.cx*side-bounds.x,s.cy*side-bounds.y));
                        ++copies;
                    }
                    revisions[s]=s.revision;
                }
                for each(bitmap in s.bitmaps)if(bitmap.visible){hidden.push(bitmap);bitmap.visible=false;}
            }
            for each(bitmap in layers)bitmap.visible=true;
        }
        private function nativeAnchor(parent:DisplayObjectContainer,surfaces:Array,index:int):Bitmap {
            var first:Bitmap=null,depth:int=parent.numChildren;
            for each(var s:Object in surfaces){
                var b:Bitmap=s.bitmaps[index];
                if(b.parent===parent && parent.getChildIndex(b)<depth){first=b;depth=parent.getChildIndex(b);}
            }
            if(!first)throw new Error("Atlas native display anchor is missing");
            return first;
        }
        public function beginFrame():void {
            for each(var b:Bitmap in hidden)if(b.parent)b.visible=true;
            hidden=[];
            for each(b in layers)b.visible=false;
        }
        public function clear():void {
            beginFrame();
            for each(var b:Bitmap in layers){if(b.parent)b.parent.removeChild(b);if(b.bitmapData)b.bitmapData.dispose();}
            layers=[];bounds=null;revisions=new Dictionary(true);location=null;side=0;
        }
    }
}
