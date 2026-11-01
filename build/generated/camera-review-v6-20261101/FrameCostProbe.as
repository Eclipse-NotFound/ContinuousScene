package {
    import flash.sampler.*;
    import flash.system.System;
    import flash.utils.getTimer;
    import flash.utils.getQualifiedClassName;

    /** Read-only, bounded diagnostic. Never used for performance acceptance. */
    public class FrameCostProbe {
        private static var report:Object={version:1,diagnosticOnly:true,memoryBench:[],windows:[],errors:[],memoryEnabled:false};
        private static var active:Boolean=false,overflowed:Boolean=false;
        private static var window:Object;
        public static function prepare():void {
            var keys:Array=["empty","total","free","private"];
            var totalCost:int=0,maxTotal:int=0;
            for(var pass:int=0;pass<16;++pass)for(var step:int=0;step<4;++step) {
                var key:String=keys[(step+pass)%4],began:int=getTimer(),value:Number=0;
                if(key=="total")value=System.totalMemoryNumber;
                else if(key=="free")value=System.freeMemory;
                else if(key=="private")value=System.privateMemory;
                var cost:int=getTimer()-began;
                report.memoryBench.push({pass:pass,key:key,value:value,ms:cost});
                if(key=="total"){totalCost+=cost;maxTotal=Math.max(maxTotal,cost);}
            }
            report.memoryEnabled=totalCost<=4 && maxTotal<=2;
            report.totalGetterCostMs=totalCost;report.maxTotalGetterMs=maxTotal;
        }
        private static function overflow():void {overflowed=true;clearSamples();}
        private static function release():void {
            stopSampling();clearSamples();setSamplerCallback(null);active=false;
        }
        public static function observe(row:Object):void {
            var began:int=getTimer();
            if(active) {
                window.endBeforeMs=getTimer();pauseSampling();
                window.endIndex=row.sequence;window.nextNativeBand=row.stageBandMs;
                window.overflow=overflowed;
                var count:Number=getSampleCount(),cpu:Object={},alloc:Object={},liveSizes:Object={},liveCounts:Object={},n:int=0,c:int=0,a:int=0,d:int=0;
                try {
                    if(count>=100000 || overflowed)throw new Error("Sample overflow");
                    for each(var sample:Sample in getSamples()) {
                        if(++n>=100000)throw new Error("Enumeration overflow");
                        if(sample is DeleteObjectSample){++d;continue;}
                        var names:Array=[];
                        if(sample.stack)for each(var frame:StackFrame in sample.stack)names.push(frame.name);
                        var key:String=JSON.stringify(names);
                        if(sample is NewObjectSample){
                            ++a;alloc[key]=int(alloc[key])+1;
                            // Size applies only to samples whose weakly referenced object is still alive.
                            // Do not equate this lower-bound census with total allocated bytes.
                            var object:*=(sample as NewObjectSample).object;
                            if(object!=null){liveSizes[key]=Number(liveSizes[key] || 0)+getSize(object);liveCounts[key]=int(liveCounts[key])+1;}
                            object=null;
                        }
                        else if(getQualifiedClassName(sample)=="flash.sampler::Sample"){++c;cpu[key]=int(cpu[key])+1;}
                        else throw new Error("Unknown sample class");
                    }
                    if(n!=count)throw new Error("Sample count mismatch");
                    window.entries={reported:count,total:n,cpu:c,newObject:a,deleteObject:d};
                    window.cpu=cpu;window.alloc=alloc;window.liveSizes=liveSizes;window.liveCounts=liveCounts;window.valid=true;
                } catch(error:Error){window.valid=false;window.error=error.message;report.errors.push(error.message);}
                finally {sample=null;frame=null;release();}
                window.collectMs=getTimer()-began;report.windows.push(window);window=null;
            }
            if(report.memoryEnabled) {
                var start:int=getTimer();row.vmTotal=System.totalMemoryNumber;row.vmReadMs=getTimer()-start;
            }
            // Two predetermined one-interval samples in each 90-interval window.
            if(row.sequence<2160 && (row.sequence%90==30 || row.sequence%90==60)) {
                window={startIndex:row.sequence,mode:row.mode,condition:row.condition,layerCondition:row.layerCondition,startBeforeMs:getTimer()};
                clearSamples();sampleInternalAllocs(true);setSamplerCallback(overflow);overflowed=false;
                startSampling();active=true;window.startAfterMs=getTimer();
            }
            row.costProbeMs=getTimer()-began;
        }
        public static function finish():Object {
            if(active){release();report.errors.push("Incomplete sample window");}
            report.cleaned=true;report.active=false;return report;
        }
    }
}
