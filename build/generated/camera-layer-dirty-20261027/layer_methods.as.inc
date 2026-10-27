        public function auditTimelines():void {
            require(world!=null && world.onPause,"Paused simulation required");++timelineAudits;
        }
        private function newPixels(w:int,h:int):BitmapData {
            require(w>0 && h>0 && liveCPUBytes+Number(w)*h*4<=128*1024*1024,"CPU cache budget exceeded");
            var result:BitmapData=new BitmapData(w,h,true,0);++allocated;
            liveCPUBytes+=Number(w)*h*4;peakCPUBytes=Math.max(peakCPUBytes,liveCPUBytes);return result;
        }
        private function disposePixels(data:BitmapData):void {
            liveCPUBytes-=Number(data.width)*data.height*4;data.dispose();++bitmapDisposals;
        }
        private function collectWatch(group:Object):void {
            var stack:Array=group.nodes.concat(),seen:Dictionary=new Dictionary(),watch:Array=[];
            while(stack.length) {
                var node:DisplayObject=stack.pop() as DisplayObject;if(node==null || seen[node])continue;seen[node]=true;++watchNodes;
                var mc:MovieClip=node as MovieClip;
                if(mc && mc.totalFrames>1)watch.push({node:mc,frame:mc.currentFrame,total:mc.totalFrames});
                var branch:DisplayObjectContainer=node as DisplayObjectContainer;
                if(branch)for(var i:int=0;i<branch.numChildren;++i)stack.push(branch.getChildAt(i));
            }
            group.watch=watch;
        }
        public function prepareWorld(w:*,area:Rectangle):void {
            require(w===world && context && !worldPrepared && !active,"Single-use layer cache required");
            require(root.visible && backdrop.visible && style(root) && root.scrollRect==null &&
                unit(root.transform.concatenatedMatrix) && neutralColor(root.transform.concatenatedColorTransform),"Unsupported world style");
            require(style(backdrop) && backdrop.scrollRect==null,"Unsupported backdrop style");
            var ancestor:DisplayObject=root.parent;
            while(ancestor && ancestor!==stage){require(style(ancestor)&&neutralColor(ancestor.transform.colorTransform),"Ancestor effects unsupported");ancestor=ancestor.parent;}
            bounds=new Rectangle(Math.floor(area.left),Math.floor(area.top),Math.ceil(area.right)-Math.floor(area.left),Math.ceil(area.bottom)-Math.floor(area.top));
            require(bounds.width>0 && bounds.height>0 && bounds.width<=4096 && bounds.height<=4096,"Bounded layer cache required");
            parents=[backdrop,root];parentVisible=[backdrop.visible,root.visible];
            var background:BitmapData=newPixels(width,height);
            try {
                background.draw(backdrop,backdrop.transform.concatenatedMatrix,backdrop.transform.concatenatedColorTransform,null,null,true);++copies;
                require(background.getColorBoundsRect(0xff000000,0xff000000,false).isEmpty(),"Opaque backdrop required");
                backdropTexture=upload(background);
            } finally {disposePixels(background);}
            scratch=newPixels(int(bounds.width),int(bounds.height));
            var container:DisplayObjectContainer=root as DisplayObjectContainer,g:*=world.grafon;
            var current:Object=null;
            for(var i:int=0;i<container.numChildren;++i) {
                var node:DisplayObject=container.getChildAt(i);require(node!=null,"Null direct world layer");worldChildren.push(node);
                var dynamic:Boolean=node===g.visObjs[2] || node===g.visObjs[3] || node===g.visObjs[4] || node===g.visObjs[5];
                if(current==null || dynamic || current.dynamic) {
                    current={index:groups.length,dynamic:dynamic,nodes:[],watch:[],tiles:[],area:null,rasterCalls:0,rasterMs:0,uploadMs:0,changes:0,empty:0,rebuilds:0};groups.push(current);
                }
                current.nodes.push(node);
            }
            var oldCull:Boolean=g.sceneCullRender;
            try {
                g.sceneCullRender=false;g.sceneTick();
                for each(var group:Object in groups){drawGroup(group);collectWatch(group);}
            } finally {g.sceneCullRender=oldCull;g.sceneTick();captureCullRestored=g.sceneCullRender===oldCull;}
            require(captureCullRestored && layerWrites==layerRestores,"Layer preparation failed to restore native state");
            worldPrepared=true;
            initial.sourceLayers="Ordered layer groups with frame-driven cache invalidation; Flash timelines remain live";
            initial.captureBounds={x:bounds.x,y:bounds.y,width:bounds.width,height:bounds.height};
            initial.layerGroups=groupSummary();
            initial.trackingLimit="Only timeline-driven visual changes in paused simulation; arbitrary bitmap pixels and script mutations untracked";
        }
        private function refreshChangedLayers():void {
            var at:int=getTimer(),dirty:Array=[];
            require(DisplayObjectContainer(root).numChildren==worldChildren.length,"World layer lifecycle changed");
            for(var i:int=0;i<worldChildren.length;++i)require(DisplayObjectContainer(root).getChildAt(i)===worldChildren[i],"World layer identity changed");
            for each(var group:Object in groups) {
                var changed:Boolean=false;
                for each(var watch:Object in group.watch) {
                    ++watchReads;
                    if(watch.node.currentFrame!=watch.frame || watch.node.totalFrames!=watch.total) {changed=true;++animationChanges;++group.changes;}
                }
                if(changed)dirty.push(group);
            }
            watchMs+=getTimer()-at;
            for each(group in dirty){drawGroup(group);collectWatch(group);}
        }
        private function drawGroup(group:Object):void {
            var at:int=getTimer(),state:Array=[],selected:Dictionary=new Dictionary();
            for each(var selectedNode:DisplayObject in group.nodes)selected[selectedNode]=true;
            scratch.fillRect(scratch.rect,0);
            try {
                for each(var node:DisplayObject in worldChildren) {
                    state.push({node:node,visible:node.visible});
                    if(!selected[node] && node.visible){node.visible=false;++layerWrites;}
                }
                scratch.draw(root,new Matrix(1,0,0,1,-bounds.x,-bounds.y),null,null,null,true);++copies;
            } finally {
                for each(var item:Object in state)if(item.node.visible!==item.visible){item.node.visible=item.visible;++layerRestores;}
            }
            ++layerRasterCalls;++group.rasterCalls;
            var used:Rectangle=scratch.getColorBoundsRect(0xff000000,0,false);
            if(used.isEmpty()) {releaseGroup(group);++group.empty;}
            else {
                if(group.area==null || !group.area.containsRect(used)) {
                    releaseGroup(group);++group.rebuilds;
                    used.inflate(64,64);used=used.intersection(scratch.rect);
                    group.area=new Rectangle(Math.floor(used.x),Math.floor(used.y),Math.ceil(used.right)-Math.floor(used.x),Math.ceil(used.bottom)-Math.floor(used.y));
                    for(var y:int=int(group.area.top);y<group.area.bottom;y+=1024)for(var x:int=int(group.area.left);x<group.area.right;x+=1024) {
                        var tw:int=Math.min(1024,group.area.right-x),th:int=Math.min(1024,group.area.bottom-y);
                        var pixels:BitmapData=newPixels(tw,th);
                        var tile:Object={pixels:pixels,rect:new Rectangle(x,y,tw,th),x:bounds.x+x,y:bounds.y+y,width:tw,height:th,texture:null};
                        group.tiles.push(tile);
                        pixels.copyPixels(scratch,tile.rect,new Point());++copies;
                        tile.texture=upload(pixels);
                    }
                } else {
                    for each(tile in group.tiles) {
                        tile.pixels.copyPixels(scratch,tile.rect,new Point());++copies;
                        var uploadAt:int=getTimer();tile.texture.uploadFromBitmapData(tile.pixels);++uploads;
                        var uploadElapsed:int=getTimer()-uploadAt;layerUploadMs+=uploadElapsed;group.uploadMs+=uploadElapsed;
                    }
                }
            }
            var elapsed:int=getTimer()-at;layerRasterMs+=elapsed;group.rasterMs+=elapsed;
        }
        private function releaseGroup(group:Object):void {
            for each(var tile:Object in group.tiles) {
                if(tile.texture){tile.texture.dispose();++texturesDisposed;gpuBytes-=Number(tile.width)*tile.height*4;}
                if(tile.pixels)disposePixels(tile.pixels);
            }
            group.tiles=[];group.area=null;
        }
        private function groupSummary():Array {
            var result:Array=[];
            for each(var group:Object in groups)result.push({index:group.index,dynamic:group.dynamic,layers:group.nodes.length,
                watched:group.watch.length,rasterCalls:group.rasterCalls,rasterMs:group.rasterMs,uploadMs:group.uploadMs,
                changes:group.changes,empty:group.empty,rebuilds:group.rebuilds,tiles:group.tiles.length,
                area:group.area?{x:group.area.x,y:group.area.y,width:group.area.width,height:group.area.height}:null});
            return result;
        }
