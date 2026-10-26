        private function adoptNativeAppends():void {
            var surfaces:Array=grafon.sceneSurfaces(),live:Dictionary=new Dictionary(true);
            require(surfaces.length>=surfaceCount && surfaces.length<4096,"Native drop is not supported by this diagnostic");
            var newSurfaces:Array=[],newTiles:Dictionary=new Dictionary(true),newNodes:int=0;
            for each(var surface:Object in surfaces) {
                require(surface!=null && !live[surface],"Duplicate live native surface");live[surface]=true;
                if(!surfaceSet[surface]) {
                    require(surface.bitmaps.length==4 && surface.nativeBuffers.length==4,"New surface is not four-layer");
                    newSurfaces.push(surface);
                    for(var k:int=0;k<4;++k) {
                        var tile:Bitmap=surface.bitmaps[k] as Bitmap;
                        require(tile!=null && getQualifiedClassName(tile)=="flash.display::Bitmap" && !nativeTileSet[tile] && !newTiles[tile],"New tile identity conflict");
                        require(tile.parent===terrain[k].target && tile.bitmapData===surface.nativeBuffers[k],"New tile parent/data mismatch");
                        newTiles[tile]={surface:surface,layer:k,data:tile.bitmapData};++newNodes;
                    }
                }
            }
            for(var oldSurface:Object in surfaceSet)require(live[oldSurface]===true,"Native surface dropped; do not restore stale data");
            if(newSurfaces.length==0)return;
            // First validate every complete old sequence and all appended tails.
            // Do not partially adopt a changed parent or an unrelated new node.
            var tails:Array=[],seen:Dictionary=new Dictionary(true),count:int=0;
            for(var l:int=0;l<terrain.length;++l) {
                var parent:DisplayObjectContainer=terrain[l].target,at:int=0,tail:Array=[];
                for each(var node:DisplayObject in parentOrders[l]) {
                    var selected:Object=selectedTiles[node];if(selected!=null && selected.held)continue;
                    require(at<parent.numChildren && parent.getChildAt(at)===node,"Original native child prefix changed");++at;
                }
                while(at<parent.numChildren) {
                    node=parent.getChildAt(at++);var meta:Object=newTiles[node];
                    require(meta!=null && meta.layer==l && !seen[node],"Appended node lacks new native ownership");
                    seen[node]=true;tail.push(node);++count;
                }
                tails.push(tail);
            }
            require(count==newNodes && count==newSurfaces.length*4,"Incomplete native append");
            for(l=0;l<terrain.length;++l)parentOrders[l]=parentOrders[l].concat(tails[l]);
            for(var newTile:Object in newTiles)nativeTileSet[newTile]=newTiles[newTile];
            for each(surface in newSurfaces)surfaceSet[surface]=true;
            surfaceCount=surfaces.length;
            report.rootSelection.adoptedSurfaces+=newSurfaces.length;
            report.rootSelection.adoptedBitmaps+=newNodes;
            ++report.rootSelection.appendAudits;
        }

