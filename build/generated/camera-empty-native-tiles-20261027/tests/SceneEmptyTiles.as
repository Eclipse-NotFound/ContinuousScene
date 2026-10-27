package tests {
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.geom.Rectangle;
    import flash.utils.getTimer;

    /** Fully empty stores stay native; only display bitmapData is temporarily null. */
    public final class SceneEmptyTiles {
        private var world:*,location:*;
        private var records:Array=[];
        private var ready:Boolean=false,enabled:Boolean=false,closed:Boolean=false;
        private var report:Object;
        public function init(w:*):Object {
            require(report==null,"Single-use empty tiles");
            world=w;location=w.loc;var at:int=getTimer();
            report={complete:false,scanned:0,selected:0,bytes:0,setupMs:0,allocated:0,disposed:0,enableWrites:0,restoreWrites:0,audits:0,enabled:false,tiles:[]};
            try {
                for each(var surface:Object in w.grafon.sceneSurfaces())for(var layer:int=0;layer<4;++layer) {
                    var source:BitmapData=surface.nativeBuffers[layer],bitmap:Bitmap=surface.bitmaps[layer];
                    require(source!=null && source.transparent && bitmap.bitmapData===source && bitmap.parent!=null,"Unexpected native tile binding");
                    require(bitmap.filters.length==0 && bitmap.mask==null && !bitmap.smoothing && bitmap.scaleX==1 && bitmap.scaleY==1 && bitmap.rotation==0 && bitmap.alpha==1 && bitmap.blendMode=="normal","Unsupported tile effects");
                    var crop:Rectangle=bitmap.scrollRect;
                    require(crop!=null && crop.equals(new Rectangle(surface.gutter,surface.gutter,surface.side,surface.side)),"Unexpected native crop");
                    ++report.scanned;
                    if(!source.getColorBoundsRect(0xFF000000,0,false).isEmpty())continue;
                    records.push({surface:surface,layer:layer,source:source,bitmap:bitmap,parent:bitmap.parent,revision:surface.revision,x:bitmap.x,y:bitmap.y,crop:crop,smoothing:bitmap.smoothing,snapping:bitmap.pixelSnapping});
                    report.tiles.push({cx:surface.cx,cy:surface.cy,layer:layer,width:source.width,height:source.height});
                }
                report.selected=records.length;require(records.length>0,"No fully transparent native buffers");
                ready=true;report.complete=true;audit();
            } finally {report.setupMs=getTimer()-at;}
            return report;
        }
        public function setEnabled(value:Boolean):void {
            if(!ready){require(!value,"Empty setup missing");return;}
            audit();if(value==enabled)return;
            for each(var r:Object in records) {
                r.bitmap.bitmapData=value?null:r.source;
                r.bitmap.smoothing=r.smoothing;r.bitmap.pixelSnapping=r.snapping;
                if(value)++report.enableWrites;else ++report.restoreWrites;
            }
            enabled=value;report.enabled=value;audit();
        }
        public function audit():void {
            if(!ready)return;
            require(world.loc===location,"Empty scene replaced");
            for each(var r:Object in records) {
                require(r.surface.revision===r.revision,"Terrain changed; empty eligibility must be refreshed");
                require(r.surface.nativeBuffers[r.layer]===r.source && r.surface.bitmaps[r.layer]===r.bitmap,"Empty native source replaced");
                require(r.bitmap.parent===r.parent && r.bitmap.bitmapData===(enabled?null:r.source),"Empty display binding changed");
                require(r.bitmap.x===r.x && r.bitmap.y===r.y && r.bitmap.smoothing===r.smoothing && r.bitmap.pixelSnapping===r.snapping,"Empty display properties changed");
            }
            ++report.audits;
        }
        public function visibleStats():Object {
            var count:int=0,pixels:Number=0;
            for each(var r:Object in records)if(r.bitmap.visible){++count;pixels+=r.surface.side*r.surface.side;}
            return {selected:records.length,visible:count,displayRectPixels:pixels,enabled:enabled};
        }
        public function clear():Object {
            if(closed)return report.cleanup;
            var result:Object={restored:true,errors:[],remaining:0};
            try {setEnabled(false);}catch(error:Error){result.errors.push(error.message);}
            for each(var r:Object in records) {
                try {
                    if(r.bitmap.bitmapData==null){r.bitmap.bitmapData=r.source;r.bitmap.smoothing=r.smoothing;r.bitmap.pixelSnapping=r.snapping;}
                    require(r.bitmap.bitmapData===r.source,"Native empty buffer not restored");
                }catch(e:Error){result.errors.push(e.message);++result.remaining;}
            }
            if(report){result.restored=result.errors.length==0;report.cleanup=result;report.enabled=false;}
            records=[];ready=false;enabled=false;closed=true;return result;
        }
        private function require(ok:Boolean,message:String):void {if(!ok)throw new Error(message);}
    }
}
