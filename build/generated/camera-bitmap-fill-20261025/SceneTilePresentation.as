package {
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.display.DisplayObjectContainer;
    import flash.display.Sprite;
    import flash.geom.ColorTransform;
    import flash.geom.Matrix;
    import flash.geom.Rectangle;
    import flash.utils.Dictionary;

    /** Trial only. Four graphics nodes borrow native buffers; no pixel copying or caching. */
    public class SceneTilePresentation {
        private var records:Dictionary=new Dictionary();
        private var groups:Array=[];
        private var world:*;
        private var location:*;
        public var copies:int=0;
        public var allocated:int=0;
        public var active:Boolean=false;
        public var updates:int=0;
        public var enables:int=0;
        public var restores:int=0;
        private var rebuilds:int=0;
        private var commands:int=0;
        private var peakCommands:int=0;
        private var liveNodes:int=0;
        private var nodesCreated:int=0;
        private var nodesRemoved:int=0;
        private var liveRecords:int=0;

        public function update(w:*,enabled:Boolean):void {
            ++updates;if(!enabled){clear();return;}
            require(w.grafon.sceneLarge && w.grafon.sceneChunkSide==320,"Native 320 scene required");
            var m:Matrix=w.visual.transform.concatenatedMatrix;
            require(m.a==1 && m.d==1 && m.b==0 && m.c==0 && m.tx==Math.floor(m.tx) && m.ty==Math.floor(m.ty),"Unit integer native transform required");
            require(w.cam.scaleV==1 && w.cam.quakeX==0 && w.cam.quakeY==0,"Unsupported zoom/shake");
            require(!w.sats.active && !w.grafon.visSats.visible,"SATS is outside this trial");
            var parents:Array=[w.grafon.visFront,w.grafon.visBack,w.grafon.visBack2,w.grafon.visVoda];
            if(active)require(w===world && w.loc===location,"Identity changed while active");
            var surfaces:Array=w.grafon.sceneSurfaces();
            require(surfaces.length>0,"Missing native surfaces");
            if(!active) {
                world=w;location=w.loc;
                for(var layer:int=0;layer<4;++layer) {
                    var parent:DisplayObjectContainer=parents[layer];
                    var anchor:int=parent.numChildren;
                    for each(var surface:Object in surfaces) {
                        var bitmap:Bitmap=surface.bitmaps[layer];
                        require(bitmap.parent===parent,"Native layer changed");
                        anchor=Math.min(anchor,parent.getChildIndex(bitmap));
                    }
                    require(anchor<parent.numChildren,"Missing native anchor");
                    var node:Sprite=new Sprite();node.mouseEnabled=false;node.mouseChildren=false;
                    node.name="ContinuousSceneBitmapFill"+layer;
                    parent.addChildAt(node,anchor);++liveNodes;++nodesCreated;
                    groups.push({parent:parent,node:node,last:[]});
                }
                active=true;++enables;
            }
            var lists:Array=[[],[],[],[]],alive:Dictionary=new Dictionary();
            for each(surface in surfaces) {
                require(surface.side==320 && surface.bitmaps.length==4 && surface.nativeBuffers.length==4,"Native surface contract changed");
                for(layer=0;layer<4;++layer) {
                    bitmap=surface.bitmaps[layer];var data:BitmapData=surface.nativeBuffers[layer];
                    var item:Object=records[bitmap];
                    require(bitmap.parent===parents[layer] && bitmap.bitmapData===data,"Native binding changed");
                    require(bitmap.x==surface.cx*320 && bitmap.y==surface.cy*320,"Native origin changed");
                    var rect:Rectangle=bitmap.scrollRect;
                    require(rect!=null && rect.x==surface.gutter && rect.y==surface.gutter && rect.width==320 && rect.height==320,"Native crop changed");
                    var bm:Matrix=bitmap.transform.matrix;
                    require(bm.a==1 && bm.b==0 && bm.c==0 && bm.d==1,"Native bitmap transform changed");
                    var color:ColorTransform=bitmap.transform.colorTransform;
                    require(color.redMultiplier==1 && color.greenMultiplier==1 && color.blueMultiplier==1 && color.alphaMultiplier==(item?0:1) &&
                        color.redOffset==0 && color.greenOffset==0 && color.blueOffset==0 && color.alphaOffset==0 &&
                        bitmap.filters.length==0 && bitmap.mask==null && bitmap.blendMode=="normal","Native bitmap style changed");
                    require(groups[layer].parent===parents[layer] && groups[layer].node.parent===parents[layer],"Presentation layer changed");
                    if(!item){item={bitmap:bitmap,alpha:bitmap.alpha};records[bitmap]=item;++liveRecords;}
                    alive[bitmap]=true;
                    if(bitmap.visible)lists[layer].push({surface:surface,bitmap:bitmap,data:data,revision:surface.revision,
                        x:bitmap.x,y:bitmap.y,gutter:surface.gutter,smooth:bitmap.smoothing});
                    if(bitmap.alpha!=0)bitmap.alpha=0;
                }
            }
            for(var missing:Object in records)if(!alive[missing])restoreRecord(missing as Bitmap);
            commands=0;
            for(layer=0;layer<4;++layer) {
                var list:Array=lists[layer];list.sort(order);
                var group:Object=groups[layer];node=group.node;
                if(!same(group.last,list)) {
                    node.graphics.clear();
                    for each(item in list) {
                        node.graphics.beginBitmapFill(item.data,new Matrix(1,0,0,1,item.x-item.gutter,item.y-item.gutter),false,item.smooth);
                        node.graphics.drawRect(item.x,item.y,320,320);node.graphics.endFill();
                    }
                    group.last=list;++rebuilds;
                }
                commands+=list.length;
            }
            peakCommands=Math.max(peakCommands,commands);
            require(commands>0 && liveNodes==4,"No actual batch terrain commands");
        }
        private function order(a:Object,b:Object):Number {
            return a.y==b.y?a.x-b.x:a.y-b.y;
        }
        private function same(a:Array,b:Array):Boolean {
            if(a.length!=b.length)return false;
            for(var i:int=0;i<a.length;++i)if(a[i].surface!==b[i].surface || a[i].bitmap!==b[i].bitmap || a[i].data!==b[i].data ||
                a[i].revision!==b[i].revision || a[i].x!=b[i].x || a[i].y!=b[i].y || a[i].gutter!=b[i].gutter || a[i].smooth!==b[i].smooth)return false;
            return true;
        }
        private function restoreRecord(bitmap:Bitmap):void {
            var item:Object=records[bitmap];if(!item)return;
            bitmap.alpha=item.alpha;require(bitmap.alpha===item.alpha,"Native alpha restoration mismatch");
            delete records[bitmap];--liveRecords;
        }
        public function clear():void {
            var problem:String="";
            for each(var group:Object in groups)try {
                var node:Sprite=group.node;node.graphics.clear();group.last=[];
                if(node.parent)node.parent.removeChild(node);require(node.parent==null,"Batch node remains attached");
                --liveNodes;++nodesRemoved;
            }catch(eNode:Error){problem+=eNode.message+";";}
            for(var nativeObject:Object in records)try {restoreRecord(nativeObject as Bitmap);}catch(eNative:Error){problem+=eNative.message+";";}
            if(active)++restores;
            groups=[];records=new Dictionary();active=false;world=null;location=null;commands=0;
            require(problem=="" && liveNodes==0 && liveRecords==0,"Batch cleanup failed: "+problem);
        }
        public function snapshot():Object {
            return {active:active,parents:groups.length,updates:updates,enables:enables,restores:restores,
                commands:commands,peakCommands:peakCommands,rebuilds:rebuilds,liveNodes:liveNodes,nodesCreated:nodesCreated,nodesRemoved:nodesRemoved,
                liveNativeRecords:liveRecords,ownBitmapAllocations:allocated,sourcePixelCopies:copies};
        }
        private function require(value:Boolean,message:String):void{if(!value)throw new Error(message);}
    }
}
