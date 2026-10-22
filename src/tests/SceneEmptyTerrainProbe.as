package tests {
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.display.DisplayObjectContainer;
    import flash.geom.Rectangle;
    import flash.utils.Dictionary;
    import flash.utils.getTimer;

    /** Isolated diagnostic, not a production visibility policy.
     * Call beginFrame BEFORE native logic (including V/SATS capture), then
     * update AFTER native logic and before presentation. Both AB arms inspect
     * the same native surfaces; enabled only controls the final visible write.
     * Only an entirely alpha-empty 400px buffer qualifies. A transparent 320px
     * centre with occupied gutters does NOT qualify: smoothing may sample them.
     */
    public class SceneEmptyTerrainProbe {
        public static const VERSION:String="empty-native-terrain-diagnostic-1";
        private static const SIDE:int=320;
        private static const GUTTER:int=40;
        private var world:*,location:*,grafon:*;
        private var parents:Array=[];
        private var cache:Dictionary=new Dictionary(true);
        private var hidden:Array=[];
        private var updates:int=0,enabledUpdates:int=0,beginCalls:int=0;
        private var contextChanges:int=0,satsBypasses:int=0;
        private var surfaceObservations:int=0,visibleObservations:int=0;
        private var transparentObservations:int=0,hiddenWrites:int=0,restoredWrites:int=0;
        private var samples:int=0,cacheHits:int=0,surfaceRevisions:int=0,dataChanges:int=0;
        private var scanCost:int=0,scanMax:int=0,updateCost:int=0;
        private var updatePendingRestores:int=0,alreadyRestored:int=0,errorCount:int=0;
        private var exampleSamples:Array=[];
        private var last:Object={enabled:false,surfaces:0,visibleLayers:0,transparentLayers:0,hidden:0};
        private var errors:Array=[];

        public function update(w:*,enabled:Boolean):void {
            var started:int=getTimer();
            // Defensive same-frame cleanup also permits paired pixel snapshots.
            // During timed play this count must be zero: it cannot repair a
            // missing pre-native beginFrame after SATS has already captured.
            if(hidden.length)++updatePendingRestores;
            beginFrame();
            ++updates;if(enabled)++enabledUpdates;
            last={enabled:enabled,surfaces:0,visibleLayers:0,transparentLayers:0,hidden:0,
                samples:0,cacheHits:0,scanCost:0,revisionChanges:0,dataChanges:0,
                foreignBindings:0,foreignParents:0,unsupportedDisplay:0,
                transparentByLayer:[0,0,0,0],hiddenByLayer:[0,0,0,0],reason:"native"};
            try {
                if(!w || !w.loc || !w.grafon || !w.grafon.sceneLarge) {
                    dropContext();last.reason="no-large-scene";return;
                }
                var g:*=w.grafon;
                var nextParents:Array=[g.visFront,g.visBack,g.visBack2,g.visVoda];
                var changed:Boolean=world!==w || location!==w.loc || grafon!==g || parents.length!=4;
                var i:int;
                for(i=0;i<4;++i) {
                    if(!(nextParents[i] is DisplayObjectContainer))throw new Error("Missing native terrain parent "+i);
                    if(parents.length==4 && parents[i]!==nextParents[i])changed=true;
                }
                if(changed) {dropContext();++contextChanges;world=w;location=w.loc;grafon=g;parents=nextParents;}
                if((w.sats && w.sats.active) || (g.visSats && g.visSats.visible)) {
                    ++satsBypasses;last.reason="sats-native-restored";return;
                }
                if(int(g.sceneChunkSide)!=SIDE)throw new Error("Empty terrain probe requires native 320px chunks");
                var surfaces:Array=g.sceneSurfaces();
                if(!surfaces)throw new Error("Native surface list unavailable");
                last.surfaces=surfaces.length;surfaceObservations+=surfaces.length;
                for each(var surface:Object in surfaces) {
                    if(int(surface.side)!=SIDE || int(surface.gutter)!=GUTTER ||
                        !surface.nativeBuffers || !surface.bitmaps ||
                        surface.nativeBuffers.length!=4 || surface.bitmaps.length!=4 ||
                        !isFinite(Number(surface.revision)))
                        throw new Error("Unexpected native surface geometry or revision");
                    var record:Object=cache[surface];
                    if(!record) {record={revision:surface.revision,layers:[]};cache[surface]=record;}
                    else if(record.revision!==surface.revision) {
                        record.revision=surface.revision;++surfaceRevisions;++last.revisionChanges;
                    }
                    for(i=0;i<4;++i) {
                        var bitmap:Bitmap=surface.bitmaps[i] as Bitmap;
                        var data:BitmapData=surface.nativeBuffers[i] as BitmapData;
                        if(!bitmap || !data)throw new Error("Missing native terrain bitmap or buffer");
                        if(!bitmap.visible)continue;
                        ++last.visibleLayers;++visibleObservations;
                        if(bitmap.bitmapData!==data) {++last.foreignBindings;continue;}
                        if(bitmap.parent!==parents[i]) {++last.foreignParents;continue;}
                        if(data.width!=SIDE+2*GUTTER || data.height!=SIDE+2*GUTTER)
                            throw new Error("Native terrain buffer is not 400px square");
                        var layer:Object=record.layers[i];
                        if(!layer || layer.revision!==surface.revision || layer.data!==data) {
                            if(layer && layer.data!==data) {++dataChanges;++last.dataChanges;}
                            var scanStart:int=getTimer();
                            var bounds:Rectangle=data.getColorBoundsRect(0xFF000000,0,false);
                            var elapsed:int=getTimer()-scanStart;
                            scanCost+=elapsed;last.scanCost+=elapsed;if(elapsed>scanMax)scanMax=elapsed;
                            ++samples;++last.samples;
                            layer={revision:surface.revision,data:data,empty:bounds.isEmpty()};
                            record.layers[i]=layer;
                            if(exampleSamples.length<12)exampleSamples.push({cx:surface.cx,cy:surface.cy,
                                layer:i,revision:surface.revision,empty:layer.empty,
                                width:data.width,height:data.height,scanCost:elapsed});
                        } else {++cacheHits;++last.cacheHits;}
                        if(!layer.empty)continue;
                        ++transparentObservations;++last.transparentLayers;++last.transparentByLayer[i];
                        // Native terrain is unfiltered. Fail closed if another
                        // presenter could synthesize alpha from empty storage.
                        if(bitmap.filters.length || bitmap.transform.colorTransform.alphaOffset!=0 ||
                            bitmap.blendMode!="normal") {++last.unsupportedDisplay;continue;}
                        if(!enabled)continue;
                        // Save the exact original reference before the only
                        // presentation write. No parent, coordinate or data edits.
                        hidden.push(bitmap);bitmap.visible=false;
                        ++hiddenWrites;++last.hidden;++last.hiddenByLayer[i];
                    }
                }
            } catch(error:Error) {
                ++errorCount;if(errors.length<12)errors.push({update:updates,message:error.message});
                beginFrame();dropContext();last.reason="error-restored";throw error;
            } finally {updateCost+=getTimer()-started;}
        }

        public function beginFrame():void {
            ++beginCalls;
            // Restore originals even if detached or replaced; never touch a
            // replacement bitmap. Only true -> false writes are owned here.
            for each(var bitmap:Bitmap in hidden) {
                if(!bitmap.visible) {bitmap.visible=true;++restoredWrites;}
                else ++alreadyRestored;
            }
            hidden=[];
        }

        private function dropContext():void {
            cache=new Dictionary(true);parents=[];world=null;location=null;grafon=null;
        }

        public function clear():void {
            beginFrame();dropContext();
            last={enabled:false,surfaces:0,visibleLayers:0,transparentLayers:0,hidden:0,reason:"cleared"};
        }

        public function snapshot():Object {
            return {version:VERSION,diagnosticOnly:true,performanceAcceptance:false,
                valid:errorCount==0,updates:updates,enabledUpdates:enabledUpdates,beginCalls:beginCalls,
                contextChanges:contextChanges,satsBypasses:satsBypasses,
                surfaceObservations:surfaceObservations,visibleLayerObservations:visibleObservations,
                transparentLayerObservations:transparentObservations,hiddenWrites:hiddenWrites,
                restoredWrites:restoredWrites,alreadyRestored:alreadyRestored,pendingRestore:hidden.length,
                samples:samples,cacheHits:cacheHits,surfaceRevisionChanges:surfaceRevisions,
                dataIdentityChanges:dataChanges,scanCost:scanCost,scanMax:scanMax,updateCost:updateCost,
                updatePendingRestores:updatePendingRestores,last:last,sampleDetails:exampleSamples.concat(),
                errors:errorCount,errorDetails:errors.concat(),
                rule:"Only completely alpha-empty native 400x400 buffers; 320px centre alone is insufficient",
                cacheKey:"surface identity + layer + surface revision + native BitmapData identity",
                timing:"Both arms inspect; enabled only hides. beginFrame must precede native logic and SATS capture",
                limitations:["Cache requires native pixel mutations to advance the surface revision.",
                    "Same-value external visibility writes cannot be distinguished from this probe's writes.",
                    "Filtered ancestors and final pixels require the separate native-versus-probe pixel check."]};
        }
    }
}
