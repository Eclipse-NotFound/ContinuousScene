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
    import flash.utils.ByteArray;
    import flash.utils.Dictionary;
    import flash.utils.Endian;
    import flash.utils.getTimer;

    /** Terminal paused-world diagnostic only. All native object/foreground rendering remains.
     * AGAL byte format: https://github.com/adobe/glsl2agal/blob/master/agalassembler/agal.h
     * Only mov and tex instructions are emitted; no assembler dependency or downloaded code.
     */
    public class SceneTilePresentation {
        private var stage:Stage;
        private var plane:Stage3D;
        private var context:Context3D;
        private var program:Program3D;
        private var vertices:VertexBuffer3D;
        private var indices:IndexBuffer3D;
        private var world:*;
        private var location:*;
        private var parents:Array=[];
        private var parentVisible:Array=[];
        private var backdrop:DisplayObject;
        private var backdropRows:Array=[];
        private var backdropTexture:RectangleTexture;
        private var backdropPixels:BitmapData;
        private var backdropMatrix:Matrix;
        private var backdropColor:ColorTransform;
        private var backdropIndex:int;
        private var backdropParent:DisplayObjectContainer;
        private var planeSaved:Object;
        private var entries:Dictionary=new Dictionary();
        private var liveTextures:Array=[];
        private var requested:Boolean=false;
        private var errorText:String="";
        private var width:int,height:int;
        private var createdAt:int;
        private var contextMs:int=0;
        private var gpuBytes:Number=0,peakGPUBytes:Number=0;
        private var texturesCreated:int=0,texturesDisposed:int=0,uploads:int=0;
        private var contextCreates:int=0,contextDisposals:int=0;
        private var captures:int=0,draws:int=0,presents:int=0;
        private var enables:int=0,restores:int=0,updateCount:int=0;
        private var bitmapDisposals:int=0;
        private var quad:Vector.<Number>=new Vector.<Number>(24,true);
        private var initial:Object;
        public var allocated:int=0;
        public var copies:int=0;
        public var active:Boolean=false;

        public function prepareContext(w:*):void {
            require(!requested && !context,"Single-use context required");
            world=w;location=w.loc;stage=w.main.stage;
            width=stage.stageWidth;height=stage.stageHeight;
            require(w.grafon.sceneLarge && width>0 && height>0 && width<=2048 && height<=2048,"Bounded native viewport required");
            require(stage.stage3Ds.length>0,"Stage3D unavailable");
            plane=stage.stage3Ds[0];
            require(plane.context3D==null,"Existing Stage3D belongs to another renderer");
            planeSaved={visible:plane.visible,x:plane.x,y:plane.y};
            plane.visible=false;plane.x=0;plane.y=0;
            createdAt=getTimer();requested=true;
            plane.addEventListener(Event.CONTEXT3D_CREATE,created);
            plane.addEventListener(ErrorEvent.ERROR,failed);
            plane.requestContext3D("auto","baseline");
        }
        private function created(event:Event):void {
            try {
                require(contextCreates==0,"Context loss/recreation requires native fallback");
                context=plane.context3D;++contextCreates;
                require(context!=null && context.driverInfo.toLowerCase().indexOf("software")<0,"Hardware context required");
                context.enableErrorChecking=true;
                context.configureBackBuffer(width,height,0,false);
                program=context.createProgram();
                program.upload(shader(false),shader(true));
                vertices=context.createVertexBuffer(4,6);
                indices=context.createIndexBuffer(6);
                indices.uploadFromVector(Vector.<uint>([0,1,2,0,2,3]),0,6);
                contextMs=getTimer()-createdAt;
                initial={driverInfo:context.driverInfo,profile:context.profile,width:width,height:height,
                    contextMs:contextMs,sourceLayers:"static backdrop, native back, native back2",
                    pixelReadback:"Context3D back buffer then native Stage over it; not OS mixed presentation"};
            } catch(error:Error) {errorText=error.toString();}
        }
        private function failed(event:ErrorEvent):void {errorText=event.text;}
        public function ready():Boolean {
            require(errorText=="",errorText);
            require(getTimer()-createdAt<10000 || context!=null,"Context creation timeout");
            return context!=null && program!=null && vertices!=null && indices!=null;
        }
        public function update(w:*,enabled:Boolean):void {
            ++updateCount;
            if(!enabled){clear();return;}
            require(ready() && w===world && w.loc===location,"World/context changed");
            if(backdrop==null)prepareBackdrop();
            verify();
            var g:*=w.grafon;
            var surfaceByBitmap:Dictionary=new Dictionary();
            var surfaces:Array=g.sceneSurfaces();
            for each(var surface:Object in surfaces) {
                require(surface.bitmaps && surface.bitmaps.length==4 && surface.nativeBuffers.length==4 &&
                    surface.side==320 && surface.gutter>=0,"Native surface contract changed");
                for(var layer:int=1;layer<=2;++layer)
                    surfaceByBitmap[surface.bitmaps[layer]]={surface:surface,layer:layer};
            }
            // Keep display-list order. Parent visibility does not alter each child's own visibility.
            liveTextures=[];
            for(layer=1;layer<=2;++layer) {
                var parent:DisplayObjectContainer=parents[layer];
                for(var child:int=0;child<parent.numChildren;++child) {
                    var node:DisplayObject=parent.getChildAt(child);
                    if(!node.visible)continue;
                    var bitmap:Bitmap=node as Bitmap;
                    var row:Object=surfaceByBitmap[bitmap];
                    require(bitmap!=null && row!=null,"Unknown visible background object");
                    surface=row.surface;
                    require(bitmap.bitmapData===surface.nativeBuffers[layer],"Borrowed native pixels changed");
                    var crop:Rectangle=bitmap.scrollRect;
                    require(crop!=null && crop.x==surface.gutter && crop.y==surface.gutter &&
                        crop.width==surface.side && crop.height==surface.side,"Native crop changed");
                    require(style(bitmap) && neutralColor(bitmap.transform.colorTransform),"Background tile effect changed");
                    var matrix:Matrix=bitmap.transform.concatenatedMatrix;
                    require(unit(matrix),"Only integer unit translation supported");
                    var x:Number=matrix.tx,y:Number=matrix.ty;
                    if(x>=width || y>=height || x+surface.side<=0 || y+surface.side<=0)continue;
                    var entry:Object=entries[bitmap];
                    var data:BitmapData=bitmap.bitmapData;
                    if(entry==null) {
                        require(data.width<=2048 && data.height<=2048,"Texture dimensions exceed baseline");
                        var bytes:Number=data.width*data.height*4;
                        require(gpuBytes+bytes<=192*1024*1024,"Texture budget exceeded");
                        var texture:RectangleTexture=context.createRectangleTexture(data.width,data.height,"bgra",false);
                        ++texturesCreated;gpuBytes+=bytes;peakGPUBytes=Math.max(peakGPUBytes,gpuBytes);
                        entry={texture:texture,data:data,revision:NaN,bytes:bytes};entries[bitmap]=entry;
                    }
                    require(entry.data===data,"Native bitmap identity changed during terminal test");
                    if(entry.revision!==surface.revision) {
                        entry.texture.uploadFromBitmapData(data);++uploads;
                        entry.revision=surface.revision;
                    }
                    liveTextures.push({entry:entry,x:x,y:y,side:surface.side,gutter:surface.gutter,
                        width:data.width,height:data.height});
                }
            }
            require(liveTextures.length>0,"No visible background tiles");
            if(!active) {
                for(layer=0;layer<parents.length;++layer)parents[layer].visible=false;
                plane.visible=true;active=true;++enables;
            }
            render(false);
        }
        private function prepareBackdrop():void {
            var g:*=world.grafon;
            backdrop=g.visFon as DisplayObject;
            require(backdrop!=null && backdrop.visible && backdrop.parent!=null,"Static visible backdrop required");
            backdropParent=backdrop.parent;backdropIndex=backdropParent.getChildIndex(backdrop);
            backdropMatrix=backdrop.transform.matrix;backdropColor=backdrop.transform.colorTransform;
            parents=[backdrop,g.visBack,g.visBack2];
            for each(var parent:DisplayObject in parents) {
                require(parent.visible && style(parent),"Unsupported background parent");
                parentVisible.push(parent.visible);
                var ancestor:DisplayObject=parent.parent;
                while(ancestor!==stage) {
                    require(ancestor!=null && style(ancestor) && neutralColor(ancestor.transform.colorTransform),
                        "Background ancestor has unsupported effect");
                    ancestor=ancestor.parent;
                }
            }
            require(g.visBack.parent===world.visual && g.visBack2.parent===world.visual &&
                world.visual.getChildIndex(g.visBack)==0 && world.visual.getChildIndex(g.visBack2)==1,
                "Background order changed");
            require(neutralColor(g.visBack.transform.colorTransform) && neutralColor(g.visBack2.transform.colorTransform),
                "Background parent tint must be native-neutral");
            rememberBackdrop(backdrop);
            backdropPixels=new BitmapData(width,height,true,0);++allocated;
            backdropPixels.draw(backdrop,backdrop.transform.concatenatedMatrix,
                backdrop.transform.concatenatedColorTransform,null,backdropPixels.rect,true);++copies;
            require(backdropPixels.getColorBoundsRect(0xFF000000,0xFF000000,false).isEmpty(),"Backdrop must cover screen opaquely");
            backdropTexture=context.createRectangleTexture(width,height,"bgra",false);
            ++texturesCreated;gpuBytes+=width*height*4;peakGPUBytes=Math.max(peakGPUBytes,gpuBytes);
            backdropTexture.uploadFromBitmapData(backdropPixels);++uploads;
            backdropPixels.dispose();backdropPixels=null;++bitmapDisposals;
            initial.backdropNodes=backdropRows.length;
        }
        private function rememberBackdrop(node:DisplayObject):void {
            require(backdropRows.length<256 && style(node),"Unsupported backdrop subtree");
            var clip:MovieClip=node as MovieClip;
            require(clip==null || clip.totalFrames==1,"Animated backdrop unsupported");
            var parent:DisplayObjectContainer=node as DisplayObjectContainer;
            backdropRows.push({target:node,parent:node.parent,matrix:node.transform.matrix,
                color:node.transform.colorTransform,visible:node.visible,children:parent?parent.numChildren:0});
            if(parent)for(var i:int=0;i<parent.numChildren;++i)rememberBackdrop(parent.getChildAt(i));
        }
        private function verify():void {
            require(stage===world.main.stage && world.loc===location && world.onPause===true &&
                stage.stageWidth==width && stage.stageHeight==height,"Terminal viewport changed");
            require(plane.context3D===context && context.driverInfo!="Disposed" && errorText=="","Context identity lost");
            require(world.grafon.visFon===backdrop && backdrop.parent===backdropParent &&
                backdropParent.getChildIndex(backdrop)==backdropIndex,"Backdrop parent changed");
            require(unit(world.visual.transform.concatenatedMatrix),"Only integer unscaled camera supported");
            for(var i:int=0;i<parents.length;++i) {
                require(style(parents[i]) && parents[i].visible==(!active && parentVisible[i]),"Background parent modified");
                if(i>0)require(neutralColor(parents[i].transform.concatenatedColorTransform),"Background tint changed");
            }
            for each(var row:Object in backdropRows) {
                var node:DisplayObject=row.target;
                require(node.parent===row.parent && sameMatrix(node.transform.matrix,row.matrix) &&
                    sameColor(node.transform.colorTransform,row.color) && style(node),"Backdrop changed");
                if(node!==backdrop)require(node.visible===row.visible,"Backdrop child visibility changed");
                if(node is DisplayObjectContainer)require(DisplayObjectContainer(node).numChildren==row.children,"Backdrop children changed");
            }
        }
        private function render(readback:Boolean,destination:BitmapData=null):void {
            require(active && context!=null,"GPU presentation inactive");
            context.clear(0,0,0,1);
            context.setProgram(program);
            context.setCulling("none");context.setDepthTest(false,"always");
            context.setBlendFactors("one","oneMinusSourceAlpha");
            context.setVertexBufferAt(0,vertices,0,"float4");
            context.setVertexBufferAt(1,vertices,4,"float2");
            drawQuad(backdropTexture,0,0,width,height,0,0,1,1);
            for each(var row:Object in liveTextures)
                drawQuad(row.entry.texture,row.x,row.y,row.side,row.side,
                    row.gutter/row.width,row.gutter/row.height,(row.gutter+row.side)/row.width,(row.gutter+row.side)/row.height);
            if(readback){context.drawToBitmapData(destination);++captures;}
            context.present();++presents;
        }
        private function drawQuad(texture:RectangleTexture,x:Number,y:Number,w:Number,h:Number,
                u0:Number,v0:Number,u1:Number,v1:Number):void {
            var left:Number=x*2/width-1,right:Number=(x+w)*2/width-1;
            var top:Number=1-y*2/height,bottom:Number=1-(y+h)*2/height;
            vertex(0,left,top,u0,v0);vertex(6,right,top,u1,v0);
            vertex(12,right,bottom,u1,v1);vertex(18,left,bottom,u0,v1);
            vertices.uploadFromVector(quad,0,4);
            context.setTextureAt(0,texture);context.drawTriangles(indices,0,2);++draws;
        }
        private function vertex(i:int,x:Number,y:Number,u:Number,v:Number):void {
            quad[i]=x;quad[i+1]=y;quad[i+2]=0;quad[i+3]=1;quad[i+4]=u;quad[i+5]=v;
        }
        public function capture(destination:BitmapData):void {
            require(destination.width==width && destination.height==height,"Readback dimensions changed");
            render(true,destination);
            // Stage.draw cannot read Stage3D. Draw only remaining native display-list layers over GPU readback.
            if(captures<=13)savePixel("gpu-raw-"+captures,destination);
            destination.draw(stage);
        }
        private function savePixel(name:String,data:BitmapData):void {
            var folder:File=File.applicationStorageDirectory.resolvePath("stage3d-pixels");
            folder.createDirectory();
            var stream:FileStream=new FileStream();
            try {
                stream.open(folder.resolvePath(name+".png"),FileMode.WRITE);
                stream.writeBytes(data.encode(data.rect,new PNGEncoderOptions()));
            } finally {stream.close();}
        }
        public function clear():void {
            if(active) {
                for(var i:int=0;i<parents.length;++i)parents[i].visible=parentVisible[i];
                active=false;++restores;
            }
            if(plane)plane.visible=false;
        }
        public function dispose():void {
            clear();
            if(plane) {
                plane.removeEventListener(Event.CONTEXT3D_CREATE,created);
                plane.removeEventListener(ErrorEvent.ERROR,failed);
            }
            for(var key:Object in entries){entries[key].texture.dispose();++texturesDisposed;}
            entries=new Dictionary();liveTextures=[];
            if(backdropTexture){backdropTexture.dispose();backdropTexture=null;++texturesDisposed;}
            if(backdropPixels){backdropPixels.dispose();backdropPixels=null;++bitmapDisposals;}
            if(vertices){vertices.dispose();vertices=null;}
            if(indices){indices.dispose();indices=null;}
            if(program){program.dispose();program=null;}
            if(context){context.dispose(false);context=null;++contextDisposals;}
            if(plane&&planeSaved){plane.x=planeSaved.x;plane.y=planeSaved.y;plane.visible=planeSaved.visible;}
            gpuBytes=0;parents=[];parentVisible=[];backdropRows=[];backdrop=null;plane=null;
        }
        public function snapshot():Object {
            return {active:active,parents:active?3:0,actualCache:active,
                allocated:allocated,disposed:bitmapDisposals,copies:copies,
                texturesCreated:texturesCreated,texturesDisposed:texturesDisposed,uploads:uploads,
                gpuBytes:gpuBytes,peakGPUBytes:peakGPUBytes,contextCreates:contextCreates,contextDisposals:contextDisposals,
                captures:captures,draws:draws,presents:presents,enables:enables,restores:restores,
                updates:updateCount,visibleQuads:liveTextures.length+1,initial:initial,
                error:errorText,ready:context!=null};
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

