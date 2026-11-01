package {
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.display.DisplayObject;
    import flash.display.DisplayObjectContainer;
    import flash.geom.Matrix;
    import flash.utils.getTimer;

    /** Diagnostic: simulation stays native; only visual snapshots are held. */
    public class ScreenPresenter {
        private var source:DisplayObject,parent:DisplayObjectContainer,image:Bitmap,data:BitmapData;
        private var hidden:Boolean=false,originalVisible:Boolean;
        private var captures:int=0,drawMs:int=0,restored:int=0,updates:int=0;
        private var age:int=0,maximumAge:int=0,held:int=0;
        private var captureX:Number=NaN,captureY:Number=NaN,captureScale:Number=NaN;
        private var mode:String="full";
        private const RESOLUTION:Number=.5;
        private const GUTTER:int=128;

        public function restore():void {
            if(hidden && source){source.visible=originalVisible;hidden=false;++restored;}
            if(image)image.visible=false;
        }
        public function update(w:*,wanted:String):void {
            restore();++updates;
            var change:Boolean=wanted!=mode;
            mode=wanted;
            if(wanted=="full")return;
            var began:int=getTimer();
            if(source!==w.visual){clear();source=w.visual;parent=source.parent;change=true;mode=wanted;}
            if(!source.visible)return;
            var current:Matrix=source.transform.concatenatedMatrix;
            if(current.b || current.c || current.a!=current.d)throw new Error("Unsupported camera transform");
            var width:int=Math.ceil((source.stage.stageWidth+GUTTER*2)*RESOLUTION);
            var height:int=Math.ceil((source.stage.stageHeight+GUTTER*2)*RESOLUTION);
            if(!data || data.width!=width || data.height!=height){
                if(data)data.dispose();data=new BitmapData(width,height,true,0);change=true;
            }
            if(!image){image=new Bitmap();image.name="ContinuousSceneTemporalDiagnostic";parent.addChildAt(image,parent.getChildIndex(source)+1);}
            var period:int=wanted=="half2"?2:3;
            var dx:Number=current.tx-captureX,dy:Number=current.ty-captureY;
            if(change || age>=period || captureScale!=current.a || Math.abs(dx)>=GUTTER-8 || Math.abs(dy)>=GUTTER-8){
                data.fillRect(data.rect,0);
                var transform:Matrix=current.clone();transform.translate(GUTTER,GUTTER);transform.scale(RESOLUTION,RESOLUTION);
                data.drawWithQuality(source,transform,source.transform.colorTransform,null,data.rect,true,"high");
                captureX=current.tx;captureY=current.ty;captureScale=current.a;age=0;dx=dy=0;++captures;
            }else ++held;
            maximumAge=Math.max(maximumAge,age);
            image.bitmapData=data;image.smoothing=true;
            var inverse:Matrix=parent.transform.concatenatedMatrix.clone();inverse.invert();
            var output:Matrix=new Matrix(1/RESOLUTION,0,0,1/RESOLUTION,-GUTTER+dx,-GUTTER+dy);output.concat(inverse);
            image.transform.matrix=output;image.visible=true;
            originalVisible=source.visible;source.visible=false;hidden=true;++age;
            drawMs+=getTimer()-began;
        }
        public function stats():Object {
            return {mode:mode,captures:captures,drawMs:drawMs,restored:restored,updates:updates,held:held,
                maximumAge:maximumAge,age:age,hidden:hidden,overlayVisible:image?image.visible:false,
                sourceVisible:source?source.visible:null,width:data?data.width:0,height:data?data.height:0};
        }
        public function capturePresented():BitmapData {
            if(!image || !image.visible)throw new Error("No candidate image");
            var result:BitmapData=new BitmapData(source.stage.stageWidth,source.stage.stageHeight,true,0);
            result.drawWithQuality(image,image.transform.concatenatedMatrix,null,null,result.rect,true,"high");return result;
        }
        public function clear():void {
            restore();if(image && image.parent)image.parent.removeChild(image);
            if(image)image.bitmapData=null;if(data)data.dispose();
            image=null;data=null;source=null;parent=null;age=0;captureScale=NaN;captureX=captureY=NaN;mode="full";
        }
    }
}
