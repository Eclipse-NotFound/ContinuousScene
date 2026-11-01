package {
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.display.DisplayObject;
    import flash.display.DisplayObjectContainer;
    import flash.geom.Matrix;
    import flash.geom.Rectangle;
    import flash.utils.getTimer;

    /** Isolated experiment: device-resolution terrain pixels, native actors unchanged. */
    public class ScreenTerrainCache {
        private var world:*,loc:*,g:*,entries:Array=[],surfaces:Array=[],revisions:Array=[];
        private var scale:Number=NaN,left:int,top:int,width:int,height:int;
        private var active:Boolean=false,fullDraws:int=0,stripDraws:int=0,shifts:int=0,updates:int=0;
        private var errors:int=0,cleanupErrors:int=0,ms:int=0,peak:int=0;
        private var reason:String="",lastError:String="";
        private var mask:int;private var resolution:Number;
        public function ScreenTerrainCache(mask:int=7,resolution:Number=.5){this.mask=mask;this.resolution=resolution;}
        public function update(w:*,enabled:Boolean):void {
            var start:int=getTimer();++updates;
            try {
                if(!enabled){clear();return;}
                var matrix:Matrix=w.visual.transform.concatenatedMatrix;matrix.scale(resolution,resolution);
                if(w.cam.quakeX || w.cam.quakeY || !w.grafon.sceneLarge || matrix.b || matrix.c || matrix.a!=matrix.d || matrix.a<0.2 || matrix.a>1)throw new Error("unsupported camera");
                if(active && (world!==w || loc!==w.loc || g!==w.grafon || scale!=matrix.a))clear();
                var nextLeft:int=int(Math.floor(-matrix.tx/64)*64)-256;
                var nextTop:int=int(Math.floor(-matrix.ty/64)*64)-256;
                var nextWidth:int=int(Math.ceil((w.cam.screenX*resolution)/64)*64)+512;
                var nextHeight:int=int(Math.ceil((w.cam.screenY*resolution)/64)*64)+512;
                if(active && (width!=nextWidth || height!=nextHeight))clear();
                if(active && -matrix.tx>=left+32 && -matrix.tx+(w.cam.screenX*resolution)<=left+width-32)nextLeft=left;
                if(active && -matrix.ty>=top+32 && -matrix.ty+(w.cam.screenY*resolution)<=top+height-32)nextTop=top;
                var dirty:Boolean=false;
                if(!active) {
                    world=w;loc=w.loc;g=w.grafon;scale=matrix.a;
                    width=nextWidth;height=nextHeight;left=nextLeft;top=nextTop;
                    var parents:Array=[g.visFront,g.visBack,g.visBack2,g.visVoda];
                    for(var i:int=0;i<parents.length;++i)if(mask & (1<<i)) {
                        var source:DisplayObjectContainer=parents[i];
                        if(source.parent!==w.visual || source.x || source.y || source.scaleX!=1 || source.scaleY!=1 || source.rotation || source.mask || source.filters.length || source.scrollRect)throw new Error("source geometry");
                        var data:BitmapData=new BitmapData(width,height,true,0);
                        var bitmap:Bitmap=new Bitmap(data,"never",true);
                        bitmap.name="ContinuousSceneScreenTerrain"+i;
                        bitmap.alpha=source.alpha;bitmap.scaleX=bitmap.scaleY=1/scale;
                        bitmap.x=left/scale;bitmap.y=top/scale;
                        w.visual.addChildAt(bitmap,w.visual.getChildIndex(source)+1);
                        entries.push({source:source,alpha:source.alpha,bitmap:bitmap,data:data});
                        source.alpha=0;
                    }
                    active=true;dirty=true;
                }
                var list:Array=g.sceneSurfaces();
                if(list.length!=surfaces.length)dirty=true;
                for(i=0;i<list.length;++i)if(list[i]!==surfaces[i] || list[i].revision!==revisions[i])dirty=true;
                surfaces=list;revisions.length=list.length;
                for(i=0;i<list.length;++i)revisions[i]=list[i].revision;
                var dx:int=nextLeft-left,dy:int=nextTop-top;
                if(Math.abs(dx)>=width || Math.abs(dy)>=height)dirty=true;
                left=nextLeft;top=nextTop;
                var exposed:Array=[];
                if(dirty || dx || dy)for each(var surface:Object in surfaces) {
                    var bounds:Rectangle=new Rectangle(surface.cx*320*scale,surface.cy*320*scale,320*scale,320*scale);
                    if(!bounds.intersects(new Rectangle(left,top,width,height)))continue;
                    for(var li:int=0;li<4;++li)if(mask & (1<<li)) {
                        var native:Bitmap=surface.bitmaps[li];
                        if(!native.visible){native.visible=true;exposed.push(native);}
                    }
                }
                try {
                for each(var item:Object in entries) {
                    if(item.source.alpha!=0 || item.bitmap.parent!==w.visual)throw new Error("source ownership changed");
                    item.bitmap.x=left/scale;item.bitmap.y=top/scale;
                    var drawMatrix:Matrix=new Matrix(scale,0,0,scale,-left,-top);
                    if(dirty) {
                        paint(item,drawMatrix,new Rectangle(0,0,width,height));++fullDraws;
                    } else if(dx || dy) {
                        item.data.scroll(-dx,-dy);
                        if(dx) {paint(item,drawMatrix,new Rectangle(dx>0?width-dx:0,0,Math.abs(dx),height));++stripDraws;}
                        if(dy) {paint(item,drawMatrix,new Rectangle(0,dy>0?height-dy:0,width,Math.abs(dy)));++stripDraws;}
                    }
                }
                } finally {for each(var restored:Bitmap in exposed)restored.visible=false;}
                if(dx || dy)++shifts;
                reason="";
            }catch(e:Error){++errors;lastError=e.message;reason=e.message;clear();}
            var elapsed:int=getTimer()-start;ms+=elapsed;peak=Math.max(peak,elapsed);
        }
        private function paint(item:Object,matrix:Matrix,clip:Rectangle):void {
            item.data.fillRect(clip,0);
            // BitmapData.draw uses the source's local content; its display alpha
            // is represented once on the replacement bitmap, as in the native tree.
            item.data.draw(item.source,matrix,null,null,clip,true);
        }
        public function nativeView(enabled:Boolean):void {
            for each(var item:Object in entries){item.source.alpha=enabled?item.alpha:0;item.bitmap.visible=!enabled;}
        }
        public function clear():void {
            for each(var item:Object in entries) {
                if(item.source.alpha==0)item.source.alpha=item.alpha;else ++cleanupErrors;
                if(item.bitmap.parent)item.bitmap.parent.removeChild(item.bitmap);
                item.data.dispose();item.bitmap.bitmapData=null;
            }
            entries=[];surfaces=[];revisions=[];active=false;world=null;loc=null;g=null;scale=NaN;
        }
        public function stats():Object {
            var matrices:Array=[];
            for each(var item:Object in entries){var m:Matrix=item.bitmap.transform.concatenatedMatrix;matrices.push({a:m.a,d:m.d,tx:m.tx,ty:m.ty});}
            return {presented:active,internalErrors:errors,cleanupErrors:cleanupErrors,lastError:lastError,lastFallback:reason,fullDraws:fullDraws,stripDraws:stripDraws,shifts:shifts,updates:updates,updateMs:ms,maxUpdateMs:peak,width:width,height:height,scale:scale,matrices:matrices};
        }
    }
}
