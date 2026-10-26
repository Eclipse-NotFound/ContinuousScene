        private var nativeTileSet:Dictionary=new Dictionary(true);
        private var selectedTiles:Dictionary=new Dictionary(true);
        private var parentOrders:Array=[];
        private var surfaceSet:Dictionary=new Dictionary(true);
        private var surfaceCount:int=0;

        private function collectRoots():void {
            require(!rootsReady && routeBounds!=null,"Tile collection state");
            var at:int=getTimer();routeBounds.inflate(320,320);
            report.rootSelection={scanned:0,selected:0,byLayer:[0,0,0,0],classes:{},skips:{},
                area:{x:routeBounds.x,y:routeBounds.y,width:routeBounds.width,height:routeBounds.height},
                perFrameFullScans:0,transitionWrites:0,audits:0,visibilityWrites:0};
            collectMasks(stage);
            var surfaces:Array=grafon.sceneSurfaces();surfaceCount=surfaces.length;
            require(surfaceCount>0 && surfaceCount<4096,"Invalid native surface set");
            for each(var surface:Object in surfaces) {
                require(surface!=null && !surfaceSet[surface] && surface.bitmaps.length==4 && surface.nativeBuffers.length==4,"Native surface ownership");
                surfaceSet[surface]=true;
                for(var k:int=0;k<4;++k) {
                    var bitmap:Bitmap=surface.bitmaps[k] as Bitmap;
                    require(bitmap!=null && getQualifiedClassName(bitmap)=="flash.display::Bitmap" && !nativeTileSet[bitmap],"Unknown/duplicate native tile");
                    require(bitmap.parent===terrain[k].target && bitmap.bitmapData===surface.nativeBuffers[k],"Native tile parent/data mismatch");
                    nativeTileSet[bitmap]={surface:surface,layer:k,data:bitmap.bitmapData};
                }
            }
            for(var l:int=0;l<terrain.length;++l) {
                var parent:DisplayObjectContainer=terrain[l].target as DisplayObjectContainer;
                require(parent!=null,"Terrain parent missing");
                var order:Array=[];parentOrders.push(order);
                for(var i:int=0;i<parent.numChildren;++i) {
                    var root:DisplayObject=parent.getChildAt(i),reason:String="",meta:Object=nativeTileSet[root];
                    order.push(root);++report.rootSelection.scanned;
                    if(meta==null)reason="not-native-tile";
                    else if(root.visible)reason="already-visible";
                    else if(root.mask!=null || maskTargets[root]===true || root.filters.length>0)reason="mask-or-filter";
                    else if(root.transform.matrix3D!=null || root.transform.matrix==null)reason="3d";
                    var bounds:Rectangle=root.getBounds(world.visual);
                    if(reason=="" && (!isFinite(bounds.x) || !isFinite(bounds.y) || !isFinite(bounds.width) || !isFinite(bounds.height) || bounds.isEmpty()))reason="bounds";
                    if(reason=="" && bounds.intersects(routeBounds))reason="route-visible";
                    if(reason=="") {
                        var tile:Bitmap=root as Bitmap;
                        var item:Object={target:tile,parent:parent,index:i,alpha:tile.alpha,matrix:tile.transform.matrix.clone(),
                            visible:tile.visible,bounds:bounds,meta:meta,rect:tile.scrollRect,held:false,
                            width:tile.bitmapData.width,height:tile.bitmapData.height};
                        roots.push(item);selectedTiles[tile]=item;++report.rootSelection.byLayer[l];
                        report.rootSelection.classes["flash.display::Bitmap"]=int(report.rootSelection.classes["flash.display::Bitmap"])+1;
                    } else report.rootSelection.skips[reason]=int(report.rootSelection.skips[reason])+1;
                }
            }
            rootsReady=true;report.rootSelection.selected=roots.length;
            report.rootSelection.surfaces=surfaceCount;report.rootSelection.prepareMs=getTimer()-at;
            require(roots.length>0,"No offscreen native tiles qualified");auditRoots();
        }

        private function auditRoots():void {
            if(!rootsReady)return;
            var surfaces:Array=grafon.sceneSurfaces();
            require(surfaces.length==surfaceCount,"Prepared surface set changed");
            var seen:Dictionary=new Dictionary(true);
            for each(var surface:Object in surfaces) {
                require(surfaceSet[surface]===true && !seen[surface],"Prepared surface identity changed");seen[surface]=true;
            }
            for each(var item:Object in roots) {
                var tile:Bitmap=item.target;
                require(tile.parent===(item.held?null:item.parent),"Tile parent changed externally");
                require(tile.visible===false && tile.alpha===item.alpha && sameMatrix(tile.transform.matrix,item.matrix),"Tile pose/visibility changed");
                require(item.meta.surface.bitmaps[item.meta.layer]===tile && item.meta.surface.nativeBuffers[item.meta.layer]===item.meta.data && tile.bitmapData===item.meta.data,"Tile native ownership changed");
                require(tile.bitmapData.width===item.width && tile.bitmapData.height===item.height && tile.mask==null && tile.filters.length==0,"Tile data/effects changed");
                var rect:Rectangle=tile.scrollRect;
                require((rect==null && item.rect==null) || (rect!=null && item.rect!=null && rect.equals(item.rect)),"Tile clipping changed");
            }
            for(var l:int=0;l<terrain.length;++l) {
                var parent:DisplayObjectContainer=terrain[l].target,at:int=0;
                for each(var node:DisplayObject in parentOrders[l]) {
                    var entry:Object=selectedTiles[node];if(entry!=null && entry.held)continue;
                    require(at<parent.numChildren && parent.getChildAt(at)===node,"Native child order changed");++at;
                }
                require(at==parent.numChildren,"Native child count changed");
            }
            ++report.rootSelection.audits;
        }

        private function restoreRoots():void {
            if(!rootsReady)return;
            var errors:Array=[],live:Dictionary=new Dictionary(true);
            for each(var surface:Object in grafon.sceneSurfaces())live[surface]=true;
            for(var l:int=0;l<terrain.length;++l) {
                var parent:DisplayObjectContainer=terrain[l].target;
                for(var i:int=0;i<parentOrders[l].length;++i) {
                    var item:Object=selectedTiles[parentOrders[l][i]];
                    if(item==null || !item.held)continue;
                    try {
                        require(live[item.meta.surface]===true && item.meta.surface.bitmaps[item.meta.layer]===item.target && item.meta.surface.nativeBuffers[item.meta.layer]===item.meta.data && item.target.bitmapData===item.meta.data,"Do not resurrect dropped native data");
                        require(item.target.parent==null && item.meta.data.width>0 && item.meta.data.height>0,"Restore ownership conflict");
                        try {parent.addChildAt(item.target,i);}
                        finally {if(item.target.parent===parent){item.held=false;++report.rootSelection.transitionWrites;}}
                        require(!item.held,"Restore callback changed parent");
                    } catch(error:Error){errors.push(error.message);}
                }
            }
            currentCondition=0;
            require(errors.length==0,"Tile restore: "+errors.join(";"));
        }

        private function applyLayers(condition:int):void {
            require(condition==0 || condition==1,"Invalid tile condition");
            var expected:Array=[grafon.visFront,grafon.visBack,grafon.visBack2,grafon.visVoda];
            for(var i:int=0;i<terrain.length;++i)require(terrain[i].target===expected[i] && terrain[i].target.parent===terrain[i].parent,"Terrain layer identity changed");
            if(condition==currentCondition)return;
            require(rootsReady,"Tile selection missing");auditRoots();
            if(condition==0)restoreRoots();
            else {
                for each(var item:Object in roots) {
                    item.held=true;
                    try {item.parent.removeChild(item.target);}
                    finally {if(item.target.parent===item.parent)item.held=false;else ++report.rootSelection.transitionWrites;}
                    require(item.target.parent==null && item.held,"Detach callback changed parent");
                }
                currentCondition=condition;
            }
        }

