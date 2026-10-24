package {
    import flash.desktop.NativeApplication;
    import flash.display.Sprite;
    import flash.events.TimerEvent;
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
    import flash.sampler.startSampling;
    import flash.sampler.stopSampling;
    import flash.system.Capabilities;
    import flash.utils.getQualifiedClassName;
    import flash.utils.getTimer;
    import flash.utils.Timer;

    /** Standalone capability check. No game classes, loader, or global settings. */
    public class SamplerCapabilityProbe extends Sprite {
        private var timer:Timer;
        private var batches:uint=0;
        private var sink:Number=0;
        public function SamplerCapabilityProbe() {
            timer=new Timer(100,1);
            timer.addEventListener(TimerEvent.TIMER_COMPLETE,run);
            timer.start();
        }
        public function knownHotLoop(duration:int):Number {
            var began:int=getTimer(),value:Number=1.234567;
            do {
                for(var i:int=0;i<4096;i++)value=(value*1.000000119+0.000021)%8191;
                ++batches;
            } while(getTimer()-began<duration);
            sink=value;
            return value;
        }
        private function stackOf(sample:Sample):Array {
            var out:Array=[];
            if(sample.stack!=null)for each(var frame:StackFrame in sample.stack) {
                out.push({name:frame.name,file:frame.file,line:frame.line});
                if(out.length==12)break;
            }
            return out;
        }
        private function run(event:TimerEvent):void {
            timer.removeEventListener(TimerEvent.TIMER_COMPLETE,run);
            timer.stop();timer=null;
            var out:Object={version:"sampler-capability-1",status:"error",supported:false,
                compilerDebug:false,gameLoaded:false,performanceEligible:false,
                applicationID:NativeApplication.nativeApplication.applicationID,
                runtime:{version:Capabilities.version,playerType:Capabilities.playerType,isDebugger:Capabilities.isDebugger},
                counts:{cpu:0,newObject:0,deleteObject:0,unknown:0,total:0,namedCPU:0,knownHotLoopCPU:0},
                examples:{cpu:[],newObject:[],deleteObject:[],knownHotLoop:[]},
                cleanup:{paused:false,stopped:false},truncated:false};
            var stageName:String="configuration",stream:FileStream=null;
            try {
                if(out.applicationID.indexOf("cs-sampler-capability-")!=0)throw new Error("Owned standalone application required");
                stream=new FileStream();stream.open(File.applicationDirectory.resolvePath("probe-config.json"),FileMode.READ);
                var cfg:Object=JSON.parse(stream.readUTFBytes(stream.bytesAvailable));stream.close();stream=null;
                var duration:int=int(cfg.durationMs);
                if(duration<100 || duration>300)throw new Error("Expected 100..300 ms workload");
                // Warm JIT without sampling; measurement still calls this named method.
                knownHotLoop(20);batches=0;
                stageName="clearSamples";clearSamples();
                stageName="startSampling";startSampling();
                out.startTimerMs=getTimer();stageName="knownHotLoop";
                out.checksum=knownHotLoop(duration);out.batches=batches;out.iterations=Number(batches)*4096;
                out.loopElapsedMs=getTimer()-int(out.startTimerMs);out.requestedMs=duration;
                stageName="pauseSampling";pauseSampling();out.cleanup.paused=true;
                stageName="getSamples";out.reportedCount=getSampleCount();
                var samples:Object=getSamples();out.iteratorAvailable=samples!=null;
                var previous:Number=NaN,first:Number=NaN,last:Number=NaN,monotonic:Boolean=true;
                if(samples!=null)for each(var sample:Sample in samples) {
                    if(out.counts.total>=20000){out.truncated=true;break;}
                    ++out.counts.total;
                    if(isNaN(first))first=sample.time;
                    last=sample.time;
                    if(!isFinite(last) || last<=0 || (!isNaN(previous) && last<previous))monotonic=false;
                    previous=last;
                    var kind:String=sample is NewObjectSample?"newObject":sample is DeleteObjectSample?"deleteObject":
                        getQualifiedClassName(sample)=="flash.sampler::Sample"?"cpu":"unknown";
                    out.counts[kind]=Number(out.counts[kind])+1;
                    var names:Array=stackOf(sample),named:Boolean=false,hot:Boolean=false;
                    for each(var frame:Object in names) {
                        if(frame.name!=null && String(frame.name).length>0)named=true;
                        if(frame.name!=null && String(frame.name).indexOf("knownHotLoop")>=0)hot=true;
                    }
                    if(kind=="cpu") {
                        if(named)++out.counts.namedCPU;
                        if(hot)++out.counts.knownHotLoopCPU;
                        if(hot && out.examples.knownHotLoop.length<4)out.examples.knownHotLoop.push({time:sample.time,stack:names});
                    }
                    if(kind!="unknown" && out.examples[kind].length<3)out.examples[kind].push({time:sample.time,stack:names});
                }
                out.firstSampleTime=first;out.lastSampleTime=last;out.sampleTimeUnit="microseconds (raw runtime values)";
                out.sampleTimesValid=monotonic && out.counts.total>0;
                out.hotLoopExecuted=out.batches>0 && out.iterations>=4096 && isFinite(out.checksum) && out.loopElapsedMs>=duration;
                out.supported=out.hotLoopExecuted && !out.truncated && out.sampleTimesValid
                    && out.counts.cpu>0 && out.counts.namedCPU>0 && out.counts.knownHotLoopCPU>0 && out.counts.unknown==0;
                out.status=out.supported?"supported":"unsupported";
                if(!out.supported)out.reason="No usable named CPU sample of the executed knownHotLoop; API presence alone is insufficient";
            } catch(error:Error) {
                out.error={stage:stageName,message:error.message,errorID:error.errorID,stack:error.getStackTrace()};
                out.status=stageName=="configuration" || stageName=="knownHotLoop"?"error":"unsupported";
                out.supported=false;
            } finally {
                if(stream!=null)try{stream.close();}catch(closeError:Error){}
                try{stopSampling();out.cleanup.stopped=true;}catch(stopError:Error){out.cleanup.error=stopError.message;out.status="error";out.supported=false;}
            }
            // Sampling is stopped before JSON allocation or file I/O.
            try {
                File.applicationStorageDirectory.createDirectory();
                stream=new FileStream();stream.open(File.applicationStorageDirectory.resolvePath("result.json"),FileMode.WRITE);
                stream.writeUTFBytes(JSON.stringify(out));stream.close();stream=null;
                trace("sampler-capability "+out.status+" cpu="+out.counts.cpu+" hot="+out.counts.knownHotLoopCPU);
                NativeApplication.nativeApplication.exit(out.status=="error"?1:0);
            } catch(writeError:Error) {
                if(stream!=null)try{stream.close();}catch(finalCloseError:Error){}
                trace("sampler-capability result write failed: "+writeError.message);
                NativeApplication.nativeApplication.exit(2);
            }
        }
    }
}
