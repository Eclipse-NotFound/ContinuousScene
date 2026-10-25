package tests {
    import flash.desktop.NativeApplication;
    import flash.display.DisplayObject;
    import flash.display.Stage;
    import flash.events.MouseEvent;
    import flash.events.TimerEvent;
    import flash.filesystem.File;
    import flash.filesystem.FileMode;
    import flash.filesystem.FileStream;
    import flash.utils.Timer;
    import flash.utils.getQualifiedClassName;
    import flash.utils.getTimer;

    /** One native input handshake before warmup, then read-only actual coordinates. */
    public class SceneWorldMouseProbe {
        private var world:Object, location:Object, visual:DisplayObject, stage:Stage;
        private var appId:String, originalTitle:String;
        private var originalVisible:Boolean=false;
        private var beginObserved:Object, afterSetup:Object, contextFailure:Object;
        private var width:int, height:int, pointX:int, pointY:int, began:int;
        private var eventSeq:int=0, timerSeq:int=0, sampled:int=0, warmed:int=0;
        private var gateTicks:int=0, released:Object;
        private var events:Array=[], errors:Array=[];
        private var ready:Object, proof:Object, timer:Timer;
        private var begun:Boolean=false, accepted:Boolean=false, cleared:Boolean=false;

        private function read(o:Object,key:String):* {return o[new QName("",key)];}
        private function windowState():Object {
            var bounds:Object=stage.nativeWindow.bounds;
            return {stageWidth:stage.stageWidth,stageHeight:stage.stageHeight,scaleMode:stage.scaleMode,align:stage.align,
                title:stage.nativeWindow.title,visible:stage.nativeWindow.visible,
                nativeBounds:{x:bounds.x,y:bounds.y,width:bounds.width,height:bounds.height},
                stageDisplayState:stage.displayState,nativeDisplayState:stage.nativeWindow.displayState};
        }
        private function context(w:Object):void {
            if(w!==world || read(w,"loc")!==location || read(w,"visual")!==visual || visual.stage!==stage) {
                contextFailure={reason:"world-stage-identity",actual:windowState()};
                throw new Error("Mouse proof lost original world/stage");
            }
            if(stage.stageWidth!=width || stage.stageHeight!=height || stage.scaleMode!="noScale" || stage.align!="TL" ||
                stage.nativeWindow.title!=appId || !stage.nativeWindow.visible) {
                contextFailure={reason:"window-state",expected:{stageWidth:width,stageHeight:height,scaleMode:"noScale",align:"TL",title:appId,visible:true},
                    actual:windowState()};
                throw new Error("Mouse proof window geometry/title/visibility changed: "+JSON.stringify(contextFailure));
            }
        }
        private function actual():Object {
            return {version:"mouse-world-native-2",appId:appId,atMs:getTimer(),eventSeq:eventSeq,timerSeq:timerSeq,
                stageWidth:stage.stageWidth,stageHeight:stage.stageHeight,scaleMode:stage.scaleMode,align:stage.align,
                stageMouseX:stage.mouseX,stageMouseY:stage.mouseY,targetX:pointX,targetY:pointY};
        }
        private function atPoint(row:Object):Boolean {
            return isFinite(row.stageMouseX) && isFinite(row.stageMouseY) &&
                Math.abs(row.stageMouseX-pointX)<=1 && Math.abs(row.stageMouseY-pointY)<=1;
        }
        private function begin(w:Object):void {
            begun=true;world=w;location=read(w,"loc");visual=read(w,"visual") as DisplayObject;
            if(visual==null || visual.stage==null)throw new Error("World visual not on Stage before mouse handshake");
            stage=visual.stage;appId=NativeApplication.nativeApplication.applicationID;
            originalTitle=stage.nativeWindow.title;originalVisible=stage.nativeWindow.visible;
            beginObserved=windowState();
            if(!/^pfe-modsettings-continuous-motion-[0-9a-f]{32}$/.test(appId))throw new Error("Independent AIR id required");
            width=stage.stageWidth;height=stage.stageHeight;
            if(width<=0 || height<=0 || width>32767 || height>32767)throw new Error("Unsupported actual Stage dimensions");
            pointX=int(width/2);pointY=int(height/2);
            stage.nativeWindow.title=appId;
            stage.nativeWindow.visible=true; // Once, on this owned private-desktop window; no activate or resize.
            afterSetup=windowState();
            context(w);
            if(read(visual,"mouseChildren")!==true || read(visual,"mouseEnabled")!==true)
                throw new Error("Native world mouse tree already disabled");
            began=getTimer();
            stage.addEventListener(MouseEvent.MOUSE_MOVE,onMove,true);
            ready=actual();ready.windowTitle=appId;ready.storageNativePath=File.applicationStorageDirectory.nativePath;
            ready.visualClass=getQualifiedClassName(visual);ready.mouseChildren=true;ready.mouseEnabled=true;
            writeOnce("world-mouse-ready.json",ready);
            timer=new Timer(100);timer.addEventListener(TimerEvent.TIMER,onTimer);timer.start();
        }
        private function onMove(event:MouseEvent):void {
            try {
                if(events.length>=32)throw new Error("Unexpected native mouse event flood");
                context(world);
                var row:Object=actual();row.seq=++eventSeq;row.eventSeq=eventSeq;
                row.type=event.type;row.eventStageX=event.stageX;row.eventStageY=event.stageY;
                row.buttonDown=event.buttonDown;row.targetClass=getQualifiedClassName(event.target);
                row.path=[];row.targetInWorld=false;
                var node:DisplayObject=event.target as DisplayObject, depth:int=0;
                while(node && depth++<64) {
                    row.path.push({name:node.name,className:getQualifiedClassName(node),isWorld:node===visual,isStage:node===stage});
                    if(node===visual)row.targetInWorld=true;
                    if(node===stage)break;
                    node=node.parent;
                }
                row.pathReachedStage=node===stage;events.push(row);
            } catch(error:*) {errors.push(String(error));if(timer)timer.stop();}
        }
        private function onTimer(event:TimerEvent):void {
            try {
                ++timerSeq;context(world);
                if(proof || errors.length>0) {timer.stop();return;}
                if(getTimer()-began>15000)throw new Error("Native mouse handshake timed out");
                var current:Object=actual();
                for each(var row:Object in events) {
                    if(row.seq>ready.eventSeq && row.type=="mouseMove" && row.buttonDown===false && row.targetInWorld &&
                        row.pathReachedStage && atPoint(row) && Math.abs(row.eventStageX-pointX)<=1 &&
                        Math.abs(row.eventStageY-pointY)<=1 && current.atMs>=row.atMs && atPoint(current)) {
                        proof={version:"mouse-world-native-2",appId:appId,event:row,laterTimer:current,ready:ready};
                        writeOnce("world-mouse-proof.json",proof);timer.stop();return;
                    }
                }
            } catch(error:*) {errors.push(String(error));timer.stop();}
        }
        public function gate(w:Object):Boolean {
            if(!begun)begin(w);
            context(w);
            if(errors.length)throw new Error("Native mouse proof: "+errors.join("; "));
            if(accepted)return true;
            ++gateTicks;
            if(getTimer()-began>15000)throw new Error("Mouse proof acceptance timed out; no warmup");
            var file:File=File.applicationStorageDirectory.resolvePath("world-mouse-accepted.json");
            if(!file.exists)return false;
            var approval:Object=readJSON(file);
            if(!proof || approval.appId!=appId || approval.eventSeq!=proof.event.seq || approval.targetX!=pointX ||
                approval.targetY!=pointY || approval.nativePostAccepted!==true)
                throw new Error("Native mouse acceptance does not match real runtime proof");
            if(!atPoint(actual()))throw new Error("Mouse left point before warmup");
            var player:Object=read(w,"gg"), grafon:Object=read(w,"grafon");
            released={atMs:getTimer(),gateTicks:gateTicks,waitMs:getTimer()-began,
                playerX:read(player,"X"),playerY:read(player,"Y"),dx:read(player,"dx"),dy:read(player,"dy"),
                sceneWarmCount:read(grafon,"sceneWarmCount"),allStat:read(w,"allStat"),onPause:read(w,"onPause"),
                nativeWorldContinued:true,probeWarmupStarted:false};
            stage.removeEventListener(MouseEvent.MOUSE_MOVE,onMove,true);
            accepted=true;return true;
        }
        public function warm(w:Object):void {
            context(w);if(!accepted || errors.length || !atPoint(actual()))throw new Error("Actual mouse drifted in warmup");
            ++warmed;
        }
        public function sample(w:Object):Object {
            context(w);var row:Object=actual();
            if(!accepted || errors.length || !atPoint(row))throw new Error("Actual mouse drifted during timing");
            ++sampled;row.sample=sampled;row.mouseChildren=read(visual,"mouseChildren");row.mouseEnabled=read(visual,"mouseEnabled");
            return row;
        }
        public function snapshot():Object {
            return {version:"mouse-world-native-2",begun:begun,accepted:accepted,cleared:cleared,appId:appId,
                ready:ready,proof:proof,released:released,gateTicks:gateTicks,events:events.concat(),errors:errors.concat(),sampled:sampled,warmed:warmed,
                beginObserved:beginObserved,afterSetup:afterSetup,contextFailure:contextFailure,
                titleRestored:stage ? stage.nativeWindow.title==originalTitle : true,
                visibilityRestored:stage ? stage.nativeWindow.visible===originalVisible : true};
        }
        public function clear():Object {
            if(!cleared) {
                if(timer)timer.stop();
                if(stage) {
                    stage.removeEventListener(MouseEvent.MOUSE_MOVE,onMove,true);
                    try {stage.nativeWindow.title=originalTitle;}
                    finally {stage.nativeWindow.visible=originalVisible;}
                }
                cleared=true;
            }
            return snapshot();
        }
        private function writeOnce(name:String,value:Object):void {
            var destination:File=File.applicationStorageDirectory.resolvePath(name);
            if(destination.exists)throw new Error("Preserve existing mouse proof file");
            var temporary:File=File.applicationStorageDirectory.resolvePath(name+".tmp"), stream:FileStream=new FileStream();
            try {stream.open(temporary,FileMode.WRITE);stream.writeUTFBytes(JSON.stringify(value));}
            finally {stream.close();}
            temporary.moveTo(destination,false);
        }
        private function readJSON(file:File):Object {
            var stream:FileStream=new FileStream(), result:Object;
            try {stream.open(file,FileMode.READ);result=JSON.parse(stream.readUTFBytes(stream.bytesAvailable));}
            finally {stream.close();}
            return result;
        }
    }
}
