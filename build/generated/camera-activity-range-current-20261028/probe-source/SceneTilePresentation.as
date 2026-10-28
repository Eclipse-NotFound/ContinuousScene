package {
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.geom.Point;
    import flash.geom.Rectangle;
    import flash.utils.Dictionary;
    /** Presentation experiment: keep full native gutters for effects/physics,
     * but give Flash an already cropped bitmap for each visible static tile. */
    public class SceneTilePresentation {
        private var entries:Dictionary=new Dictionary();
        private var pool:Array=[];
        private var location:*;
        private var zero:Point=new Point();
        public var copies:int=0;
        public var allocated:int=0;
        public function update(w:*,enabled:Boolean):void {
            if(!enabled || !w.grafon.sceneLarge){clear();return;}
            if(location!==w.loc){clear();location=w.loc;}
            var alive:Dictionary=new Dictionary(true);
            for each(var s:Object in w.grafon.sceneSurfaces()) {
                alive[s]=true;
                var active:Boolean=false;
                for each(var raster:Bitmap in s.bitmaps)if(raster.visible){active=true;break;}
                var e:Object=entries[s];
                if(!active){if(e)release(s,e);continue;}
                if(!e){entries[s]=e={data:[],revision:-1};}
                for(var i:int=0;i<4;++i){
                    raster=s.bitmaps[i];
                    var data:BitmapData=e.data[i];
                    if(data==null){
                        data=pool.length?pool.pop():null;
                        if(data && (data.width!=s.side || data.height!=s.side)){data.dispose();data=null;}
                        if(!data){data=new BitmapData(s.side,s.side,true,0);++allocated;}
                        e.data[i]=data;
                    }
                    if(e.revision!==s.revision){
                        data.copyPixels(s.nativeBuffers[i],new Rectangle(s.gutter,s.gutter,s.side,s.side),zero);++copies;
                    }
                    if(raster.bitmapData!==data)raster.bitmapData=data;
                    if(raster.scrollRect!=null)raster.scrollRect=null;
                }
                e.revision=s.revision;
            }
            for(var old:Object in entries)if(!alive[old])release(old,entries[old]);
        }
        private function release(s:Object,e:Object):void {
            for(var i:int=0;i<e.data.length;++i){
                var raster:Bitmap=s.bitmaps[i],data:BitmapData=e.data[i];
                if(raster.bitmapData===data){
                    if(raster.parent){raster.bitmapData=s.nativeBuffers[i];raster.scrollRect=new Rectangle(s.gutter,s.gutter,s.side,s.side);}
                    else raster.bitmapData=null;
                }
                if(pool.length<64)pool.push(data);else data.dispose();
            }
            delete entries[s];
        }
        public function clear():void {
            for(var s:Object in entries)release(s,entries[s]);
            for each(var data:BitmapData in pool)data.dispose();pool=[];
            entries=new Dictionary();location=null;
        }
    }
}
