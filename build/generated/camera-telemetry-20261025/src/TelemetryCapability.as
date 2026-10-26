package {
    import flash.desktop.NativeApplication;
    import flash.display.Sprite;
    import flash.events.Event;
    import flash.filesystem.File;
    import flash.filesystem.FileMode;
    import flash.filesystem.FileStream;
    import flash.profiler.Telemetry;
    import flash.utils.getTimer;

    public class TelemetryCapability extends Sprite {
        private var frames:int=0;
        private var ticks:Array=[];
        private var start:int;
        private var connectedFrames:int=0;
        public function TelemetryCapability() {
            if(!/^com\.remains\.telemetry\.[0-9a-f]{32}$/.test(NativeApplication.nativeApplication.applicationID))
                throw new Error("Only isolated telemetry capability application allowed");
            stage.frameRate=60;
            for(var i:int=0;i<60;++i) {
                var part:Sprite=new Sprite();part.graphics.beginFill(0x334455+i*1000);
                part.graphics.drawRect(0,0,55,55);part.graphics.endFill();
                part.x=(i%10)*60;part.y=int(i/10)*60;addChild(part);
            }
            start=getTimer();addEventListener(Event.ENTER_FRAME,step);
        }
        private function step(event:Event):void {
            ++frames;var now:int=getTimer();ticks.push(now);
            if(Telemetry.connected)++connectedFrames;
            Telemetry.sendMetric("remains.capability.frame",{appId:NativeApplication.nativeApplication.applicationID,frame:frames,timer:now});
            var marker:Number=Telemetry.spanMarker;
            if(frames>=30 && frames<50)while(getTimer()-now<3){}
            Telemetry.sendSpanMetric("remains.capability.work",marker,frames);
            x=(frames%2==0?0:5);
            if(frames==120) {
                removeEventListener(Event.ENTER_FRAME,step);
                var out:Object={appId:NativeApplication.nativeApplication.applicationID,frames:frames,
                    connectedFrames:connectedFrames,start:start,end:getTimer(),ticks:ticks,
                    userDirectory:File.userDirectory.nativePath,storage:File.applicationStorageDirectory.nativePath};
                var file:File=File.applicationStorageDirectory.resolvePath("result.json");
                var stream:FileStream=new FileStream();stream.open(file,FileMode.WRITE);
                stream.writeUTFBytes(JSON.stringify(out));stream.close();
                NativeApplication.nativeApplication.exit(0);
            }
        }
    }
}
