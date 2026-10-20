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
        public var copies:int=0;
        public var rebuilds:int=0;
        public function update(w:*,enabled:Boolean):void {
            if(!enabled || !w.grafon.sceneLarge){clear();return;}
            var g:*=w.grafon,parents:Array=[g.visFront,g.visBack,g.visBack2,g.visVoda];
            if(layers.length && layers[0].parent!==parents[0])clear();
            var view:Rectangle=g.sceneViewport();
            var needed:Rectangle=new Rectangle(Math.floor(view.x/320)*320,Math.floor(view.y/320)*320,
                (Math.ceil(view.right/320)-Math.floor(view.x/320))*320,
                (Math.ceil(view.bottom/320)-Math.floor(view.y/320))*320);
            if(!bounds || !bounds.containsRect(needed)) {
                beginFrame();
                var next:Rectangle=needed.clone();next.inflate(320,320);
                var old:Rectangle=bounds;
                for(var i:int=0;i<4;++i){
                    var data:BitmapData=new BitmapData(next.width,next.height,true,0);
                    if(!layers[i]){layers[i]=new Bitmap();parents[i].addChild(layers[i]);}
                    var bitmap:Bitmap=layers[i];
                    if(bitmap.bitmapData){
                        data.copyPixels(bitmap.bitmapData,bitmap.bitmapData.rect,new Point(old.x-next.x,old.y-next.y));
                        bitmap.bitmapData.dispose();
                    }
                    bitmap.bitmapData=data;bitmap.x=next.x;bitmap.y=next.y;
                }
                // Keep only cells copied wholly from the preceding atlas.
                for(var prior:Object in revisions)
                    if(!old || !old.containsRect(new Rectangle(prior.cx*320,prior.cy*320,320,320)))delete revisions[prior];
                bounds=next;++rebuilds;
            }
            beginFrame();
            for each(var s:Object in g.sceneSurfaces()) {
                if(!bounds.intersects(new Rectangle(s.cx*320,s.cy*320,320,320)))continue;
                if(revisions[s]!==s.revision){
                    for(i=0;i<4;++i){
                        Bitmap(layers[i]).bitmapData.copyPixels(s.nativeBuffers[i],
                            new Rectangle(s.gutter,s.gutter,s.side,s.side),new Point(s.cx*320-bounds.x,s.cy*320-bounds.y));
                        ++copies;
                    }
                    revisions[s]=s.revision;
                }
                for each(bitmap in s.bitmaps)if(bitmap.visible){hidden.push(bitmap);bitmap.visible=false;}
            }
            for each(bitmap in layers)bitmap.visible=true;
        }
        public function beginFrame():void {
            for each(var b:Bitmap in hidden)if(b.parent)b.visible=true;
            hidden=[];
            for each(b in layers)b.visible=false;
        }
        public function clear():void {
            beginFrame();
            for each(var b:Bitmap in layers){if(b.parent)b.parent.removeChild(b);b.bitmapData.dispose();}
            layers=[];bounds=null;revisions=new Dictionary(true);
        }
    }
}
