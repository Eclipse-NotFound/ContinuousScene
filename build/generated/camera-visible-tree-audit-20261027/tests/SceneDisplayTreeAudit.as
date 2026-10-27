package tests {
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.display.DisplayObject;
    import flash.display.DisplayObjectContainer;
    import flash.display.MovieClip;
    import flash.display.Stage;
    import flash.geom.ColorTransform;
    import flash.geom.Matrix;
    import flash.geom.Rectangle;
    import flash.utils.Dictionary;
    import flash.utils.getQualifiedClassName;
    import flash.utils.getTimer;

    /** Bounded read-only display/bitmap census, strictly outside timed windows. */
    public final class SceneDisplayTreeAudit {
        public static function run(w:*):Object {
            var at:int=getTimer(),stage:Stage=w.main.stage;
            var out:Object={version:"full-display-tree-audit-1",readOnly:true,complete:false,errors:[],nodes:[],bitmaps:[],
                classes:{},filters:{},effectiveNodes:0,cachedNodes:0,filteredNodes:0,uniqueBitmapBytes:0,
                worldUnits:w.loc.units.length,viewport:{width:stage.stageWidth,height:stage.stageHeight}};
            var roles:Dictionary=new Dictionary(true),ids:Dictionary=new Dictionary(true),bitmapIds:Dictionary=new Dictionary(true);
            roles[stage]="stage";roles[w.main]="main";roles[w.visual]="world";roles[w.vscene]="vscene";roles[w.vblack]="vblack";
            var g:*=w.grafon;
            for each(var field:String in ["visFon","visLight","visFront","visBack","visBack2","visVoda","visSats","ramT","ramB","ramL","ramR"])
                if(g[field] is DisplayObject)roles[g[field]]=field;
            for(var l:int=0;l<g.visObjs.length;++l)roles[g.visObjs[l]]="objects-"+l;
            var stack:Array=[{node:stage,parent:-1,index:0,depth:0,visible:true,alpha:1}],seen:int=0;
            var view:Rectangle=new Rectangle(0,0,stage.stageWidth,stage.stageHeight);
            while(stack.length) {
                var entry:Object=stack.pop(),node:DisplayObject=entry.node;
                if(node==null){out.errors.push("Null display child");continue;}
                if(ids[node]!==undefined){out.errors.push("Duplicate display object");continue;}
                if(++seen>20000){out.errors.push("20000-node bound exceeded");break;}
                var id:int=out.nodes.length;ids[node]=id;
                var type:String=getQualifiedClassName(node),r:Object={id:id,parent:entry.parent,index:entry.index,depth:entry.depth,
                    role:roles[node]===undefined?null:roles[node],className:type,name:node.name,visible:node.visible,alpha:node.alpha,
                    effectiveVisible:entry.visible && node.visible,effectiveAlpha:entry.alpha*node.alpha,
                    cacheAsBitmap:node.cacheAsBitmap,blend:node.blendMode,filters:[],maskClass:node.mask?getQualifiedClassName(node.mask):null};
                out.nodes.push(r);out.classes[type]=int(out.classes[type])+1;
                try {
                    var local:Rectangle=node.getBounds(node),bounds:Rectangle=node.getBounds(stage),clip:Rectangle=node.scrollRect;
                    r.localBounds=rect(local);r.stageBounds=rect(bounds);r.boundsIntersectViewport=bounds.intersects(view);
                    r.scrollRect=clip?rect(clip):null;r.matrix3D=node.transform.matrix3D!=null;
                    r.localMatrix=matrix(node.transform.matrix);r.stageMatrix=matrix(node.transform.concatenatedMatrix);
                    var ct:ColorTransform=node.transform.colorTransform;
                    r.color=[ct.redMultiplier,ct.greenMultiplier,ct.blueMultiplier,ct.alphaMultiplier,ct.redOffset,ct.greenOffset,ct.blueOffset,ct.alphaOffset];
                    for each(var f:* in node.filters) {
                        var ft:String=getQualifiedClassName(f),detail:Object={className:ft};
                        for each(field in ["blurX","blurY","quality","distance","angle","strength","inner","knockout","hideObject","alpha","color"])
                            if(field in f)detail[field]=f[field];
                        r.filters.push(detail);out.filters[ft]=int(out.filters[ft])+1;
                    }
                    if(r.cacheAsBitmap)++out.cachedNodes;
                    if(r.filters.length)++out.filteredNodes;
                    if(r.effectiveVisible && r.effectiveAlpha>0)++out.effectiveNodes;
                    var mc:MovieClip=node as MovieClip;
                    if(mc)r.timeline={current:mc.currentFrame,total:mc.totalFrames,isPlaying:mc.isPlaying};
                    var bmp:Bitmap=node as Bitmap;
                    if(bmp) {
                        r.smoothing=bmp.smoothing;r.pixelSnapping=bmp.pixelSnapping;r.bitmapId=null;
                        var data:BitmapData=bmp.bitmapData;
                        if(data) {
                            var bid:*=bitmapIds[data];
                            if(bid===undefined) {
                                bid=out.bitmaps.length;bitmapIds[data]=bid;
                                var bd:Object={id:bid,width:data.width,height:data.height,transparent:data.transparent,displayReferences:0};
                                out.bitmaps.push(bd);out.uniqueBitmapBytes+=Number(data.width)*data.height*4;
                            }
                            ++out.bitmaps[int(bid)].displayReferences;r.bitmapId=bid;
                        }
                    }
                } catch(error:Error){r.readError=error.message;out.errors.push("node "+id+": "+error.message);}
                var c:DisplayObjectContainer=node as DisplayObjectContainer;
                if(c)for(var i:int=c.numChildren-1;i>=0;--i)
                    stack.push({node:c.getChildAt(i),parent:id,index:i,depth:entry.depth+1,visible:r.effectiveVisible,alpha:r.effectiveAlpha});
            }
            out.complete=out.errors.length==0;out.elapsedMs=getTimer()-at;return out;
        }
        private static function rect(r:Rectangle):Object {return {x:r.x,y:r.y,width:r.width,height:r.height};}
        private static function matrix(m:Matrix):Object {return m?{a:m.a,b:m.b,c:m.c,d:m.d,tx:m.tx,ty:m.ty}:null;}
    }
}
