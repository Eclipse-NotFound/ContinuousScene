package tests {
    import flash.utils.getTimer;

    /** Diagnostic bridge only. It never advances the game or wakes an actor. */
    public class SceneActivityRangeProbe {
        private var host:Object, api:Object;
        private var started:Boolean=false, cleared:Boolean=false, expected:Boolean=false;
        private var samples:int=0, lastTick:Number=NaN;
        private var switches:Array=[];
        private var lastVerify:Object;
        private const VERSION:String="activity-camera-range-1";

        private function context(w:Object):void {
            if(host!==w || !w || !w.main)throw new Error("Activity range host changed");
            var carrier:Object=w.main.getChildByName("ContinuousSceneCarrier");
            if(!carrier || carrier["nativeAPI"]!==api)throw new Error("Activity range API changed");
            if(api.activityCameraRangeVersion()!==VERSION)throw new Error("Activity range version changed");
        }
        public function select(w:Object,index:int):Object {
            if(index<0 || index>3)throw new Error("Activity range requires four ABBA windows");
            if(!started) {
                host=w;
                var carrier:Object=w.main.getChildByName("ContinuousSceneCarrier");
                if(!carrier)throw new Error("Activity range carrier missing");
                api=carrier["nativeAPI"];
                for each(var name:String in ["activityCameraRangeVersion","activityCameraRangeSet",
                    "activityCameraRangeVerify","activityCameraRangeSnapshot"])
                    if(!api || !(api[name] is Function))throw new Error("Activity range API missing: "+name);
                context(w);
                var initial:Object=api.activityCameraRangeSnapshot();
                if(initial.enabled!==false || initial.requestedEnabled!==false || initial.failed!==false)
                    throw new Error("Activity range did not begin in original mode");
                started=true;
            }
            context(w);
            if(cleared)throw new Error("Activity range already cleared");
            expected=index==1 || index==2;
            var before:Object=api.activityCameraRangeSnapshot();
            api.activityCameraRangeSet(expected);
            var after:Object=api.activityCameraRangeSnapshot();
            if(after.enabled!==expected || after.requestedEnabled!==expected || after.failed!==false)
                throw new Error("Activity range switch failed");
            var result:Object={index:index,atMs:getTimer(),enabled:expected,before:before,after:after};
            switches.push(result);
            return result;
        }
        public function sample(w:Object):Object {
            context(w);
            if(!started || cleared)throw new Error("Activity range sample outside active probe");
            lastVerify=api.activityCameraRangeVerify();
            if(!lastVerify || lastVerify.version!==VERSION || lastVerify.ok!==true || lastVerify.failed!==false ||
                lastVerify.enabled!==expected || lastVerify.pending!==false || lastVerify.tick===null ||
                !isFinite(Number(lastVerify.tick)) || (isFinite(lastTick) && Number(lastVerify.tick)<=lastTick) ||
                lastVerify.checkComplete!==true || lastVerify.visibleSleeping!==0 || !lastVerify.errors || lastVerify.errors.length!=0 ||
                (lastVerify.applied===true && lastVerify.viewportContained!==true) ||
                (!expected && lastVerify.applied!==false))
                throw new Error("Activity range frame failed: "+JSON.stringify(lastVerify));
            lastTick=Number(lastVerify.tick);++samples;
            return {sample:samples,atMs:getTimer(),expectedEnabled:expected,verification:lastVerify};
        }
        public function clear():Object {
            var result:Object={version:VERSION,started:started,cleared:false,samples:samples,
                switches:switches.concat(),lastVerify:lastVerify,errors:[]};
            try {
                if(started) {
                    context(host);
                    result.before=api.activityCameraRangeSnapshot();
                    api.activityCameraRangeSet(false);
                    result.after=api.activityCameraRangeSnapshot();
                    if(result.after.enabled!==false || result.after.requestedEnabled!==false)
                        throw new Error("Activity range original mode not restored");
                }
                cleared=true;
            } catch(error:*) {result.errors.push(String(error));}
            result.cleared=cleared;
            return result;
        }
    }
}
