package {
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.display.DisplayObjectContainer;
    import flash.geom.Point;
    import flash.geom.Rectangle;

    /** Isolated diagnostic. Fixed world pages; borrowed native pixels are never modified. */
    public class SceneRasterPresentation {
        private static const CELL:int=320;
        private static const PAGE:int=1280;
        private static const LIMIT:int=8;
        private static const LAYER_BYTES:Number=1280*1280*4;
        private static const NAMES:Array=["ContinuousSceneAtlasFront","ContinuousSceneAtlasBack","ContinuousSceneAtlasBack2","ContinuousSceneAtlasWater"];
        private var pages:Array=[];
        private var hidden:Array=[];
        private var location:*;
        private var poseValid:Boolean=false;
        private var poseX:Number=NaN,poseY:Number=NaN,poseScale:Number=NaN;
        private var clock:int=0;
        private var liveBytes:Number=0;
        private var peakBytes:Number=0;
        private var peakPages:int=0;
        private var pagesCreated:int=0,pagesDisposed:int=0,allocations:int=0,disposals:int=0;
        private var evictions:int=0,pageReuses:int=0,cellClears:int=0;
        private var allocatedBytes:Number=0;
        private var requestedPages:int=0;
        private var requestedKeys:Array=[];
        private var fallbackReason:String="";
        public var copies:int=0;
        public var rebuilds:int=0;
        public var presented:Boolean=false;

        public function update(w:*,enabled:Boolean,forcePresentation:Boolean=false):void {
            beginFrame();
            requestedPages=0;requestedKeys=[];fallbackReason="";
            if(!enabled || !w.grafon.sceneLarge){clear();fallbackReason="disabled-or-native-scene";return;}
            var g:*=w.grafon;
            var parents:Array=[g.visFront,g.visBack,g.visBack2,g.visVoda];
            if(location!==w.loc)clear();
            var page:Object;
            var changedParent:Boolean=false;
            for each(page in pages)for(var layer:int=0;layer<page.layers.length;++layer)
                if(page.layers[layer].parent!==parents[layer])changedParent=true;
            if(changedParent)clear();
            location=w.loc;
            if(w.sats.active || g.visSats.visible){fallback("sats");return;}
            var matrix:*=w.visual.transform.concatenatedMatrix;
            var nextX:Number=Number(w.cam.vx),nextY:Number=Number(w.cam.vy),nextScale:Number=Number(w.cam.scaleV);
            var quakeX:Number=Number(w.cam.quakeX),quakeY:Number=Number(w.cam.quakeY);
            if(w.visual.stage==null || matrix==null || !isFinite(nextX) || !isFinite(nextY) ||
                !isFinite(nextScale) || nextScale!=1 || !isFinite(quakeX) || !isFinite(quakeY) ||
                quakeX!=Math.floor(quakeX) || quakeY!=Math.floor(quakeY) ||
                !isFinite(matrix.a) || !isFinite(matrix.b) || !isFinite(matrix.c) || !isFinite(matrix.d) ||
                !isFinite(matrix.tx) || !isFinite(matrix.ty) || matrix.a!=1 || matrix.b!=0 || matrix.c!=0 || matrix.d!=1 ||
                matrix.tx!=Math.floor(matrix.tx) || matrix.ty!=Math.floor(matrix.ty)){
                fallback("non-unit-or-fractional-geometry");return;
            }
            if(int(g.sceneChunkSide)!=CELL){fallback("unsupported-native-cell-side");return;}
            var view:Rectangle=g.sceneViewport();
            if(!view || view.isEmpty() || !isFinite(view.x) || !isFinite(view.y) ||
                !isFinite(view.width) || !isFinite(view.height) || !isFinite(view.right) || !isFinite(view.bottom)){
                fallback("invalid-viewport");return;
            }
            var left:Number=Math.floor(view.left/PAGE),right:Number=Math.ceil(view.right/PAGE)-1;
            var top:Number=Math.floor(view.top/PAGE),bottom:Number=Math.ceil(view.bottom/PAGE)-1;
            var count:Number=(right-left+1)*(bottom-top+1);
            if(!isFinite(count) || count<1 || count>LIMIT || Math.abs(left)>1000000 || Math.abs(right)>1000000 ||
                Math.abs(top)>1000000 || Math.abs(bottom)>1000000){
                requestedPages=isFinite(count)?int(Math.min(count,int.MAX_VALUE)):int.MAX_VALUE;
                fallback("viewport-exceeds-page-budget");return;
            }
            requestedPages=int(count);
            var required:Object={};
            for(var py:int=int(top);py<=int(bottom);++py)for(var px:int=int(left);px<=int(right);++px){
                var key:String=px+":"+py;required[key]=true;requestedKeys.push(key);
            }
            var surfaces:Array=g.sceneSurfaces();
            if(!surfaces.length){fallback("no-native-surfaces");return;}
            var byCell:Object={};
            for each(var surface:Object in surfaces){
                if(int(surface.side)!=CELL || !isFinite(Number(surface.gutter)) || Number(surface.gutter)<0 ||
                    Number(surface.gutter)!=Math.floor(Number(surface.gutter)) ||
                    Number(surface.x)+Number(surface.gutter)!=Number(surface.cx)*CELL ||
                    Number(surface.y)+Number(surface.gutter)!=Number(surface.cy)*CELL ||
                    !surface.bitmaps || surface.bitmaps.length!=4 || !surface.nativeBuffers || surface.nativeBuffers.length!=4 ||
                    !isFinite(Number(surface.revision)))throw new Error("Paged atlas native surface contract changed");
                byCell[surface.cx+":"+surface.cy]=surface;
            }
            ++clock;
            // Release out-of-range pages, then make room BEFORE allocating any missing page.
            for(var p:int=pages.length-1;p>=0;--p){
                page=pages[p];
                if(!required[page.key] && (page.px<left-1 || page.px>right+1 || page.py<top-1 || page.py>bottom+1))dropAt(p,true);
            }
            var missing:int=0;
            for each(key in requestedKeys)if(findPage(key)==null)++missing;
            while(pages.length+missing>LIMIT){
                var oldest:int=-1;
                for(p=0;p<pages.length;++p)if(!required[pages[p].key] && (oldest<0 || pages[p].used<pages[oldest].used))oldest=p;
                if(oldest<0)throw new Error("Paged atlas cache budget invariant failed");
                dropAt(oldest,true);
            }
            var useAtlas:Boolean=forcePresentation || (poseValid && (nextX!=poseX || nextY!=poseY || nextScale!=poseScale));
            var toHide:Array=[];
            for(py=int(top);py<=int(bottom);++py)for(px=int(left);px<=int(right);++px){
                key=px+":"+py;page=findPage(key);
                if(page==null)page=createPage(px,py,parents,surfaces);
                else ++pageReuses;
                page.used=clock;
                syncPage(page,byCell,parents,toHide);
            }
            // All copies complete before changing the original visible set.
            if(useAtlas){
                for each(var nativeBitmap:Bitmap in toHide)if(nativeBitmap.visible){hidden.push(nativeBitmap);nativeBitmap.visible=false;}
                for each(page in pages)if(required[page.key])for each(var bitmap:Bitmap in page.layers)bitmap.visible=true;
            }
            presented=useAtlas;
            poseValid=true;poseX=nextX;poseY=nextY;poseScale=nextScale;
        }

        private function fallback(reason:String):void {
            beginFrame();poseValid=false;fallbackReason=reason;
        }

        private function findPage(key:String):Object {
            for each(var page:Object in pages)if(page.key==key)return page;
            return null;
        }

        private function nativeAnchor(parent:DisplayObjectContainer,surfaces:Array,index:int):Bitmap {
            var first:Bitmap=null,depth:int=parent.numChildren;
            for each(var s:Object in surfaces){
                var b:Bitmap=s.bitmaps[index];
                if(b && b.parent===parent && parent.getChildIndex(b)<depth){first=b;depth=parent.getChildIndex(b);}
            }
            if(!first)throw new Error("Paged atlas native display anchor is missing");
            return first;
        }

        private function createPage(px:int,py:int,parents:Array,surfaces:Array):Object {
            if(pages.length>=LIMIT)throw new Error("Paged atlas allocation would exceed page cap");
            var anchors:Array=[];
            for(var i:int=0;i<4;++i)anchors.push(nativeAnchor(parents[i],surfaces,i));
            var page:Object={key:px+":"+py,px:px,py:py,layers:[],data:[],cells:new Array(16),points:[],rects:[],used:clock};
            for(var cell:int=0;cell<16;++cell){
                page.points.push(new Point((cell%4)*CELL,int(cell/4)*CELL));
                page.rects.push(new Rectangle((cell%4)*CELL,int(cell/4)*CELL,CELL,CELL));
            }
            pages.push(page);++pagesCreated;++rebuilds;
            peakPages=Math.max(peakPages,pages.length);
            try {
                for(i=0;i<4;++i){
                    var data:BitmapData=new BitmapData(PAGE,PAGE,true,0);
                    page.data.push(data);++allocations;liveBytes+=LAYER_BYTES;allocatedBytes+=LAYER_BYTES;
                    peakBytes=Math.max(peakBytes,liveBytes);
                    var bitmap:Bitmap=new Bitmap(data,anchors[i].pixelSnapping,anchors[i].smoothing);
                    bitmap.name=NAMES[i];bitmap.x=px*PAGE;bitmap.y=py*PAGE;bitmap.visible=false;
                    page.layers.push(bitmap);
                    parents[i].addChildAt(bitmap,parents[i].getChildIndex(anchors[i]));
                }
            } catch(error:*) {
                dropAt(pages.indexOf(page),false);throw error;
            }
            return page;
        }

        private function syncPage(page:Object,byCell:Object,parents:Array,toHide:Array):void {
            for(var cell:int=0;cell<16;++cell){
                var cx:int=page.px*4+cell%4,cy:int=page.py*4+int(cell/4);
                var surface:Object=byCell[cx+":"+cy];
                var record:Object=page.cells[cell];
                var i:int;
                if(surface==null){
                    if(record!=null){
                        for(i=0;i<4;++i)if(record.shown[i]){page.data[i].fillRect(page.rects[cell],0);++cellClears;}
                        page.cells[cell]=null;
                    }
                    continue;
                }
                if(record==null){record={entry:null,revision:NaN,sources:[null,null,null,null],shown:[false,false,false,false]};page.cells[cell]=record;}
                var changed:Boolean=record.entry!==surface || record.revision!==surface.revision;
                var sourceRect:Rectangle=null;
                for(i=0;i<4;++i){
                    var bitmap:Bitmap=surface.bitmaps[i] as Bitmap;
                    var source:BitmapData=surface.nativeBuffers[i] as BitmapData;
                    if(bitmap==null || source==null || bitmap.parent!==parents[i] || bitmap.bitmapData!==source ||
                        source.width<Number(surface.gutter)+CELL || source.height<Number(surface.gutter)+CELL)
                        throw new Error("Paged atlas native layer identity changed");
                    var show:Boolean=bitmap.visible;
                    if(show){
                        if(changed || record.sources[i]!==source || !record.shown[i]){
                            if(sourceRect==null)sourceRect=new Rectangle(surface.gutter,surface.gutter,CELL,CELL);
                            page.data[i].copyPixels(source,sourceRect,page.points[cell]);++copies;
                        }
                        toHide.push(bitmap);
                    } else if(record.shown[i]){page.data[i].fillRect(page.rects[cell],0);++cellClears;}
                    record.sources[i]=source;record.shown[i]=show;
                }
                record.entry=surface;record.revision=surface.revision;
            }
        }

        public function beginFrame():void {
            presented=false;
            for each(var nativeBitmap:Bitmap in hidden)if(nativeBitmap.parent)nativeBitmap.visible=true;
            hidden=[];
            for each(var page:Object in pages)for each(var bitmap:Bitmap in page.layers)bitmap.visible=false;
        }

        private function dropAt(index:int,evicted:Boolean):void {
            var page:Object=pages[index];
            for each(var bitmap:Bitmap in page.layers){if(bitmap.parent)bitmap.parent.removeChild(bitmap);bitmap.bitmapData=null;}
            for each(var data:BitmapData in page.data){data.dispose();++disposals;liveBytes-=LAYER_BYTES;}
            page.layers=[];page.data=[];page.cells=[];
            pages.splice(index,1);++pagesDisposed;if(evicted)++evictions;
        }

        public function snapshot():Object {
            var attached:int=0,live:int=0;
            var resident:Array=[],visible:Array=[],rows:Array=[];
            for each(var page:Object in pages){
                resident.push(page.key);var shown:Boolean=false;
                for each(var bitmap:Bitmap in page.layers){if(bitmap.parent)++attached;if(bitmap.bitmapData)++live;if(bitmap.visible)shown=true;}
                if(shown)visible.push(page.key);
                rows.push({key:page.key,px:page.px,py:page.py,used:page.used,layers:page.layers.length,visible:shown});
            }
            return {version:"atlas-paged-1",presented:presented,copies:copies,rebuilds:rebuilds,
                layers:live,attached:attached,liveBitmaps:live,pixelStorageBytes:liveBytes,
                pendingHidden:hidden.length,hasBounds:pages.length>0,hasLocation:location!=null,poseValid:poseValid,
                pageSide:PAGE,cellSide:CELL,pageLimit:LIMIT,livePages:pages.length,peakPages:peakPages,
                pagesCreated:pagesCreated,pagesDisposed:pagesDisposed,allocations:allocations,disposals:disposals,
                peakPixelStorageBytes:peakBytes,totalAllocatedPixelBytes:allocatedBytes,pageReuses:pageReuses,
                evictions:evictions,cellClears:cellClears,cellsCleared:cellClears,requestedPages:requestedPages,fallbackReason:fallbackReason,
                currentPageKeys:requestedKeys.concat(),residentPageKeys:resident,visiblePageKeys:visible,pages:rows};
        }

        public function clear():void {
            beginFrame();
            while(pages.length)dropAt(pages.length-1,false);
            location=null;poseValid=false;poseX=poseY=poseScale=NaN;
            requestedPages=0;requestedKeys=[];fallbackReason="";presented=false;
        }
    }
}
