package tests {
    import flash.display.DisplayObject;

    /** Terminal diagnostic only. This deliberately hides game content.
     *
     * Call start after the native tick, then sample ONCE per subsequent frame
     * at the same probe phase. dt spans the previous probe to this probe;
     * nativeBand belongs to the CURRENT native tick. sample attributes dt to
     * the control installed by the PREVIOUS call, before applying the next
     * control. Never call sample on the same frame as start.
     *
     * dtMinusNativeBand is NOT renderer CPU: it still includes other script,
     * the previous probe tail, frame pacing, presentation and scheduling.
     * The caller should separately retain currentScriptBeforeProbe and raw dt.
     * No frame listeners, world updates, child enumeration or pixel reads occur
     * here. Only the six visObjs layer.visible values may be changed.
     */
    public class SceneDisplayAttribution {
        public static const VERSION:String = "short-window-display-1";
        private static const MODES:Array = ["all", "none", "boxes", "units", "effects"];
        private static const MASKS:Array = [63, 0, 3, 4, 56];

        private var world:*, location:*, grafon:*, layerArray:*;
        private var layers:Array = [];
        private var parents:Array = [];
        private var original:Array = [];
        private var baselineMask:int = 0;
        private var expectedMask:int = 0;
        private var order:Array = [];
        private var orderRows:Array = [];
        private var windowLength:int = 30;
        private var cursor:int = 0;
        private var windowIndex:int = 0;
        private var windowFrame:int = 0;
        private var expectedFrames:int = 0;
        private var currentMode:int = 0;
        private var lastChange:Boolean = false;
        private var started:Boolean = false;
        private var completed:Boolean = false;
        private var aborted:Boolean = false;
        private var closed:Boolean = false;
        private var invalidSamples:int = 0;
        private var negativeResiduals:int = 0;
        private var events:Array = [];
        private var startInfo:Object;
        private var cleanupInfo:Object;

        public function get done():Boolean { return completed || aborted; }
        public function get totalFrames():int { return expectedFrames; }
        public function get startReport():Object { return startInfo; }

        /** One balancedPairs cycle is ten rows of five windows (1500 frames).
         * For five controls, a Williams row and its reverse together cover
         * both directions of carry-over. Five label rotations balance every
         * control across positions and every ordered pair within rows.
         * Adjacent forward/reverse rows also balance linear drift locally.
         */
        public function start(w:*, windowFrames:int = 30, balancedPairs:int = 1):Object {
            if(started) throw new Error("SceneDisplayAttribution requires a fresh instance per run");
            if(windowFrames < 2 || balancedPairs < 1 || balancedPairs > 20)
                throw new Error("Invalid display attribution window/cycle count");
            if(!w || !w.loc || !w.grafon || !w.grafon.visObjs || w.grafon.visObjs.length != 6)
                throw new Error("Display attribution requires exactly six native object layers");
            world = w; location = w.loc; grafon = w.grafon; layerArray = grafon.visObjs;
            windowLength = windowFrames;
            for(var i:int = 0; i < 6; ++i) {
                var layer:DisplayObject = layerArray[i] as DisplayObject;
                if(!layer || !layer.parent || layers.indexOf(layer) >= 0)
                    throw new Error("Missing, detached or duplicate object layer " + i);
                layers.push(layer); parents.push(layer.parent); original.push(layer.visible);
                if(layer.visible) baselineMask |= 1 << i;
            }
            var base:Array = [0, 1, 4, 2, 3];
            for(var cycle:int = 0; cycle < balancedPairs; ++cycle) {
                for(var shift:int = 0; shift < 5; ++shift) {
                    var forward:Array = [];
                    for(i = 0; i < 5; ++i) forward.push((int(base[i]) + shift) % 5);
                    appendRow(forward);
                    appendRow(forward.concat().reverse());
                }
            }
            expectedFrames = order.length * windowLength;
            expectedMask = baselineMask;
            started = true;
            startInfo = {
                version:VERSION, diagnosticOnly:true, performanceAcceptance:false,
                windowFrames:windowLength, cycles:balancedPairs, rounds:orderRows.length,
                plannedWindows:order.length, plannedFrames:expectedFrames,
                orderRows:copyRows(), originalVisible:original.concat(), originalVisibleMask:baselineMask,
                layerIdentityRule:"The six initial DisplayObject references and their parents must remain identical",
                controls:{all:[0,1,2,3,4,5], none:[], boxes:[0,1], units:[2], effects:[3,4,5]},
                controlMeaning:"Show only listed layers, intersected with original visible values",
                balance:"Each 10-row cycle balances positions and all ordered pairs within rows; row boundaries are recorded separately",
                timing:"dt is assigned to the previously installed control; dtMinusNativeBand is only a residual, not render CPU",
                visibilityGuard:"Detects net external visible changes at sample boundaries; transient changes that are restored between samples cannot be observed",
                transitionRule:"First sample in every " + windowLength + "-frame window is marked transition and excluded from eligible samples"
            };
            try { install(int(order[0])); }
            catch(error:Error) { aborted = true; clear(); throw error; }
            return startInfo;
        }

        private function appendRow(ids:Array):void {
            var names:Array = [];
            for each(var id:int in ids) { order.push(id); names.push(MODES[id]); }
            orderRows.push(names);
        }

        private function copyRows():Array {
            var result:Array = [];
            for each(var row:Array in orderRows) result.push(row.concat());
            return result;
        }

        /** Does not keep duplicate per-frame arrays; retain the returned row in
         * the calling probe. Finishing the last sample automatically restores.
         */
        public function sample(w:*, dt:Number, nativeBand:Number):Object {
            if(!started || done || closed) throw new Error("Display attribution is not sampling");
            var issues:Array = inspect(w);
            var observed:int = visibleMask();
            var numeric:Boolean = isFinite(dt) && isFinite(nativeBand) && dt >= 0 && nativeBand >= 0;
            var residual:Number = dt - nativeBand;
            var transition:Boolean = windowFrame == 0;
            var row:Object = {
                frame:cursor, window:windowIndex, round:int(windowIndex / 5), position:windowIndex % 5,
                frameInWindow:windowFrame, rowStart:windowIndex % 5 == 0 && transition,
                control:issues.length ? "unknown" : MODES[currentMode], expectedControl:MODES[currentMode],
                previousVisibleMask:expectedMask, observedVisibleMask:observed,
                transition:transition, visibilityChanged:transition && lastChange,
                dt:dt, currentNativeBand:nativeBand, dtMinusNativeBand:residual,
                eligible:numeric && residual >= 0 && !transition && issues.length == 0,
                issues:issues, appliedNext:null, nextTransition:false, done:false
            };
            ++cursor;
            if(!numeric) {
                issues.push({kind:"invalid-timing", dt:dt, currentNativeBand:nativeBand});
                row.eligible = false;
            }
            if(numeric && residual < 0) { ++negativeResiduals; row.eligible = false; }
            if(issues.length) {
                ++invalidSamples; aborted = true;
                events.push({frame:cursor - 1, window:windowIndex, issues:issues});
                row.done = true; row.aborted = true; row.cleanup = clear();
                return row;
            }
            ++windowFrame;
            if(windowFrame == windowLength) {
                windowFrame = 0; ++windowIndex;
                if(windowIndex == order.length) {
                    completed = true; row.done = true; row.cleanup = clear();
                    return row;
                }
                try { install(int(order[windowIndex])); }
                catch(error:Error) {
                    aborted = true;
                    events.push({frame:cursor - 1, kind:"apply-failed", message:error.message});
                    row.done = true; row.aborted = true; row.cleanup = clear();
                    return row;
                }
                row.nextTransition = true;
            }
            row.appliedNext = MODES[currentMode];
            row.nextVisibleMask = expectedMask;
            return row;
        }

        private function install(id:int):void {
            var desired:int = baselineMask & int(MASKS[id]);
            lastChange = desired != expectedMask;
            // Do not touch unchanged values or any descendant display object.
            for(var i:int = 0; i < 6; ++i) {
                var value:Boolean = (desired & (1 << i)) != 0;
                if(layers[i].visible != value) layers[i].visible = value;
                // Track each completed write, including a partial apply failure.
                if(value) expectedMask |= 1 << i; else expectedMask &= ~(1 << i);
            }
            currentMode = id;
        }

        private function visibleMask():int {
            var result:int = 0;
            for(var i:int = 0; i < layers.length; ++i) if(layers[i].visible) result |= 1 << i;
            return result;
        }

        private function inspect(w:*):Array {
            var issues:Array = [];
            if(w !== world || !w || w.loc !== location || w.grafon !== grafon) {
                issues.push({kind:"world-or-location-changed"}); return issues;
            }
            var current:* = grafon.visObjs;
            if(current !== layerArray) issues.push({kind:"layer-array-replaced"});
            if(!current || current.length != 6) issues.push({kind:"layer-count-changed"});
            for(var i:int = 0; i < 6; ++i) {
                if(!current || current.length <= i || current[i] !== layers[i])
                    issues.push({kind:"layer-replaced", layer:i});
                if(layers[i].parent !== parents[i]) issues.push({kind:"layer-parent-changed", layer:i});
                var expected:Boolean = (expectedMask & (1 << i)) != 0;
                if(layers[i].visible != expected)
                    issues.push({kind:"external-visible-change", layer:i, expected:expected, actual:layers[i].visible});
            }
            return issues;
        }

        /** Idempotent; never resets done/completed. Restore only values still
         * owned by this helper. Conflicting external writes are reported and
         * left untouched. Rebuilt replacement layers were never ours to edit.
         */
        public function clear():Object {
            if(closed) return cleanupInfo;
            if(!started) return {started:false, restored:true};
            if(!completed && !aborted) {
                aborted = true; events.push({frame:cursor, kind:"cleared-before-completion"});
            }
            var changes:Array = [], restored:Boolean = true;
            for(var i:int = 0; i < layers.length; ++i) {
                var layer:DisplayObject = layers[i] as DisplayObject;
                var expected:Boolean = (expectedMask & (1 << i)) != 0;
                try {
                    if(layer.visible != expected) {
                        changes.push({kind:"cleanup-external-visible", layer:i, expected:expected,
                            actual:layer.visible, original:original[i]});
                    } else if(layer.visible != original[i]) layer.visible = original[i];
                    if(layer.visible != original[i]) restored = false;
                } catch(error:Error) {
                    restored = false; changes.push({kind:"cleanup-failed", layer:i, message:error.message});
                }
            }
            closed = true;
            cleanupInfo = {started:true, restored:restored, originalVisible:original.concat(),
                finalOriginalLayerMask:visibleMask(), changes:changes, replacementLayersUntouched:true};
            if(changes.length) events.push({frame:cursor, kind:"cleanup-observations", changes:changes});
            return cleanupInfo;
        }

        public function snapshot():Object {
            return {version:VERSION, diagnosticOnly:true, performanceAcceptance:false,
                started:started, done:done, complete:completed, aborted:aborted, closed:closed,
                sampledFrames:cursor, plannedFrames:expectedFrames, windowFrames:windowLength,
                windows:order.length, rounds:orderRows.length, invalidSamples:invalidSamples,
                negativeResidualSamples:negativeResiduals, startReport:startInfo,
                events:events.concat(), cleanup:cleanupInfo};
        }
    }
}
