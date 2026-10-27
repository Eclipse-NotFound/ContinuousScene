package {
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.display.DisplayObjectContainer;
    import flash.geom.Point;
    import flash.events.Event;
    import flash.geom.Rectangle;
    import flash.utils.Dictionary;

    /** Isolated diagnostic. Fixed world pages; borrowed native pixels are never modified. */
    public class ScenePersistentAtlas {
        private static const CELL:int=320;
        private static const PAGE:int=1280;
        private static const LIMIT:int=8;
        private static const LAYER_BYTES:Number=1280*1280*4;
        private static const NAMES:Array=["ContinuousSceneAtlasFront","ContinuousSceneAtlasBack","ContinuousSceneAtlasBack2","ContinuousSceneAtlasWater"];
        private var atlasWorld:*;
        private var bindingParents:Array=[];
        private var bindingSurfaces:Array=[];
        private var bindingCells:Object={};
        private var bindingExtras:Array=[];
        private var expectedVisibility:Dictionary=new Dictionary();
        private var boundEpoch:int=-1,treeEpoch:int=0;
        private var boundResident:int=-1,boundRedraws:int=-1,boundEvictions:int=-1;
        private var visibilityKey:String="";
        private var bindingRefreshes:int=0,visibilityRefreshes:int=0,visibilityWrites:int=0,restoreWrites:int=0;
        private var bindingReuses:int=0;
        private var pages:Array=[];
        private var freePages:Array=[];
        private var poolLocation:*;
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
        private var stationarySkips:int=0;
        private var alphaRectChecks:int=0,emptyCopiesAvoided:int=0,backgroundMerges:int=0;
        public var copies:int=0;
        public var rebuilds:int=0;
        public var presented:Boolean=false;

        public function update(w:*,enabled:Boolean,forcePresentation:Boolean=false):void {
            requestedPages=0;requestedKeys=[];fallbackReason="";
            if(!enabled || !w.grafon.sceneLarge){clear();fallbackReason="disabled-or-native-scene";return;}
            if(poolLocation!==w.loc || pages.length+freePages.length!=LIMIT){clear();fallbackReason="pool-not-prepared";return;}
            var g:*=w.grafon;
            var parents:Array=[g.visFront,g.visBack,g.visBack2,g.visVoda];
            if(location!==w.loc)clear();
            var page:Object;
            var changedParent:Boolean=false;
            for each(page in pages)for(var layer:int=0;layer<page.layers.length;++layer)
                if(page.layers[layer].parent!==parents[layer])changedParent=true;
            if(changedParent){clear();fallbackReason="pool-not-prepared";return;}
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
            // The optional idle bypass explicitly restores native tiles.
            // Forced presentation remains bound through subsequent native frames.
            if(!forcePresentation && poseValid && nextX==poseX && nextY==poseY && nextScale==poseScale){
                beginFrame();++stationarySkips;return;
            }
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
            refreshBindings(g,parents);
            var surfaces:Array=bindingSurfaces;
            if(!surfaces.length){fallback("no-native-surfaces");return;}
            if(!backgroundCompatible(parents,surfaces)){fallback("background-order-or-effects");return;}
            refreshVisibility(view);
            var byCell:Object=bindingCells;
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
                for each(var nativeBitmap:Bitmap in toHide)if(nativeBitmap.visible){nativeBitmap.visible=false;++visibilityWrites;}
                hidden=toHide;
                for each(page in pages)for(var displayLayer:int=0;displayLayer<4;++displayLayer)page.layers[displayLayer].visible=Boolean(required[page.key]) && page.content[displayLayer];
            }
            presented=useAtlas;
            poseValid=true;poseX=nextX;poseY=nextY;poseScale=nextScale;
        }

        private function backgroundCompatible(parents:Array,surfaces:Array):Boolean {
            var lower:DisplayObjectContainer=parents[1],upper:DisplayObjectContainer=parents[2];
            if(lower.parent==null || lower.parent!==upper.parent ||
                lower.parent.getChildIndex(upper)!=lower.parent.getChildIndex(lower)+1)return false;
            for each(var parent:DisplayObjectContainer in [lower,upper]) {
                if(!parent.visible || parent.alpha!=1 || parent.x!=0 || parent.y!=0 || parent.scaleX!=1 || parent.scaleY!=1 ||
                    parent.rotation!=0 || parent.blendMode!="normal" || parent.mask!=null || parent.filters.length!=0 ||
                    parent.scrollRect!=null || parent.transform.matrix3D!=null)return false;
                var color:*=parent.transform.colorTransform;
                if(color.redMultiplier!=1 || color.greenMultiplier!=1 || color.blueMultiplier!=1 || color.alphaMultiplier!=1 ||
                    color.redOffset!=0 || color.greenOffset!=0 || color.blueOffset!=0 || color.alphaOffset!=0)return false;

            }
            for each(var extra:* in bindingExtras)if(extra.visible)return false;
            return true;
        }

        private function onTreeMutation(event:Event):void {
            var child:*=event.target;
            if(isOwnedLayer(child))return;
            ++treeEpoch;
        }

        private function isOwnedLayer(child:*):Boolean {
            for each(var page:Object in pages)for each(var layer:Bitmap in page.layers)if(child===layer)return true;
            for each(page in freePages)for each(layer in page.layers)if(child===layer)return true;
            return false;
        }

        private function refreshBindings(g:*,parents:Array):void {
            if(boundEpoch==treeEpoch && boundResident==g.sceneResident && boundRedraws==g.sceneRedraws && boundEvictions==g.sceneEvictions) {
                ++bindingReuses;return;
            }
            var surfaces:Array=g.sceneSurfaces(),cells:Object={},allowed:Dictionary=new Dictionary();
            for each(var surface:Object in surfaces) {
                if(int(surface.side)!=CELL || !isFinite(Number(surface.gutter)) || Number(surface.gutter)<0 ||
                    Number(surface.gutter)!=Math.floor(Number(surface.gutter)) ||
                    Number(surface.x)+Number(surface.gutter)!=Number(surface.cx)*CELL ||
                    Number(surface.y)+Number(surface.gutter)!=Number(surface.cy)*CELL ||
                    !surface.bitmaps || surface.bitmaps.length!=4 || !surface.nativeBuffers || surface.nativeBuffers.length!=4 ||
                    !isFinite(Number(surface.revision)))throw new Error("Persistent atlas native surface contract changed");
                var key:String=surface.cx+":"+surface.cy;
                if(cells[key])throw new Error("Persistent atlas duplicate cell");
                cells[key]=surface;
                for(var layer:int=0;layer<4;++layer) {
                    var bitmap:Bitmap=surface.bitmaps[layer];
                    if(!bitmap || bitmap.parent!==parents[layer] || bitmap.bitmapData!==surface.nativeBuffers[layer])throw new Error("Persistent atlas new native binding mismatch");
                    allowed[bitmap]=true;
                }
            }
            var extras:Array=[];
            for each(var parent:DisplayObjectContainer in [parents[1],parents[2]])for(var i:int=0;i<parent.numChildren;++i) {
                var child:*=parent.getChildAt(i);
                if(!allowed[child] && !isOwnedLayer(child))extras.push(child);
            }
            bindingSurfaces=surfaces;bindingCells=cells;bindingExtras=extras;
            boundEpoch=treeEpoch;boundResident=g.sceneResident;boundRedraws=g.sceneRedraws;boundEvictions=g.sceneEvictions;
            visibilityKey="";++bindingRefreshes;
        }

        private function refreshVisibility(view:Rectangle):void {
            var key:String=Math.floor(view.left/CELL)+":"+Math.floor(view.top/CELL)+":"+Math.ceil(view.right/CELL)+":"+Math.ceil(view.bottom/CELL)+":"+boundEpoch+":"+boundRedraws;
            if(key==visibilityKey)return;
            expectedVisibility=new Dictionary();
            for each(var surface:Object in bindingSurfaces) {
                var visible:Boolean=view.intersects(new Rectangle(surface.cx*CELL,surface.cy*CELL,CELL,CELL));
                for each(var bitmap:Bitmap in surface.bitmaps)expectedVisibility[bitmap]=visible;
            }
            visibilityKey=key;++visibilityRefreshes;
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

        public function preallocate(w:*):void {
            if(poolLocation===w.loc && pages.length+freePages.length==LIMIT)return;
            clear();
            if(!w || !w.loc || !w.grafon.sceneLarge)throw new Error("Pool requires a loaded large scene");
            poolLocation=location=w.loc;atlasWorld=w;
            bindingParents=[w.grafon.visFront,w.grafon.visBack,w.grafon.visBack2,w.grafon.visVoda];
            for each(var parent:DisplayObjectContainer in bindingParents) {
                parent.addEventListener(Event.ADDED,onTreeMutation);
                parent.addEventListener(Event.REMOVED,onTreeMutation);
            }
            try {
                for(var slot:int=0;slot<LIMIT;++slot){
                    var page:Object={key:"",px:0,py:0,layers:[],data:[],cells:new Array(16),points:[],rects:[],used:0,reused:false};
                    freePages.push(page);
                    for(var cell:int=0;cell<16;++cell){
                        page.points.push(new Point((cell%4)*CELL,int(cell/4)*CELL));
                        page.rects.push(new Rectangle((cell%4)*CELL,int(cell/4)*CELL,CELL,CELL));
                    }
                    for(var i:int=0;i<4;++i){
                        var data:BitmapData=new BitmapData(PAGE,PAGE,true,0);
                        page.data.push(data);++allocations;liveBytes+=LAYER_BYTES;allocatedBytes+=LAYER_BYTES;
                        peakBytes=Math.max(peakBytes,liveBytes);
                        var bitmap:Bitmap=new Bitmap(data);bitmap.name=NAMES[i];bitmap.visible=false;
                        page.layers.push(bitmap);
                    }
                }
            } catch(error:*) {clear();throw error;}
        }

        /** Benchmark-only native arm; the product disable path remains clear(). */
        public function useNativeForTest():void {
            beginFrame();requestedPages=0;requestedKeys=[];poseValid=false;
            fallbackReason="disabled-or-native-scene";
        }

        private function createPage(px:int,py:int,parents:Array,surfaces:Array):Object {
            if(pages.length>=LIMIT || !freePages.length)throw new Error("Prepared atlas pool exhausted");
            var page:Object=freePages.pop();
            page.key=px+":"+py;page.px=px;page.py=py;page.used=clock;page.cells=new Array(16);page.content=[false,false,false,false];
            pages.push(page);++pagesCreated;++rebuilds;peakPages=Math.max(peakPages,pages.length);
            try {
                for(var i:int=0;i<4;++i){
                    var anchor:Bitmap=nativeAnchor(parents[i],surfaces,i);
                    if(page.reused)page.data[i].fillRect(page.data[i].rect,0);
                    var bitmap:Bitmap=page.layers[i];
                    bitmap.pixelSnapping=anchor.pixelSnapping;bitmap.smoothing=anchor.smoothing;
                    bitmap.x=px*PAGE;bitmap.y=py*PAGE;bitmap.visible=false;
                    parents[i].addChildAt(bitmap,parents[i].getChildIndex(anchor));
                }
                page.reused=true;
            } catch(error:*) {dropAt(pages.indexOf(page),false);throw error;}
            return page;
        }

        private function syncPage(page:Object,byCell:Object,parents:Array,toHide:Array):void {
            page.content=[false,false,false,false];
            for(var cell:int=0;cell<16;++cell){
                var cx:int=page.px*4+cell%4,cy:int=page.py*4+int(cell/4);
                var surface:Object=byCell[cx+":"+cy];
                var record:Object=page.cells[cell];
                var i:int;
                if(surface==null){
                    if(record!=null){
                        for(i=0;i<4;++i)if(record.shown[i]){page.data[i].fillRect(page.rects[cell],0);++cellClears;}
                        if(record.shown[1] && !record.shown[2]){page.data[2].fillRect(page.rects[cell],0);++cellClears;}
                        page.cells[cell]=null;
                    }
                    continue;
                }
                if(record==null){record={entry:null,revision:NaN,sources:[null,null,null,null],shown:[false,false,false,false],hasPixels:[false,false,false,false]};page.cells[cell]=record;}
                var changed:Boolean=record.entry!==surface || record.revision!==surface.revision;
                var backgroundChanged:Boolean=changed || record.sources[1]!==surface.nativeBuffers[1] ||
                    record.sources[2]!==surface.nativeBuffers[2] || record.shown[1]!==Boolean(expectedVisibility[surface.bitmaps[1]]) ||
                    record.shown[2]!==Boolean(expectedVisibility[surface.bitmaps[2]]);
                var sourceRect:Rectangle=null;
                for(i=0;i<4;++i){
                    var bitmap:Bitmap=surface.bitmaps[i] as Bitmap;
                    var source:BitmapData=surface.nativeBuffers[i] as BitmapData;
                    if(bitmap==null || source==null || bitmap.parent!==parents[i] || bitmap.bitmapData!==source ||
                        source.width<Number(surface.gutter)+CELL || source.height<Number(surface.gutter)+CELL)
                        throw new Error("Paged atlas native layer identity changed");
                    var show:Boolean=Boolean(expectedVisibility[bitmap]);
                    if(show){
                        if(changed || record.sources[i]!==source || !record.shown[i]){
                            if(sourceRect==null)sourceRect=new Rectangle(surface.gutter,surface.gutter,CELL,CELL);
                            var wasNonempty:Boolean=record.hasPixels[i];
                            // Bounds intersection is conservative: false proves the
                            // entire centre transparent; true may still include holes.
                            record.hasPixels[i]=source.getColorBoundsRect(0xFF000000,0,false).intersects(sourceRect);
                            ++alphaRectChecks;
                            if(i==0 || i==3) {
                                if(record.hasPixels[i]){page.data[i].copyPixels(source,sourceRect,page.points[cell]);++copies;}
                                else {
                                    if(wasNonempty){page.data[i].fillRect(page.rects[cell],0);++cellClears;}
                                    ++emptyCopiesAvoided;
                                }
                            } else if(!record.hasPixels[i])++emptyCopiesAvoided;
                        }
                        if(record.hasPixels[i])page.content[i]=true;
                        toHide.push(bitmap);
                    } else if(record.shown[i] && (i==0 || i==3)){page.data[i].fillRect(page.rects[cell],0);++cellClears;}
                    record.sources[i]=source;record.shown[i]=show;
                }
                var lowerVisible:Boolean=record.shown[1] && record.hasPixels[1];
                var upperVisible:Boolean=record.shown[2] && record.hasPixels[2];
                page.content[1]=false;
                if(lowerVisible || upperVisible)page.content[2]=true;
                if(backgroundChanged) {
                    if(sourceRect==null)sourceRect=new Rectangle(surface.gutter,surface.gutter,CELL,CELL);
                    if(lowerVisible){page.data[2].copyPixels(surface.nativeBuffers[1],sourceRect,page.points[cell]);++copies;}
                    else {page.data[2].fillRect(page.rects[cell],0);++cellClears;}
                    if(upperVisible){page.data[2].copyPixels(surface.nativeBuffers[2],sourceRect,page.points[cell],null,null,lowerVisible);++copies;}
                    ++backgroundMerges;
                }
                record.entry=surface;record.revision=surface.revision;
            }
        }

        public function beginFrame():void {
            presented=false;
            if(atlasWorld && atlasWorld.loc===location && bindingSurfaces.length) {
                var view:Rectangle=atlasWorld.grafon.sceneViewport();
                for each(var surface:Object in bindingSurfaces) {
                    var wanted:Boolean=view==null || view.intersects(new Rectangle(surface.cx*CELL,surface.cy*CELL,CELL,CELL));
                    for each(var nativeBitmap:Bitmap in surface.bitmaps)if(nativeBitmap.parent && nativeBitmap.visible!=wanted) {
                        nativeBitmap.visible=wanted;++restoreWrites;
                    }
                }
            } else for each(nativeBitmap in hidden)if(nativeBitmap.parent)nativeBitmap.visible=true;
            hidden=[];
            for each(var page:Object in pages)for each(var bitmap:Bitmap in page.layers)bitmap.visible=false;
        }

        private function dropAt(index:int,evicted:Boolean):void {
            var page:Object=pages[index];
            for each(var bitmap:Bitmap in page.layers){if(bitmap.parent)bitmap.parent.removeChild(bitmap);bitmap.visible=false;}
            page.cells=[];page.key="";freePages.push(page);
            pages.splice(index,1);++pagesDisposed;if(evicted)++evictions;
        }

        public function snapshot():Object {
            var attached:int=0,live:int=0;
            var resident:Array=[],visible:Array=[],rows:Array=[];
            for each(var page:Object in pages){
                resident.push(page.key);var shown:Boolean=false;
                for each(var bitmap:Bitmap in page.layers){if(bitmap.parent)++attached;if(bitmap.bitmapData)++live;if(bitmap.visible)shown=true;}
                if(shown)visible.push(page.key);
                rows.push({key:page.key,px:page.px,py:page.py,used:page.used,layers:page.layers.length,visible:shown,layerHasPixels:page.content.concat(),layerVisible:[page.layers[0].visible,page.layers[1].visible,page.layers[2].visible,page.layers[3].visible]});
            }
            return {version:"persistent-atlas-1",bindingRefreshes:bindingRefreshes,bindingReuses:bindingReuses,visibilityRefreshes:visibilityRefreshes,visibilityWrites:visibilityWrites,restoreWrites:restoreWrites,treeEpoch:treeEpoch,boundEpoch:boundEpoch,stationarySkips:stationarySkips,alphaRectChecks:alphaRectChecks,emptyCopiesAvoided:emptyCopiesAvoided,backgroundMerges:backgroundMerges,freePages:freePages.length,poolPages:pages.length+freePages.length,poolReady:poolLocation!=null,ownedBitmaps:allocations-disposals,presented:presented,copies:copies,rebuilds:rebuilds,
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
            while(freePages.length){
                var page:Object=freePages.pop();
                for each(var bitmap:Bitmap in page.layers){if(bitmap.parent)bitmap.parent.removeChild(bitmap);bitmap.bitmapData=null;}
                for each(var data:BitmapData in page.data){data.dispose();++disposals;liveBytes-=LAYER_BYTES;}
                page.layers=[];page.data=[];page.cells=[];
            }
            for each(var parent:DisplayObjectContainer in bindingParents) {
                parent.removeEventListener(Event.ADDED,onTreeMutation);
                parent.removeEventListener(Event.REMOVED,onTreeMutation);
            }
            bindingParents=[];bindingSurfaces=[];bindingCells={};bindingExtras=[];expectedVisibility=new Dictionary();
            boundEpoch=-1;boundResident=boundRedraws=boundEvictions=-1;visibilityKey="";atlasWorld=null;
            poolLocation=null;location=null;poseValid=false;poseX=poseY=poseScale=NaN;
            requestedPages=0;requestedKeys=[];fallbackReason="";presented=false;
        }
    }
}
