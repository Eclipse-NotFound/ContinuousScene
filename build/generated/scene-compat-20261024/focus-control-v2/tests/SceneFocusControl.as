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
        private var world:*,manager:*,form:DisplayObjectContainer,visual:DisplayObject,stage:Stage;
        private var controls:Array=[],windows:Array=[],errors:Array=[];
        private var names:Object={};
        private var qualification:Object=null;
        private var started:Boolean=false,closed:Boolean=false;
        private var activeIndex:int=-1;

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
            nativeFocus();
            qualification={passed:true,discoveryMs:getTimer()-began,existingControls:found,
                managerClass:getQualifiedClassName(manager),managerCount:1,formClass:getQualifiedClassName(form),
                formIsStage:form===stage,containsVisual:form.contains(visual),privateQNames:recorded,
                initialActivated:true,initialStageFocusIsStage:true,initialLastFocusNull:true,
                initialDefButtonNull:true,initialDefaultButtonNull:true,initialOnConsol:false};
            started=true;
        }
        private function focusKind(value:*):String {
            if(value===null)return "null";
            if(value===undefined)return "undefined";
            if(value===stage)return "same-stage";
            return getQualifiedClassName(value);
        }
        private function nativeFocus():void {
            var current:*=stage.focus,last:*=manager[names.lastFocus],button:*=manager[names.defButton],
                defaultButton:*=manager[names._defaultButton];
            // World.step assigns the existing Stage to focus during normal gameplay.
            // Observe that exact identity; never clear or assign focus in this diagnostic.
            if(current!==stage || last!==null || button!==null || defaultButton!==null)
                fail("Native focus eligibility failed: stage.focus="+focusKind(current)+
                    "; lastFocus="+focusKind(last)+"; defButton="+focusKind(button)+
                    "; _defaultButton="+focusKind(defaultButton));
        }
        private function identity(w:*):void {
            if(w!==world || w.visual!==visual || w.main.stage!==stage || manager[FORM]!==form ||
                form.stage!==stage || !form.contains(visual))fail("Manager/world/form/visual identity changed");
            for each(var control:* in controls)
                if(control.stage!==stage || control[FOCUS]!==manager)fail("Original UI component changed manager or stage");
        }
        private function state(w:*,expected:Boolean):Object {
            gameplay(w);identity(w);nativeFocus();
            if(manager[names.activated]!==expected)fail("FocusManager activated state differs from requested window");
            return {activated:expected,identity:true,containsVisual:true,stageFocusIsStage:true,
                lastFocusNull:true,defButtonNull:true,defaultButtonNull:true,onConsol:false};
        }

        public function begin(w:*,index:int):Object {
            if(closed)fail("Focus diagnostic already closed");
            if(!started){if(index!=0)fail("Focus diagnostic must start at window zero");acquire(w);}
            if(index!=windows.length || index<0 || index>3)fail("Unexpected focus window order");
            var enabled:Boolean=index==0 || index==3;
            var prior:Boolean=index==0 || index==1;
            var before:Object=state(w,prior),began:int=getTimer();
            if(enabled!=prior) {
                if(enabled)manager[ACTIVATE]();else manager[DEACTIVATE]();
            }
            var after:Object=state(w,enabled),ended:int=getTimer();
            var row:Object={index:index,arm:enabled?"active":"inactive",expectedActivated:enabled,
                beginAtMs:began,transitionMs:ended-began,before:before,after:after,
                frames:0,states:[],ended:false,diagnosticOnly:true,performanceEligible:false};
            windows.push(row);activeIndex=index;
            return row;
        }
        public function sample(w:*,index:int,age:int):void {
            if(!started || closed || index!=activeIndex || age!=int(windows[index].frames))
                fail("Focus observation does not match original consecutive combat frames");
            gameplay(w);identity(w);nativeFocus();
            var expected:Boolean=index==0 || index==3;
            if(manager[names.activated]!==expected)fail("FocusManager activated changed during combat");
            windows[index].frames=Number(windows[index].frames)+1;
            if(age%30==0 || age==299)windows[index].states.push({age:age,activated:expected,
                identity:true,stageFocusIsStage:true,menu:false,pip:false,sats:false,onConsol:false});
        }
        public function end(w:*,index:int):void {
            if(!started || closed || index!=activeIndex || windows[index].frames!=300)
                fail("Focus window ended without 300 real combat frames");
            windows[index].end=state(w,index==0 || index==3);
            windows[index].ended=true;
        }
        public function clear(w:*):Object {
            var cleanup:Object={attempted:started,restored:!started,reactivated:false,error:null};
            try {
                if(started) {
                    identity(w);
                    try {
                        if(manager[names.activated]!==true){manager[ACTIVATE]();cleanup.reactivated=true;}
                    } finally {
                        cleanup.restored=manager[names.activated]===true;
                    }
                    cleanup.state=state(w,true);
                }
            } catch(error:*) {cleanup.error=String(error);cleanup.restored=false;}
            finally {closed=true;}
            var valid:Boolean=started && errors.length==0 && cleanup.restored && windows.length==4;
            for(var i:int=0;i<windows.length;++i)valid=valid && windows[i].index==i &&
                windows[i].frames==300 && windows[i].ended;
            return {version:"focus-control-2",valid:valid,diagnosticOnly:true,performanceEligible:false,
                qualification:qualification,windows:windows,errors:errors,cleanup:cleanup,
                limitations:["Public deactivate/activate affects the whole UI focus manager, not just ADDED/REMOVED",
                    "TAB/Enter/mouse focus and menu/console behavior are excluded; Stage focus identity is retained and private lastFocus/default buttons must remain null",
                    "Restore rebuilds functional registration for the current tree; dictionaries, candidate arrays and relative listener registration order are not byte-identical",
                    "Discovery, window switches and activation scans remain inside continuous elapsed time",
                    "No native sampler is active; observer checks still add diagnostic overhead",
                    "Only the existing manager shared by discovered attached PipPage controls is controlled; no manager is created"]};
        }
    }
}
