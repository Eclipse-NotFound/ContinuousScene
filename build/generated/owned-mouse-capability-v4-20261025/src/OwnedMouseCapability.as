package {
    import flash.desktop.NativeApplication;
    import flash.display.DisplayObject;
    import flash.display.Sprite;
    import flash.display.StageAlign;
    import flash.display.StageScaleMode;
    import flash.events.Event;
    import flash.events.MouseEvent;
    import flash.events.TimerEvent;
    import flash.filesystem.File;
    import flash.filesystem.FileMode;
    import flash.filesystem.FileStream;
    import flash.utils.Timer;
    import flash.utils.getQualifiedClassName;
    import flash.utils.getTimer;

    [SWF(width="640", height="480", frameRate="30", backgroundColor="#242830")]
    public class OwnedMouseCapability extends Sprite {
        private var appId:String;
        private var nonce:String;
        private var started:int;
        private var timer:Timer;
        private var ready:Boolean = false;
        private var finished:Boolean = false;
        private var events:Array = [];
        private var timers:Array = [];
        private var errors:Array = [];
        private var eventSeq:int = 0;
        private var writeSeq:int = 0;
        private var timerSeq:int = 0;
        private var storage:File;

        public function OwnedMouseCapability() {
            if (stage) initialize();
            else addEventListener(Event.ADDED_TO_STAGE, initialize);
        }

        private function initialize(event:Event = null):void {
            removeEventListener(Event.ADDED_TO_STAGE, initialize);
            try {
                appId = NativeApplication.nativeApplication.applicationID;
                var config:Object = readJSON(File.applicationDirectory.resolvePath("fixture.json"));
                nonce = String(config.nonce);
                if (!/^[0-9a-f]{32}$/.test(nonce) ||
                    appId != "com.remains.ownedmouse." + nonce || config.appId != appId) {
                    throw new Error("Independent fixture identity mismatch");
                }
                storage = File.applicationStorageDirectory;
                started = getTimer();
                // The document root is timeline-owned; do not rename it.
                stage.scaleMode = StageScaleMode.NO_SCALE;
                stage.align = StageAlign.TOP_LEFT;
                // No NativeWindow activation: the descriptor alone makes it visible
                // on the caller-owned private desktop.
                stage.nativeWindow.title = appId;
                for (var i:int = 0; i < 3; i++) {
                    var target:Sprite = new Sprite();
                    target.name = "target" + i;
                    target.x = 40 + 200 * i;
                    target.y = 180;
                    target.mouseEnabled = true;
                    target.mouseChildren = false;
                    target.graphics.beginFill([0xD96558, 0x6EBF72, 0x639AD6][i]);
                    target.graphics.drawRect(0, 0, 100, 100);
                    target.graphics.endFill();
                    addChild(target);
                }
                stage.addEventListener(MouseEvent.MOUSE_MOVE, onMouseMove);
                timer = new Timer(100);
                timer.addEventListener(TimerEvent.TIMER, onTimer);
                timer.start();
            } catch (error:Error) {
                errors.push(String(error));
                finish("initialize-error", 2);
            }
        }

        private function base():Object {
            return {version:"owned-mouse-capability-4", appId:appId, nonce:nonce,
                appMs:getTimer() - started, stageWidth:stage.stageWidth,
                stageHeight:stage.stageHeight, scaleMode:stage.scaleMode,
                align:stage.align, eventSeq:eventSeq, timerSeq:timerSeq,
                stageMouseX:stage.mouseX, stageMouseY:stage.mouseY,
                diagnosticOnly:true, performanceEligible:false};
        }

        private function onMouseMove(event:MouseEvent):void {
            if (finished) return;
            try {
                if (events.length >= 64) throw new Error("Native event limit exceeded");
                var row:Object = base();
                row.seq = ++eventSeq;
                row.eventSeq = eventSeq;
                row.type = event.type;
                row.eventPhase = event.eventPhase;
                row.eventStageX = event.stageX;
                row.eventStageY = event.stageY;
                row.buttonDown = event.buttonDown;
                row.targetClass = getQualifiedClassName(event.target);
                row.path = [];
                var node:DisplayObject = event.target as DisplayObject;
                var depth:int = 0;
                while (node && depth++ < 16) {
                    row.path.push({name:node.name, className:getQualifiedClassName(node),
                        isStage:node === stage, isProbeRoot:node === this});
                    if (node === stage) break;
                    node = node.parent;
                }
                row.pathReachedStage = node === stage;
                row.targetName = event.target is DisplayObject ? DisplayObject(event.target).name : null;
                events.push(row);
                writeObservations();
            } catch (error:Error) {
                errors.push(String(error));
                finish("event-error", 2);
            }
        }

        private function onTimer(event:TimerEvent):void {
            if (finished) return;
            try {
                var row:Object = base();
                row.seq = ++timerSeq;
                row.timerSeq = timerSeq;
                timers.push(row);
                // Descriptor width/height include native window chrome on this runtime.
                // Adjust only this owned window once, then require exact Stage/client size.
                if (timerSeq == 1 && stage.stageWidth > 0 && stage.stageHeight > 0) {
                    stage.nativeWindow.width += 640 - stage.stageWidth;
                    stage.nativeWindow.height += 480 - stage.stageHeight;
                }
                if (timers.length > 650) throw new Error("Timer observation limit exceeded");
                writeObservations();
                if (!ready && timerSeq >= 2 && stage.stageWidth == 640 && stage.stageHeight == 480) {
                    ready = true;
                    var readyRow:Object = base();
                    readyRow.storageNativePath = storage.nativePath;
                    readyRow.windowTitle = stage.nativeWindow.title;
                    readyRow.targets = ["target0", "target1", "target2"];
                    writeJSON("ready.json", readyRow);
                }
                var commandFile:File = storage.resolvePath("command.json");
                if (commandFile.exists) {
                    var command:Object = readJSON(commandFile);
                    if (command.appId != appId || command.nonce != nonce || command.action != "finish")
                        throw new Error("Unexpected fixture control command");
                    finish("runner-finish:" + String(command.reason), 0);
                } else if (getTimer() - started >= 60000) {
                    finish("fixture-timeout", 3);
                }
            } catch (error:Error) {
                errors.push(String(error));
                finish("timer-error", 2);
            }
        }

        private function writeObservations():void {
            var row:Object = base();
            row.events = events;
            row.timers = timers;
            row.errors = errors;
            writeJSON("events.json", row);
        }

        private function finish(reason:String, code:int):void {
            if (finished) return;
            finished = true;
            if (timer) timer.stop();
            try {
                if (storage) {
                    var row:Object = base();
                    row.reason = reason;
                    row.events = events;
                    row.timers = timers;
                    row.errors = errors;
                    row.capabilityPassed = null; // Only the runner compares the native input sequence.
                    writeJSON("result.json", row);
                }
            } finally {
                NativeApplication.nativeApplication.exit(code);
            }
        }

        private function writeJSON(name:String, value:Object):void {
            if (name == "events.json") {
                var sequence:String = "0000000000" + String(++writeSeq);
                name = "events-" + sequence.substr(sequence.length - 10) + ".json";
            }
            var destination:File = storage.resolvePath(name);
            var temporary:File = storage.resolvePath(name + ".tmp");
            var stream:FileStream = new FileStream();
            try {
                stream.open(temporary, FileMode.WRITE);
                stream.writeUTFBytes(JSON.stringify(value));
            } finally { stream.close(); }
            temporary.moveTo(destination, true);
        }

        private function readJSON(file:File):Object {
            var stream:FileStream = new FileStream();
            var result:Object;
            try {
                stream.open(file, FileMode.READ);
                result = JSON.parse(stream.readUTFBytes(stream.bytesAvailable));
            } finally { stream.close(); }
            return result;
        }
    }
}
