package {
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.display.DisplayObject;
    import flash.display.DisplayObjectContainer;
    import flash.geom.Matrix;
    import flash.geom.Rectangle;
    import flash.utils.getTimer;

    /** Diagnostic only. Never modifies a source bitmap, enemy or simulation tick. */
    public class ScreenPresenter {
        private var source:DisplayObject, parent:DisplayObjectContainer, image:Bitmap;
        private var buffers:Object={};
        private var hidden:Boolean=false, originalVisible:Boolean;
        private var captures:int=0, totalMs:int=0, maxMs:int=0, mode:String="full";
        private var renders:int=0, restored:int=0;

        public function restore():void {
            if(hidden && source){source.visible=originalVisible;hidden=false;++restored;}
            if(image)image.visible=false;
        }
        public function update(w:*, wanted:String):void {
            restore();mode=wanted;
            if(wanted=="full")return;
            var start:int=getTimer();
            if(source!==w.visual){clear();source=w.visual;parent=source.parent;}
            if(!source.visible)return;
            var scale:Number=wanted=="half" || wanted=="half-low"?.5:(wanted=="soft"?.75:1);
            var quality:String=wanted=="edge" || wanted=="half-low"?"low":"high";
            var width:int=Math.ceil(source.stage.stageWidth*scale),height:int=Math.ceil(source.stage.stageHeight*scale);
            var key:String=width+"x"+height;
            var data:BitmapData=buffers[key] as BitmapData;
            if(!data){data=new BitmapData(width,height,true,0);buffers[key]=data;}
            if(!image){image=new Bitmap();image.name="ContinuousSceneQualityProbe";parent.addChildAt(image,parent.getChildIndex(source)+1);}
            data.fillRect(data.rect,0);
            var transform:Matrix=source.transform.concatenatedMatrix.clone();transform.scale(scale,scale);
            data.drawWithQuality(source,transform,source.transform.colorTransform,null,data.rect,true,quality);
            image.bitmapData=data;image.smoothing=true;
            var inverse:Matrix=parent.transform.concatenatedMatrix.clone();inverse.invert();
            var output:Matrix=new Matrix(1/scale,0,0,1/scale);output.concat(inverse);
            image.transform.matrix=output;image.visible=true;
            originalVisible=source.visible;source.visible=false;hidden=true;
            var elapsed:int=getTimer()-start;totalMs+=elapsed;maxMs=Math.max(maxMs,elapsed);++captures;++renders;
        }
        public function stats():Object {
            return {mode:mode,captures:captures,drawMs:totalMs,maxDrawMs:maxMs,restored:restored,
                hidden:hidden,overlayVisible:image?image.visible:false,sourceVisible:source?source.visible:null,
                width:image && image.bitmapData?image.bitmapData.width:0,height:image && image.bitmapData?image.bitmapData.height:0,
                siblingIndex:image && image.parent?image.parent.getChildIndex(image):-1};
        }
        public function capturePresented():BitmapData {
            if(!image || !image.visible)throw new Error("No candidate image");
            var result:BitmapData=new BitmapData(source.stage.stageWidth,source.stage.stageHeight,true,0);
            result.drawWithQuality(image,image.transform.concatenatedMatrix,null,null,result.rect,true,"high");
            return result;
        }
        public function clear():void {
            restore();if(image && image.parent)image.parent.removeChild(image);
            if(image)image.bitmapData=null;
            for each(var b:BitmapData in buffers)b.dispose();
            image=null;buffers={};source=null;parent=null;
        }
    }
}
