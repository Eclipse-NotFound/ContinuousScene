package tests {
    import flash.sampler.Sample;
    import flash.sampler.NewObjectSample;
    import flash.sampler.DeleteObjectSample;
    import flash.sampler.StackFrame;
    import flash.sampler.clearSamples;
    import flash.sampler.getSampleCount;
    import flash.sampler.getSamples;
    import flash.sampler.pauseSampling;
    import flash.sampler.sampleInternalAllocs;
    import flash.sampler.setSamplerCallback;
    import flash.sampler.startSampling;
    import flash.sampler.stopSampling;
    import flash.utils.getQualifiedClassName;
    import flash.utils.getTimer;

    /** Test-only CPU stack attribution; never a frame-rate acceptance probe. */
    public final class SceneCameraSampler {
        private static const LIMIT:int=100000;
        private var current:Object=null;
        private var windows:Array=[];
        private var errors:Array=[];
        private var active:Boolean=false;
        private var overflowed:Boolean=false;
        private var callbackInstalled:Boolean=false;
        private var cleanupOK:Boolean=true;
        private var finished:Boolean=false;

        public function get sampling():Boolean {return active;}

        // The runtime pauses before this callback and resumes after it returns.
        // Never aggregate here or rely on stopSampling inside this callback.
        private function overflow():void {overflowed=true;clearSamples();}

        public function head(segment:int,age:int,name:String):void {
            if(finished || age<115 || age>119)return;
            if(age==115) {
                if(current!=null) {
                    errors.push("Previous sampler window was not completed");
                    complete(int(current.segment));
                }
                overflowed=false;
                current={segment:segment,name:name,firstAge:115,lastAge:119,headFrames:0,
                    valid:false,attributionReady:false,diagnosticOnly:true,performanceEligible:false,
                    startTimerBeforeMs:null,startTimerAfterMs:null,endTimerBeforeMs:null,endTimerAfterMs:null,
                    pausedAge:null,paused:false,stopped:false,callbackCleared:false,
                    overflow:false,overLimit:false,errors:[],counts:{total:0,cpu:0,newObject:0,deleteObject:0,unknown:0},
                    firstSampleTime:null,lastSampleTime:null,sampleTimesValid:false,
                    cpuExamples:[],recognizedExamples:{game:[],gameClass:[],realisticVision:[],continuousScene:[],fixture:[]},
                    categories:{emptyStack:0,anonymousTop:0,fullyAnonymous:0,game:0,gameClass:0,
                        realisticVision:0,continuousScene:0,fixture:0,flashAPI:0,nativeMarker:0,otherNamed:0},
                    top:[],stacks:[],inclusiveNames:[]};
                try {
                    clearSamples();
                    current.initialSampleCount=getSampleCount();
                    if(current.initialSampleCount!=0)throw new Error("Sampler did not clear before window");
                    sampleInternalAllocs(false);
                    setSamplerCallback(overflow);callbackInstalled=true;
                    current.startTimerBeforeMs=getTimer();
                    startSampling();active=true;
                    current.startTimerAfterMs=getTimer();
                } catch(error:*) {current.errors.push("start: "+String(error));release();}
            }
            if(current!=null && current.segment==segment) {
                current.headFrames=Number(current.headFrames)+1;
                current.lastObservedHeadAge=age;
            }
        }

        // Called before beginProbeTiming, heartbeat, and all ordinary tick work.
        // Age 119 has already executed its native/high-priority update once.
        public function beforeTick(segment:int,age:int):void {
            if(current==null || !active)return;
            if(overflowed || segment!=int(current.segment) || age==119) {
                current.endTimerBeforeMs=getTimer();
                try {pauseSampling();current.paused=true;}
                catch(error:*) {current.errors.push("pause: "+String(error));}
                finally {active=false;}
                current.endTimerAfterMs=getTimer();current.pausedAge=age;
                current.overflow=overflowed;
                if(overflowed)current.errors.push("Sample stream overflowed; callback cleared lost samples");
                if(segment!=int(current.segment))current.errors.push("Segment identity changed during sampling");
            }
        }

        private static function increment(map:Object,key:String):void {
            map[key]=map.hasOwnProperty(key)?Number(map[key])+1:1;
        }
        private static function nameRows(map:Object):Array {
            var out:Array=[];
            for(var key:String in map)out.push({name:key.substr(1),samples:map[key]});
            out.sortOn(["samples","name"],[Array.NUMERIC|Array.DESCENDING,0]);
            return out;
        }
        private static function example(target:Array,time:Number,names:Array):void {
            if(target.length<4)target.push({time:time,names:names});
        }

        // These diagnostics run only after pauseSampling, never in active frames.
        private static function rawTime(value:Number):* {
            return isFinite(value)?value:String(value);
        }
        private static function timeStats():Object {
            return {count:0,finite:0,positive:0,nonFinite:0,nonPositive:0,nonMonotonic:0,
                bad:0,maxBackward:0,min:null,max:null,firstTime:null,lastTime:null,
                lastType:null,lastIndex:null,badExamples:[]};
        }
        private static function recordTime(stats:Object,index:int,type:String,time:Number):Boolean {
            var hasPrevious:Boolean=stats.count>0;
            var previous:Number=hasPrevious?Number(stats.lastTime):NaN;
            var reason:String="",backward:Number=0;
            stats.count=Number(stats.count)+1;
            if(isFinite(time)) {
                stats.finite=Number(stats.finite)+1;
                if(stats.min==null || time<Number(stats.min))stats.min=time;
                if(stats.max==null || time>Number(stats.max))stats.max=time;
            } else {stats.nonFinite=Number(stats.nonFinite)+1;reason+="non-finite;";}
            if(time>0)stats.positive=Number(stats.positive)+1;
            if(time<=0){stats.nonPositive=Number(stats.nonPositive)+1;reason+="non-positive;";}
            if(hasPrevious && time<previous) {
                stats.nonMonotonic=Number(stats.nonMonotonic)+1;
                backward=previous-time;
                if(backward>Number(stats.maxBackward))stats.maxBackward=rawTime(backward);
                reason+="backward;";
            }
            if(reason.length>0) {
                stats.bad=Number(stats.bad)+1;
                if(stats.badExamples.length<8)stats.badExamples.push({index:index,type:type,
                    prevType:hasPrevious?stats.lastType:null,prevIndex:hasPrevious?stats.lastIndex:null,
                    prevTime:hasPrevious?stats.lastTime:null,time:rawTime(time),
                    delta:hasPrevious?rawTime(time-previous):null,reason:reason});
            }
            if(!hasPrevious)stats.firstTime=rawTime(time);
            stats.lastTime=rawTime(time);stats.lastType=type;stats.lastIndex=index;
            return reason.length>0;
        }

        private function aggregate():void {
            var reported:Number=getSampleCount();current.reportedSampleCount=reported;
            if(!isFinite(reported) || reported<0 || reported>=LIMIT) {
                current.overLimit=reported>=LIMIT;
                current.errors.push("Sample count invalid or reached 100000 limit");return;
            }
            var stream:Object=getSamples();current.iteratorAvailable=stream!=null;
            if(stream==null){current.errors.push("No sample iterator");return;}
            var top:Object={},stacks:Object={},inclusive:Object={};
            var newStacks:Object={},newTop:Object={},uniqueNewStacks:int=0;
            var first:Number=NaN,last:Number=NaN,previous:Number=NaN,timeOK:Boolean=true;
            var firstCPU:Number=NaN,lastCPU:Number=NaN;
            var counts:Object=current.counts,categories:Object=current.categories;
            current.timeDiagnostics={version:"sampler-time-diagnostics-1",global:timeStats(),
                byType:{cpu:timeStats(),newObject:timeStats(),deleteObject:timeStats(),unknown:timeStats()},
                globalBadByCurrentType:{cpu:0,newObject:0,deleteObject:0,unknown:0},
                cpuTimes:[],cpuGlobalIndices:[],
                nonFiniteEncoding:"NaN/Infinity/-Infinity strings preserve values JSON numbers cannot encode",
                ordering:"global compares adjacent iterator entries; byType compares adjacent entries of that type; indices are zero based"};
            for each(var sample:Sample in stream) {
                if(counts.total>=LIMIT-1) {
                    current.overLimit=true;current.errors.push("Enumeration reached 100000 limit");break;
                }
                counts.total=Number(counts.total)+1;
                if(isNaN(first))first=sample.time;
                last=sample.time;
                if(!isFinite(last) || last<=0 || (!isNaN(previous) && last<previous))timeOK=false;
                previous=last;
                var timeKind:String=sample is NewObjectSample?"newObject":sample is DeleteObjectSample?"deleteObject":
                    getQualifiedClassName(sample)=="flash.sampler::Sample"?"cpu":"unknown";
                var globalBad:Boolean=recordTime(current.timeDiagnostics.global,int(counts.total)-1,timeKind,last);
                recordTime(current.timeDiagnostics.byType[timeKind],int(counts.total)-1,timeKind,last);
                if(globalBad)current.timeDiagnostics.globalBadByCurrentType[timeKind]=
                    Number(current.timeDiagnostics.globalBadByCurrentType[timeKind])+1;
                // Only copied stack names are retained; never read sample.object, id, type or size.
                if(sample is NewObjectSample) {
                    counts.newObject=Number(counts.newObject)+1;
                    var allocationNames:Array=[];
                    if(sample.stack!=null)for each(var allocationFrame:StackFrame in sample.stack)
                        allocationNames.push(allocationFrame.name==null?"":String(allocationFrame.name));
                    var allocationKey:String="$"+JSON.stringify(allocationNames);
                    if(!newStacks.hasOwnProperty(allocationKey)) {
                        if(++uniqueNewStacks>4096)throw new Error("Allocation stack cardinality exceeded 4096");
                        newStacks[allocationKey]={names:allocationNames,samples:0};
                    }
                    newStacks[allocationKey].samples=Number(newStacks[allocationKey].samples)+1;
                    var allocationTop:String=allocationNames.length==0?"<empty-stack>":allocationNames[0].length==0?"<anonymous>":allocationNames[0];
                    increment(newTop,"$"+allocationTop);
                    continue;
                }
                if(sample is DeleteObjectSample){counts.deleteObject=Number(counts.deleteObject)+1;continue;}
                if(getQualifiedClassName(sample)!="flash.sampler::Sample") {
                    counts.unknown=Number(counts.unknown)+1;continue;
                }
                counts.cpu=Number(counts.cpu)+1;
                current.timeDiagnostics.cpuTimes.push(rawTime(last));
                current.timeDiagnostics.cpuGlobalIndices.push(int(counts.total)-1);
                if(isNaN(firstCPU))firstCPU=last;
                lastCPU=last;
                var names:Array=[],named:Boolean=false,game:Boolean=false,gameClass:Boolean=false;
                var rv:Boolean=false,cs:Boolean=false,fixture:Boolean=false,flashAPI:Boolean=false,nativeMarker:Boolean=false;
                var seen:Object={};
                if(sample.stack!=null)for each(var frame:StackFrame in sample.stack) {
                    var name:String=frame.name==null?"":String(frame.name),lower:String=name.toLowerCase();
                    names.push(name);
                    if(name.length>0) {
                        named=true;
                        if(!seen.hasOwnProperty("$"+name)){increment(inclusive,"$"+name);seen["$"+name]=true;}
                    }
                    if(name.indexOf("fe.")==0 || name.indexOf("fe::")==0)game=true;
                    if(name.indexOf("fe::Game/")==0 || name.indexOf("fe.Game/")==0)gameClass=true;
                    if(lower.indexOf("realisticvision")>=0)rv=true;
                    if(name.indexOf("tests::")==0 || name.indexOf("tests.")==0 ||
                        name.indexOf("ContinuousSceneMotionProbe/")==0)fixture=true;
                    else if(lower.indexOf("continuousscene")>=0 || lower.indexOf("nativescene")>=0)cs=true;
                    if(name.indexOf("flash.")==0 || name.indexOf("flash::")==0)flashAPI=true;
                    if(lower.indexOf("[native]")>=0)nativeMarker=true;
                }
                var firstName:String=names.length==0?"<empty-stack>":names[0].length==0?"<anonymous>":names[0];
                increment(top,"$"+firstName);
                var stackKey:String="$"+JSON.stringify(names);
                if(!stacks.hasOwnProperty(stackKey))stacks[stackKey]={names:names,samples:0};
                stacks[stackKey].samples=Number(stacks[stackKey].samples)+1;
                if(names.length==0)categories.emptyStack=Number(categories.emptyStack)+1;
                else if(names[0].length==0)categories.anonymousTop=Number(categories.anonymousTop)+1;
                if(!named)categories.fullyAnonymous=Number(categories.fullyAnonymous)+1;
                if(game){categories.game=Number(categories.game)+1;example(current.recognizedExamples.game,last,names);}
                if(gameClass){categories.gameClass=Number(categories.gameClass)+1;example(current.recognizedExamples.gameClass,last,names);}
                if(rv){categories.realisticVision=Number(categories.realisticVision)+1;example(current.recognizedExamples.realisticVision,last,names);}
                if(cs){categories.continuousScene=Number(categories.continuousScene)+1;example(current.recognizedExamples.continuousScene,last,names);}
                if(fixture){categories.fixture=Number(categories.fixture)+1;example(current.recognizedExamples.fixture,last,names);}
                if(flashAPI)categories.flashAPI=Number(categories.flashAPI)+1;
                if(nativeMarker)categories.nativeMarker=Number(categories.nativeMarker)+1;
                if(named && !game && !rv && !cs && !fixture && !flashAPI && !nativeMarker)categories.otherNamed=Number(categories.otherNamed)+1;
                if(current.cpuExamples.length<8)current.cpuExamples.push({time:last,names:names});
            }
            current.firstSampleTime=isNaN(first)?null:first;current.lastSampleTime=isNaN(last)?null:last;
            current.sampleTimesValid=timeOK && counts.total>0;
            current.enumerationMatchesCount=counts.total==reported;
            current.rawSampleSpanUs=isNaN(first) || isNaN(last)?null:last-first;
            current.firstCPUSampleTime=isNaN(firstCPU)?null:firstCPU;
            current.lastCPUSampleTime=isNaN(lastCPU)?null:lastCPU;
            current.rawCPUSampleSpanUs=isNaN(firstCPU) || isNaN(lastCPU)?null:lastCPU-firstCPU;
            current.windowWallMs=current.startTimerAfterMs==null || current.endTimerBeforeMs==null?null:
                Number(current.endTimerBeforeMs)-Number(current.startTimerAfterMs);
            current.newObjectTop=nameRows(newTop);current.newObjectStacks=[];
            for(var allocation:String in newStacks)current.newObjectStacks.push(newStacks[allocation]);
            current.newObjectStacks.sortOn("samples",Array.NUMERIC|Array.DESCENDING);
            current.top=nameRows(top);current.inclusiveNames=nameRows(inclusive);
            for(var key:String in stacks)current.stacks.push(stacks[key]);
            current.stacks.sortOn("samples",Array.NUMERIC|Array.DESCENDING);
        }

        // Always releases the stream even when iteration or stack access throws.
        private function release():void {
            try {stopSampling();if(current!=null)current.stopped=true;}
            catch(error:*) {cleanupOK=false;errors.push("stopSampling: "+String(error));}
            finally {
                active=false;
                if(callbackInstalled) {
                    try {setSamplerCallback(null);callbackInstalled=false;if(current!=null)current.callbackCleared=true;}
                    catch(callbackError:*) {cleanupOK=false;errors.push("clear callback: "+String(callbackError));}
                }
            }
        }

        public function complete(segment:int):Object {
            if(current==null)return null;
            var result:Object=current,aggregationStart:int=getTimer();
            try {
                if(active) {
                    beforeTick(segment,-1);
                    if(active){pauseSampling();active=false;current.paused=true;}
                    current.errors.push("Window ended before expected age 119 pause");
                }
                if(segment!=int(current.segment))current.errors.push("Wrong segment passed to complete");
                current.overflow=overflowed;
                if(!overflowed)aggregate();
            } catch(error:*) {current.errors.push("aggregate: "+String(error));}
            finally {release();}
            current.aggregationMs=getTimer()-aggregationStart;
            current.valid=current.errors.length==0 && !current.overflow && !current.overLimit &&
                current.paused && current.stopped && current.callbackCleared && current.headFrames==5 &&
                current.pausedAge==119 && current.lastObservedHeadAge==119 && current.timeDiagnostics!=null && current.timeDiagnostics.byType.cpu.bad==0 &&
                current.enumerationMatchesCount && current.counts.unknown==0;
            current.attributionReady=current.valid && current.counts.cpu>0 && current.categories.game>0;
            windows.push(current);current=null;
            return result;
        }

        public function finish():Object {
            try {if(current!=null)complete(int(current.segment));}
            finally {release();finished=true;}
            var valid:Boolean=cleanupOK && errors.length==0 && windows.length==8,gamePositive:Boolean=true;
            for(var i:int=0;i<windows.length;++i) {
                valid=valid && windows[i].valid && windows[i].segment==i;
                gamePositive=gamePositive && windows[i].attributionReady;
            }
            return {version:"room-camera-allocation-sampler-1",diagnosticOnly:true,performanceEligible:false,
                valid:valid,attributionReady:valid && gamePositive,incomplete:!valid,
                windows:windows,errors:errors,cleanup:{stopped:cleanupOK,callbackCleared:!callbackInstalled,active:active},
                sampleLimitPerWindow:LIMIT,sampleTimeUnit:"microseconds (raw runtime clock)",internalAllocations:false,
                boundary:"Before applying camera age115 through next helper entry after age119: five outgoing camera/render intervals, with intervening native updates. Mixed allocation/CPU iterator order is recorded, not used as a CPU clock.",
                limitations:["CPU sample stack occurrences are not milliseconds or complete wall-time/render/GPU accounting",
                    "CPU first/last times and counts expose sparse coverage; fe.* presence alone does not establish full interval coverage",
                    "AS allocations remain sampled; only copied new-object stack names are aggregated after pause; no live objects, IDs, types or sizes are read",
                    "Sample cap is not a memory bound; overflow discards samples and invalidates the entire diagnostic",
                    "Category labels are raw-name heuristics; complete stack names remain available for review",
                    "nativeMarker only counts literal [native] names; anonymous and flash API names are not proof of native render time",
                    "Sampler global state is owned by this isolated process; no prior sampler callback or allocation setting is claimed restored"]};
        }
    }
}
