package {
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.geom.Point;
    import flash.geom.Rectangle;
    /** Keep full native sight state; only crop its enlarged display texture. */
    public class SceneFogPresentation {
        private var bitmap:Bitmap;
        private var original:BitmapData;
        private var cropped:BitmapData;
        private var zero:Point=new Point();
        public function update(w:*,enabled:Boolean):void {
            var g:*=w.grafon;
            if(!enabled || !g.sceneLarge){clear();return;}
            var target:Bitmap=g.visLight.getChildAt(0) as Bitmap,source:BitmapData=g.lightBmp;
            if(bitmap!==target || original!==source){clear();bitmap=target;original=source;}
            var view:Rectangle=g.sceneViewport();if(!view){clear();return;}
            var width:int=Math.min(source.width,Math.ceil(view.width/g.visLight.scaleX)+6);
            var height:int=Math.min(source.height,Math.ceil(view.height/g.visLight.scaleY)+6);
            var x:int=Math.max(0,Math.min(source.width-width,Math.floor((view.x-g.visLight.x)/g.visLight.scaleX)-2));
            var y:int=Math.max(0,Math.min(source.height-height,Math.floor((view.y-g.visLight.y)/g.visLight.scaleY)-2));
            if(!cropped || cropped.width!=width || cropped.height!=height){
                if(cropped){if(bitmap.bitmapData===cropped)bitmap.bitmapData=source;cropped.dispose();}
                cropped=new BitmapData(width,height,true,0);
            }
            cropped.copyPixels(source,new Rectangle(x,y,width,height),zero);
            if(bitmap.bitmapData!==cropped)bitmap.bitmapData=cropped;
            bitmap.smoothing=true;bitmap.x=x;bitmap.y=y;
        }
        public function clear():void {
            if(bitmap && bitmap.bitmapData===cropped){bitmap.bitmapData=original;bitmap.smoothing=true;bitmap.x=bitmap.y=0;}
            if(cropped)cropped.dispose();bitmap=null;original=null;cropped=null;
        }
    }
}
