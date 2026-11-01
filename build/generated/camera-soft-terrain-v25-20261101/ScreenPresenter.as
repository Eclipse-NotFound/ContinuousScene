package {
    import flash.display.BitmapData;
    public class ScreenPresenter {
        private var cache:ScreenTerrainCache,world:*,mode:String="full";
        private var count:int=0,restores:int=0,priorMs:int=0;
        public function restore():void {clear();}
        public function update(w:*,wanted:String):void {
            if(wanted!=mode || world!==w){clear();mode=wanted;world=w;}
            if(wanted=="full")return;
            if(!cache)cache=new ScreenTerrainCache(7,wanted=="half"?.5:.75);
            cache.update(w,true);++count;
        }
        public function stats():Object {
            var s:Object=cache?cache.stats():null;
            return {mode:mode,captures:count,drawMs:priorMs+(s?s.updateMs:0),restored:restores,
                active:s?s.presented:false,errors:s?s.internalErrors+s.cleanupErrors:0,
                overlayVisible:s?s.presented:false,terrain:s};
        }
        public function capturePresented():BitmapData {
            var data:BitmapData=new BitmapData(world.visual.stage.stageWidth,world.visual.stage.stageHeight,true,0);
            data.draw(world.visual,world.visual.transform.concatenatedMatrix,null,null,null,true);return data;
        }
        public function clear():void {
            if(cache){cache.clear();priorMs+=cache.stats().updateMs;++restores;}
            cache=null;world=null;mode="full";
        }
    }
}
