package tests {
    import flash.display.DisplayObject;
    import flash.utils.getQualifiedClassName;

    /** Terminal display-only diagnostic. Simulation is never skipped.
     * sample runs after the native tick and charges dt to the PREVIOUS installed
     * control, then reapplies the next control for the upcoming presentation.
     * Native visibility rewrites are observations, not identity failures.
     */
    public class SceneWorldLayerAttribution {
        public static const VERSION:String="world-layers-short-window-1";
        private static const MODES:Array=["all","no-fog","no-terrain","no-objects","no-world"];
        private static const LABELS:Array=["world","fog","front","back","back2","water",
            "objects-0","objects-1","objects-2","objects-3","objects-4","objects-5"];
        private static const MASKS:Array=[4095,4093,4035,63,4094];
        private var world:*,location:*,grafon:*,objectArray:*;
        private var layers:Array=[],parents:Array=[],original:Array=[],originalEffective:Array=[];
        private var effectiveControls:Array=[],order:Array=[],orderRows:Array=[];
        private var baselineMask:int=0,expectedMask:int=0;
        private var windowLength:int=30,cursor:int=0,windowIndex:int=0,windowFrame:int=0;
        private var expectedFrames:int=0,currentMode:int=0;
        private var started:Boolean=false,completed:Boolean=false,aborted:Boolean=false,closed:Boolean=false;
        private var lastChange:Boolean=false;
        private var invalidSamples:int=0,negativeResiduals:int=0;
        private var reassertFrames:int=0,reassertObservations:int=0,reassertWrites:int=0;
        private var reassertByLayer:Array=[0,0,0,0,0,0,0,0,0,0,0,0];
        private var reassertByControl:Array=[0,0,0,0,0];
        private var events:Array=[],startInfo:Object,cleanupInfo:Object;

        public function get done():Boolean{return completed || aborted;}
        public function get totalFrames():int{return expectedFrames;}
        public function get startReport():Object{return startInfo;}

        public function start(w:*,windowFrames:int=30,balancedPairs:int=1):Object {
            if(started)throw new Error("World layer attribution requires a fresh instance");
            if(windowFrames<2 || balancedPairs<1 || balancedPairs>20)
                throw new Error("Invalid world layer attribution window/cycle count");
            if(!w || !w.loc || !w.grafon || !w.grafon.visObjs || w.grafon.visObjs.length!=6)
                throw new Error("World layer attribution requires six native object layers");
            world=w;location=w.loc;grafon=w.grafon;objectArray=grafon.visObjs;
            var selected:Array=currentLayers(w),details:Array=[];
            for(var i:int=0;i<selected.length;++i) {
                var layer:DisplayObject=selected[i] as DisplayObject;
                if(!layer || !layer.parent || layers.indexOf(layer)>=0)
                    throw new Error("Missing, detached or duplicate world layer "+LABELS[i]);
                layers.push(layer);parents.push(layer.parent);original.push(layer.visible);
                originalEffective.push(isEffectivelyVisible(layer));
                if(layer.visible)baselineMask|=1<<i;
                details.push({index:i,label:LABELS[i],name:layer.name,type:getQualifiedClassName(layer),
                    parentName:layer.parent.name,parentType:getQualifiedClassName(layer.parent),
                    visible:layer.visible,effectiveVisible:originalEffective[i]});
            }
            effectiveControls=[originalEffective[0],originalEffective[1],
                anyEffective(2,6),anyEffective(6,12),originalEffective[0]];
            var ineffective:Array=[];
            for(i=0;i<5;++i)if(!effectiveControls[i])ineffective.push(MODES[i]);
            windowLength=windowFrames;
            var base:Array=[0,1,4,2,3];
            for(var cycle:int=0;cycle<balancedPairs;++cycle)for(var shift:int=0;shift<5;++shift) {
                var forward:Array=[];
                for(i=0;i<5;++i)forward.push((int(base[i])+shift)%5);
                appendRow(forward);appendRow(forward.concat().reverse());
            }
            expectedFrames=order.length*windowLength;expectedMask=baselineMask;started=true;
            startInfo={version:VERSION,diagnosticOnly:true,performanceAcceptance:false,
                windowFrames:windowLength,cycles:balancedPairs,rounds:orderRows.length,
                plannedWindows:order.length,plannedFrames:expectedFrames,orderRows:copyRows(),
                originalVisible:original.concat(),originalVisibleMask:baselineMask,
                originalEffectiveVisible:originalEffective.concat(),layers:details,
                controls:MODES.concat(),effectiveControls:effectiveControls.concat(),ineffectiveControls:ineffective,
                controlMeaning:"Restore baseline flags, then hide only the named group; all simulation continues",
                layerIdentityRule:"Initial world, location, grafon, object array, 12 layer references and direct parents must remain identical",
                balance:"Ten rows of five windows balance positions and ordered pairs within rows; forward/reverse rows alternate",
                timing:"dt belongs to the previously installed control; dtMinusNativeBand is not renderer CPU",
                visibilityGuard:"Native visibility rewrites are counted and reasserted at every sample; later writes before presentation cannot be observed",
                transitionRule:"First sample of each window is excluded; baseline-hidden controls are not attribution-eligible"};
            try{install(int(order[0]),0);}
            catch(error:Error){aborted=true;clear();throw error;}
            return startInfo;
        }

        private function currentLayers(w:*):Array {
            var g:*=w.grafon;
            var result:Array=[w.visual,g.visLight,g.visFront,g.visBack,g.visBack2,g.visVoda];
            if(g.visObjs)for(var i:int=0;i<g.visObjs.length && i<6;++i)result.push(g.visObjs[i]);
            return result;
        }
        private function isEffectivelyVisible(layer:DisplayObject):Boolean {
            for(var node:DisplayObject=layer;node;node=node.parent)if(!node.visible)return false;
            return true;
        }
        private function anyEffective(first:int,end:int):Boolean {
            for(var i:int=first;i<end;++i)if(originalEffective[i])return true;
            return false;
        }
        private function appendRow(ids:Array):void {
            var names:Array=[];
            for each(var id:int in ids){order.push(id);names.push(MODES[id]);}
            orderRows.push(names);
        }
        private function copyRows():Array {
            var result:Array=[];
            for each(var row:Array in orderRows)result.push(row.concat());
            return result;
        }

        public function sample(w:*,dt:Number,nativeBand:Number):Object {
            if(!started || done || closed)throw new Error("World layer attribution is not sampling");
            var issues:Array=inspect(w),observed:int=visibleMask(),rewriteMask:int=observed^expectedMask;
            var rewriteCount:int=0;
            for(var i:int=0;i<12;++i)if((rewriteMask&(1<<i))!=0){++rewriteCount;++reassertByLayer[i];}
            if(rewriteCount){++reassertFrames;reassertObservations+=rewriteCount;reassertByControl[currentMode]+=rewriteCount;}
            var numeric:Boolean=isFinite(dt) && isFinite(nativeBand) && dt>=0 && nativeBand>=0;
            var residual:Number=dt-nativeBand,transition:Boolean=windowFrame==0;
            var effective:Boolean=Boolean(effectiveControls[currentMode]);
            var row:Object={frame:cursor,window:windowIndex,round:int(windowIndex/5),position:windowIndex%5,
                frameInWindow:windowFrame,rowStart:windowIndex%5==0 && transition,
                control:issues.length?"unknown":MODES[currentMode],expectedControl:MODES[currentMode],
                previousVisibleMask:expectedMask,observedVisibleMask:observed,
                visibilityRewriteMask:rewriteMask,visibilityRewrites:rewriteCount,reassertCount:0,
                transition:transition,visibilityChanged:transition && lastChange,
                controlEffective:effective,baselineEligible:effective,
                dt:dt,currentNativeBand:nativeBand,dtMinusNativeBand:residual,
                eligible:numeric && residual>=0 && !transition && issues.length==0 && effective,
                issues:issues,appliedNext:null,nextTransition:false,done:false};
            ++cursor;
            if(!numeric){issues.push({kind:"invalid-timing",dt:dt,currentNativeBand:nativeBand});row.eligible=false;}
            if(numeric && residual<0){++negativeResiduals;row.eligible=false;}
            if(issues.length) {
                ++invalidSamples;aborted=true;events.push({frame:cursor-1,window:windowIndex,issues:issues});
                row.done=true;row.aborted=true;row.cleanup=clear();return row;
            }
            ++windowFrame;
            var next:int=currentMode;
            if(windowFrame==windowLength) {
                windowFrame=0;++windowIndex;
                if(windowIndex==order.length){completed=true;row.done=true;row.cleanup=clear();return row;}
                next=int(order[windowIndex]);row.nextTransition=true;
            }
            try{row.reassertCount=install(next,rewriteMask);}
            catch(error:Error) {
                aborted=true;row.eligible=false;
                events.push({frame:cursor-1,kind:"apply-failed",message:error.message});
                row.done=true;row.aborted=true;row.cleanup=clear();return row;
            }
            row.appliedNext=MODES[currentMode];row.nextVisibleMask=expectedMask;
            return row;
        }

        /** Count a reassert write only when a native rewrite is actually undone;
         * a planned mode change that agrees with the new native value is free. */
        private function install(id:int,rewriteMask:int):int {
            var desired:int=baselineMask&int(MASKS[id]);
            lastChange=desired!=expectedMask;
            var reapplied:int=0;
            for(var i:int=0;i<12;++i) {
                var value:Boolean=(desired&(1<<i))!=0;
                if(layers[i].visible!=value) {
                    layers[i].visible=value;
                    if((rewriteMask&(1<<i))!=0){++reapplied;++reassertWrites;}
                }
                if(value)expectedMask|=1<<i;else expectedMask&=~(1<<i);
            }
            currentMode=id;return reapplied;
        }
        private function visibleMask():int {
            var result:int=0;
            for(var i:int=0;i<layers.length;++i)if(layers[i].visible)result|=1<<i;
            return result;
        }
        private function inspect(w:*):Array {
            var issues:Array=[];
            if(!w || w!==world || w.loc!==location || w.grafon!==grafon) {
                issues.push({kind:"world-or-location-changed"});return issues;
            }
            if(grafon.visObjs!==objectArray)issues.push({kind:"object-array-replaced"});
            if(!grafon.visObjs || grafon.visObjs.length!=6)issues.push({kind:"object-layer-count-changed"});
            var current:Array=currentLayers(w);
            for(var i:int=0;i<12;++i) {
                if(i>=current.length || current[i]!==layers[i])issues.push({kind:"layer-replaced",layer:LABELS[i]});
                if(layers[i].parent!==parents[i])issues.push({kind:"layer-parent-changed",layer:LABELS[i]});
            }
            return issues;
        }

        /** This terminal diagnostic owns visibility until close. Restore the
         * original references even after a native rewrite; never edit replacements. */
        public function clear():Object {
            if(closed)return cleanupInfo;
            if(!started)return {started:false,restored:true};
            if(!completed && !aborted){aborted=true;events.push({frame:cursor,kind:"cleared-before-completion"});}
            var changes:Array=[],restored:Boolean=true;
            for(var i:int=0;i<layers.length;++i) {
                var layer:DisplayObject=layers[i] as DisplayObject;
                try {
                    var expected:Boolean=(expectedMask&(1<<i))!=0;
                    if(layer.visible!=expected)changes.push({kind:"cleanup-native-visible-rewrite",layer:LABELS[i],
                        expected:expected,actual:layer.visible,original:original[i]});
                    if(layer.visible!=original[i])layer.visible=original[i];
                    if(layer.visible!=original[i])restored=false;
                } catch(error:Error){restored=false;changes.push({kind:"cleanup-failed",layer:LABELS[i],message:error.message});}
            }
            closed=true;
            cleanupInfo={started:true,restored:restored,originalVisible:original.concat(),
                finalOriginalLayerMask:visibleMask(),changes:changes,replacementLayersUntouched:true};
            if(changes.length)events.push({frame:cursor,kind:"cleanup-observations",changes:changes});
            return cleanupInfo;
        }

        public function snapshot():Object {
            return {version:VERSION,diagnosticOnly:true,performanceAcceptance:false,
                started:started,done:done,complete:completed,aborted:aborted,closed:closed,
                sampledFrames:cursor,plannedFrames:expectedFrames,windowFrames:windowLength,
                windows:order.length,rounds:orderRows.length,invalidSamples:invalidSamples,
                negativeResidualSamples:negativeResiduals,reassertFrames:reassertFrames,
                reassertObservations:reassertObservations,reassertWrites:reassertWrites,
                reassertByLayer:reassertByLayer.concat(),reassertByControl:reassertByControl.concat(),
                startReport:startInfo,events:events.concat(),cleanup:cleanupInfo};
        }
    }
}
