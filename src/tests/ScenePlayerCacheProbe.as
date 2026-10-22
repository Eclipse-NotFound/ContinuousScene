package tests {
    import flash.desktop.NativeApplication;
    import flash.display.BitmapData;
    import flash.display.DisplayObject;
    import flash.display.Stage;
    import flash.geom.Rectangle;
    import flash.utils.Dictionary;
    import flash.utils.getQualifiedClassName;

    /** Isolated diagnostic: only the player's existing visual root cache flag.
     * No wrapper, bitmap replacement, quality, animation or gameplay changes.
     * Child animation can invalidate the root cache every frame; this helper
     * does not assume that enabling the flag will improve performance.
     */
    public class ScenePlayerCacheProbe {
        private var record:Object;
        private var excluded:Dictionary = new Dictionary(true);
        private var safetyChecked:Boolean = false;
        private var safe:Boolean = false;
        private var updates:int = 0;
        private var enabledUpdates:int = 0;
        private var changed:int = 0;
        private var restored:int = 0;
        private var replacements:int = 0;
        private var conflictCount:int = 0;
        private var errorCount:int = 0;
        private var originalTrue:int = 0;
        private var originalFalse:int = 0;
        private var lastEnabled:Boolean = false;
        private var conflicts:Array = [];
        private var errors:Array = [];

        public function update(w:*, enabled:Boolean):void {
            ++updates;
            if(enabled) ++enabledUpdates;
            lastEnabled = enabled;
            try {
                if(!safetyChecked) {
                    safetyChecked = true;
                    safe = NativeApplication.nativeApplication.applicationID.indexOf("pfe-modsettings-continuous-motion-") == 0;
                }
                if(!safe) throw new Error("Player cache probe requires isolated motion storage");
                var visual:DisplayObject = w && w.gg ? w.gg.vis as DisplayObject : null;
                if(record && (!w || record.world !== w || record.location !== w.loc ||
                    record.player !== w.gg || record.visual !== visual || record.parent !== record.visual.parent)) {
                    ++replacements;
                    if(!restore("identity-change")) return;
                    record = null;
                }
                if(!w || !w.loc || !visual || !visual.parent) return;
                if(excluded[visual]) return;
                if(!record) {
                    // A native root filter automatically requests caching. Such
                    // a root is not a controllable false/true comparison.
                    if(visual.filters.length) {
                        conflict(visual,"root-filter-present-at-claim");
                        return;
                    }
                    var original:Boolean = visual.cacheAsBitmap;
                    record = {world:w,location:w.loc,player:w.gg,visual:visual,parent:visual.parent,
                        original:original,applied:false};
                    if(original) ++originalTrue; else ++originalFalse;
                }
                if(visual.filters.length) {
                    conflict(visual,"native-root-filter-changed");
                    // Restore the requested flag; filters may keep its public
                    // getter true. No filter value is changed by this helper.
                    if(restore("root-filter-change")) record = null;
                    return;
                }
                var expected:Boolean = record.applied ? true : Boolean(record.original);
                if(visual.cacheAsBitmap != expected) {
                    conflict(visual,"external-cache-write");
                    record.applied = false;
                    record = null;
                    return;
                }
                if(enabled && !record.original && !record.applied) {
                    // Save ownership before the write, so an exception remains
                    // recoverable by clear().
                    record.applied = true;
                    visual.cacheAsBitmap = true;
                    if(!visual.cacheAsBitmap) throw new Error("Player root rejected cache flag");
                    ++changed;
                } else if(!enabled) restore("control-window");
            } catch(error:Error) {
                fail("update",error);
                restore("update-error");
            }
        }

        public function clear():void {
            lastEnabled = false;
            if(restore("clear")) record = null;
        }

        public function snapshot():Object {
            var state:Object = null;
            if(record) {
                var visual:DisplayObject = record.visual as DisplayObject;
                state = {visualClass:getQualifiedClassName(visual),original:record.original,
                    current:visual.cacheAsBitmap,applied:record.applied,
                    rootFilterCount:visual.filters.length,parentStable:visual.parent === record.parent};
            }
            return {version:"player-root-cache-diagnostic-1",diagnosticOnly:true,performanceAcceptance:false,
                valid:safe && conflictCount == 0 && errorCount == 0,enabled:lastEnabled,
                updates:updates,enabledUpdates:enabledUpdates,changed:changed,restored:restored,
                replacements:replacements,originalTrue:originalTrue,originalFalse:originalFalse,
                pendingRestore:record && record.applied ? 1 : 0,
                conflicts:conflictCount,errors:errorCount,conflictDetails:conflicts.concat(),
                errorDetails:errors.concat(),state:state,
                limitations:[
                    "Only gg.vis.cacheAsBitmap is controlled; child filters and all native animation continue unchanged.",
                    "Animated descendants can dirty the cache every frame. No reuse or speed improvement is assumed.",
                    "External writes that keep the expected Boolean unchanged cannot be detected.",
                    "Timing must be collected separately from verify(), which allocates and reads pixels."
                ]};
        }

        /** Same synchronous frame, at the CURRENT real camera transform.
         * This compares BitmapData.draw(stage), not an OS-presented screenshot.
         * It is a single-pose oracle, not animation/zoom/lifecycle acceptance.
         * No native world step, timeline command or camera change occurs here.
         */
        public function verify(w:*):Object {
            var baseline:BitmapData, candidate:BitmapData, after:BitmapData;
            var result:Object = {version:"player-root-cache-pixel-1",diagnosticOnly:true,
                performanceAcceptance:false,valid:false,equal:false,restoredEqual:false,
                oracle:"Three BitmapData.draw(stage) captures in one synchronous frame: original, cached, original",
                limitations:["Current camera and animation pose only; no timeline advancement.",
                    "BitmapData.draw equality does not prove identical OS presentation or cached-frame performance."]};
            try {
                if(record && record.applied) throw new Error("verify requires an inactive cache probe");
                update(w,false);
                if(!snapshot().valid || !record || record.original) throw new Error("No uncached native player root for comparison");
                var stage:Stage = w.main.stage as Stage;
                if(!stage || stage.stageWidth < 1 || stage.stageHeight < 1 ||
                    stage.stageWidth > 4096 || stage.stageHeight > 2160) throw new Error("Unsupported pixel-check viewport");
                var visual:DisplayObject = record.visual as DisplayObject;
                result.view = {width:stage.stageWidth,height:stage.stageHeight,quality:stage.quality,
                    cameraScale:w.cam.scaleV,worldScaleX:w.visual.scaleX,worldScaleY:w.visual.scaleY,
                    worldX:w.visual.x,worldY:w.visual.y,playerX:visual.x,playerY:visual.y,
                    playerScaleX:visual.scaleX,playerScaleY:visual.scaleY,playerRotation:visual.rotation};
                baseline = capture(stage);
                update(w,true);
                if(!snapshot().valid || !record || !record.applied) throw new Error("Cache was not enabled for pixel comparison");
                candidate = capture(stage);
                update(w,false);
                if(!snapshot().valid || !record || record.applied || visual.cacheAsBitmap) throw new Error("Cache was not restored for pixel comparison");
                after = capture(stage);
                result.cached = compare(baseline,candidate);
                result.restored = compare(baseline,after);
                result.equal = result.cached.equal;
                result.restoredEqual = result.restored.equal;
                result.valid = snapshot().valid && result.restoredEqual;
            } catch(error:Error) { fail("verify",error); result.error = error.message; }
            finally {
                clear();
                if(baseline) baseline.dispose();
                if(candidate) candidate.dispose();
                if(after) after.dispose();
            }
            result.probe = snapshot();
            result.valid = result.valid && result.probe.valid && result.probe.pendingRestore == 0;
            return result;
        }

        private static function capture(stage:Stage):BitmapData {
            var pixels:BitmapData = new BitmapData(stage.stageWidth,stage.stageHeight,false,0);
            try { pixels.draw(stage); }
            catch(error:Error) { pixels.dispose(); throw error; }
            return pixels;
        }

        private static function compare(a:BitmapData,b:BitmapData):Object {
            var delta:* = a.compare(b);
            if(delta === 0) return {equal:true,changedPixels:0,maxChannelDifference:0,bounds:null};
            if(!(delta is BitmapData)) return {equal:false,compareCode:delta};
            var bounds:Rectangle = delta.getColorBoundsRect(0xFFFFFFFF,0,false);
            var count:int = 0,maxDifference:int = 0;
            try {
                for(var y:int = int(bounds.top); y < bounds.bottom; ++y) {
                    for(var x:int = int(bounds.left); x < bounds.right; ++x) {
                        var p:uint = a.getPixel32(x,y),q:uint = b.getPixel32(x,y);
                        if(p == q) continue;
                        ++count;
                        for(var shift:int = 0; shift < 32; shift += 8) {
                            var difference:int = Math.abs(int((p >>> shift) & 255)-int((q >>> shift) & 255));
                            if(difference > maxDifference) maxDifference = difference;
                        }
                    }
                }
            } finally { delta.dispose(); }
            return {equal:false,changedPixels:count,maxChannelDifference:maxDifference,
                bounds:{x:bounds.x,y:bounds.y,width:bounds.width,height:bounds.height}};
        }

        private function restore(reason:String):Boolean {
            if(!record || !record.applied) return true;
            var visual:DisplayObject = record.visual as DisplayObject;
            try {
                if(visual.cacheAsBitmap === true) {
                    visual.cacheAsBitmap = record.original;
                    // A native filter may require caching regardless of the
                    // requested flag, and is not ours to remove.
                    if(visual.cacheAsBitmap != record.original && visual.filters.length == 0)
                        throw new Error("Player cache restoration did not take effect");
                    ++restored;
                } else conflict(visual,"restore-observed-external-write:"+reason);
                record.applied = false;
                return true;
            } catch(error:Error) { fail("restore:"+reason,error); }
            return false;
        }

        private function conflict(visual:DisplayObject,reason:String):void {
            ++conflictCount; excluded[visual] = true;
            if(conflicts.length < 40) conflicts.push({reason:reason,update:updates,
                visualClass:getQualifiedClassName(visual),current:visual.cacheAsBitmap});
        }

        private function fail(where:String,error:Error):void {
            ++errorCount;
            if(errors.length < 40) errors.push({where:where,message:error.message,update:updates});
        }
    }
}
