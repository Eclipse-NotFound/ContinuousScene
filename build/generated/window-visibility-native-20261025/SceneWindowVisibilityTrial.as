package {
    import flash.desktop.NativeApplication;
    import flash.display.NativeWindow;
    import flash.display.Stage;
    import flash.utils.getTimer;

    /** Private-desktop visibility sensitivity, never a gameplay optimization. */
    public class SceneWindowVisibilityTrial {
        private var world:*,stage:Stage,window:NativeWindow;
        private var originalVisible:Boolean,expectedVisible:Boolean;
        private var initialized:Boolean=false,closed:Boolean=false;
        private var observed:int=0,caseIndex:int=-1;
        public var report:Object={version:"window-visibility-native-1",diagnosticOnly:true,
            performanceEligible:false,complete:false,errors:[],switches:[]};

        private function state(w:*):Object {
            if(!stage || !window || window.closed)throw new Error("Owned native window is unavailable");
            if(w!==world || w.main.stage!==stage || stage.nativeWindow!==window)
                throw new Error("Native window or Stage identity changed");
            return {visible:window.visible,active:window.active,
                applicationActiveWindowMatches:NativeApplication.nativeApplication.activeWindow===window,
                displayState:window.displayState,stageWidth:stage.stageWidth,stageHeight:stage.stageHeight,
                frameRate:stage.frameRate,onPause:w.onPause,
                quality:stage.quality,stageDisplayState:stage.displayState,renderMode:window.renderMode,
                bounds:{x:window.bounds.x,y:window.bounds.y,width:window.bounds.width,height:window.bounds.height}};
        }
        public function switchCase(w:*,index:int,caseBegin:int):Object {
            var start:int=getTimer();
            if(closed)throw new Error("Visibility trial already cleared");
            if(!initialized){
                world=w;stage=w.main.stage as Stage;
                if(!stage)throw new Error("No native Stage");
                window=stage.nativeWindow;
                if(!window || window.closed)throw new Error("No open native window");
                originalVisible=window.visible;initialized=true;
                report.initial=state(w);
                if(originalVisible)throw new Error("Expected unchanged hidden descriptor at entry");
            }
            if(index!=caseIndex+1 || index<0 || index>3)throw new Error("Visibility cases are out of order");
            var before:Object=state(w);
            expectedVisible=index==1 || index==2;
            window.visible=expectedVisible;
            var after:Object=state(w),end:int=getTimer();
            if(after.visible!==expectedVisible)throw new Error("Native visibility write was not applied");
            caseIndex=index;
            var row:Object={index:index,expectedVisible:expectedVisible,caseBeginAtMs:caseBegin,
                switchBeginAtMs:start,switchEndAtMs:end,switchMs:end-start,before:before,after:after,frames:[]};
            report.switches.push({index:index,expectedVisible:expectedVisible,before:before,after:after,
                caseBeginAtMs:caseBegin,switchBeginAtMs:start,switchEndAtMs:end,switchMs:end-start});
            return row;
        }
        public function observe(w:*,index:int,frame:int):Object {
            var start:int=getTimer();
            if(!initialized || closed || index!=caseIndex || frame<0 || frame>=300)
                throw new Error("Unexpected visibility observation");
            var value:Object=state(w);
            if(value.visible!==expectedVisible)throw new Error("External window visibility change");
            ++observed;value.index=index;value.frame=frame;value.elapsedMs=getTimer()-start;
            return value;
        }
        public function finish(w:*,complete:Boolean):Object {
            report.observations=observed;report.complete=complete && observed==1200 && caseIndex==3;
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
                    if(!window || window.closed)throw new Error("Owned window closed before restoration");
                    window.visible=originalVisible;
                    report.finalAfterRestore=state(world);
                    restored=window.visible===originalVisible;
                    if(!restored)throw new Error("Original visibility was not restored");
                } catch(error:*){errors.push(String(error));}
            }
            var cleanup:Object={restored:restored,initialized:initialized,originalVisible:originalVisible,
                pendingRestore:initialized && !restored?1:0,errors:errors};
            if(restored){world=null;stage=null;window=null;closed=true;}
            report.cleanup=cleanup;return cleanup;
        }
    }
}
