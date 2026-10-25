package {
    import flash.desktop.NativeApplication;
    import flash.display.NativeWindow;
    import flash.display.Stage;
    import flash.display.StageQuality;
    import flash.utils.getTimer;

    /** Quality sensitivity only; native battle and all simulation remain active. */
    public class SceneStageQualityTrial {
        private var world:*,camera:*,visual:*;
        private var stage:Stage,window:NativeWindow;
        private var originalQuality:String,expectedQuality:String;
        private var initialized:Boolean=false,closed:Boolean=false,pending:Boolean=false;
        private var observed:int=0,caseIndex:int=-1,nextFrame:int=0;
        public var report:Object={version:"stage-quality-native-1",diagnosticOnly:true,
            performanceEligible:false,pixelAcceptance:false,complete:false,errors:[],switches:[],
            limits:["Only Stage.quality is written; no visibility, focus, camera, input, AI, weapon or RNG change.",
                "LOW may change BitmapData.draw rasterization and newly drawn decals or tiles; those pixels can persist into later HIGH windows.",
                "This is quality sensitivity, not isolated final presentation cost, pixel equivalence or a deployable optimization.",
                "Window state is read only at case transitions and termination; private-desktop state does not prove foreground presentation."]};

        private function identity(w:*):void {
            if(!stage || !window || window.closed)throw new Error("Owned native Stage or window unavailable");
            if(w!==world || w.main.stage!==stage || stage.nativeWindow!==window || w.cam!==camera || w.visual!==visual)
                throw new Error("Quality trial world, Stage, window, camera or visual identity changed");
        }
        private function state(w:*):Object {
            identity(w);
            var bounds:*=window.bounds;
            return {quality:stage.quality,normalizedQuality:String(stage.quality).toUpperCase(),
                visible:window.visible,active:window.active,closed:window.closed,
                applicationActiveWindowMatches:NativeApplication.nativeApplication.activeWindow===window,
                displayState:window.displayState,stageWidth:stage.stageWidth,stageHeight:stage.stageHeight,
                frameRate:stage.frameRate,onPause:w.onPause,stageDisplayState:stage.displayState,
                renderMode:window.renderMode,cameraScale:camera.scaleV,
                visualScaleX:visual.scaleX,visualScaleY:visual.scaleY,
                bounds:{x:bounds.x,y:bounds.y,width:bounds.width,height:bounds.height}};
        }
        public function switchCase(w:*,index:int,caseBegin:int):Object {
            var start:int=getTimer();
            if(closed)throw new Error("Quality trial already cleared");
            if(!initialized){
                world=w;stage=w.main.stage as Stage;camera=w.cam;visual=w.visual;
                if(!stage)throw new Error("No native Stage");
                window=stage.nativeWindow;
                if(!window || window.closed)throw new Error("No open native window");
                originalQuality=stage.quality;initialized=true;report.initial=state(w);
                if(String(originalQuality).toUpperCase()!="HIGH")throw new Error("Quality trial requires initial HIGH");
            }
            if(index!=caseIndex+1 || index<0 || index>3 || (caseIndex>=0 && nextFrame!=300))
                throw new Error("Quality cases are out of order or previous case incomplete");
            var before:Object=state(w);
            if(caseIndex>=0 && before.normalizedQuality!==expectedQuality)
                throw new Error("External quality change before case transition");
            expectedQuality=index==1 || index==2?"LOW":"HIGH";
            pending=true;
            stage.quality=expectedQuality=="LOW"?StageQuality.LOW:StageQuality.HIGH;
            var after:Object=state(w),end:int=getTimer();
            if(after.normalizedQuality!==expectedQuality)throw new Error("Requested Stage quality was not applied");
            caseIndex=index;nextFrame=0;
            var row:Object={index:index,expectedQuality:expectedQuality,caseBeginAtMs:caseBegin,
                switchBeginAtMs:start,switchEndAtMs:end,switchMs:end-start,before:before,after:after,frames:[]};
            report.switches.push({index:index,expectedQuality:expectedQuality,before:before,after:after,
                caseBeginAtMs:caseBegin,switchBeginAtMs:start,switchEndAtMs:end,switchMs:end-start});
            return row;
        }
        public function observe(w:*,index:int,frame:int):Object {
            var start:int=getTimer();
            if(!initialized || closed || index!=caseIndex || frame!=nextFrame || frame<0 || frame>=300)
                throw new Error("Unexpected quality observation");
            identity(w);
            var actual:String=stage.quality;
            if(actual.toUpperCase()!==expectedQuality)throw new Error("External Stage quality change during observation");
            ++observed;++nextFrame;
            return {index:index,frame:frame,quality:actual,normalizedQuality:actual.toUpperCase(),elapsedMs:getTimer()-start};
        }
        public function finish(w:*,complete:Boolean):Object {
            report.observations=observed;
            report.complete=complete && observed==1200 && caseIndex==3 && nextFrame==300;
            try {if(initialized)report.finalBeforeRestore=state(w);}
            catch(error:*){report.errors.push("Final state: "+String(error));}
            finally {report.cleanup=clear();}
            return report;
        }
        public function clear():Object {
            if(closed)return report.cleanup;
            var errors:Array=[],restored:Boolean=!initialized;
            if(initialized){
                try {
                    if(!stage || !window || window.closed)throw new Error("Owned Stage/window unavailable for quality restoration");
                    stage.quality=originalQuality;
                    restored=stage.quality===originalQuality;
                    if(!restored)throw new Error("Original Stage quality was not restored exactly");
                    pending=false;
                    report.finalAfterRestore=state(world);
                } catch(error:*){errors.push(String(error));}
            }
            var cleanup:Object={restored:restored,initialized:initialized,originalQuality:originalQuality,
                pendingRestore:pending?1:0,errors:errors};
            if(restored && errors.length==0){world=null;camera=null;visual=null;stage=null;window=null;closed=true;}
            report.cleanup=cleanup;return cleanup;
        }
    }
}
