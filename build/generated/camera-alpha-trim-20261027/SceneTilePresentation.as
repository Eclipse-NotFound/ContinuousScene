package {
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.geom.Rectangle;
    import flash.utils.Dictionary;
    import flash.utils.getTimer;

    /** Diagnostic: eliminate proven transparent margins, without copied pixels. */
    public class SceneTilePresentation {
        private var entries:Dictionary=new Dictionary();
        private var records:Array=[];
        private var world:*,location:*;
        public var active:Boolean=false;
        public var copies:int=0,allocated:int=0,updates:int=0,enables:int=0,restores:int=0;
        private var boundsChecks:int=0,changedClips:int=0,setupMs:int=0;
        private var visibleNativePixels:Number=0,visibleCroppedPixels:Number=0;
        private var visibleBitmaps:int=0,trimmedBitmaps:int=0,emptyBitmaps:int=0;

        public function update(w:*,enabled:Boolean):void {
            ++updates;
            if(!enabled){clear();return;}
            require(w.grafon.sceneLarge && !w.sats.active && !w.grafon.visSats.visible,"Native terrain required");
            if(!active){world=w;location=w.loc;active=true;++enables;}
            require(w===world && w.loc===location,"Scene identity changed");
            visibleNativePixels=visibleCroppedPixels=0;
            visibleBitmaps=trimmedBitmaps=emptyBitmaps=0;
            var at:int=getTimer();
            for each(var surface:Object in w.grafon.sceneSurfaces()) {
                var row:Object=entries[surface];
                if(!row) {
                    row={surface:surface,bitmaps:[]};entries[surface]=row;records.push(row);
                    for(var i:int=0;i<4;++i) {
                        var b:Bitmap=surface.bitmaps[i],source:BitmapData=surface.nativeBuffers[i];
                        var nativeRect:Rectangle=new Rectangle(surface.gutter,surface.gutter,surface.side,surface.side);
                        require(b!=null && b.bitmapData===source && b.parent!=null && b.scrollRect!=null && b.scrollRect.equals(nativeRect),"Native crop mismatch");
                        require(b.scaleX==1 && b.scaleY==1 && b.rotation==0 && b.mask==null && b.filters.length==0 &&
                            !b.smoothing && b.transform.matrix3D==null,"Unsupported native tile appearance");
                        row.bitmaps.push({bitmap:b,parent:b.parent,source:source,x:b.x,y:b.y,
                            original:nativeRect,revision:NaN,crop:null});
                    }
                }
                for(i=0;i<4;++i) {
                    var item:Object=row.bitmaps[i];b=item.bitmap;source=surface.nativeBuffers[i];
                    require(b===surface.bitmaps[i] && b.parent===item.parent && b.bitmapData===source && source===item.source,
                        "Native tile identity changed");
                    if(item.revision!==surface.revision) {
                        // An outer alpha rectangle is conservative: every removed
                        // pixel is guaranteed fully transparent, including gutters.
                        var bounds:Rectangle=source.getColorBoundsRect(0xFF000000,0,false);
                        var crop:Rectangle=bounds.intersection(item.original);
                        if(crop.isEmpty())crop=new Rectangle(item.original.x,item.original.y,0,0);
                        if(item.crop==null || !item.crop.equals(crop)) {
                            b.scrollRect=crop;b.x=item.x+crop.x-item.original.x;b.y=item.y+crop.y-item.original.y;
                            item.crop=crop;++changedClips;
                        }
                        item.revision=surface.revision;++boundsChecks;
                    }
                    require(b.x==item.x+item.crop.x-item.original.x && b.y==item.y+item.crop.y-item.original.y &&
                        b.scrollRect!=null && b.scrollRect.equals(item.crop),"Transparent margin crop changed externally");
                    if(b.visible) {
                        ++visibleBitmaps;visibleNativePixels+=surface.side*surface.side;
                        visibleCroppedPixels+=item.crop.width*item.crop.height;
                        if(!item.crop.equals(item.original))++trimmedBitmaps;
                        if(item.crop.isEmpty())++emptyBitmaps;
                    }
                }
            }
            setupMs+=getTimer()-at;
        }
        public function clear():void {
            if(active) {
                for each(var row:Object in records)for each(var item:Object in row.bitmaps) {
                    var b:Bitmap=item.bitmap;
                    require(b.bitmapData===item.source && b.parent===item.parent,"Native tile changed before restore");
                    b.scrollRect=item.original;b.x=item.x;b.y=item.y;
                    require(b.x===item.x && b.y===item.y && b.scrollRect.equals(item.original),"Native tile restoration failed");
                }
                active=false;++restores;
            }
            records=[];entries=new Dictionary();world=null;location=null;
            visibleNativePixels=visibleCroppedPixels=0;visibleBitmaps=trimmedBitmaps=emptyBitmaps=0;
        }
        public function snapshot():Object {
            return {active:active,parents:active?4:0,cropActive:active,
                ownBitmapAllocations:allocated,sourcePixelCopies:copies,updates:updates,enables:enables,restores:restores,
                boundsChecks:boundsChecks,changedClips:changedClips,setupMs:setupMs,liveRecords:records.length,
                visibleNativePixels:visibleNativePixels,visibleCroppedPixels:visibleCroppedPixels,
                visibleBitmaps:visibleBitmaps,trimmedBitmaps:trimmedBitmaps,emptyBitmaps:emptyBitmaps};
        }
        private function require(value:Boolean,message:String):void{if(!value)throw new Error(message);}
    }
}
