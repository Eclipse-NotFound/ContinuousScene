package {
    import flash.desktop.NativeApplication;
    import flash.display.Stage;
    import flash.events.Event;
    import flash.filesystem.File;
    import flash.filesystem.FileMode;
    import flash.filesystem.FileStream;
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
    import flash.system.Capabilities;
    import flash.utils.getQualifiedClassName;
    import flash.utils.getTimer;

    /** Diagnostic addon. No game-class imports, sampled-object references or display edits.
     * Sampler API/lifecycle follows the successful capability probe and the
     * CPU-only re-review of combat-sampler-v3. Never a frame-rate benchmark.
     */
    public class ContinuousSceneTailSamplerMod {
        private static const LIMIT:int=100000;
        private static var stage:Stage;
        private static var output:File;
        private static var plan:Object;
        private static var report:Object;
        private static var current:Object;
        private static var heads:int=0,index:int=0;
        private static var initialized:Boolean=false,done:Boolean=false;
        private static var active:Boolean=false,ownsSampler:Boolean=false;
        private static var callbackInstalled:Boolean=false,overflowed:Boolean=false;
        private static var writeAllowed:Boolean=false;

        public static function init(host:*):void {
            var app:String=NativeApplication.nativeApplication.applicationID;
            if(!/^pfe-modsettings-continuous-motion-[0-9a-f]{32}$/.test(app))return;
            if(initialized)return;
            initialized=true;
            report={version:"camera-tail-sampling-1",applicationID:app,diagnosticOnly:true,
                performanceEligible:false,performanceAcceptance:false,deployed:false,
                complete:false,valid:false,windows:[],errors:[],saveMs:[],
                runtime:{version:Capabilities.version,playerType:Capabilities.playerType,
                    isDebugger:Capabilities.isDebugger},
                boundary:"This Stage's lowest-priority ENTER_FRAME listener to its next highest-priority listener; not all display-object broadcasts or pure rendering",
                listenerPriority:{head:2147483647,tail:-2147483648},
                limitations:["Equal-priority listeners run in registration order; an existing highest-priority callback may run before pause",
                    "CPU stack occurrences are not milliseconds, GPU time, all-thread CPU, draw counts or physical presentations",
                    "AS allocations remain sampled even with sampleInternalAllocs(false); observer overhead is not subtracted",
                    "Schedules are runtime getTimer values; the runner must intersect actual windows with completed workload intervals",
                    "Only CPU stack names/counts are retained; new/delete entries are counted without reading object references",
                    "This isolated diagnostic owns sampler state; it does not claim to restore an unreadable prior callback"]};
            try {
                plan=readPlan();
                require(plan.version=="camera-tail-sampling-plan-1" && plan.applicationID===app,
                    "Plan must match this exact application ID");
                var schedule:Array=plan.tailAtMs as Array;
                require(schedule!=null && schedule.length>0 && schedule.length<=4,"Expected 1..4 sparse windows");
                var previous:Number=-1000;
                for each(var value:* in schedule) {
                    require(typeof value=="number" && isFinite(value) && value==Math.floor(value)
                        && value>=1000 && value<=180000 && value-previous>=1000,"Invalid sparse schedule");
                    previous=Number(value);
                }
                output=File.applicationStorageDirectory.resolvePath("tail-sampler.json");
                require(!output.exists,"Refuse an existing addon result");
                writeAllowed=true;
                require(Capabilities.isDebugger,"Sampler requires the previously verified debugger runtime");
                stage=host.stage as Stage;
                require(stage!=null,"Host Stage unavailable");
                report.plan=plan;report.initializedAtMs=getTimer();
                report.stage={width:stage.stageWidth,height:stage.stageHeight,frameRate:stage.frameRate};
                stage.addEventListener(Event.ENTER_FRAME,onHead,false,2147483647);
                stage.addEventListener(Event.ENTER_FRAME,onTail,false,-2147483648);
                save();
            } catch(error:Error) {finish("init: "+error.message);}
        }

        private static function require(ok:Boolean,message:String):void {
            if(!ok)throw new Error(message);
        }

        private static function readPlan():Object {
            var stream:FileStream=new FileStream(),result:Object;
            var opened:Boolean=false;
            try {
                stream.open(File.applicationDirectory.resolvePath("tail-sampler-plan.json"),FileMode.READ);
                opened=true;
                require(stream.bytesAvailable<=8192,"Plan too large");
                result=JSON.parse(stream.readUTFBytes(stream.bytesAvailable));
            } finally {if(opened)stream.close();}
            return result;
        }

        // As in the existing sampler: runtime pauses before this callback and
        // resumes after it. Do not aggregate, log, or pretend stop persists here.
        private static function overflow():void {overflowed=true;clearSamples();}

        private static function onTail(event:Event):void {
            if(done || active || heads==0 || index>=plan.tailAtMs.length)return;
            if(getTimer()<Number(plan.tailAtMs[index]))return;
            try {
                require(event.currentTarget===stage,"Tail came from another Stage");
                overflowed=false;
                current={index:index,requestedAtMs:plan.tailAtMs[index],tailHeadSequence:heads,
                    startBeforeMs:null,startAfterMs:null,endBeforeMs:null,endAfterMs:null,
                    entries:{total:0,cpu:0,newObject:0,deleteObject:0,unknown:0},stacks:[],
                    cpuFirstUs:null,cpuLastUs:null,cpuNonMonotonic:0,cpuInvalidTimes:0,
                    overflow:false,errors:[],valid:false,attributionReady:false,cleanup:{},ownMs:{}};
                var began:int=getTimer();
                ownsSampler=true;
                clearSamples();
                require(getSampleCount()==0,"Sampler did not clear");
                sampleInternalAllocs(false);
                setSamplerCallback(overflow);callbackInstalled=true;
                current.startBeforeMs=getTimer();
                startSampling();active=true;
                current.startAfterMs=getTimer();
                current.ownMs.setupAndStart=getTimer()-began;
            } catch(error:Error) {finish("tail: "+error.message);}
        }

        private static function onHead(event:Event):void {
            if(done)return;
            ++heads;
            if(!active)return;
            try {
                current.endBeforeMs=getTimer();
                pauseSampling();active=false;
                current.endAfterMs=getTimer();
                current.ownMs.pause=int(current.endAfterMs)-int(current.endBeforeMs);
                current.headSequence=heads;
                current.intervalMs=int(current.endBeforeMs)-int(current.startAfterMs);
                require(event.currentTarget===stage && heads==int(current.tailHeadSequence)+1,
                    "Window did not end at the next head");
                current.overflow=overflowed;
                require(!overflowed,"Overflow discarded samples");
                var began:int=getTimer();
                try {aggregate();}
                finally {current.ownMs.aggregate=getTimer()-began;}
            } catch(error:Error) {current.errors.push("head: "+error.message);}
            finally {release();}
            current.valid=current.errors.length==0 &&
                current.entries.unknown==0 && current.cpuNonMonotonic==0 && current.cpuInvalidTimes==0 &&
                current.entries.total==current.reportedEntries && current.cleanup.stopped===true &&
                current.cleanup.cleared===true && current.cleanup.callbackCleared===true;
            current.attributionReady=current.valid && current.entries.cpu>0;
            report.windows.push(current);
            var valid:Boolean=current.valid;
            current=null;++index;
            if(!valid)finish("Invalid sampled window");
            else if(index==plan.tailAtMs.length)finish();
            else save();
        }

        private static function aggregate():void {
            var count:Number=getSampleCount();
            current.reportedEntries=count;
            require(isFinite(count) && count>=0 && count<LIMIT,"Sample count reached 100000 limit");
            var iterator:Object=null,sample:Sample=null,frame:StackFrame=null;
            var names:Array=null,byStack:Object={},key:String;
            var previousCPU:Number=NaN,stamp:Number;
            try {
                iterator=getSamples();
                if(iterator==null && count==0)return;
                require(iterator!=null,"Sample iterator unavailable with nonzero count");
                for each(sample in iterator) {
                    require(current.entries.total<LIMIT-1,"Enumeration reached limit");
                    current.entries.total=Number(current.entries.total)+1;
                    if(sample is NewObjectSample) {
                        current.entries.newObject=Number(current.entries.newObject)+1;continue;
                    }
                    if(sample is DeleteObjectSample) {
                        current.entries.deleteObject=Number(current.entries.deleteObject)+1;continue;
                    }
                    if(getQualifiedClassName(sample)!="flash.sampler::Sample") {
                        current.entries.unknown=Number(current.entries.unknown)+1;continue;
                    }
                    current.entries.cpu=Number(current.entries.cpu)+1;
                    stamp=sample.time;
                    if(!isFinite(stamp) || stamp<=0)
                        current.cpuInvalidTimes=Number(current.cpuInvalidTimes)+1;
                    if(!isNaN(previousCPU) && stamp<previousCPU)
                        current.cpuNonMonotonic=Number(current.cpuNonMonotonic)+1;
                    if(current.cpuFirstUs==null)current.cpuFirstUs=stamp;
                    current.cpuLastUs=stamp;previousCPU=stamp;
                    names=[];
                    if(sample.stack!=null)for each(frame in sample.stack)
                        names.push(frame.name==null?"":String(frame.name));
                    key="$"+JSON.stringify(names);
                    if(!byStack.hasOwnProperty(key))byStack[key]={names:names,samples:0};
                    byStack[key].samples=Number(byStack[key].samples)+1;
                }
                for(key in byStack)current.stacks.push(byStack[key]);
                current.stacks.sortOn("samples",Array.NUMERIC|Array.DESCENDING);
            } finally {
                // Retain only strings/counts, never Sample/StackFrame/iterator or
                // allocated/deleted object references after stopping the stream.
                sample=null;frame=null;iterator=null;names=null;byStack=null;
            }
        }

        private static function release():void {
            if(!ownsSampler)return;
            var began:int=getTimer(),errors:Array=current?current.errors:report.errors;
            var result:Object=current?current.cleanup:{};
            try {stopSampling();result.stopped=true;}
            catch(error:Error) {errors.push("stopSampling: "+error.message);}
            active=false;
            try {clearSamples();result.cleared=true;}
            catch(clearError:Error) {errors.push("clearSamples: "+clearError.message);}
            if(callbackInstalled) {
                try {setSamplerCallback(null);callbackInstalled=false;result.callbackCleared=true;}
                catch(callbackError:Error) {errors.push("clear callback: "+callbackError.message);}
            } else result.callbackCleared=true;
            ownsSampler=false;
            if(current)current.ownMs.release=getTimer()-began;
            report.lastCleanup=result;
        }

        private static function save():void {
            if(!writeAllowed)return;
            var began:int=getTimer(),stream:FileStream=new FileStream();
            var opened:Boolean=false;
            try {
                stream.open(output,FileMode.WRITE);
                opened=true;
                stream.writeUTFBytes(JSON.stringify(report,null,2));
            } catch(error:Error) {report.errors.push("save: "+error.message);}
            finally {
                if(opened)try {stream.close();}
                catch(closeError:Error) {report.errors.push("close: "+closeError.message);}
            }
            // A save reports preceding writes; the final save's own duration
            // cannot be included in itself without another unbounded write.
            report.saveMs.push(getTimer()-began);
        }

        private static function finish(reason:String=null):void {
            if(done)return;
            if(reason!=null)report.errors.push(reason);
            release();
            if(current) {report.windows.push(current);current=null;}
            done=true;
            if(stage) {
                stage.removeEventListener(Event.ENTER_FRAME,onHead);
                stage.removeEventListener(Event.ENTER_FRAME,onTail);
            }
            report.complete=plan!=null && plan.tailAtMs is Array && index==plan.tailAtMs.length;
            report.valid=report.complete && report.errors.length==0;
            report.finishedAtMs=getTimer();report.listenersRemoved=true;
            report.active=false;report.callbackInstalled=callbackInstalled;
            save();
        }
    }
}
