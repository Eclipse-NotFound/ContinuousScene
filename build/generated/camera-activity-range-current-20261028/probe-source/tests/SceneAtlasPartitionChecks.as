package tests {
    import flash.desktop.NativeApplication;
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.display.DisplayObject;
    import flash.display.DisplayObjectContainer;
    import flash.geom.Matrix;
    import flash.geom.Point;
    import flash.geom.Rectangle;

    /** Same-frame geometry diagnostic. Uses existing atlas/native pixel stores.
     * The caller supplies a native stage capture with all four atlases hidden.
     * No world step, camera change, helper update or native buffer write occurs.
     */
    public class SceneAtlasPartitionChecks {
        private static const GUTTER:int=40;
        private static const NAMES:Array=["ContinuousSceneAtlasFront","ContinuousSceneAtlasBack",
            "ContinuousSceneAtlasBack2","ContinuousSceneAtlasWater"];

        public static function run(w:*,reference:BitmapData,check:Function,name:String):Object {
            var result:Object={name:name,diagnosticOnly:true,performanceEligible:false,valid:false,
                oracle:"Synchronous stage draws against the supplied native capture; existing pixel stores copied without resampling",
                gutter:GUTTER,rows:null,columns:null,restored:null,cleanupErrors:[]};
            result["rows-native-gutters"]=null;
            var layers:Array=[],native:Array=[],owned:Array=[],image:BitmapData=null;
            try {
                var app:String=NativeApplication.nativeApplication.applicationID;
                var prefix:String="pfe-modsettings-continuous-motion-";
                if(app.indexOf(prefix)!=0 || app.length<=prefix.length+7)
                    throw new Error("Partition checks require unique isolated motion storage");
                if(!reference || reference.width!=w.main.stage.stageWidth || reference.height!=w.main.stage.stageHeight)
                    throw new Error("Reference dimensions do not match the current stage");
                if(!w.grafon.sceneLarge || w.sats.active || w.grafon.visSats.visible)
                    throw new Error("Partition checks require an active native large scene outside SATS");
                var surfaces:Array=w.grafon.sceneSurfaces();
                if(!surfaces.length)throw new Error("No resident native surfaces");
                var side:int=int(surfaces[0].side);
                if(side!=320 || int(w.grafon.sceneChunkSide)!=side)
                    throw new Error("This diagnostic requires the current 320px native geometry");
                result.side=side;
                result.camera={scale:w.cam.scaleV,vx:w.cam.vx,vy:w.cam.vy,
                    visual:w.visual.transform.matrix.toString()};
                var parents:Array=[w.grafon.visFront,w.grafon.visBack,w.grafon.visBack2,w.grafon.visVoda];
                for(var layerIndex:int=0;layerIndex<4;++layerIndex) {
                    var parent:DisplayObjectContainer=parents[layerIndex] as DisplayObjectContainer;
                    var atlas:Bitmap=parent.getChildByName(NAMES[layerIndex]) as Bitmap;
                    if(!atlas || !atlas.bitmapData || atlas.visible || atlas.scrollRect!=null || atlas.mask!=null)
                        throw new Error("Four hidden, unclipped atlas layers are required");
                    var matrix:Matrix=atlas.transform.matrix;
                    if(matrix.a!=1 || matrix.d!=1 || matrix.b!=0 || matrix.c!=0 ||
                        atlas.x%side!=0 || atlas.y%side!=0 ||
                        atlas.bitmapData.width%side!=0 || atlas.bitmapData.height%side!=0)
                        throw new Error("Atlas transform or dimensions do not match the native grid");
                    var children:Array=[];
                    for(var childIndex:int=0;childIndex<parent.numChildren;++childIndex)
                        children.push(parent.getChildAt(childIndex));
                    layers.push({parent:parent,atlas:atlas,data:atlas.bitmapData,visible:atlas.visible,
                        matrix:matrix.clone(),children:children,depth:parent.getChildIndex(atlas)});
                }
                var nativeVisible:int=0;
                for each(var surface:Object in surfaces) {
                    if(int(surface.side)!=side || int(surface.gutter)!=GUTTER)
                        throw new Error("Native surface geometry changed within one scene");
                    for(layerIndex=0;layerIndex<4;++layerIndex) {
                        var bitmap:Bitmap=surface.bitmaps[layerIndex] as Bitmap;
                        if(!bitmap || bitmap.parent!==parents[layerIndex])
                            throw new Error("Native bitmap is not attached to its expected layer");
                        native.push({bitmap:bitmap,visible:bitmap.visible,parent:bitmap.parent,data:bitmap.bitmapData});
                        if(bitmap.visible)++nativeVisible;
                    }
                }
                if(nativeVisible==0)throw new Error("Native reference has no visible resident bitmaps");
                result.nativeBitmaps=native.length;result.nativeVisible=nativeVisible;
                image=capture(w);result.input=compare(image,reference);image.dispose();image=null;
                check(name+"-partition-input-reference",result.input.equal,result.input);
                if(!result.input.equal)throw new Error("Supplied native reference is not the current synchronous frame");

                for each(var mode:String in ["rows","columns","rows-native-gutters"]) {
                    var row:Object={mode:mode,strips:0,copiedPixels:0,clippedGutters:0,layers:[]};
                    try {
                        for each(var old:Object in native)old.bitmap.visible=false;
                        for(layerIndex=0;layerIndex<4;++layerIndex) {
                            if(mode=="rows-native-gutters")
                                addNativeGutterRows(layers[layerIndex],side,layerIndex,surfaces,owned,row);
                            else addStrips(layers[layerIndex],side,mode,layerIndex,owned,row);
                        }
                        image=capture(w);row.pixels=compare(image,reference);image.dispose();image=null;
                        row.equal=row.pixels.equal;result[mode]=row;
                        check(name+"-partition-"+mode+"-pixels",row.equal,row);
                    } finally {
                        removeStrips(owned,result.cleanupErrors);
                        restoreNative(native,result.cleanupErrors);
                    }
                }
            } catch(error:Error) {
                result.error=error.message;
                check(name+"-partition-execution",false,result.error);
            } finally {
                if(image){image.dispose();image=null;}
                removeStrips(owned,result.cleanupErrors);
                restoreNative(native,result.cleanupErrors);
                restoreOrder(layers,result.cleanupErrors);
                result.bindingsRestored=bindingsRestored(layers,native);
                try {
                    if(reference) {
                        image=capture(w);result.restored=compare(image,reference);
                    }
                } catch(restoreError:Error) {
                    result.cleanupErrors.push("restore-capture: "+restoreError.message);
                } finally {if(image){image.dispose();image=null;}}
                check(name+"-partition-bindings-restored",result.bindingsRestored && result.cleanupErrors.length==0,
                    {bindings:result.bindingsRestored,errors:result.cleanupErrors});
                check(name+"-partition-reference-restored",result.restored && result.restored.equal,result.restored);
            }
            result.valid=!result.error && result.bindingsRestored && result.cleanupErrors.length==0 &&
                result.restored && result.restored.equal;
            return result;
        }

        private static function addStrips(layer:Object,side:int,mode:String,index:int,owned:Array,row:Object):void {
            var atlas:Bitmap=layer.atlas,source:BitmapData=layer.data;
            var horizontal:Boolean=mode=="rows";
            var count:int=horizontal?source.height/side:source.width/side;
            var width:int=horizontal?source.width:side,height:int=horizontal?side:source.height;
            var details:Object={layer:index,count:count,depth:layer.depth,atlasX:atlas.x,atlasY:atlas.y,
                contentWidth:width,contentHeight:height,bufferWidth:width+GUTTER*2,bufferHeight:height+GUTTER*2,
                pixelSnapping:atlas.pixelSnapping,smoothing:atlas.smoothing,filters:atlas.filters.length};
            row.layers.push(details);
            for(var i:int=0;i<count;++i) {
                var x:Number=atlas.x+(horizontal?0:i*side),y:Number=atlas.y+(horizontal?i*side:0);
                var data:BitmapData=new BitmapData(width+GUTTER*2,height+GUTTER*2,true,0);
                var record:Object={bitmap:null,data:data};owned.push(record);
                var requested:Rectangle=new Rectangle(x-atlas.x-GUTTER,y-atlas.y-GUTTER,
                    data.width,data.height);
                var available:Rectangle=requested.intersection(source.rect);
                // Clip explicitly: any unavailable outer atlas gutter remains
                // transparent, while interior gutters come from the same atlas.
                if(!available.isEmpty())data.copyPixels(source,available,
                    new Point(available.x-requested.x,available.y-requested.y));
                if(!available.equals(requested))++row.clippedGutters;
                row.copiedPixels+=available.width*available.height;
                var strip:Bitmap=new Bitmap(data,atlas.pixelSnapping,atlas.smoothing);record.bitmap=strip;
                strip.name="ContinuousSceneAtlasPartition-"+mode+"-"+index+"-"+i;
                strip.x=x;strip.y=y;
                strip.alpha=atlas.alpha;strip.blendMode=atlas.blendMode;
                strip.transform.colorTransform=atlas.transform.colorTransform;
                strip.filters=atlas.filters;strip.cacheAsBitmap=atlas.cacheAsBitmap;
                strip.scrollRect=new Rectangle(GUTTER,GUTTER,width,height);
                layer.parent.addChildAt(strip,int(layer.depth)+i);++row.strips;
            }
        }

        private static function addNativeGutterRows(layer:Object,side:int,index:int,surfaces:Array,owned:Array,row:Object):void {
            var atlas:Bitmap=layer.atlas,source:BitmapData=layer.data;
            var count:int=source.height/side,columns:int=source.width/side,width:int=source.width;
            var firstX:int=atlas.x/side,firstY:int=atlas.y/side,grid:Object={};
            for each(var surface:Object in surfaces)grid[surface.cx+":"+surface.cy]=surface;
            var details:Object={layer:index,count:count,depth:layer.depth,atlasX:atlas.x,atlasY:atlas.y,
                contentWidth:width,contentHeight:side,bufferWidth:width+GUTTER*2,bufferHeight:side+GUTTER*2,
                pixelSnapping:atlas.pixelSnapping,smoothing:atlas.smoothing,filters:atlas.filters.length,
                source:"nativeBuffers; complete per-cell vertical gutter",copiedCells:0,missingCells:0,
                copiedEdgeGutters:0,missingEdgeGutters:0};
            row.layers.push(details);
            for(var i:int=0;i<count;++i) {
                var data:BitmapData=new BitmapData(width+GUTTER*2,side+GUTTER*2,true,0);
                var record:Object={bitmap:null,data:data};owned.push(record);
                for(var column:int=0;column<columns;++column) {
                    surface=grid[(firstX+column)+":"+(firstY+i)];
                    if(!surface) {
                        ++details.missingCells;
                        if(column==0)++details.missingEdgeGutters;
                        if(column==columns-1)++details.missingEdgeGutters;
                        continue;
                    }
                    var nativeData:BitmapData=surface.nativeBuffers[index] as BitmapData;
                    if(!nativeData || nativeData.width<side+GUTTER*2 || nativeData.height<side+GUTTER*2)
                        throw new Error("Native row gutter buffer is missing or undersized");
                    if(Bitmap(surface.bitmaps[index]).bitmapData!==nativeData)
                        throw new Error("Native row gutter buffer is not the current display source");
                    // Each cell supplies its own top/bottom gutter. Do not take
                    // these pixels from the preceding/following atlas centres.
                    data.copyPixels(nativeData,new Rectangle(GUTTER,0,side,side+GUTTER*2),
                        new Point(GUTTER+column*side,0));
                    ++details.copiedCells;row.copiedPixels+=side*(side+GUTTER*2);
                    if(column==0) {
                        data.copyPixels(nativeData,new Rectangle(0,0,GUTTER,side+GUTTER*2),new Point(0,0));
                        ++details.copiedEdgeGutters;row.copiedPixels+=GUTTER*(side+GUTTER*2);
                    }
                    if(column==columns-1) {
                        data.copyPixels(nativeData,new Rectangle(GUTTER+side,0,GUTTER,side+GUTTER*2),
                            new Point(GUTTER+width,0));
                        ++details.copiedEdgeGutters;row.copiedPixels+=GUTTER*(side+GUTTER*2);
                    }
                }
                var strip:Bitmap=new Bitmap(data,atlas.pixelSnapping,atlas.smoothing);record.bitmap=strip;
                strip.name="ContinuousSceneAtlasPartition-rows-native-gutters-"+index+"-"+i;
                strip.x=atlas.x;strip.y=(firstY+i)*side;
                strip.alpha=atlas.alpha;strip.blendMode=atlas.blendMode;
                strip.transform.colorTransform=atlas.transform.colorTransform;
                strip.filters=atlas.filters;strip.cacheAsBitmap=atlas.cacheAsBitmap;
                strip.scrollRect=new Rectangle(GUTTER,GUTTER,width,side);
                layer.parent.addChildAt(strip,int(layer.depth)+i);++row.strips;
            }
        }

        private static function removeStrips(owned:Array,errors:Array):void {
            while(owned.length) {
                var record:Object=owned.pop(),bitmap:Bitmap=record.bitmap as Bitmap;
                try {if(bitmap && bitmap.parent)bitmap.parent.removeChild(bitmap);}
                catch(error:Error){errors.push("remove-strip: "+error.message);}
                try {if(bitmap)bitmap.bitmapData=null;if(record.data)record.data.dispose();}
                catch(disposeError:Error){errors.push("dispose-strip: "+disposeError.message);}
            }
        }
        private static function restoreNative(native:Array,errors:Array):void {
            for each(var old:Object in native) {
                try {old.bitmap.visible=old.visible;}
                catch(error:Error){errors.push("restore-native: "+error.message);}
            }
        }
        private static function restoreOrder(layers:Array,errors:Array):void {
            for each(var layer:Object in layers) {
                var parent:DisplayObjectContainer=layer.parent;
                try {
                    for(var i:int=0;i<layer.children.length;++i) {
                        var child:DisplayObject=layer.children[i] as DisplayObject;
                        if(child.parent!==parent)throw new Error("Original child changed parent");
                        if(parent.getChildIndex(child)!=i)parent.setChildIndex(child,i);
                    }
                    layer.atlas.visible=layer.visible;
                }catch(error:Error){errors.push("restore-order: "+error.message);}
            }
        }
        private static function bindingsRestored(layers:Array,native:Array):Boolean {
            for each(var layer:Object in layers) {
                var parent:DisplayObjectContainer=layer.parent,atlas:Bitmap=layer.atlas;
                if(parent.numChildren!=layer.children.length || atlas.bitmapData!==layer.data ||
                    atlas.visible!==layer.visible || atlas.transform.matrix.toString()!=layer.matrix.toString() || atlas.scrollRect!=null)
                    return false;
                for(var i:int=0;i<layer.children.length;++i)if(parent.getChildAt(i)!==layer.children[i])return false;
            }
            for each(var old:Object in native)if(old.bitmap.visible!==old.visible ||
                old.bitmap.parent!==old.parent || old.bitmap.bitmapData!==old.data)return false;
            return layers.length==4 && native.length>0;
        }
        private static function capture(w:*):BitmapData {
            var image:BitmapData=new BitmapData(w.main.stage.stageWidth,w.main.stage.stageHeight,false,0);
            try {image.draw(w.main.stage);}
            catch(error:Error){image.dispose();throw error;}
            return image;
        }
        private static function compare(actual:BitmapData,expected:BitmapData):Object {
            var delta:*=actual.compare(expected);
            if(delta===0)return {equal:true,count:0,maxDelta:0,bounds:null,samples:[]};
            if(!(delta is BitmapData))return {equal:false,compareCode:delta};
            var row:Object={equal:false,count:0,maxDelta:0,samples:[]};
            try {
                var rect:Rectangle=delta.getColorBoundsRect(0xFFFFFFFF,0,false);
                row.bounds={x:rect.x,y:rect.y,width:rect.width,height:rect.height};
                var a:Vector.<uint>=actual.getVector(rect),b:Vector.<uint>=expected.getVector(rect);
                for(var i:int=0;i<a.length;++i)if(a[i]!==b[i]) {
                    ++row.count;
                    for(var shift:int=0;shift<32;shift+=8)
                        row.maxDelta=Math.max(row.maxDelta,Math.abs(int((a[i]>>>shift)&255)-int((b[i]>>>shift)&255)));
                    if(row.samples.length<6)row.samples.push({x:rect.x+i%int(rect.width),y:rect.y+int(i/int(rect.width)),
                        actual:a[i].toString(16),native:b[i].toString(16)});
                }
            } finally {delta.dispose();}
            return row;
        }
    }
}
