        private function actorExtent(node:DisplayObject):Rectangle {
            ++dirtyOwnerReads;
            var m:Matrix=root.transform.concatenatedMatrix;
            require(unit(m),"Actor extent requires integer unit camera");
            var rect:Rectangle=node.transform.pixelBounds;
            rect.offset(-m.tx,-m.ty);
            rect=rect.union(node.getBounds(root));
            require(isFinite(rect.x)&&isFinite(rect.y)&&isFinite(rect.width)&&isFinite(rect.height),"Invalid actor extent");
            // A bounded diagnostic hypothesis, not a proven general filter bound.
            // Complete native actor-layer comparison independently checks coverage.
            rect.inflate(16,16);rect.offset(-bounds.x,-bounds.y);
            return rect.intersection(scratch.rect);
        }
        private function collectWatch(group:Object):void {
            var stack:Array=[],seen:Dictionary=new Dictionary(),watch:Array=[],owners:Dictionary=new Dictionary();
            for each(var layer:DisplayObject in group.nodes) {
                if(group.actor) {
                    var outer:DisplayObjectContainer=layer as DisplayObjectContainer;
                    require(outer!=null,"Actor layer must be a container");
                    for(var k:int=0;k<outer.numChildren;++k) {
                        var top:DisplayObject=outer.getChildAt(k);if(top!=null)stack.push({node:top,owner:top});
                    }
                } else stack.push({node:layer,owner:layer});
            }
            while(stack.length) {
                var entry:Object=stack.pop(),node:DisplayObject=entry.node as DisplayObject;
                if(node==null || seen[node])continue;seen[node]=true;++watchNodes;
                var mc:MovieClip=node as MovieClip;
                if(mc && mc.totalFrames>1) {
                    watch.push({node:mc,owner:entry.owner,frame:mc.currentFrame,total:mc.totalFrames});
                    if(group.actor && owners[entry.owner]==null)owners[entry.owner]=actorExtent(entry.owner);
                }
                var branch:DisplayObjectContainer=node as DisplayObjectContainer;
                if(branch)for(var i:int=0;i<branch.numChildren;++i)stack.push({node:branch.getChildAt(i),owner:entry.owner});
            }
            group.watch=watch;group.extents=owners;
        }
        private function maskedDraw(group:Object,destination:BitmapData,area:Rectangle):void {
            var state:Array=[],selected:Dictionary=new Dictionary();
            for each(var selectedNode:DisplayObject in group.nodes)selected[selectedNode]=true;
            destination.fillRect(destination.rect,0);
            try {
                for each(var node:DisplayObject in worldChildren) {
                    state.push({node:node,visible:node.visible});
                    if(!selected[node] && node.visible){node.visible=false;++layerWrites;}
                }
                destination.draw(root,new Matrix(1,0,0,1,-bounds.x-area.x,-bounds.y-area.y),null,null,null,true);++copies;
            } finally {
                for each(var item:Object in state)if(item.node.visible!==item.visible){item.node.visible=item.visible;++layerRestores;}
            }
        }
        private function redrawActorTiles(group:Object,changed:Dictionary):void {
            var at:int=getTimer(),dirty:Object={},count:int=0;
            for(var ownerKey:Object in changed) {
                var owner:DisplayObject=ownerKey as DisplayObject;
                var old:Rectangle=group.extents[owner] as Rectangle;
                require(old!=null,"Missing prior actor coverage");
                var rect:Rectangle=old.union(actorExtent(owner)).intersection(scratch.rect);
                if(rect.isEmpty()){++tileSkipChanges;continue;}
                for(var y:int=int(rect.top/512)*512;y<rect.bottom;y+=512)for(var x:int=int(rect.left/512)*512;x<rect.right;x+=512) {
                    var key:String=x+":"+y;if(dirty[key]==null){dirty[key]=new Rectangle(x,y,Math.min(512,bounds.width-x),Math.min(512,bounds.height-y));++count;}
                }
            }
            dirtyTilesMax=Math.max(dirtyTilesMax,count);
            // Stable traversal follows tile coordinates, not Dictionary order.
            for(y=0;y<bounds.height;y+=512)for(x=0;x<bounds.width;x+=512) {
                key=x+":"+y;var area:Rectangle=dirty[key] as Rectangle;if(area==null)continue;
                var tile:Object=null;
                for each(var candidate:Object in group.tiles)if(candidate.key==key){tile=candidate;break;}
                if(tile==null) {
                    var pixels:BitmapData=newPixels(int(area.width),int(area.height));
                    tile={pixels:pixels,rect:area,x:bounds.x+x,y:bounds.y+y,width:area.width,height:area.height,texture:null,key:key};group.tiles.push(tile);
                }
                maskedDraw(group,tile.pixels,area);++tileRefreshes;
                var uploadAt:int=getTimer();
                if(tile.texture==null)tile.texture=upload(tile.pixels);
                else{tile.texture.uploadFromBitmapData(tile.pixels);++uploads;}
                tileUploadMs+=getTimer()-uploadAt;
            }
            tileRefreshMs+=getTimer()-at;
        }
        private function verifyActorTiles():void {
            require(actorGroup!=null && oracleImage!=null,"Actor oracle missing");
            maskedDraw(actorGroup,scratch,scratch.rect);
            oracleImage.fillRect(oracleImage.rect,0);
            for each(var tile:Object in actorGroup.tiles){oracleImage.copyPixels(tile.pixels,tile.pixels.rect,tile.rect.topLeft);++copies;}
            var difference:Object=scratch.compare(oracleImage),same:Boolean=difference===0;
            ++oracleCalls;oracleChecks.push({call:oracleCalls,equal:same,tiles:actorGroup.tiles.length,refreshes:tileRefreshes});
            if(oracleCalls==1 || !same){savePixel("actor-native-"+oracleCalls,scratch);savePixel("actor-cached-"+oracleCalls,oracleImage);}
            if(difference is BitmapData) {
                var data:BitmapData=difference as BitmapData;++allocated;liveCPUBytes+=Number(data.width)*data.height*4;
                peakCPUBytes=Math.max(peakCPUBytes,liveCPUBytes);disposePixels(data);
            }
            require(same,"Changed actor tiles differ from complete native layer");
        }
