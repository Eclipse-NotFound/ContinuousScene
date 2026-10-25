package tests {
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.display.DisplayObject;
    import flash.display.DisplayObjectContainer;
    import flash.geom.Matrix;
    import flash.geom.Rectangle;
    import flash.utils.Dictionary;
    import flash.utils.getQualifiedClassName;
    import flash.utils.getTimer;

    /** Isolated attribution only. No pixel copies, visibility writes or native hooks. */
    public class SceneNativeTerrainDetach {
        public static const VERSION:String = "native-terrain-detach-2";
        private static const LIMIT:int = 4096;
        private var world:Object, grafon:Object, location:Object;
        private var parents:Array = [], children:Array = [], surfaces:Array = [], records:Array = [];
        private var byBitmap:Dictionary = new Dictionary(true);
        private var bySurface:Dictionary = new Dictionary(true);
        private var names:Object = {};
        private var valid:Boolean = true, initialized:Boolean = false, cleared:Boolean = false;
        private var lastApplied:Boolean = false;
        private var errors:Array = [];
        private var held:int = 0, detaches:int = 0, restores:int = 0, droppedSkipped:int = 0;
        private var updates:int = 0, headChecks:int = 0, scannedNodes:int = 0, structureChecks:int = 0;
        private var elapsedMs:int = 0, enteringRestores:int = 0, peakHeld:int = 0;
        private var initialSurfaces:int = 0, surfacesAdded:int = 0, surfacesRetired:int = 0;
        private var nodesCreated:int = 0, nodesRetired:int = 0, retiredHeld:int = 0, generation:int = 0, bindingsCleared:int = 0;

        private function read(o:Object, name:String):* {
            var q:QName = names[name] as QName;
            if(q == null) { q = new QName("",name); names[name] = q; }
            return o[q];
        }
        private function fail(message:String):void {
            valid = false;
            if(errors.length < 32) errors.push(message);
        }
        private function nativeSurfaces():Array {
            var f:Function = read(grafon,"sceneSurfaces") as Function;
            if(f == null) throw new Error("Missing public sceneSurfaces");
            var a:Array = f.call(grafon) as Array;
            if(a == null || a.length > LIMIT) throw new Error("Invalid or excessive surfaces");
            return a;
        }
        private function contextOK(w:Object):Boolean {
            if(w !== world || read(w,"grafon") !== grafon || read(w,"loc") !== location ||
               read(grafon,"loc") !== location || read(grafon,"sceneLarge") !== true) return false;
            var ctr:Object = read(w,"ctr"), sats:Object = read(w,"sats");
            var overlay:DisplayObject = read(grafon,"visSats") as DisplayObject;
            if(ctr == null || sats == null || overlay == null) return false;
            return !Boolean(read(ctr,"keySats")) && !Boolean(read(sats,"active")) && !overlay.visible;
        }
        private function attributes(b:Bitmap):Object {
            var r:Rectangle = b.scrollRect;
            return {x:b.x,y:b.y,scaleX:b.scaleX,scaleY:b.scaleY,rotation:b.rotation,
                alpha:b.alpha,blend:b.blendMode,smoothing:b.smoothing,snapping:b.pixelSnapping,
                cache:b.cacheAsBitmap,rect:r == null ? null : r.clone()};
        }
        private function sameAttributes(r:Object):Boolean {
            var b:Bitmap = r.bitmap, a:Object = r.attributes, v:Rectangle = b.scrollRect;
            var q:Rectangle = a.rect as Rectangle;
            return b.x === a.x && b.y === a.y && b.scaleX === a.scaleX && b.scaleY === a.scaleY &&
                b.rotation === a.rotation && b.alpha === a.alpha && b.blendMode === a.blend &&
                b.smoothing === a.smoothing && b.pixelSnapping === a.snapping && b.cacheAsBitmap === a.cache &&
                b.mask == null && b.filters.length == 0 && ((v == null && q == null) ||
                (v != null && q != null && v.x === q.x && v.y === q.y && v.width === q.width && v.height === q.height));
        }
        private function finite(value:Number):Boolean { return !isNaN(value) && isFinite(value); }

        public function begin(w:Object):Boolean {
            var started:int = getTimer();
            if(initialized || cleared || !valid) { fail("begin called more than once"); return false; }
            try {
                world = w; grafon = read(w,"grafon"); location = read(w,"loc");
                if(!contextOK(w)) throw new Error("Not an idle-SATS native large scene");
                parents = [read(grafon,"visFront"),read(grafon,"visBack"),read(grafon,"visBack2"),read(grafon,"visVoda")];
                var layer:int, i:int, p:DisplayObjectContainer, b:Bitmap, s:Object, a:Array, data:Array;
                for(layer=0;layer<4;++layer) {
                    p = parents[layer] as DisplayObjectContainer;
                    if(p == null || p.stage == null || p.numChildren > LIMIT*4) throw new Error("Invalid native parent");
                    for(i=0;i<layer;++i) if(parents[i] === p) throw new Error("Duplicate native parent");
                    var order:Array = [];
                    for(i=0;i<p.numChildren;++i) order.push(p.getChildAt(i));
                    children.push(order);
                }
                surfaces = nativeSurfaces();
                if(surfaces.length == 0) throw new Error("No native surfaces");
                for each(s in surfaces) {
                    if(s == null || bySurface[s]) throw new Error("Duplicate surface");
                    a = s.bitmaps as Array; data = s.nativeBuffers as Array;
                    if(a == null || data == null || a.length != 4 || data.length != 4) throw new Error("Non-four-layer surface");
                    bySurface[s] = [];
                    for(layer=0;layer<4;++layer) {
                        b = a[layer] as Bitmap; p = parents[layer];
                        if(b == null || getQualifiedClassName(b) != "flash.display::Bitmap" || byBitmap[b] ||
                           b.parent !== p || b.bitmapData !== data[layer] || !(data[layer] is BitmapData))
                            throw new Error("Foreign bitmap, parent or data");
                        if(b.bitmapData.width <= 0 || b.bitmapData.height <= 0 || b.mask != null || b.filters.length != 0 ||
                           !finite(b.x) || !finite(b.y) || !finite(b.alpha) || !finite(b.scaleX) || !finite(b.scaleY) || !finite(b.rotation))
                            throw new Error("Unsupported bitmap display state");
                        var r:Object = {surface:s,layer:layer,bitmap:b,data:data[layer],parent:p,
                            parentParent:p.parent,index:p.getChildIndex(b),held:false,attributes:attributes(b)};
                        byBitmap[b] = r; records.push(r); bySurface[s].push(r); ++nodesCreated;
                    }
                }
                initialSurfaces = surfaces.length; initialized = true;
                validate(w);
            } catch(error:*) { fail("begin: " + String(error)); }
            elapsedMs += getTimer()-started;
            return valid && initialized;
        }

        /** Does NOT churn the display tree each frame. SATS is forbidden in this diagnostic. */
        public function beginFrame(w:Object):void {
            var started:int = getTimer(); ++headChecks;
            if(initialized && valid && !cleared) {
                try { if(!contextOK(w)) throw new Error("Context changed or SATS requested before native frame"); }
                catch(error:*) { fail("head: " + String(error)); restoreForExit(); }
            }
            elapsedMs += getTimer()-started;
        }
        private function validate(w:Object):void {
            if(!initialized || cleared || !contextOK(w)) throw new Error("Inactive context or forbidden SATS");
            if(read(grafon,"visFront") !== parents[0] || read(grafon,"visBack") !== parents[1] ||
               read(grafon,"visBack2") !== parents[2] || read(grafon,"visVoda") !== parents[3])
                throw new Error("Native parent field identity changed");
            reconcileSurfaces(nativeSurfaces());
            var r:Object, b:Bitmap;
            for each(r in records) {
                ++scannedNodes; b = r.bitmap;
                if(r.surface.bitmaps[r.layer] !== b || r.surface.nativeBuffers[r.layer] !== r.data ||
                   b.bitmapData !== r.data || b.bitmapData.width <= 0 || b.bitmapData.height <= 0 ||
                   r.parent.parent !== r.parentParent || b.parent !== (r.held ? null : r.parent) || !sameAttributes(r))
                    throw new Error("Bitmap ownership, data, display attributes or ancestry changed");
            }
            if(!orderExact()) throw new Error("Native parent child sequence changed");
        }
        /** Admit only complete native Drop and four-layer tail append; no display writes here. */
        private function reconcileSurfaces(current:Array):void {
            var seen:Dictionary=new Dictionary(true), freshByBitmap:Dictionary=new Dictionary(true);
            var retiredByBitmap:Dictionary=new Dictionary(true), fresh:Array=[], retired:Array=[];
            var s:Object,r:Object,b:Bitmap,p:DisplayObjectContainer,layer:int,i:int;
            for each(s in current) {
                if(s==null || seen[s])throw new Error("Duplicate/null current surface");
                seen[s]=true;
                if(bySurface[s])continue;
                var bits:Array=s.bitmaps as Array, data:Array=s.nativeBuffers as Array, group:Array=[];
                if(bits==null || data==null || bits.length!=4 || data.length!=4)throw new Error("Incomplete new surface");
                for(layer=0;layer<4;++layer) {
                    b=bits[layer] as Bitmap;p=parents[layer];
                    if(b==null || getQualifiedClassName(b)!="flash.display::Bitmap" || byBitmap[b] || freshByBitmap[b] ||
                       b.parent!==p || b.bitmapData!==data[layer] || !(data[layer] is BitmapData))
                        throw new Error("New surface bitmap is not a unique native-owned child");
                    if(b.bitmapData.width<=0 || b.bitmapData.height<=0 || b.mask!=null || b.filters.length!=0 ||
                       !finite(b.x)||!finite(b.y)||!finite(b.alpha)||!finite(b.scaleX)||!finite(b.scaleY)||!finite(b.rotation))
                        throw new Error("Unsupported new surface display state");
                    r={surface:s,layer:layer,bitmap:b,data:data[layer],parent:p,parentParent:p.parent,
                        index:p.getChildIndex(b),held:false,attributes:attributes(b)};
                    freshByBitmap[b]=r;group.push(r);
                }
                fresh.push({surface:s,records:group});
            }
            for each(s in surfaces)if(!seen[s]) {
                group=bySurface[s] as Array;
                if(group==null || group.length!=4)throw new Error("Unknown retired surface group");
                for each(r in group) {
                    // sceneDrop leaves the original arrays, but removes every child and nulls its binding.
                    if(r.surface.bitmaps[r.layer]!==r.bitmap || r.surface.nativeBuffers[r.layer]!==r.data ||
                       r.bitmap.parent!==null || r.bitmap.bitmapData!==null)
                        throw new Error("Missing surface is not a complete native Drop");
                    retiredByBitmap[r.bitmap]=true;
                }
                retired.push({surface:s,records:group});
            }
            if(fresh.length==0 && retired.length==0)return;

            var nextChildren:Array=[], appendOrder:Array=[];
            for(layer=0;layer<4;++layer) {
                p=parents[layer];var order:Array=[], at:int=0, appended:Array=[];
                for each(var node:DisplayObject in children[layer]) {
                    if(retiredByBitmap[node])continue;
                    order.push(node);r=byBitmap[node];
                    if(r && r.held)continue;
                    if(at>=p.numChildren || p.getChildAt(at)!==node)
                        throw new Error("Existing non-target anchor or remaining order changed");
                    ++at;
                }
                while(at<p.numChildren) {
                    node=p.getChildAt(at++);r=freshByBitmap[node];
                    if(r==null || r.layer!=layer || appended.indexOf(r.surface)>=0)
                        throw new Error("Unknown child or non-tail native insertion");
                    order.push(node);appended.push(r.surface);
                }
                if(appended.length!=fresh.length)throw new Error("Not all new surfaces append in every layer");
                if(layer==0)appendOrder=appended;
                else for(i=0;i<appendOrder.length;++i)if(appended[i]!==appendOrder[i])
                    throw new Error("Four native layer append orders differ");
                nextChildren.push(order);
            }
            // Commit identity bookkeeping only after every parent and every retired group passed.
            var kept:Array=[];
            for each(r in records) {
                if(retiredByBitmap[r.bitmap]) {
                    if(r.held){r.held=false;--held;++retiredHeld;}
                    delete byBitmap[r.bitmap];++nodesRetired;
                } else kept.push(r);
            }
            for each(var item:Object in retired) {delete bySurface[item.surface];++surfacesRetired;}
            for each(item in fresh) {
                bySurface[item.surface]=item.records;++surfacesAdded;
                for each(r in item.records){byBitmap[r.bitmap]=r;kept.push(r);++nodesCreated;}
            }
            records=kept;children=nextChildren;surfaces=current.concat();++generation;
        }
        private function orderExact():Boolean {
            ++structureChecks;
            for(var layer:int=0;layer<4;++layer) {
                var p:DisplayObjectContainer = parents[layer], at:int = 0;
                for each(var node:DisplayObject in children[layer]) {
                    var r:Object = byBitmap[node];
                    if(r && r.held) continue;
                    if(at >= p.numChildren || p.getChildAt(at) !== node) return false;
                    ++at;
                }
                if(at != p.numChildren) return false;
            }
            return true;
        }
        private function restoreSelected(all:Boolean):int {
            var count:int = 0;
            for(var layer:int=0;layer<4;++layer) {
                var p:DisplayObjectContainer = parents[layer], at:int = 0;
                for each(var node:DisplayObject in children[layer]) {
                    var r:Object = byBitmap[node];
                    if(r && r.held) {
                        if(!all && !r.bitmap.visible) continue;
                        try { p.addChildAt(r.bitmap,at); }
                        finally {
                            if(r.bitmap.parent === p) { r.held = false; --held; ++restores; ++count; }
                        }
                        if(r.held) throw new Error("Listener changed restored bitmap parent");
                    }
                    ++at;
                }
            }
            return count;
        }
        private function detachInvisible():int {
            var count:int = 0;
            for(var layer:int=0;layer<4;++layer) {
                var p:DisplayObjectContainer = parents[layer], order:Array = children[layer];
                for(var i:int=order.length-1;i>=0;--i) {
                    var r:Object = byBitmap[order[i]];
                    if(r == null || r.held || r.bitmap.visible) continue;
                    // Set ownership before removeChild: an event listener may throw after removal.
                    r.held = true; ++held; ++detaches; ++count;
                    try { p.removeChild(r.bitmap); }
                    catch(error:*) {
                        if(r.bitmap.parent === p) { r.held=false; --held; --detaches; --count; }
                        throw error;
                    }
                }
            }
            peakHeld = Math.max(peakHeld,held);
            return count;
        }
        public function update(w:Object, enabled:Boolean):Object {
            var started:int = getTimer(), prior:Boolean = lastApplied;
            var visible:Array=[0,0,0,0], invisible:Array=[0,0,0,0], heldLayers:Array=[0,0,0,0];
            var entered:int=0, detached:int=0; ++updates;
            try {
                if(!valid) throw new Error("Previous diagnostic failure");
                validate(w);
                var beforeGeneration:int=generation;
                for each(var observation:Object in records) observation.observedVisible = observation.bitmap.visible;
                entered = restoreSelected(!enabled);
                if(enabled) { enteringRestores += entered; detached = detachInvisible(); }
                validate(w);
                if(generation!=beforeGeneration)throw new Error("Native lifecycle changed inside the tree operation");
                for each(observation in records) if(observation.bitmap.visible !== observation.observedVisible ||
                    (observation.held && observation.bitmap.visible)) throw new Error("Native visibility changed during tree operation");
            } catch(error:*) { fail("update: " + String(error)); restoreForExit(); }
            for each(var r:Object in records) {
                if(r.bitmap.visible) ++visible[r.layer]; else ++invisible[r.layer];
                if(r.held) ++heldLayers[r.layer];
            }
            lastApplied = held > 0;
            var own:int = getTimer()-started; elapsedMs += own;
            return {version:VERSION,enabled:enabled,applied:lastApplied,previousApplied:prior,valid:valid,
                surfaces:surfaces.length,nativeVisible:visible,nativeInvisible:invisible,heldByLayer:heldLayers,
                enteredRestored:enabled ? entered : 0,restoredThisUpdate:entered,newlyDetached:detached,
                ownMs:own,snapshot:snapshot()};
        }

        /** Best effort on failure. Never attach a node no longer owned by a live native surface. */
        private function restoreForExit():void {
            if(!initialized || held == 0) return;
            var live:Dictionary = new Dictionary(true), sourceKnown:Boolean = false;
            try {
                if(read(world,"grafon") === grafon && read(world,"loc") === location && read(grafon,"loc") === location) {
                    var current:Array=nativeSurfaces();
                    try { reconcileSurfaces(current); }
                    catch(reconcileError:*) { fail("Exit lifecycle validation: "+String(reconcileError)); }
                    for each(var s:Object in current) live[s] = true;
                    sourceKnown = true;
                }
            } catch(error:*) { fail("Cannot verify live surfaces during restore: " + String(error)); }
            for(var layer:int=0;layer<4;++layer) {
                var p:DisplayObjectContainer = parents[layer], order:Array = children[layer];
                for(var i:int=0;i<order.length;++i) {
                    var r:Object=byBitmap[order[i]];
                    if(r == null || !r.held) continue;
                    try {
                        if(!sourceKnown) { fail("Live ownership unknown; held node not reattached"); continue; }
                        if(!live[r.surface] || r.surface.bitmaps[r.layer] !== r.bitmap ||
                           r.surface.nativeBuffers[r.layer] !== r.data || r.bitmap.bitmapData !== r.data) {
                            r.held=false; --held; ++droppedSkipped;
                            fail("Native dropped/replaced a held bitmap; not resurrected"); continue;
                        }
                        if(r.bitmap.parent !== null || p.parent !== r.parentParent || r.data.width <= 0 || r.data.height <= 0)
                            throw new Error("Restore ownership/ancestry conflict");
                        var before:int=-1, after:int=-1, j:int;
                        for(j=i+1;j<order.length;++j) if(order[j].parent === p) { before=p.getChildIndex(order[j]); break; }
                        for(j=i-1;j>=0;--j) if(order[j].parent === p) { after=p.getChildIndex(order[j]); break; }
                        if(before>=0 && after>=before) throw new Error("Original neighbors reordered");
                        var at:int=before>=0 ? before : (after>=0 ? after+1 : (p.numChildren==0 ? 0 : -1));
                        if(at<0) throw new Error("No trustworthy restoration anchor");
                        try { p.addChildAt(r.bitmap,at); }
                        finally {
                            if(r.bitmap.parent === p) { r.held=false; --held; ++restores; }
                        }
                        if(r.held) throw new Error("Listener changed restored bitmap parent");
                    } catch(restoreError:*) { fail("restore: " + String(restoreError)); }
                }
            }
            try { if(!orderExact()) fail("Original complete child sequence not restored"); }
            catch(orderError:*) { fail("Restore order verification: " + String(orderError)); }
            lastApplied = held > 0;
        }
        public function snapshot():Object {
            return {version:VERSION,diagnosticOnly:true,performanceEligible:false,valid:valid,
                initialized:initialized,cleared:cleared,held:held,pendingRestore:held,applied:held>0,
                surfaces:surfaces.length,nodes:records.length,detaches:detaches,restores:restores,
                initialSurfaces:initialSurfaces,surfacesAdded:surfacesAdded,surfacesRetired:surfacesRetired,
                nodesCreated:nodesCreated,nodesRetired:nodesRetired,retiredHeld:retiredHeld,generation:generation,bindingsCleared:bindingsCleared,
                droppedSkipped:droppedSkipped,enteringRestores:enteringRestores,peakHeld:peakHeld,
                updates:updates,headChecks:headChecks,scannedNodes:scannedNodes,structureChecks:structureChecks,
                elapsedMs:elapsedMs,errors:errors.concat()};
        }

        private function comparePixels(a:BitmapData,b:BitmapData,images:Array):Object {
            var result:Object={exactEqual:false,diffCount:0,maxRGB:0,maxAlpha:0};
            var difference:Object=a.compare(b);
            if(difference is Number) {
                if(Number(difference)!=0) throw new Error("Bitmap comparison dimensions differ: "+difference);
                result.exactEqual=true;return result;
            }
            var delta:BitmapData=difference as BitmapData;
            if(delta==null)throw new Error("Unknown BitmapData.compare result");
            images.push(delta);
            for(var y:int=0;y<a.height;++y) for(var x:int=0;x<a.width;++x) {
                var left:uint=a.getPixel32(x,y),right:uint=b.getPixel32(x,y);
                if(left==right)continue;
                result.diffCount=Number(result.diffCount)+1;
                for(var shift:int=0;shift<24;shift+=8)
                    result.maxRGB=Math.max(result.maxRGB,Math.abs(int((left>>>shift)&255)-int((right>>>shift)&255)));
                result.maxAlpha=Math.max(result.maxAlpha,Math.abs(int(left>>>24)-int(right>>>24)));
            }
            return result;
        }
        private function capture(view:DisplayObject,width:int,height:int,matrix:Matrix,images:Array):BitmapData {
            var data:BitmapData=new BitmapData(width,height,true,0);images.push(data);
            data.draw(view,matrix,null,null,null,false);return data;
        }
        /** Terminal component only, after the continuous timing interval has been closed. */
        public function checkPixels(w:Object):Object {
            var started:int=getTimer(),images:Array=[];
            var out:Object={version:VERSION,diagnosticOnly:true,performanceEligible:false,valid:false,equal:false,
                restored:false,heldPositive:false,cases:[],samples:0,bitmapsCreated:0,bitmapsDisposed:0,errors:[]};
            try {
                if(!valid || !initialized || held!=0)throw new Error("Pixel check requires a valid native-bound end state");
                validate(w);out.before=snapshot();
                var view:DisplayObject=read(w,"visual") as DisplayObject;
                if(view==null || view.stage==null)throw new Error("World is not on Stage");
                for(var ancestor:DisplayObject=view;ancestor;ancestor=ancestor.parent)
                    if(!ancestor.visible || !finite(ancestor.alpha) || ancestor.alpha<=0)throw new Error("World ancestry is hidden");
                var width:int=view.stage.stageWidth,height:int=view.stage.stageHeight;
                if(width<=0 || height<=0 || width>8192 || height>8192 || Number(width)*height>8388608)
                    throw new Error("Invalid or excessive capture dimensions");
                var matrix:Matrix=view.transform.concatenatedMatrix;
                if(!finite(matrix.a)||!finite(matrix.b)||!finite(matrix.c)||!finite(matrix.d)||!finite(matrix.tx)||!finite(matrix.ty))
                    throw new Error("Nonfinite actual world-to-Stage matrix");
                out.width=width;out.height=height;
                out.matrix={a:matrix.a,b:matrix.b,c:matrix.c,d:matrix.d,tx:matrix.tx,ty:matrix.ty};
                var nativeImage:BitmapData=capture(view,width,height,matrix,images);out.samples=Number(out.samples)+1;
                out.nonemptyNative=!nativeImage.getColorBoundsRect(0xFF000000,0,false).isEmpty();
                if(!out.nonemptyNative)throw new Error("Native capture contains no visible alpha");
                var detached:Object=update(w,true);out.detached=detached;out.heldPositive=held>0;
                if(!detached.valid || held==0)throw new Error("No valid actual detached-node comparison");
                var detachedImage:BitmapData=capture(view,width,height,matrix,images);out.samples=Number(out.samples)+1;
                var returned:Object=update(w,false);out.returned=returned;
                if(!returned.valid || held!=0)throw new Error("Native binding restoration failed before third image");
                var restoredImage:BitmapData=capture(view,width,height,matrix,images);out.samples=Number(out.samples)+1;
                var a:Object=comparePixels(nativeImage,detachedImage,images);a.name="native-vs-detached";out.cases.push(a);
                var b:Object=comparePixels(nativeImage,restoredImage,images);b.name="native-vs-restored";out.cases.push(b);
                validate(w);
                var actual:Matrix=view.transform.concatenatedMatrix;
                if(actual.a!==matrix.a||actual.b!==matrix.b||actual.c!==matrix.c||actual.d!==matrix.d||
                   actual.tx!==matrix.tx||actual.ty!==matrix.ty||view.stage.stageWidth!=width||view.stage.stageHeight!=height)
                    throw new Error("Capture geometry changed within the synchronous check");
                out.valid=true;out.equal=a.exactEqual && b.exactEqual;
            } catch(error:*) { out.errors.push(String(error)); }
            finally {
                if(held>0) {
                    try { if(valid)update(w,false);else restoreForExit(); }
                    catch(restoreError:*) { out.errors.push("Pixel finally restore: "+String(restoreError)); }
                }
                out.bitmapsCreated=images.length;
                for each(var data:BitmapData in images) {
                    try { data.dispose();out.bitmapsDisposed=Number(out.bitmapsDisposed)+1; }
                    catch(disposeError:*) { out.errors.push("Pixel dispose: "+String(disposeError)); }
                }
                out.after=snapshot();out.restored=valid && held==0 && droppedSkipped==0;
                if(!out.restored || out.bitmapsCreated!=out.bitmapsDisposed || out.errors.length)out.valid=false;
                out.elapsedMs=getTimer()-started;
            }
            return out;
        }
        public function clear():Object {
            var started:int=getTimer();
            if(!cleared) {
                if(initialized && valid) {
                    try { validate(world); }
                    catch(error:*) { fail("cleanup validation: " + String(error)); }
                }
                restoreForExit();
                if(held==0) {
                    bindingsCleared+=records.length;
                    parents=[]; children=[]; surfaces=[]; records=[];
                    byBitmap=new Dictionary(true); bySurface=new Dictionary(true);
                    world=null; grafon=null; location=null; initialized=false; cleared=true;
                }
            }
            elapsedMs += getTimer()-started;
            return {restored:held==0 && valid && droppedSkipped==0,pendingRestore:held,errors:errors.concat(),snapshot:snapshot()};
        }
    }
}
