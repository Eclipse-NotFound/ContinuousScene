package {
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.display.DisplayObject;
    import flash.display.DisplayObjectContainer;
    import flash.display.MovieClip;
    import flash.display.Stage;
    import flash.display.PNGEncoderOptions;
    import flash.filesystem.File;
    import flash.filesystem.FileMode;
    import flash.filesystem.FileStream;
    import flash.display.Stage3D;
    import flash.display3D.Context3D;
    import flash.display3D.IndexBuffer3D;
    import flash.display3D.VertexBuffer3D;
    import flash.display3D.Program3D;
    import flash.display3D.textures.RectangleTexture;
    import flash.events.Event;
    import flash.events.ErrorEvent;
    import flash.geom.ColorTransform;
    import flash.geom.Matrix;
    import flash.geom.Rectangle;
    import flash.geom.Point;
    import flash.utils.ByteArray;
    import flash.utils.Dictionary;
    import flash.utils.Endian;
    import flash.utils.getTimer;
    import flash.utils.getQualifiedClassName;

    /** Layer-cache prototype; native Flash timelines remain live in both arms.
     * Shader byte format inherited from the audited local Stage3D diagnostic.
     * This class is never linked into the production mod.
     */
    public class SceneTilePresentation {
        private var stage:Stage,plane:Stage3D,context:Context3D,program:Program3D;
        private var vertices:VertexBuffer3D,indices:IndexBuffer3D;
        private var world:*,location:*,root:DisplayObject,backdrop:DisplayObject;
        private var parents:Array=[],parentVisible:Array=[],textures:Array=[],clips:Array=[];
        private var planeSaved:Object,bounds:Rectangle,initial:Object;
        private var backdropTexture:RectangleTexture;
        private var width:int,height:int,requested:Boolean=false,createdAt:int,errorText:String="";
        private var gpuBytes:Number=0,peakGPUBytes:Number=0;
        private var texturesCreated:int=0,texturesDisposed:int=0,uploads:int=0;
        private var contextCreates:int=0,contextDisposals:int=0,bitmapDisposals:int=0;
        private var captures:int=0,draws:int=0,presents:int=0,enables:int=0,restores:int=0,updateCount:int=0;
        private var clipsStopped:int=0,clipsResumed:int=0,timelineAudits:int=0;
        private var timelinesFrozen:Boolean=false,timelinesRestored:Boolean=false;
        private var timelineChanges:Array=[];
        private var emptySlots:Array=[],walkedNodes:int=0;
        private var observations:Dictionary=new Dictionary(),observationSteps:int=0,implicitStopped:int=0;
        private var observationReport:Array=[];
        private var frameScriptDrainDone:Boolean=false,frameScriptDrains:Array=[];
        private var captureCullRestored:Boolean=false,worldPrepared:Boolean=false;
        private var groups:Array=[],worldChildren:Array=[],scratch:BitmapData;
        private var nativeTail:Array=[];
        private var originalLayerVisibility:Dictionary=new Dictionary();
        private var lowerLayerCount:int=0;
        private var actorGroup:Object=null,oracleImage:BitmapData;
        private var tileRefreshes:int=0,tileRefreshMs:int=0,tileUploadMs:int=0,tileSkipChanges:int=0;
        private var dirtyTilesMax:int=0,oracleCalls:int=0,oracleChecks:Array=[];
        private var dirtyOwnerReads:int=0,actorDrawCalls:int=0,actorDrawMs:int=0;private var actorDirtyPixels:Number=0;
        private var layerRasterCalls:int=0,layerRasterMs:int=0,layerUploadMs:int=0;
        private var animationChanges:int=0,watchReads:int=0,watchNodes:int=0,watchMs:int=0;
        private var liveCPUBytes:Number=0,peakCPUBytes:Number=0;
        private var layerWrites:int=0,layerRestores:int=0;
        private var quad:Vector.<Number>=new Vector.<Number>(24,true);
        public var allocated:int=0,copies:int=0,active:Boolean=false;

        public function prepareContext(w:*):void {
            require(!requested && !context,"Single-use context required");
            world=w;location=w.loc;stage=w.main.stage;root=w.visual;backdrop=w.grafon.visFon;
            width=stage.stageWidth;height=stage.stageHeight;
            require(w.grafon.sceneLarge && width>0 && height>0 && width<=2048 && height<=2048,"Bounded native viewport required");
            require(stage.stage3Ds.length>0,"Stage3D unavailable");plane=stage.stage3Ds[0];
            require(plane.context3D==null,"Existing Stage3D belongs to another renderer");
            planeSaved={visible:plane.visible,x:plane.x,y:plane.y};plane.visible=false;plane.x=0;plane.y=0;
            createdAt=getTimer();requested=true;
            plane.addEventListener(Event.CONTEXT3D_CREATE,created);plane.addEventListener(ErrorEvent.ERROR,failed);
            plane.requestContext3D("auto","baseline");
        }
        private function created(event:Event):void {
            try {
                require(contextCreates==0,"Context recreation unsupported");context=plane.context3D;++contextCreates;
                require(context!=null && context.driverInfo.toLowerCase().indexOf("software")<0,"Hardware context required");
                context.enableErrorChecking=true;context.configureBackBuffer(width,height,0,false);
                program=context.createProgram();program.upload(shader(false),shader(true));
                vertices=context.createVertexBuffer(4,6);indices=context.createIndexBuffer(6);
                indices.uploadFromVector(Vector.<uint>([0,1,2,0,2,3]),0,6);
                initial={driverInfo:context.driverInfo,profile:context.profile,width:width,height:height,
                    contextMs:getTimer()-createdAt,sourceLayers:"fixed entire world and static backdrop; native UI retained",
                    limits:"No dynamic gameplay; CPU readback plus Stage.draw is not OS-window acceptance"};
            } catch(error:Error){errorText=error.message;}
        }
        private function failed(event:ErrorEvent):void {errorText=event.text;}
        public function ready():Boolean {
            require(errorText=="",errorText);require(context!=null || getTimer()-createdAt<10000,"Context creation timeout");
            return context!=null;
        }
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
                    var selectedVisible:Boolean=selected[node] && originalLayerVisibility[node];
                    if(node.visible!==selectedVisible){node.visible=selectedVisible;++layerWrites;}
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
            var dirtyUnion:Rectangle=null;
            for(var dirtyKey:String in dirty)dirtyUnion=dirtyUnion==null?dirty[dirtyKey].clone():dirtyUnion.union(dirty[dirtyKey]);
            if(dirtyUnion!=null) {
                var actor:DisplayObject=group.nodes[0];
                require(group.nodes.length==1 && actor===world.grafon.visObjs[2] && style(actor) && actor.scrollRect==null &&
                    sameMatrix(actor.transform.matrix,new Matrix()) && neutralColor(actor.transform.colorTransform),"Actor layer must be neutral identity");
                var drawAt:int=getTimer();
                scratch.fillRect(dirtyUnion,0);
                scratch.draw(actor,new Matrix(1,0,0,1,-bounds.x,-bounds.y),null,null,dirtyUnion,true);
                ++copies;++actorDrawCalls;actorDrawMs+=getTimer()-drawAt;actorDirtyPixels+=dirtyUnion.width*dirtyUnion.height;
            }
            // Stable traversal follows tile coordinates, not Dictionary order.
            for(y=0;y<bounds.height;y+=512)for(x=0;x<bounds.width;x+=512) {
                key=x+":"+y;var area:Rectangle=dirty[key] as Rectangle;if(area==null)continue;
                var tile:Object=null;
                for each(var candidate:Object in group.tiles)if(candidate.key==key){tile=candidate;break;}
                if(tile==null) {
                    var pixels:BitmapData=newPixels(int(area.width),int(area.height));
                    tile={pixels:pixels,rect:area,x:bounds.x+x,y:bounds.y+y,width:area.width,height:area.height,texture:null,key:key};group.tiles.push(tile);
                }
                tile.pixels.copyPixels(scratch,area,new Point());++copies;++tileRefreshes;
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
        public function prepareWorld(w:*,area:Rectangle):void {
            require(w===world && context && !worldPrepared && !active,"Single-use layer cache required");
            require(root.visible && backdrop.visible && style(root) && root.scrollRect==null &&
                unit(root.transform.concatenatedMatrix) && neutralColor(root.transform.concatenatedColorTransform),"Unsupported world style");
            require(style(backdrop) && backdrop.scrollRect==null,"Unsupported backdrop style");
            var ancestor:DisplayObject=root.parent;
            while(ancestor && ancestor!==stage){require(style(ancestor)&&neutralColor(ancestor.transform.colorTransform),"Ancestor effects unsupported");ancestor=ancestor.parent;}
            bounds=new Rectangle(Math.floor(area.left),Math.floor(area.top),Math.ceil(area.right)-Math.floor(area.left),Math.ceil(area.bottom)-Math.floor(area.top));
            require(bounds.width>0 && bounds.height>0 && bounds.width<=4096 && bounds.height<=4096,"Bounded layer cache required");
            parents=[backdrop];parentVisible=[backdrop.visible];
            var background:BitmapData=newPixels(width,height);
            try {
                background.draw(backdrop,backdrop.transform.concatenatedMatrix,backdrop.transform.concatenatedColorTransform,null,null,true);++copies;
                require(background.getColorBoundsRect(0xff000000,0xff000000,false).isEmpty(),"Opaque backdrop required");
                backdropTexture=upload(background);
            } finally {disposePixels(background);}
            scratch=newPixels(int(bounds.width),int(bounds.height));
            var container:DisplayObjectContainer=root as DisplayObjectContainer,g:*=world.grafon;
            var current:Object=null;
            var nativeStart:int=container.getChildIndex(g.visObjs[4]);
            require(nativeStart>container.getChildIndex(g.visObjs[2]),"Native upper layer ordering invalid");
            for(var i:int=0;i<container.numChildren;++i) {
                var node:DisplayObject=container.getChildAt(i);require(node!=null,"Null direct world layer");worldChildren.push(node);
                originalLayerVisibility[node]=node.visible;
                if(i>=nativeStart){nativeTail.push(node);continue;}
                parents.push(node);parentVisible.push(node.visible);++lowerLayerCount;
                var dynamic:Boolean=node===g.visObjs[2] || node===g.visObjs[3] || node===g.visObjs[4] || node===g.visObjs[5];
                if(current==null || dynamic || current.dynamic) {
                    current={index:groups.length,dynamic:dynamic,nodes:[],watch:[],tiles:[],area:null,rasterCalls:0,rasterMs:0,uploadMs:0,changes:0,empty:0,rebuilds:0};groups.push(current);
                }
                current.nodes.push(node);if(node===g.visObjs[2]){current.actor=true;actorGroup=current;}
            }
            var oldCull:Boolean=g.sceneCullRender;
            try {
                g.sceneCullRender=false;g.sceneTick();
                for each(var group:Object in groups){drawGroup(group);collectWatch(group);}
                oracleImage=newPixels(int(bounds.width),int(bounds.height));
            } finally {g.sceneCullRender=oldCull;g.sceneTick();captureCullRestored=g.sceneCullRender===oldCull;}
            require(captureCullRestored && layerWrites==layerRestores,"Layer preparation failed to restore native state");
            worldPrepared=true;
            initial.sourceLayers="GPU lower layers, native visObjs[4] and complete ordered tail; Flash timelines remain live";
            initial.lowerLayerCount=lowerLayerCount;initial.nativeTailCount=nativeTail.length;
            initial.nativeTailClasses=[];
            for each(var tail:DisplayObject in nativeTail)initial.nativeTailClasses.push(getQualifiedClassName(tail));
            initial.captureBounds={x:bounds.x,y:bounds.y,width:bounds.width,height:bounds.height};
            initial.layerGroups=groupSummary();
            initial.trackingLimit="Only timeline-driven visual changes in paused simulation; arbitrary bitmap pixels and script mutations untracked";
        }
        private function refreshChangedLayers():void {
            var at:int=getTimer(),dirty:Array=[];
            require(DisplayObjectContainer(root).numChildren==worldChildren.length,"World layer lifecycle changed");
            for(var i:int=0;i<worldChildren.length;++i)require(DisplayObjectContainer(root).getChildAt(i)===worldChildren[i],"World layer identity changed");
            for each(var group:Object in groups) {
                var changed:Boolean=false,owners:Dictionary=new Dictionary();
                for each(var watch:Object in group.watch) {
                    ++watchReads;
                    if(watch.node.currentFrame!=watch.frame || watch.node.totalFrames!=watch.total) {
                        changed=true;++animationChanges;++group.changes;owners[watch.owner]=true;
                    }
                }
                if(changed)dirty.push({group:group,owners:owners});
            }
            watchMs+=getTimer()-at;
            for each(var item:Object in dirty) {
                if(item.group.actor)redrawActorTiles(item.group,item.owners);else drawGroup(item.group);
                collectWatch(item.group);
            }
        }
        private function drawGroup(group:Object):void {
            var at:int=getTimer(),state:Array=[],selected:Dictionary=new Dictionary();
            for each(var selectedNode:DisplayObject in group.nodes)selected[selectedNode]=true;
            scratch.fillRect(scratch.rect,0);
            try {
                for each(var node:DisplayObject in worldChildren) {
                    state.push({node:node,visible:node.visible});
                    var selectedVisible:Boolean=selected[node] && originalLayerVisibility[node];
                    if(node.visible!==selectedVisible){node.visible=selectedVisible;++layerWrites;}
                }
                scratch.draw(root,new Matrix(1,0,0,1,-bounds.x,-bounds.y),null,null,null,true);++copies;
            } finally {
                for each(var item:Object in state)if(item.node.visible!==item.visible){item.node.visible=item.visible;++layerRestores;}
            }
            ++layerRasterCalls;++group.rasterCalls;
            if(group.actor) {
                for each(var actorTile:Object in group.tiles) {
                    actorTile.pixels.copyPixels(scratch,actorTile.rect,new Point());++copies;
                    actorTile.texture.uploadFromBitmapData(actorTile.pixels);++uploads;
                }
                if(!group.initialized) {
                    group.initialized=true;
                    for(var ay:int=0;ay<bounds.height;ay+=512)for(var ax:int=0;ax<bounds.width;ax+=512) {
                        var ar:Rectangle=new Rectangle(ax,ay,Math.min(512,bounds.width-ax),Math.min(512,bounds.height-ay));
                        var actorPixels:BitmapData=newPixels(int(ar.width),int(ar.height));
                        actorPixels.copyPixels(scratch,ar,new Point());++copies;
                        var alpha:Rectangle=actorPixels.getColorBoundsRect(0xff000000,0,false);
                        if(alpha.isEmpty()){disposePixels(actorPixels);continue;}
                        group.tiles.push({pixels:actorPixels,rect:ar,x:bounds.x+ax,y:bounds.y+ay,width:ar.width,height:ar.height,
                            texture:upload(actorPixels),key:ax+":"+ay});
                    }
                }
                var actorElapsed:int=getTimer()-at;layerRasterMs+=actorElapsed;group.rasterMs+=actorElapsed;return;
            }
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
        private function upload(pixels:BitmapData):RectangleTexture {
            var bytes:Number=pixels.width*pixels.height*4;
            require(gpuBytes+bytes<=128*1024*1024,"GPU allocation bound exceeded");
            var texture:RectangleTexture=context.createRectangleTexture(pixels.width,pixels.height,"bgra",false);
            ++texturesCreated;gpuBytes+=bytes;peakGPUBytes=Math.max(peakGPUBytes,gpuBytes);
            try {texture.uploadFromBitmapData(pixels);++uploads;}
            catch(error:Error){texture.dispose();++texturesDisposed;gpuBytes-=bytes;throw error;}
            return texture;
        }
        public function update(w:*,enabled:Boolean):void {
            ++updateCount;if(!enabled){clear();return;}
            require(worldPrepared && w===world && world.loc===location && world.onPause,"Prepared paused world required");
            require(stage.stageWidth==width && stage.stageHeight==height && errorText=="","GPU viewport/context changed");
            require(unit(root.transform.concatenatedMatrix),"Non-integer world transform");
            refreshChangedLayers();
            if(!active){
                for(var hidden:int=0;hidden<parents.length;++hidden)parents[hidden].visible=false;
                plane.visible=true;active=true;++enables;
            }
            require(root.visible && !backdrop.visible,"Native overlay world/backdrop state changed");
            for each(var hiddenLayer:DisplayObject in parents)require(!hiddenLayer.visible,"Cached lower layer re-enabled");
            render(false);
        }
        private function render(readback:Boolean,destination:BitmapData=null):void {
            require(active,"GPU inactive");context.clear(0,0,0,1);
            context.setProgram(program);context.setCulling("none");context.setDepthTest(false,"always");
            context.setBlendFactors("one","oneMinusSourceAlpha");
            context.setVertexBufferAt(0,vertices,0,"float4");context.setVertexBufferAt(1,vertices,4,"float2");
            drawQuad(backdropTexture,0,0,width,height);
            var m:Matrix=root.transform.concatenatedMatrix;
            for each(var group:Object in groups)for each(var t:Object in group.tiles)drawQuad(t.texture,t.x+m.tx,t.y+m.ty,t.width,t.height);
            if(readback){context.drawToBitmapData(destination);++captures;}
            context.present();++presents;
        }
        private function drawQuad(texture:RectangleTexture,x:Number,y:Number,w:Number,h:Number):void {
            var left:Number=x/width*2-1,right:Number=(x+w)/width*2-1,top:Number=1-y/height*2,bottom:Number=1-(y+h)/height*2;
            vertex(0,left,top,0,0);vertex(6,right,top,1,0);vertex(12,right,bottom,1,1);vertex(18,left,bottom,0,1);
            vertices.uploadFromVector(quad,0,4);context.setTextureAt(0,texture);context.drawTriangles(indices,0,2);++draws;
        }
        private function vertex(i:int,x:Number,y:Number,u:Number,v:Number):void {
            quad[i]=x;quad[i+1]=y;quad[i+2]=0;quad[i+3]=1;quad[i+4]=u;quad[i+5]=v;
        }
        public function capture(destination:BitmapData):void {
            require(destination.width==width && destination.height==height,"Readback size changed");
            verifyActorTiles();render(true,destination);if(captures==1)savePixel("gpu-raw-1",destination);
            destination.draw(stage); // Native UI only; this does not validate OS mixing.
        }
        private function savePixel(name:String,data:BitmapData):void {
            var folder:File=File.applicationStorageDirectory.resolvePath("stage3d-pixels");folder.createDirectory();
            var stream:FileStream=new FileStream();
            try{stream.open(folder.resolvePath(name+".png"),FileMode.WRITE);stream.writeBytes(data.encode(data.rect,new PNGEncoderOptions()));}
            finally{stream.close();}
        }
        public function clear():void {
            if(active){for(var i:int=0;i<parents.length;++i)parents[i].visible=parentVisible[i];active=false;++restores;}
            if(plane)plane.visible=false;
        }
        public function dispose():void {
            clear();
            if(plane){plane.removeEventListener(Event.CONTEXT3D_CREATE,created);plane.removeEventListener(ErrorEvent.ERROR,failed);}
            for each(var group:Object in groups)releaseGroup(group);
            if(scratch){disposePixels(scratch);scratch=null;}if(oracleImage){disposePixels(oracleImage);oracleImage=null;}
            if(backdropTexture){backdropTexture.dispose();backdropTexture=null;++texturesDisposed;}
            if(vertices){vertices.dispose();vertices=null;}if(indices){indices.dispose();indices=null;}if(program){program.dispose();program=null;}
            if(context){context.dispose(false);context=null;++contextDisposals;}
            if(plane&&planeSaved){plane.x=planeSaved.x;plane.y=planeSaved.y;plane.visible=planeSaved.visible;}
            gpuBytes=0;parents=[];parentVisible=[];plane=null;
            timelinesRestored=true; // No animation state was changed by this experiment.
        }
        public function snapshot():Object {
            return {active:active,parents:active?parents.length:0,lowerLayerCount:lowerLayerCount,nativeTailCount:nativeTail.length,nativeRootVisible:root!=null && root.visible,actualCache:active,allocated:allocated,disposed:bitmapDisposals,copies:copies,
                texturesCreated:texturesCreated,texturesDisposed:texturesDisposed,uploads:uploads,gpuBytes:gpuBytes,peakGPUBytes:peakGPUBytes,
                contextCreates:contextCreates,contextDisposals:contextDisposals,captures:captures,draws:draws,presents:presents,
                enables:enables,restores:restores,updates:updateCount,initial:initial,error:errorText,ready:context!=null,
                worldPrepared:worldPrepared,captureCullRestored:captureCullRestored,timelineCount:0,
                actorDrawCalls:actorDrawCalls,actorDrawMs:actorDrawMs,actorDirtyPixels:actorDirtyPixels,tileRefreshes:tileRefreshes,tileRefreshMs:tileRefreshMs,tileUploadMs:tileUploadMs,tileSkipChanges:tileSkipChanges,
                dirtyTilesMax:dirtyTilesMax,dirtyOwnerReads:dirtyOwnerReads,oracleCalls:oracleCalls,oracleChecks:oracleChecks.concat(),
                liveAnimation:true,layerRasterCalls:layerRasterCalls,layerRasterMs:layerRasterMs,layerUploadMs:layerUploadMs,
                animationChanges:animationChanges,watchReads:watchReads,watchNodes:watchNodes,watchMs:watchMs,
                layerWrites:layerWrites,layerRestores:layerRestores,liveCPUBytes:liveCPUBytes,peakCPUBytes:peakCPUBytes,
                groups:groupSummary(),
                clipsStopped:clipsStopped,clipsResumed:clipsResumed,timelineAudits:timelineAudits,timelinesRestored:timelinesRestored,timelineChanges:timelineChanges.concat(),emptySlots:emptySlots,walkedNodes:walkedNodes,
                observationSteps:observationSteps,implicitStopped:implicitStopped,observedImplicit:observationReport,
                playbackRestoreLimit:"No stop/play/goto calls. Frame-driven layer changes only; simulation remains paused.",frameScriptDrainDone:frameScriptDrainDone,frameScriptDrains:frameScriptDrains.concat()};
        }
        private function shader(fragment:Boolean):ByteArray {
            var out:ByteArray=new ByteArray();out.endian=Endian.LITTLE_ENDIAN;
            out.writeByte(0xa0);out.writeUnsignedInt(1);out.writeByte(0xa1);out.writeByte(fragment?1:0);
            if(fragment) {
                // tex ft0, v0, fs0 <2d,clamp,nearest,mipnone>; mov oc, ft0
                out.writeUnsignedInt(0x28);out.writeUnsignedInt(0x020f0000);
                source(out,4,0);out.writeUnsignedInt(0);out.writeUnsignedInt(5);
                mov(out,3,0,2,0);
            } else {
                mov(out,3,0,0,0); // mov op, va0
                mov(out,4,0,0,1); // mov v0, va1
            }
            out.position=0;return out;
        }
        private function mov(out:ByteArray,dt:int,dn:int,st:int,sn:int):void {
            out.writeUnsignedInt(0);out.writeUnsignedInt((dt<<24)|0x000f0000|dn);
            source(out,st,sn);out.writeUnsignedInt(0);out.writeUnsignedInt(0);
        }
        private function source(out:ByteArray,type:int,index:int):void {
            out.writeUnsignedInt(0xe4000000|index);out.writeUnsignedInt(type);
        }
        private function style(node:DisplayObject):Boolean {
            return node!=null && node.alpha==1 && node.filters.length==0 && node.mask==null &&
                node.transform.matrix3D==null && node.blendMode=="normal" && !node.cacheAsBitmap;
        }
        private function unit(m:Matrix):Boolean {
            return m.a==1 && m.b==0 && m.c==0 && m.d==1 &&
                isFinite(m.tx)&&isFinite(m.ty)&&m.tx==Math.floor(m.tx)&&m.ty==Math.floor(m.ty);
        }
        private function neutralColor(c:ColorTransform):Boolean {
            return c.redMultiplier==1&&c.greenMultiplier==1&&c.blueMultiplier==1&&c.alphaMultiplier==1&&
                c.redOffset==0&&c.greenOffset==0&&c.blueOffset==0&&c.alphaOffset==0;
        }
        private function sameMatrix(a:Matrix,b:Matrix):Boolean {
            return a.a===b.a&&a.b===b.b&&a.c===b.c&&a.d===b.d&&a.tx===b.tx&&a.ty===b.ty;
        }
        private function sameColor(a:ColorTransform,b:ColorTransform):Boolean {
            return a.redMultiplier===b.redMultiplier&&a.greenMultiplier===b.greenMultiplier&&a.blueMultiplier===b.blueMultiplier&&
                a.alphaMultiplier===b.alphaMultiplier&&a.redOffset===b.redOffset&&a.greenOffset===b.greenOffset&&
                a.blueOffset===b.blueOffset&&a.alphaOffset===b.alphaOffset;
        }
        private function require(ok:Boolean,message:String):void {if(!ok)throw new Error(message);}
    }
}

