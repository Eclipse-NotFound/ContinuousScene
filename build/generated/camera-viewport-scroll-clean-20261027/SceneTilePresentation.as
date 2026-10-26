package {
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.display.DisplayObjectContainer;
    import flash.geom.Matrix;
    import flash.geom.Point;
    import flash.geom.Rectangle;
    import flash.utils.Dictionary;
    import flash.utils.getTimer;

    /** Trial: four viewport buffers scroll old pixels; exposed strips and revisions refill. */
    public class SceneTilePresentation {
        private var groups:Array=[];
        private var records:Dictionary=new Dictionary();
        private var cells:Object={};
        private var world:*;
        private var location:*;
        private var width:int=0,height:int=0;
        private var originX:int=0,originY:int=0;
        private var valid:Boolean=false;
        private var point:Point=new Point();
        private var rect:Rectangle=new Rectangle();
        private var recordCount:int=0;
        public var copies:int=0,allocated:int=0,disposed:int=0;
        public var active:Boolean=false;
        public var updates:int=0,enables:int=0,restores:int=0;
        public var scrolls:int=0,fullRefreshes:int=0,dirtyRects:int=0;
        public var copiedPixels:Number=0,scrolledPixels:Number=0;
        public var prepareMs:int=0;

        public function update(w:*,enabled:Boolean):void {
            ++updates;
            if(!enabled){clear();return;}
            require(w.grafon.sceneLarge && w.grafon.sceneChunkSide==320,"Native 320 scene required");
            var matrix:Matrix=w.visual.transform.concatenatedMatrix;
            require(matrix.a==1 && matrix.d==1 && matrix.b==0 && matrix.c==0 &&
                matrix.tx==Math.floor(matrix.tx) && matrix.ty==Math.floor(matrix.ty),"Unit integer camera required");
            require(w.cam.scaleV==1 && w.cam.quakeX==0 && w.cam.quakeY==0 &&
                !w.sats.active && !w.grafon.visSats.visible,"Unsupported zoom/shake/SATS");
            var parents:Array=[w.grafon.visFront,w.grafon.visBack,w.grafon.visBack2,w.grafon.visVoda];
            var surfaces:Array=w.grafon.sceneSurfaces();
            require(surfaces.length>0,"Missing native surfaces");
            if(groups.length==0)prepare(w,parents,surfaces);
            require(w===world && w.loc===location && width==w.main.stage.stageWidth && height==w.main.stage.stageHeight,
                "Location or screen changed");
            var nextX:int=-int(matrix.tx),nextY:int=-int(matrix.ty);
            var dx:int=originX-nextX,dy:int=originY-nextY;
            var full:Boolean=!valid || Math.abs(dx)>=width || Math.abs(dy)>=height;
            var dirty:Array=[];
            if(full){dirty.push(new Rectangle(nextX,nextY,width,height));++fullRefreshes;}
            else {
                if(dx>0)dirty.push(new Rectangle(nextX,nextY,dx,height));
                else if(dx<0)dirty.push(new Rectangle(nextX+width+dx,nextY,-dx,height));
                if(dy>0)dirty.push(new Rectangle(nextX,nextY,width,dy));
                else if(dy<0)dirty.push(new Rectangle(nextX,nextY+height+dy,width,-dy));
            }
            var alive:Dictionary=new Dictionary(),newCells:Object={};
            for each(var surface:Object in surfaces) {
                require(surface.side==320 && surface.bitmaps.length==4 && surface.nativeBuffers.length==4,
                    "Native surface contract changed");
                var key:String=surface.cx+":"+surface.cy;
                var prior:Object=cells[key];
                var state:Object={surface:surface,revision:surface.revision,show:[],sources:[],
                    x:int(surface.cx)*320,y:int(surface.cy)*320};
                var changed:Boolean=prior==null || prior.surface!==surface || prior.revision!==surface.revision;
                for(var layer:int=0;layer<4;++layer) {
                    var bitmap:Bitmap=surface.bitmaps[layer];
                    var data:BitmapData=surface.nativeBuffers[layer];
                    var record:Object=records[bitmap];
                    var parent:DisplayObjectContainer=parents[layer];
                    require(parent===groups[layer].parent && groups[layer].node.parent===parent,
                        "Presentation parent changed");
                    var pm:Matrix=parent.transform.matrix;
                    require(pm.a==1 && pm.d==1 && pm.b==0 && pm.c==0 && pm.tx==0 && pm.ty==0,
                        "Unsupported layer transform");
                    require(bitmap.parent===parent && bitmap.bitmapData===data &&
                        bitmap.x==state.x && bitmap.y==state.y,"Native tile binding changed");
                    var crop:Rectangle=bitmap.scrollRect;
                    var bm:Matrix=bitmap.transform.matrix;
                    var color:*=bitmap.transform.colorTransform;
                    require(crop!=null && crop.x==surface.gutter && crop.y==surface.gutter &&
                        crop.width==320 && crop.height==320 && bm.a==1 && bm.d==1 && bm.b==0 && bm.c==0 &&
                        bitmap.filters.length==0 && bitmap.mask==null && bitmap.blendMode=="normal" &&
                        color.redMultiplier==1 && color.greenMultiplier==1 && color.blueMultiplier==1 &&
                        color.alphaMultiplier==(record && active?0:1) &&
                        color.redOffset==0 && color.greenOffset==0 && color.blueOffset==0 && color.alphaOffset==0,
                        "Native tile crop or style changed");
                    if(record==null){record={bitmap:bitmap,alpha:bitmap.alpha};records[bitmap]=record;++recordCount;}
                    alive[bitmap]=true;state.show.push(bitmap.visible);state.sources.push(data);
                    if(prior!=null && (prior.show[layer]!==bitmap.visible || prior.sources[layer]!==data))changed=true;
                }
                if(changed && !full)dirty.push(new Rectangle(state.x,state.y,320,320));
                newCells[key]=state;
            }
            for(key in cells)if(newCells[key]==null && !full)dirty.push(new Rectangle(cells[key].x,cells[key].y,320,320));
            for(var missing:Object in records)if(!alive[missing])restoreRecord(missing as Bitmap);
            cells=newCells;
            var view:Rectangle=new Rectangle(nextX,nextY,width,height);
            for(layer=0;layer<4;++layer) {
                var group:Object=groups[layer];data=group.data;
                var changedPixels:Boolean=full || dx!=0 || dy!=0 || dirty.length>0;
                if(changedPixels)data.lock();
                try {
                    if(!full && (dx!=0 || dy!=0)) {
                        data.scroll(dx,dy);++scrolls;scrolledPixels+=Number(width-Math.abs(dx))*(height-Math.abs(dy));
                    }
                    for each(var area:Rectangle in dirty) {
                        var clipped:Rectangle=area.intersection(view);
                        if(clipped.isEmpty())continue;
                        rect.setTo(clipped.x-nextX,clipped.y-nextY,clipped.width,clipped.height);
                        data.fillRect(rect,0);++dirtyRects;
                        for each(surface in surfaces) {
                            if(!surface.bitmaps[layer].visible)continue;
                            var left:int=Math.max(clipped.left,int(surface.cx)*320);
                            var top:int=Math.max(clipped.top,int(surface.cy)*320);
                            var right:int=Math.min(clipped.right,(int(surface.cx)+1)*320);
                            var bottom:int=Math.min(clipped.bottom,(int(surface.cy)+1)*320);
                            if(right<=left || bottom<=top)continue;
                            rect.setTo(left-int(surface.cx)*320+surface.gutter,
                                top-int(surface.cy)*320+surface.gutter,right-left,bottom-top);
                            point.setTo(left-nextX,top-nextY);
                            data.copyPixels(surface.nativeBuffers[layer],rect,point);
                            ++copies;copiedPixels+=Number(right-left)*(bottom-top);
                        }
                    }
                } finally {if(changedPixels)data.unlock();}
                if(group.node.x!=nextX)group.node.x=nextX;
                if(group.node.y!=nextY)group.node.y=nextY;
                if(!group.node.visible)group.node.visible=true;
            }
            for(var hidden:Object in records)if(Bitmap(hidden).alpha!=0)Bitmap(hidden).alpha=0;
            if(!active){active=true;++enables;}
            originX=nextX;originY=nextY;valid=true;
        }

        private function prepare(w:*,parents:Array,surfaces:Array):void {
            var started:int=getTimer();
            world=w;location=w.loc;width=w.main.stage.stageWidth;height=w.main.stage.stageHeight;
            require(width>0 && height>0 && width<=4096 && height<=4096 && width*height<=8388608,"Viewport budget exceeded");
            try {
                for(var i:int=0;i<4;++i) {
                    var parent:DisplayObjectContainer=parents[i];
                    var anchor:int=parent.numChildren;
                    for each(var surface:Object in surfaces)anchor=Math.min(anchor,parent.getChildIndex(surface.bitmaps[i]));
                    require(anchor<parent.numChildren,"Native anchor missing");
                    var data:BitmapData=new BitmapData(width,height,true,0);++allocated;
                    var bitmap:Bitmap=new Bitmap(data,"always",false);bitmap.visible=false;
                    bitmap.name="ContinuousSceneViewportScroll"+i;
                    groups.push({parent:parent,node:bitmap,data:data});
                    parent.addChildAt(bitmap,anchor);
                }
            } finally {prepareMs+=getTimer()-started;}
        }

        private function restoreRecord(bitmap:Bitmap):void {
            var record:Object=records[bitmap];
            bitmap.alpha=record.alpha;
            require(bitmap.alpha===record.alpha,"Native alpha restore failed");
            delete records[bitmap];--recordCount;
        }

        public function clear():void {
            for each(var group:Object in groups)if(group.node.visible)group.node.visible=false;
            for(var key:Object in records)if(Bitmap(key).alpha!=records[key].alpha)Bitmap(key).alpha=records[key].alpha;
            if(active){active=false;++restores;}
        }

        public function dispose():void {
            clear();
            for each(var group:Object in groups) {
                if(group.node.parent!=null)group.node.parent.removeChild(group.node);
                group.node.bitmapData=null;group.data.dispose();++disposed;
            }
            groups=[];records=new Dictionary();cells={};recordCount=0;
            world=null;location=null;valid=false;
        }

        public function snapshot():Object {
            return {active:active,parents:active?groups.length:0,updates:updates,enables:enables,restores:restores,
                ownBitmapAllocations:allocated,ownBitmapDisposals:disposed,liveBitmaps:allocated-disposed,
                sourcePixelCopies:copies,cacheBytes:Number(allocated-disposed)*width*height*4,prepareMs:prepareMs,
                scrolls:scrolls,fullRefreshes:fullRefreshes,dirtyRects:dirtyRects,copiedPixels:copiedPixels,
                scrolledPixels:scrolledPixels,nativeRecords:recordCount,width:width,height:height};
        }
        private function require(value:Boolean,message:String):void{if(!value)throw new Error(message);}
    }
}

