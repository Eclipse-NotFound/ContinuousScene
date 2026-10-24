package tests {
    import flash.display.DisplayObject;
    import flash.display.DisplayObjectContainer;
    import flash.display.Stage;
    import flash.sampler.getMemberNames;
    import flash.system.ApplicationDomain;
    import flash.utils.getQualifiedClassName;
    import flash.utils.getTimer;

    /** Isolated diagnostic upper bound. Never install in the production game. */
    public final class SceneFocusControl {
        private static const FORM:QName=new QName("","form");
        private static const FOCUS:QName=new QName("","focusManager");
        private static const SCROLL:QName=new QName("","scBar");
        private static const CONSTRUCTOR:QName=new QName("","constructor");
        private static const ACTIVATE:QName=new QName("","activate");
        private static const DEACTIVATE:QName=new QName("","deactivate");
        private static const SET_FOCUS:QName=new QName("","setFocus");
        private var world:*,manager:*,form:DisplayObjectContainer,visual:DisplayObject,stage:Stage;
        private var controls:Array=[],windows:Array=[],errors:Array=[];
        private var names:Object={};
        private var qualification:Object=null;
        private var started:Boolean=false,closed:Boolean=false;
        private var activeIndex:int=-1;
        private var focusCycles:int=0;

        private function fail(message:String):void {errors.push(message);throw new Error(message);}
        private function gameplay(w:*):void {
            if(!w || w.allStat!=1 || w.onPause || w.onConsol!==false || w.t_exit!=0 || !w.pip || w.pip.active ||
                !w.sats || w.sats.active || !w.mm || w.mm.active)
                fail("Focus diagnostic requires uninterrupted gameplay without menu/Pip/SATS/console/travel");
        }
        private function acquire(w:*):void {
            var began:int=getTimer();gameplay(w);
            if(!w.main || !w.main.stage || !w.vpip || !w.visual)fail("Existing host UI roots unavailable");
            var ad:ApplicationDomain=w.main.loaderInfo.applicationDomain;
            var ui:Class=ad.getDefinition("fl.core.UIComponent") as Class;
            var fm:Class=ad.getDefinition("fl.managers.FocusManager") as Class;
            if(!ui || !fm)fail("Host UIComponent/FocusManager definitions unavailable");
            var candidates:Array=[],pip:DisplayObjectContainer=w.vpip as DisplayObjectContainer;
            var found:Array=[];
            // Existing PipPage constructors attach their page and public scBar.
            // No global scene walk and no new UIComponent or FocusManager.
            for(var i:int=0;i<pip.numChildren;++i) {
                var page:DisplayObject=pip.getChildAt(i);
                if(!(SCROLL in page))continue;
                var control:*=Object(page)[SCROLL];
                if(!(control is ui) || control.stage!==w.main.stage)continue;
                var candidate:*=control[FOCUS];
                if(!candidate)continue;
                if(!(candidate is fm) || Object(candidate)[CONSTRUCTOR]!==fm)
                    fail("Existing component returned a foreign FocusManager");
                var candidateForm:DisplayObjectContainer=candidate[FORM] as DisplayObjectContainer;
                if(!candidateForm || !candidateForm.contains(w.visual))continue;
                if(candidates.indexOf(candidate)<0)candidates.push(candidate);
                controls.push(control);
                found.push({pageIndex:i,componentClass:getQualifiedClassName(control),componentName:control.name});
            }
            if(candidates.length!=1 || controls.length==0)
                fail("Expected exactly one existing manager whose form contains game visual; got "+candidates.length);
            manager=candidates[0];form=manager[FORM] as DisplayObjectContainer;
            world=w;visual=w.visual;stage=w.main.stage;
            if(form!==stage)fail("Focus diagnostic requires the existing manager form to be exactly Stage");
            var wanted:Object={activated:true,lastFocus:true,defButton:true,_defaultButton:true};
            var iterator:Object=getMemberNames(manager);
            if(iterator==null)fail("Private QName diagnostic unavailable");
            for each(var q:QName in iterator)if(wanted.hasOwnProperty(q.localName)) {
                if(names.hasOwnProperty(q.localName))fail("Ambiguous private QName "+q.localName);
                names[q.localName]=q;
            }
            var recorded:Object={};
            for(var key:String in wanted) {
                if(!names.hasOwnProperty(key))fail("Required private QName unavailable: "+key);
                recorded[key]={localName:QName(names[key]).localName,uri:QName(names[key]).uri};
            }
            if(manager[names.activated]!==true)fail("Existing manager is not initially active");
            nativeFocus(true);
            qualification={passed:true,discoveryMs:getTimer()-began,existingControls:found,
                managerClass:getQualifiedClassName(manager),managerCount:1,formClass:getQualifiedClassName(form),
                formIsStage:form===stage,containsVisual:form.contains(visual),privateQNames:recorded,
                initialActivated:manager[names.activated]===true,initialStageFocusIsStage:stage.focus===stage,
                initialLastFocusIsStage:manager[names.lastFocus]===stage,
                initialDefButtonNull:true,initialDefaultButtonNull:true,initialOnConsol:false};
            started=true;
        }
        private function focusKind(value:*):String {
            if(value===null)return "null";
            if(value===undefined)return "undefined";
            if(value===stage)return "same-stage";
            return getQualifiedClassName(value);
        }
        private function nativeFocus(expected:Boolean):void {
            var current:*=stage.focus,last:*=manager[names.lastFocus],button:*=manager[names.defButton],
                defaultButton:*=manager[names._defaultButton];
            var expectedLast:*=expected?stage:null;
            if(current!==stage || last!==expectedLast || button!==null || defaultButton!==null)
                fail("Native focus eligibility failed: expectedActivated="+expected+
                    "; stage.focus="+focusKind(current)+"; lastFocus="+focusKind(last)+
                    "; defButton="+focusKind(button)+"; _defaultButton="+focusKind(defaultButton));
        }
        private function activateWithFocusCycle():void {
            // Restore only our known Stage/empty-button state through public APIs.
            nativeFocus(false);
            manager[ACTIVATE]();
            if(manager[names.activated]!==true)fail("Public activate did not activate the manager");
            stage.focus=null;
            ++focusCycles;
            try {manager[SET_FOCUS](stage);}
            finally {if(stage.focus===null)manager[SET_FOCUS](stage);}
            // FOCUS_IN must naturally restore lastFocus; never write the private slot.
            nativeFocus(true);
        }
        private function identity(w:*):void {
            if(w!==world || w.visual!==visual || w.main.stage!==stage || manager[FORM]!==form ||
                form!==stage || form.stage!==stage || !form.contains(visual))fail("Manager/world/form/visual identity changed");
            for each(var control:* in controls)
                if(control.stage!==stage || control[FOCUS]!==manager)fail("Original UI component changed manager or stage");
        }
        private function state(w:*,expected:Boolean):Object {
            gameplay(w);identity(w);nativeFocus(expected);
            if(manager[names.activated]!==expected)fail("FocusManager activated state differs from requested window");
            return {activated:manager[names.activated],identity:true,formIsStage:form===stage,
                containsVisual:form.contains(visual),stageFocusIsStage:stage.focus===stage,
                lastFocusMatchesMode:manager[names.lastFocus]===(expected?stage:null),
                defButtonNull:manager[names.defButton]===null,defaultButtonNull:manager[names._defaultButton]===null,
                onConsol:w.onConsol};
        }

        public function begin(w:*,index:int):Object {
            if(closed)fail("Focus diagnostic already closed");
            if(!started){if(index!=0)fail("Focus diagnostic must start at window zero");acquire(w);}
            if(index!=windows.length || index<0 || index>3)fail("Unexpected focus window order");
            var enabled:Boolean=index==0 || index==3;
            var prior:Boolean=index==0 || index==1;
            var before:Object=state(w,prior),began:int=getTimer(),cyclesBefore:int=focusCycles;
            if(enabled!=prior) {
                if(enabled)activateWithFocusCycle();else manager[DEACTIVATE]();
            }
            var after:Object=state(w,enabled),ended:int=getTimer();
            var row:Object={index:index,arm:enabled?"active":"inactive",expectedActivated:enabled,
                beginAtMs:began,transitionMs:ended-began,focusCycles:focusCycles-cyclesBefore,before:before,after:after,
                frames:0,states:[],ended:false,diagnosticOnly:true,performanceEligible:false};
            windows.push(row);activeIndex=index;
            return row;
        }
        public function sample(w:*,index:int,age:int):void {
            if(!started || closed || index!=activeIndex || age!=int(windows[index].frames))
                fail("Focus observation does not match original consecutive combat frames");
            var expected:Boolean=index==0 || index==3;
            gameplay(w);identity(w);nativeFocus(expected);
            if(manager[names.activated]!==expected)fail("FocusManager activated changed during combat");
            windows[index].frames=Number(windows[index].frames)+1;
            if(age%30==0 || age==299)windows[index].states.push({age:age,activated:manager[names.activated],
                identity:true,stageFocusIsStage:stage.focus===stage,
                lastFocusMatchesMode:manager[names.lastFocus]===(expected?stage:null),
                menu:w.mm.active,pip:w.pip.active,sats:w.sats.active,onConsol:w.onConsol});
        }
        public function end(w:*,index:int):void {
            if(!started || closed || index!=activeIndex || windows[index].frames!=300)
                fail("Focus window ended without 300 real combat frames");
            windows[index].end=state(w,index==0 || index==3);
            windows[index].ended=true;
        }
        public function clear(w:*):Object {
            var cyclesBefore:int=focusCycles;
            var cleanup:Object={attempted:started,restored:!started,reactivated:false,focusCycles:0,error:null};
            try {
                if(started) {
                    identity(w);
                    if(manager[names.activated]!==true || manager[names.lastFocus]!==stage) {
                        cleanup.reactivated=manager[names.activated]!==true;
                        activateWithFocusCycle();
                    }
                    cleanup.state=state(w,true);
                    cleanup.restored=cleanup.state.activated===true && cleanup.state.formIsStage &&
                        cleanup.state.stageFocusIsStage && cleanup.state.lastFocusMatchesMode &&
                        cleanup.state.defButtonNull && cleanup.state.defaultButtonNull && cleanup.state.onConsol===false;
                }
            } catch(error:*) {cleanup.error=String(error);cleanup.restored=false;}
            finally {closed=true;cleanup.focusCycles=focusCycles-cyclesBefore;}
            var valid:Boolean=started && errors.length==0 && cleanup.restored && windows.length==4;
            for(var i:int=0;i<windows.length;++i)valid=valid && windows[i].index==i &&
                windows[i].frames==300 && windows[i].ended;
            return {version:"focus-control-3",valid:valid,diagnosticOnly:true,performanceEligible:false,
                qualification:qualification,windows:windows,errors:errors,cleanup:cleanup,focusCycles:focusCycles,
                limitations:["Public deactivate/activate affects the whole UI focus manager, not just ADDED/REMOVED",
                    "TAB/Enter/mouse focus and menu/console behavior are excluded; Stage focus remains Stage during all measured native frames; lastFocus is Stage in A and null in B; default buttons remain null",
                    "Isolated diagnostic only: B-to-A activation briefly cycles public Stage.focus through null and setFocus(Stage), requiring natural FOCUS_IN to restore lastFocus",
                    "Restore rebuilds functional registration for the current tree; dictionaries, candidate arrays and relative listener registration order are not byte-identical",
                    "Discovery, window switches and activation scans remain inside continuous elapsed time",
                    "No native sampler is active; observer checks still add diagnostic overhead",
                    "Only the existing manager shared by discovered attached PipPage controls is controlled; no manager is created"]};
        }
    }
}
