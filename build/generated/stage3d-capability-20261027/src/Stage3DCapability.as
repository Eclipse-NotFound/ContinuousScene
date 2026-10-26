package {
    import flash.display.Sprite;
    import flash.display.BitmapData;
    import flash.display.StageAlign;
    import flash.display.StageScaleMode;
    import flash.display3D.Context3D;
    import flash.events.Event;
    import flash.events.ErrorEvent;
    import flash.events.TimerEvent;
    import flash.desktop.NativeApplication;
    import flash.filesystem.File;
    import flash.filesystem.FileMode;
    import flash.filesystem.FileStream;
    import flash.system.Capabilities;
    import flash.utils.Timer;
    import flash.utils.getTimer;

    [SWF(width="256", height="256", frameRate="60", backgroundColor="#000000")]
    public final class Stage3DCapability extends Sprite {
        private var result:Object = {version:"stage3d-capability-1", passed:false,
            diagnosticOnly:true, deployed:false, errors:[], allocations:0, disposals:0};
        private var context:Context3D;
        private var bitmap:BitmapData;
        private var deadline:Timer;
        private var done:Boolean = false;
        private var started:int;
        public function Stage3DCapability() {
            if (stage) start(); else addEventListener(Event.ADDED_TO_STAGE, added);
        }
        private function added(event:Event):void {
            removeEventListener(Event.ADDED_TO_STAGE, added);
            start();
        }
        private function start():void {
            started = getTimer();
            try {
                var stream:FileStream = new FileStream();
                stream.open(File.applicationDirectory.resolvePath("fixture.json"), FileMode.READ);
                var fixture:Object = JSON.parse(stream.readUTFBytes(stream.bytesAvailable));
                stream.close();
                result.appId = fixture.appId; result.nonce = fixture.nonce;
                var descriptor:XML = NativeApplication.nativeApplication.applicationDescriptor;
                var ns:Namespace = descriptor.namespace();
                result.actualAppId = String(descriptor.ns::id);
                if (result.actualAppId != result.appId) throw new Error("Application identity mismatch");
                stage.align = StageAlign.TOP_LEFT;
                stage.scaleMode = StageScaleMode.NO_SCALE;
                result.runtime = Capabilities.version;
                result.stageWidth = stage.stageWidth; result.stageHeight = stage.stageHeight;
                result.requestedMode = "auto"; result.requestedProfile = "baseline";
                if (stage.stageWidth != 256 || stage.stageHeight != 256 || stage.stage3Ds.length == 0)
                    throw new Error("Unexpected Stage dimensions/capability");
                deadline = new Timer(10000, 1);
                deadline.addEventListener(TimerEvent.TIMER_COMPLETE, timeout);
                deadline.start();
                stage.stage3Ds[0].addEventListener(Event.CONTEXT3D_CREATE, created);
                stage.stage3Ds[0].addEventListener(ErrorEvent.ERROR, failed);
                stage.stage3Ds[0].requestContext3D("auto", "baseline");
            } catch (error:Error) { result.errors.push(error.toString()); finish(); }
        }
        private function timeout(event:TimerEvent):void {
            result.errors.push("Context3D creation timeout"); finish();
        }
        private function failed(event:ErrorEvent):void {
            result.errors.push("Stage3D error: " + event.text); finish();
        }
        private function created(event:Event):void {
            if (done) return;
            try {
                context = stage.stage3Ds[0].context3D;
                result.driverInfo = context.driverInfo;
                result.profile = context.profile;
                result.contextMs = getTimer() - started;
                result.hardwareReported = result.driverInfo.toLowerCase().indexOf("software") < 0;
                context.enableErrorChecking = true;
                context.configureBackBuffer(256, 256, 0, false);
                context.clear(0.25, 0.5, 0.75, 1.0);
                bitmap = new BitmapData(256,256,true,0); result.allocations++;
                context.drawToBitmapData(bitmap);
                var maxRGB:int = 0, maxAlpha:int = 0, pixels:int = 0;
                for (var y:int=0; y<256; ++y) for (var x:int=0; x<256; ++x) {
                    var pixel:uint=bitmap.getPixel32(x,y);
                    maxRGB=Math.max(maxRGB,Math.abs(int((pixel>>16)&255)-64),
                        Math.abs(int((pixel>>8)&255)-128),Math.abs(int(pixel&255)-191));
                    maxAlpha=Math.max(maxAlpha,Math.abs(int(pixel>>>24)-255)); pixels++;
                }
                result.readback={pixels:pixels,firstPixel:bitmap.getPixel32(0,0).toString(16),
                    maxRGB:maxRGB,maxAlpha:maxAlpha};
                if (maxRGB>1 || maxAlpha!=0) throw new Error("Clear/readback mismatch");
                context.present();
                result.presentCalled = true;
                result.passed = true;
            } catch (error:Error) { result.errors.push(error.toString()); }
            finish();
        }
        private function finish():void {
            if (done) return; done=true;
            if (deadline) { deadline.stop(); deadline.removeEventListener(TimerEvent.TIMER_COMPLETE,timeout); }
            if (stage && stage.stage3Ds.length) {
                stage.stage3Ds[0].removeEventListener(Event.CONTEXT3D_CREATE,created);
                stage.stage3Ds[0].removeEventListener(ErrorEvent.ERROR,failed);
            }
            if (bitmap) { bitmap.dispose(); bitmap=null; result.disposals++; }
            if (context) {
                try { context.dispose(false); result.contextDisposed=true; }
                catch (error:Error) { result.errors.push(error.toString()); }
                context=null;
            }
            result.elapsedMs=getTimer()-started;
            result.passed=result.passed && result.errors.length==0 &&
                result.allocations==result.disposals && result.contextDisposed===true;
            var output:FileStream=new FileStream();
            output.open(File.applicationStorageDirectory.resolvePath("result.json"),FileMode.WRITE);
            output.writeUTFBytes(JSON.stringify(result)); output.close();
            NativeApplication.nativeApplication.exit(result.passed?0:1);
        }
    }
}

