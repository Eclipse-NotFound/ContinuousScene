package tests {
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.display.DisplayObjectContainer;
    import flash.geom.Matrix;
    import flash.geom.ColorTransform;
    import flash.geom.Point;
    import flash.geom.Rectangle;
    import flash.utils.Dictionary;
    import flash.utils.getTimer;

    /** Diagnostic only. The caller owns before-native / final-after-native timing.
     * Native pixels, simulation, draw order and all bitmap geometry stay original.
     * Any prewarming or resident change invalidates this one-use probe. */
    public class SceneFrontShadowProbe {
        public static const VERSION:String = "front-shadow-diagnostic-1";
        private static const MAX_ENTRIES:int = 256;
        private static const COUNTERS:Array = ["sceneResident","sceneWarmCount",
            "sceneWarmSlices","sceneWarmForced","sceneRedraws","sceneEvictions","sceneMisses"];
        private var world:*, location:*, grafon:*;
        private var records:Array = [];
        private var byEntry:Dictionary = new Dictionary();
        private var counters:Object = {};
        private var observedCounters:Object = {};
        private var windows:Array = [], current:Object;
        private var zero:Point = new Point();
        private var started:Boolean = false, closed:Boolean = false, aborted:Boolean = false;
        private var held:Boolean = false, prepared:Boolean = false;
        private var frameSerial:int = 0, expectedEnabled:Boolean = false;
        private var failures:Array = [], cleanupInfo:Object;
        private var totals:Object = freshCounts();
        private var setupMs:int = 0, cleanupMs:int = 0, allocatedBytes:Number = 0;
        private var cleanupErrors:int = 0;

        private static function freshCounts():Object {
            return {frames:0,revisionDelta:0,changedEntries:0,multiRevisionEntries:0,
                repeatedRevisionUnits:0,maxRevisionDelta:0,visibleChangedEntries:0,
                visibleMultiRevisionEntries:0,newBlocks:0,removedBlocks:0,
                fullSyncs:0,tailSyncs:0,copyPixels:0,copyBytes:0,
                prepareMs:0,updateMs:0,syncMs:0,ownMs:0};
        }
        private function add(name:String,value:Number):void {
            totals[name] += value;
            if(current)current.counts[name] += value;
        }
        private function maximum(name:String,value:Number):void {
            totals[name] = Math.max(Number(totals[name]),value);
            if(current)current.counts[name] = Math.max(Number(current.counts[name]),value);
        }
        private function rectEqual(a:Rectangle,b:Rectangle):Boolean {
            return a == null ? b == null : b != null && a.equals(b);
        }
        private function matrixEqual(a:Matrix,b:Matrix):Boolean {
            return a.a == b.a && a.b == b.b && a.c == b.c && a.d == b.d && a.tx == b.tx && a.ty == b.ty;
        }
        private function colorEqual(a:ColorTransform,b:ColorTransform):Boolean {
            return a.redMultiplier == b.redMultiplier && a.greenMultiplier == b.greenMultiplier &&
                a.blueMultiplier == b.blueMultiplier && a.alphaMultiplier == b.alphaMultiplier &&
                a.redOffset == b.redOffset && a.greenOffset == b.greenOffset &&
                a.blueOffset == b.blueOffset && a.alphaOffset == b.alphaOffset;
        }
        private function unsafeState(w:*):String {
            if(!w || w !== world || w.loc !== location || w.grafon !== grafon)return "context-changed";
            if(!grafon.sceneLarge || grafon.scenePreload || !grafon.sceneCullRender || int(grafon.sceneChunkSide) != 320)
                return "unsupported-scene-mode";
            if(w.allStat != 1 || w.onPause || w.t_exit != 0)return "inactive-pause-or-travel";
            if(!w.ctr || !w.sats || w.ctr.keySats || w.sats.active || grafon.visSats.visible)return "sats-or-capture";
            var reason:String = "";
            for each(var key:String in COUNTERS) {
                observedCounters[key] = Number(grafon[key]);
                if(!reason && Number(observedCounters[key]) !== Number(counters[key]))reason = "counter-changed:" + key;
            }
            return reason;
        }
        private function geometryOK(r:Object):Boolean {
            var b:Bitmap = r.bitmap;
            return b.parent === r.parent && b.x == r.x && b.y == r.y &&
                b.pixelSnapping == r.pixelSnapping && b.smoothing == r.smoothing &&
                rectEqual(b.scrollRect,r.scrollRect) && matrixEqual(b.transform.matrix,r.matrix) &&
                colorEqual(b.transform.colorTransform,r.colorTransform) &&
                b.alpha == r.alpha && b.blendMode == r.blendMode && b.mask === r.mask &&
                b.cacheAsBitmap == r.cached && b.filters.length == 0;
        }
        private function inspect():String {
            var surfaces:Array = grafon.sceneSurfaces();
            if(!surfaces)return "surface-api-unavailable";
            ++frameSerial;
            var found:int = 0, additions:int = 0;
            for each(var s:Object in surfaces) {
                var r:Object = byEntry[s];
                if(!r){++additions;continue;}
                if(r.seen == frameSerial)return "duplicate-surface";
                r.seen = frameSerial;++found;
                if(s.bitmaps !== r.bitmapArray || s.nativeBuffers !== r.nativeArray ||
                    s.bitmaps[0] !== r.bitmap || s.nativeBuffers[0] !== r.source)
                    return "native-identity-changed";
                if(r.source.width != 400 || r.source.height != 400 ||
                    Number(s.side) != 320 || Number(s.gutter) != 40 ||
                    Number(s.x) != r.entryX || Number(s.y) != r.entryY)
                    return "native-geometry-changed";
                if(!geometryOK(r))return "bitmap-property-changed";
                if(r.bitmap.bitmapData !== (held ? r.shadow : r.source))return "bitmap-binding-conflict";
                var revision:Number = Number(s.revision);
                if(!isFinite(revision) || revision != Math.floor(revision) || revision < r.revision)
                    return "revision-invalid-or-rewound";
            }
            if(additions)add("newBlocks",additions);
            if(found < records.length)add("removedBlocks",records.length-found);
            return additions || found != records.length || surfaces.length != records.length ? "resident-identity-changed" : "";
        }

        /** Call once outside measured windows, after warm-up has settled. */
        public function start(w:*):Object {
            if(started || closed)throw new Error("Front shadow probe is one-use");
            var at:int = getTimer();started = true;world = w;
            try {
                if(!w || !w.loc || !w.grafon)throw new Error("Missing native context");
                location = w.loc;grafon = w.grafon;
                for each(var key:String in COUNTERS) {
                    var value:Number = Number(grafon[key]);
                    if(!isFinite(value))throw new Error("Counter unavailable: " + key);
                    counters[key] = value;
                }
                var reason:String = unsafeState(w);
                if(reason)throw new Error(reason);
                var surfaces:Array = grafon.sceneSurfaces();
                if(!surfaces || surfaces.length == 0 || surfaces.length > MAX_ENTRIES || surfaces.length != int(grafon.sceneResident))
                    throw new Error("Unsupported resident population");
                var seenBitmaps:Dictionary = new Dictionary(), seenData:Dictionary = new Dictionary();
                for each(var s:Object in surfaces) {
                    var b:Bitmap = s.bitmaps ? s.bitmaps[0] as Bitmap : null;
                    var source:BitmapData = s.nativeBuffers ? s.nativeBuffers[0] as BitmapData : null;
                    var clip:Rectangle = b ? b.scrollRect : null;
                    if(!b || !source || byEntry[s] || seenBitmaps[b] || seenData[source] ||
                        b.parent !== grafon.visFront || b.bitmapData !== source ||
                        source.width != 400 || source.height != 400 ||
                        int(s.side) != 320 || int(s.gutter) != 40 ||
                        !clip || clip.x != 40 || clip.y != 40 || clip.width != 320 || clip.height != 320 ||
                        b.filters.length || b.mask || b.cacheAsBitmap || b.blendMode != "normal" || b.alpha != 1)
                        throw new Error("Unsupported native front surface");
                    var revision:Number = Number(s.revision);
                    if(!isFinite(revision) || revision != Math.floor(revision) || revision < 0)
                        throw new Error("Invalid starting revision");
                    var r:Object = {entry:s,bitmap:b,source:source,shadow:null,parent:b.parent,
                        bitmapArray:s.bitmaps,nativeArray:s.nativeBuffers,revision:revision,seen:0,
                        entryX:Number(s.x),entryY:Number(s.y),x:b.x,y:b.y,matrix:b.transform.matrix.clone(),
                        colorTransform:b.transform.colorTransform,
                        scrollRect:clip.clone(),pixelSnapping:b.pixelSnapping,smoothing:b.smoothing,
                        alpha:b.alpha,blendMode:b.blendMode,mask:b.mask,cached:b.cacheAsBitmap,
                        initialVisible:b.visible,initialWidth:b.width,initialHeight:b.height};
                    records.push(r);byEntry[s] = r;seenBitmaps[b] = true;seenData[source] = true;
                    r.shadow = source.clone();allocatedBytes += 400*400*4;
                    add("fullSyncs",1);add("copyPixels",400*400);add("copyBytes",400*400*4);
                }
            } catch(error:Error) {fail("start:" + error.message);clear();}
            setupMs += getTimer()-at;
            return snapshot();
        }

        /** A/B switches are explicit. Continuous primary timing must retain their cost. */
        public function beginWindow(w:*,enabled:Boolean):Object {
            if(!started || closed || aborted)throw new Error("Front shadow probe is unavailable");
            var at:int = getTimer();
            if(current)current.closed = true;
            restoreBindings();
            if(aborted)return snapshot();
            current = {index:windows.length,enabled:enabled,acceptable:true,closed:false,
                counts:freshCounts(),switchMs:0,failures:[]};windows.push(current);
            expectedEnabled = enabled;prepared = false;
            try {
                var reason:String = unsafeState(w);
                if(!reason)reason = inspect();
                if(reason){fail(reason);return snapshot();}
                for each(var r:Object in records) {
                    r.revision = Number(r.entry.revision);
                    if(enabled)sync(r,true);
                }
                if(enabled) {
                    // Set ownership before assignment so a partial failure can unwind.
                    held = true;
                    for each(r in records) {
                        r.bitmap.bitmapData = r.shadow;
                        r.bitmap.smoothing = r.smoothing; // bitmapData assignment resets it.
                    }
                }
            } catch(error:Error) {fail("begin-window:" + error.message);}
            finally {var elapsed:int = getTimer()-at;setupMs += elapsed;current.switchMs += elapsed;}
            return snapshot();
        }

        /** Must run before native step. Restore before V/SATS or any inactive state. */
        public function prepareFrame(w:*):void {
            if(!started || closed || aborted || !current)return;
            var at:int = getTimer();
            try {
                if(prepared){fail("missing-previous-tail");return;}
                var reason:String = unsafeState(w);
                if(reason){fail(reason);return;}
                prepared = true;
            } catch(error:Error) {fail("prepare:" + error.message);}
            finally {var elapsed:int = getTimer()-at;add("prepareMs",elapsed);add("ownMs",elapsed);}
        }

        /** Last game-write tail, before presentation. No native tick is skipped. */
        public function update(w:*,enabled:Boolean):void {
            if(!started || closed || aborted || !current)return;
            var at:int = getTimer();
            try {
                if(!prepared || enabled != expectedEnabled){fail("tail-order-or-window-mode");return;}
                prepared = false;
                var reason:String = unsafeState(w);
                if(!reason)reason = inspect();
                if(reason){fail(reason);return;}
                for each(var r:Object in records) {
                    var revision:Number = Number(r.entry.revision), delta:Number = revision-r.revision;
                    if(delta > 0) {
                        add("revisionDelta",delta);add("changedEntries",1);maximum("maxRevisionDelta",delta);
                        if(r.bitmap.visible)add("visibleChangedEntries",1);
                        if(delta > 1) {
                            add("multiRevisionEntries",1);add("repeatedRevisionUnits",delta-1);
                            if(r.bitmap.visible)add("visibleMultiRevisionEntries",1);
                        }
                        if(enabled)sync(r,false);
                    }
                    r.revision = revision;
                }
                add("frames",1);
            } catch(error:Error) {fail("tail:" + error.message);}
            finally {var elapsed:int = getTimer()-at;add("updateMs",elapsed);add("ownMs",elapsed);}
        }
        private function sync(r:Object,full:Boolean):void {
            var at:int = getTimer();
            r.shadow.copyPixels(r.source,r.source.rect,zero,null,null,false);
            add(full ? "fullSyncs" : "tailSyncs",1);
            add("copyPixels",400*400);add("copyBytes",400*400*4);
            if(!full)add("syncMs",getTimer()-at);
        }
        private function fail(reason:String):void {
            aborted = true;prepared = false;
            if(failures.length < 20)failures.push(reason);
            if(current){current.acceptable = false;if(current.failures.length < 20)current.failures.push(reason);}
            restoreBindings();
        }
        private function restoreBindings():void {
            for each(var r:Object in records) {
                var b:Bitmap = r.bitmap;
                try {
                    if(b.bitmapData === r.shadow && r.shadow != null) {
                        // Do not resurrect a removed node or an original buffer disposed by sceneDrop.
                        var live:Boolean = b.parent === r.parent && r.entry.bitmaps === r.bitmapArray &&
                            r.entry.nativeBuffers === r.nativeArray && r.entry.bitmaps[0] === b &&
                            r.entry.nativeBuffers[0] === r.source && r.source.width == 400 && r.source.height == 400;
                        b.bitmapData = live ? r.source : null;
                        b.smoothing = r.smoothing;
                        // Other properties were never changed by this probe. Preserve native/external edits.
                    } else if(b.bitmapData !== r.source && b.bitmapData != null && held) {
                        aborted = true;++cleanupErrors;
                        if(current)current.acceptable = false;
                        if(failures.length < 20)failures.push("cleanup-external-binding-left-untouched");
                    }
                } catch(error:Error) {
                    aborted = true;++cleanupErrors;if(current)current.acceptable = false;
                    try {if(b.bitmapData === r.shadow)b.bitmapData = null;}catch(ignored:Error){}
                    if(failures.length < 20)failures.push("cleanup:" + error.message);
                }
            }
            held = false;
        }
        /** Restore only our bitmapData binding; never dispose native data. */
        public function clear():Object {
            if(closed)return cleanupInfo;
            var at:int = getTimer();restoreBindings();
            var disposed:int = 0, leaked:int = 0;
            for each(var r:Object in records)if(r.shadow != null) {
                try {
                    if(r.bitmap.bitmapData === r.shadow){++leaked;continue;}
                    r.shadow.dispose();r.shadow = null;++disposed;
                } catch(error:Error){++leaked;if(failures.length < 20)failures.push("dispose:" + error.message);}
            }
            if(current){current.closed = true;if(leaked)current.acceptable = false;}
            closed = true;prepared = false;cleanupMs += getTimer()-at;
            cleanupInfo = {restored:leaked == 0 && cleanupErrors == 0,disposedClones:disposed,
                leakedClones:leaked,nativeDataDisposed:0,heldBindings:held,
                cleanupErrors:cleanupErrors,externalPropertyEditsPreserved:true};
            return cleanupInfo;
        }
        private function capture(w:*):BitmapData {
            var image:BitmapData = new BitmapData(w.main.stage.stageWidth,w.main.stage.stageHeight,false,0);
            try {image.draw(w.main.stage);}catch(error:Error){image.dispose();throw error;}
            return image;
        }
        private function difference(a:BitmapData,b:BitmapData):Object {
            var delta:* = a.compare(b);
            var result:Object = {equal:delta === 0,diffCount:0,maxChannelDelta:0};
            if(delta === 0)return result;
            if(!(delta is BitmapData))throw new Error("Capture dimensions or comparison failed");
            try {
                for(var y:int=0;y<a.height;++y) {
                    var av:Vector.<uint> = a.getVector(new Rectangle(0,y,a.width,1));
                    var bv:Vector.<uint> = b.getVector(new Rectangle(0,y,b.width,1));
                    for(var x:int=0;x<av.length;++x)if(av[x] != bv[x]) {
                        ++result.diffCount;
                        for(var shift:int=0;shift<=24;shift+=8)
                            result.maxChannelDelta = Math.max(result.maxChannelDelta,
                                Math.abs(int((av[x]>>>shift)&255)-int((bv[x]>>>shift)&255)));
                    }
                }
            } finally {BitmapData(delta).dispose();}
            return result;
        }
        /** Terminal same-frame check. Never advances native logic or edits source pixels.
         * Also checks the currently held B image before resync, when available. */
        public function verify(w:*):Object {
            var result:Object = {version:VERSION,valid:false,equal:false,restored:false,
                sameFrame:true,tailSyncsObserved:totals.tailSyncs,tailImageChecked:held,
                nativePixelWrites:0,verificationFullSyncs:0,bitmapPropertiesPreserved:false,error:null};
            var original:BitmapData=null,repeat:BitmapData=null,shadow:BitmapData=null;
            var restored:BitmapData=null,heldImage:BitmapData=null;
            try {
                if(!started || closed || aborted)throw new Error("Probe unavailable for verification");
                var reason:String = unsafeState(w);if(!reason)reason = inspect();
                if(reason)throw new Error(reason);
                if(held)heldImage = capture(w);
                restoreBindings();
                if(aborted)throw new Error("Could not restore reference binding");
                original = capture(w);repeat = capture(w);
                result.referenceRepeat = difference(original,repeat);
                if(!result.referenceRepeat.equal)throw new Error("Reference pixels changed without a native tick");
                if(heldImage)result.tailImage = difference(original,heldImage);
                // Terminal verification is separate from measured window counters.
                for each(var r:Object in records) {
                    r.shadow.copyPixels(r.source,r.source.rect,zero,null,null,false);
                    ++result.verificationFullSyncs;
                }
                held = true;
                for each(r in records) {
                    r.bitmap.bitmapData = r.shadow;r.bitmap.smoothing = r.smoothing;
                }
                shadow = capture(w);result.bindingImage = difference(original,shadow);
                restoreBindings();restored = capture(w);result.restoreImage = difference(original,restored);
                result.valid = true;
                result.equal = result.bindingImage.equal && (!result.tailImage || result.tailImage.equal);
                result.restored = result.restoreImage.equal && !aborted;
                result.bitmapPropertiesPreserved = true;
                for each(r in records)
                    if(r.bitmap.bitmapData !== r.source || !geometryOK(r))result.bitmapPropertiesPreserved = false;
                result.restored = result.restored && result.bitmapPropertiesPreserved;
                result.width = original.width;result.height = original.height;
                result.camera = {scale:w.cam.scaleV,vx:w.cam.vx,vy:w.cam.vy};
            } catch(error:Error) {result.error = error.message;fail("verify:"+error.message);}
            finally {
                result.cleanup = clear();
                result.restored = result.restored && result.cleanup.restored;
                if(original)original.dispose();if(repeat)repeat.dispose();if(shadow)shadow.dispose();
                if(restored)restored.dispose();if(heldImage)heldImage.dispose();
            }
            return result;
        }
        public function snapshot():Object {
            return {version:VERSION,diagnosticOnly:true,performanceAcceptance:false,
                started:started,closed:closed,aborted:aborted,heldBindings:held,
                surfaceAPI:"sceneSurfaces",residentEntries:records.length,allocatedBytes:allocatedBytes,
                staticResidentRequired:true,counters:counters,observedCounters:observedCounters,
                prepared:prepared,currentEnabled:expectedEnabled,totals:totals,windows:windows,
                setupMs:setupMs,cleanupMs:cleanupMs,totalOwnMs:Number(totals.ownMs)+setupMs+cleanupMs,
                failures:failures,cleanup:cleanupInfo,
                revisionMeaning:"All sceneApply kinds increment entry.revision; counts are not exact front hits",
                timingContract:"prepareFrame before native; update after every game pixel writer and before presentation",
                geometry:"Original 400x400 data, 320x320 scrollRect at 40, original bitmap and parent",
                scope:"No host patch, no new listeners, no pixel tolerance, no gameplay or production claim"};
        }
    }
}
