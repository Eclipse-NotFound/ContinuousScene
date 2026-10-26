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

    /** Fixed-picture feasibility only; animations are frozen identically in both arms.
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
        private var refreshArea:Rectangle,refreshIntersection:Rectangle,refreshScissor:Rectangle;
        private var refreshMatrix:Matrix,refreshPixels:BitmapData,refreshTexture:RectangleTexture;
        private var regionRasterCalls:int=0,regionRasterMs:int=0,regionUploadMs:int=0;
        private var regionFirstAlphaBounds:Object;
        private var safeRegionCull:Dictionary=new Dictionary(),knownRegionCull:Dictionary=new Dictionary();
        private var regionCullClassifications:int=0,regionItemsDrawn:int=0,regionItemsSkipped:int=0;
        private var regionSelectionMs:int=0,regionItemDrawMs:int=0,regionRootQueries:int=0;
        private var splitLayers:Array=[];
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
        public function observeTimelines(w:*):void {
            require(w===world && world.onPause && !timelinesFrozen,"Paused observation required");
            var seen:Dictionary=new Dictionary(),stack:Array=[root,backdrop];
            while(stack.length) {
                var node:DisplayObject=stack.pop() as DisplayObject;if(node==null || seen[node])continue;seen[node]=true;
                var mc:MovieClip=node as MovieClip;
                if(mc && mc.totalFrames>1)observations[mc]={first:mc.currentFrame,last:mc.currentFrame,total:mc.totalFrames,
                    moved:false,changes:0,reportedPlaying:mc.isPlaying};
                var container:DisplayObjectContainer=node as DisplayObjectContainer;
                if(container)for(var i:int=0;i<container.numChildren;++i) {
                    var child:DisplayObject=container.getChildAt(i);if(child!=null)stack.push(child);
                }
            }
        }
        public function observeStep():void {
            require(!timelinesFrozen && observationSteps<8,"Fixed eight-interval observation only");
            for(var key:Object in observations) {
                var mc:MovieClip=key as MovieClip,item:Object=observations[key];
                require(mc.totalFrames==item.total,"Timeline shape changed during observation");
                if(mc.currentFrame!=item.last){item.moved=true;++item.changes;}
                item.last=mc.currentFrame;item.reportedPlaying=item.reportedPlaying||mc.isPlaying;
            }
            ++observationSteps;
        }
        public function freezeTimelines(w:*):void {
            require(w===world && world.onPause && !timelinesFrozen,"Paused single-use timeline capture required");
            require(observationSteps==8,"Eight observation intervals required");timelinesFrozen=true;
            var seen:Dictionary=new Dictionary(),stack:Array=[{node:root,path:"world"},{node:backdrop,path:"backdrop"}];
            while(stack.length) {
                var visit:Object=stack.pop(),node:DisplayObject=visit.node as DisplayObject;
                require(node!=null,"Invalid queued display node: "+visit.path);++walkedNodes;
                if(seen[node])continue;seen[node]=true;
                var mc:MovieClip=node as MovieClip;
                if(mc && mc.totalFrames>1) {
                    var item:Object={clip:mc,frame:mc.currentFrame,total:mc.totalFrames,playing:mc.isPlaying,className:getQualifiedClassName(mc),name:mc.name,path:visit.path};
                    var observed:Object=observations[mc];
                    item.implicit=observed!=null && observed.moved && !item.playing;
                    item.resume=item.playing || item.implicit;
                    clips.push(item);
                    if(item.resume){mc.stop();++clipsStopped;}
                    if(item.implicit){++implicitStopped;observationReport.push({path:visit.path,first:observed.first,last:observed.last,changes:observed.changes,reportedPlaying:observed.reportedPlaying});}
                }
                var container:DisplayObjectContainer=node as DisplayObjectContainer;
                if(container)for(var i:int=0;i<container.numChildren;++i) {
                    var child:DisplayObject=container.getChildAt(i);
                    if(child==null) {
                        // A second immediate read must also be empty; no renderer object exists here.
                        require(container.getChildAt(i)==null,"Transient child disappeared during inventory");
                        emptySlots.push({parent:visit.path,parentClass:getQualifiedClassName(container),index:i,count:container.numChildren});
                    } else stack.push({node:child,path:visit.path+"/"+i+":"+getQualifiedClassName(child)});
                }
                require(clips.length<30000,"Unbounded timeline inventory");
            }
            auditTimelines();
        }
        public function settleFrameScripts():void {
            require(timelinesFrozen && !frameScriptDrainDone,"Single fixed frame-script drain required");
            frameScriptDrainDone=true;
            for each(var item:Object in clips) {
                if(item.clip.currentFrame==item.frame && item.clip.totalFrames==item.total && !item.clip.isPlaying)continue;
                // Source-verified class only: frame1 -> random play; frame55 -> play(2).
                // Any other post-freeze change remains a hard failure. No retry loop.
                require(item.playing && item.resume && item.className=="pfe_fla::bloat_bulk_896" &&
                    (item.frame==1 || item.frame==55) && item.clip.totalFrames==55 && item.clip.isPlaying,
                    "Unexpected animation change in fixed frame-script drain: "+item.path);
                frameScriptDrains.push({path:item.path,beforeFrame:item.frame,afterFrame:item.clip.currentFrame});
                item.frame=item.clip.currentFrame;item.clip.stop();
            }
        }
        public function auditTimelines():void {
            require(timelinesFrozen && !timelinesRestored,"Timelines not owned");
            var changes:int=0;
            for each(var item:Object in clips)if(item.clip.currentFrame!=item.frame || item.clip.totalFrames!=item.total || item.clip.isPlaying) {
                ++changes;
                if(timelineChanges.length<32)timelineChanges.push({audit:timelineAudits,className:item.className,name:item.name,path:item.path,
                    beforeFrame:item.frame,afterFrame:item.clip.currentFrame,beforeTotal:item.total,afterTotal:item.clip.totalFrames,
                    beforePlaying:item.playing,afterPlaying:item.clip.isPlaying});
            }
            require(changes==0,"Fixed-picture timeline changes: "+changes);
            ++timelineAudits;
        }
        public function configureRefreshArea(intersection:Rectangle):void {
            require(!worldPrepared && refreshArea==null && intersection!=null,"Single bounded refresh area required");
            require(intersection.width>=512 && intersection.height>=512,"Prepared viewport intersection too small");
            refreshIntersection=intersection.clone();
            refreshArea=new Rectangle(Math.floor(intersection.x+(intersection.width-512)/2),
                Math.floor(intersection.y+(intersection.height-512)/2),512,512);
            require(intersection.containsRect(refreshArea),"Refresh area must be visible throughout route");
            refreshMatrix=new Matrix(1,0,0,1,-refreshArea.x,-refreshArea.y);
            refreshScissor=new Rectangle(0,0,512,512);
        }
        public function prepareWorld(w:*,area:Rectangle):void {
            require(w===world && context && !worldPrepared && !active,"Single-use snapshot required");
            auditTimelines();require(root.visible && backdrop.visible,"Native world/backdrop must be visible");
            require(style(root) && root.scrollRect==null && unit(root.transform.concatenatedMatrix) && neutralColor(root.transform.concatenatedColorTransform),"Unsupported world style/transform");
            require(style(backdrop) && backdrop.scrollRect==null,"Unsupported backdrop style");
            require(!DisplayObjectContainer(root).contains(backdrop),"Backdrop cannot also be inside captured world");
            var ancestor:DisplayObject=root.parent;
            while(ancestor && ancestor!==stage){require(style(ancestor) && neutralColor(ancestor.transform.colorTransform),"World ancestor effect unsupported");ancestor=ancestor.parent;}
            bounds=new Rectangle(Math.floor(area.left),Math.floor(area.top),Math.ceil(area.right)-Math.floor(area.left),Math.ceil(area.bottom)-Math.floor(area.top));
            require(bounds.width>0 && bounds.height>0 && bounds.width<=4096 && bounds.height<=4096,"Whole capture exceeds fixed bound");
            parents=[backdrop,root];parentVisible=[backdrop.visible,root.visible];
            var pixels:BitmapData=null,tile:BitmapData=null;
            var g:*=world.grafon,oldCull:Boolean=g.sceneCullRender;
            try {
                pixels=new BitmapData(width,height,true,0);++allocated;
                pixels.draw(backdrop,backdrop.transform.concatenatedMatrix,backdrop.transform.concatenatedColorTransform,null,null,true);++copies;
                require(pixels.getColorBoundsRect(0xff000000,0xff000000,false).isEmpty(),"Backdrop capture must be opaque");
                backdropTexture=upload(pixels);pixels.dispose();pixels=null;++bitmapDisposals;
                // All route cells were prepared before this point. Only visibility is changed,
                // synchronously for the capture; the native culling flag is restored in finally.
                g.sceneCullRender=false;g.sceneTick();
                pixels=new BitmapData(int(bounds.width),int(bounds.height),true,0);++allocated;
                pixels.draw(root,new Matrix(1,0,0,1,-bounds.x,-bounds.y),null,null,null,true);++copies;
                for(var y:int=0;y<bounds.height;y+=1024)for(var x:int=0;x<bounds.width;x+=1024) {
                    var tw:int=Math.min(1024,bounds.width-x),th:int=Math.min(1024,bounds.height-y);
                    tile=new BitmapData(tw,th,true,0);++allocated;
                    tile.copyPixels(pixels,new Rectangle(x,y,tw,th),new Point(0,0));++copies;
                    textures.push({texture:upload(tile),x:bounds.x+x,y:bounds.y+y,width:tw,height:th});
                    tile.dispose();tile=null;++bitmapDisposals;
                }
                require(refreshArea!=null && bounds.containsRect(refreshArea),"Refresh area outside world capture");
                refreshPixels=new BitmapData(512,512,true,0);++allocated;
                refreshTexture=upload(refreshPixels);
                worldPrepared=true;
                initial.refreshArea={x:refreshArea.x,y:refreshArea.y,width:512,height:512};
                initial.refreshIntersection={x:refreshIntersection.x,y:refreshIntersection.y,width:refreshIntersection.width,height:refreshIntersection.height};
                initial.sourceLayers="fixed world cache plus ordered-root region redraw; native UI retained";
                var graph:*=world.grafon;
                splitLayers=[graph.visBack,graph.visBack2,graph.visFront];
                for each(var objectLayer:* in graph.visObjs)splitLayers.push(objectLayer);
                // Only known empty wrapper Sprites may be flattened; unknown layers
                // and grouped effects remain a single native draw.
                initial.regionCullLimit="Filter/mask eligibility is memoized only because poses/styles are frozen. Not a production dynamic tracker.";
                initial.captureBounds={x:bounds.x,y:bounds.y,width:bounds.width,height:bounds.height};
                initial.worldTiles=textures.length;initial.timelineCount=clips.length;initial.clipsStopped=clipsStopped;
            } finally {
                if(tile){tile.dispose();++bitmapDisposals;}
                if(pixels){pixels.dispose();++bitmapDisposals;}
                g.sceneCullRender=oldCull;g.sceneTick();captureCullRestored=g.sceneCullRender===oldCull;
            }
            require(captureCullRestored,"Capture culling flag did not restore");auditTimelines();
        }
        private function refreshRegion():void {
            require(active && refreshPixels!=null && refreshTexture!=null,"Missing persistent region buffer");
            var at:int=getTimer(),wasVisible:Boolean=root.visible;
            try {
                root.visible=true;
                refreshPixels.fillRect(refreshPixels.rect,0);
                drawRegionItems();
                ++copies;++regionRasterCalls;
            } finally {root.visible=wasVisible;}
            regionRasterMs+=getTimer()-at;at=getTimer();
            refreshTexture.uploadFromBitmapData(refreshPixels);++uploads;regionUploadMs+=getTimer()-at;
            if(regionRasterCalls==1) {
                var occupied:Rectangle=refreshPixels.getColorBoundsRect(0xff000000,0,false);
                regionFirstAlphaBounds={x:occupied.x,y:occupied.y,width:occupied.width,height:occupied.height};
                savePixel("refresh-region-1",refreshPixels);
                var reference:BitmapData=null,referenceVisible:Boolean=root.visible;
                try {
                    reference=new BitmapData(512,512,true,0);++allocated;root.visible=true;
                    reference.draw(root,refreshMatrix,null,null,null,true);++copies;
                    savePixel("refresh-native-1",reference);
                } finally {root.visible=referenceVisible;if(reference){reference.dispose();++bitmapDisposals;}}
            }
        }
        private function drawRegionItems():void {
            var container:DisplayObjectContainer=root as DisplayObjectContainer;
            var rootMatrix:Matrix=root.transform.concatenatedMatrix;rootMatrix.invert();
            for(var i:int=0;i<container.numChildren;++i) {
                var layer:DisplayObject=container.getChildAt(i);
                if(layer==null || !layer.visible || layer.alpha==0)continue;
                var children:DisplayObjectContainer=layer as DisplayObjectContainer;
                var flatten:Boolean=children!=null && splitLayers.indexOf(layer)>=0 && style(layer) && layer.scrollRect==null &&
                    neutralColor(layer.transform.colorTransform) && identity(layer.transform.matrix);
                if(flatten) {
                    // Masks crossing immediate siblings must remain grouped.
                    for(var k:int=0;k<children.numChildren;++k) {
                        var probe:DisplayObject=children.getChildAt(k);
                        if(probe!=null && probe.mask!=null){flatten=false;break;}
                    }
                }
                if(flatten)for(var j:int=0;j<children.numChildren;++j)drawRegionItem(children.getChildAt(j),rootMatrix);
                else drawRegionItem(layer,rootMatrix);
            }
        }
        private function identity(m:Matrix):Boolean {
            return m.a==1 && m.b==0 && m.c==0 && m.d==1 && m.tx==0 && m.ty==0;
        }
        private function cullSafe(node:DisplayObject):Boolean {
            if(knownRegionCull[node])return safeRegionCull[node];
            ++regionCullClassifications;
            var stack:Array=[node],safe:Boolean=true;
            while(stack.length) {
                var child:DisplayObject=stack.pop() as DisplayObject;
                if(child==null)continue;
                if(child.filters.length || child.mask!=null || child.scrollRect!=null || child.transform.matrix3D!=null){safe=false;break;}
                var branch:DisplayObjectContainer=child as DisplayObjectContainer;
                if(branch)for(var i:int=0;i<branch.numChildren;++i)stack.push(branch.getChildAt(i));
            }
            knownRegionCull[node]=true;safeRegionCull[node]=safe;return safe;
        }
        private function drawRegionItem(node:DisplayObject,inverseRoot:Matrix):void {
            ++regionRootQueries;
            if(node==null || !node.visible || node.alpha==0){++regionItemsSkipped;return;}
            var at:int=getTimer();
            if(cullSafe(node)) {
                var extent:Rectangle=node.getBounds(root);
                // One extra pixel retains antialiasing at the edge; filtered or
                // masked subtrees never use geometric culling.
                extent.inflate(1,1);
                if(!extent.intersects(refreshArea)){
                    ++regionItemsSkipped;regionSelectionMs+=getTimer()-at;return;
                }
            }
            var matrix:Matrix=node.transform.concatenatedMatrix;matrix.concat(inverseRoot);
            matrix.tx-=refreshArea.x;matrix.ty-=refreshArea.y;
            regionSelectionMs+=getTimer()-at;at=getTimer();
            refreshPixels.draw(node,matrix,node.transform.colorTransform,node.blendMode,null,true);
            ++regionItemsDrawn;regionItemDrawMs+=getTimer()-at;
        }
        private function upload(pixels:BitmapData):RectangleTexture {
            var bytes:Number=pixels.width*pixels.height*4;
            require(gpuBytes+bytes<=96*1024*1024,"GPU allocation bound exceeded");
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
            if(!active){backdrop.visible=false;root.visible=false;plane.visible=true;active=true;++enables;}
            require(!root.visible && !backdrop.visible,"Native world was re-enabled");refreshRegion();render(false);
        }
        private function render(readback:Boolean,destination:BitmapData=null):void {
            require(active,"GPU inactive");context.clear(0,0,0,1);
            context.setProgram(program);context.setCulling("none");context.setDepthTest(false,"always");
            context.setBlendFactors("one","oneMinusSourceAlpha");
            context.setVertexBufferAt(0,vertices,0,"float4");context.setVertexBufferAt(1,vertices,4,"float2");
            drawQuad(backdropTexture,0,0,width,height);
            var m:Matrix=root.transform.concatenatedMatrix;
            for each(var t:Object in textures)drawQuad(t.texture,t.x+m.tx,t.y+m.ty,t.width,t.height);
            refreshScissor.x=refreshArea.x+m.tx;refreshScissor.y=refreshArea.y+m.ty;
            require(refreshScissor.x>=0 && refreshScissor.y>=0 && refreshScissor.right<=width && refreshScissor.bottom<=height,
                "Refresh region left prepared viewport intersection");
            context.setScissorRectangle(refreshScissor);
            try {
                // Opaque backdrop replaces the old world pixels, including pixels that
                // become transparent. Blending new content over the old tile would ghost.
                drawQuad(backdropTexture,0,0,width,height);
                drawQuad(refreshTexture,refreshScissor.x,refreshScissor.y,512,512);
            } finally {context.setScissorRectangle(null);}
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
            render(true,destination);if(captures==1)savePixel("gpu-raw-1",destination);
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
            for each(var t:Object in textures){t.texture.dispose();++texturesDisposed;}textures=[];
            if(refreshTexture){refreshTexture.dispose();refreshTexture=null;++texturesDisposed;}
            if(refreshPixels){refreshPixels.dispose();refreshPixels=null;++bitmapDisposals;}
            if(backdropTexture){backdropTexture.dispose();backdropTexture=null;++texturesDisposed;}
            if(vertices){vertices.dispose();vertices=null;}if(indices){indices.dispose();indices=null;}if(program){program.dispose();program=null;}
            if(context){context.dispose(false);context=null;++contextDisposals;}
            if(plane&&planeSaved){plane.x=planeSaved.x;plane.y=planeSaved.y;plane.visible=planeSaved.visible;}
            gpuBytes=0;parents=[];parentVisible=[];plane=null;
            // Only resume clips stopped by this diagnostic; preserve all initially stopped clips.
            var restoreErrors:Array=[];
            for each(var item:Object in clips) {
                var untouched:Boolean=item.clip.currentFrame==item.frame && item.clip.totalFrames==item.total && !item.clip.isPlaying;
                if(!untouched)restoreErrors.push("Timeline state changed");
                if(item.resume && untouched){item.clip.play();++clipsResumed;}
                if(item.clip.isPlaying!==item.resume)restoreErrors.push("Timeline play state restore failed");
            }
            timelinesRestored=restoreErrors.length==0;
            require(timelinesRestored,"Timeline cleanup: "+restoreErrors.join(","));
        }
        public function snapshot():Object {
            return {active:active,parents:active?2:0,actualCache:active,allocated:allocated,disposed:bitmapDisposals,copies:copies,
                texturesCreated:texturesCreated,texturesDisposed:texturesDisposed,uploads:uploads,gpuBytes:gpuBytes,peakGPUBytes:peakGPUBytes,
                contextCreates:contextCreates,contextDisposals:contextDisposals,captures:captures,draws:draws,presents:presents,
                enables:enables,restores:restores,updates:updateCount,initial:initial,error:errorText,ready:context!=null,
                worldPrepared:worldPrepared,captureCullRestored:captureCullRestored,timelineCount:clips.length,
                clipsStopped:clipsStopped,clipsResumed:clipsResumed,timelineAudits:timelineAudits,timelinesRestored:timelinesRestored,timelineChanges:timelineChanges.concat(),emptySlots:emptySlots,walkedNodes:walkedNodes,
                observationSteps:observationSteps,implicitStopped:implicitStopped,observedImplicit:observationReport,
                playbackRestoreLimit:"Observed implicit movers resume with play; public isPlaying may become true. Terminal diagnostic only.",frameScriptDrainDone:frameScriptDrainDone,frameScriptDrains:frameScriptDrains.concat(),regionRasterCalls:regionRasterCalls,regionRasterMs:regionRasterMs,regionUploadMs:regionUploadMs,regionFirstAlphaBounds:regionFirstAlphaBounds,regionRootQueries:regionRootQueries,regionItemsDrawn:regionItemsDrawn,regionItemsSkipped:regionItemsSkipped,regionCullClassifications:regionCullClassifications,regionSelectionMs:regionSelectionMs,regionItemDrawMs:regionItemDrawMs};
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

