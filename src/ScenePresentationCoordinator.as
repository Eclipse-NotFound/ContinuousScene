package {
    import flash.events.Event;
    import flash.utils.getDefinitionByName;

    /** Optional native-terrain presentation. Owns no source pixels or gameplay state. */
    public class ScenePresentationCoordinator {
        private static var main:*,worldClass:Class;
        private static var presenter:SceneEventBitmapFill=new SceneEventBitmapFill();
        private static var settings:*,settingsRevision:int=-1;
        private static var switches:Array=[];
        private static var enabled:Boolean=true,faulted:Boolean=false;
        private static var touched:Boolean=false,presented:Boolean=false;
        private static var lastReason:String="not-installed",lastError:String="";
        private static var updates:int=0,earlyClears:int=0,resets:int=0,settingsReads:int=0;

        public static function install(host:*):void {
            if(main)return;
            main=host;worldClass=getDefinitionByName("fe.World") as Class;
            var carrier:*=main.getChildByName("ContinuousSceneCarrier");
            carrier["nativeAPI"]["scenePresentationResetV1"]=clear;
            carrier["nativeAPI"]["scenePresentationStatsV1"]=stats;
            carrier["nativeAPI"]["scenePresentationEnabledV1"]=setEnabled;
            main.stage.addEventListener(Event.ENTER_FRAME,beforeNative,false,500,true);
        }

        // Called before RV's priority 0 listener. Its hotkey/setters change flags
        // between frames, so the original native bitmaps are restored first.
        private static function beforeNative(event:Event):void {
            if(!touched)return;
            try {
                var reason:String=eligibility(worldClass["w"]);
                if(reason!=""){++earlyClears;clear(reason);}
            } catch(error:Error){fail(error);}
        }

        // The production entry invokes this last at priority -200, after the
        // normal camera/cull and all three supported visual-mod frame handlers.
        public static function update(w:*):void {
            ++updates;
            try {
                var reason:String=eligibility(w);
                if(reason!=""){clear(reason);return;}
                touched=true;
                presenter.update(w,true);
                var status:Object=presenter.stats();
                presented=Boolean(status.presented);
                lastReason=String(status.lastFallback);
                if(status.internalErrors || status.cleanupErrors)
                    throw new Error("Terrain presentation: "+status.lastError);
            } catch(error:Error){fail(error);}
        }

        private static function eligibility(w:*):String {
            if(!enabled)return "disabled";
            if(faulted)return "failed";
            if(!w || !w.loc || !w.grafon || !w.cam || !w.gg || !w.sats)return "world-not-ready";
            if(!w.grafon.sceneLarge || w.grafon.sceneChunkSide!=320)return "native-room";
            if(w.t_exit!=0 || w.allStat!=1 || w.onPause)return "world-inactive";
            if(w.sats.active || w.grafon.visSats.visible)return "sats";
            if(w.grafon.sceneWarmVerify)return "native-validation";
            if(w.cam.scaleV!=1 || w.cam.quakeX!=0 || w.cam.quakeY!=0)return "zoom-or-shake";
            if(!readSwitches())return "visual-settings-unknown";
            for each(var item:Object in switches) {
                // Getter callbacks remain owned by their modules. getPages is
                // a read-only registry contract: do not replace any item/setter.
                var value:*=item["get"].call(item);
                ++settingsReads;
                if(!(value is Boolean))return "visual-setting-type";
                if(value===true)return "visual-effect-enabled";
            }
            return "";
        }

        private static function readSwitches():Boolean {
            var holder:*=main.getChildByName("ModSettingsCarrier");
            var api:*=holder?holder["modAPI"]:null;
            if(!api || !(api.getPages is Function)) {
                if(settings!=null || switches.length){clear("settings-unavailable");}
                settings=null;settingsRevision=-1;switches=[];return false;
            }
            var revision:int=int(api.revision);
            if(api===settings && revision==settingsRevision)return switches.length==4;
            clear("settings-rebound");
            settings=api;settingsRevision=revision;switches=[];
            var wanted:Object={"realisticvision:enabled":true,"realisticvision:wallbright":true,
                "wallblend:enabled":true,"light-and-darkness:enabled":true};
            var found:Object={},items:Array=[];
            for each(var page:Object in api.getPages()) {
                if(!page || !(page.items is Array))continue;
                for each(var item:Object in page.items) {
                    if(!item)continue;
                    var key:String=String(page.modId)+":"+String(item.key);
                    if(!wanted[key])continue;
                    if(found[key] || !(item["get"] is Function))return false;
                    found[key]=true;items.push(item);
                }
            }
            if(items.length!=4)return false;
            switches=items;return true;
        }

        // Synchronous lifecycle boundary: invoked before native SATS capture,
        // scene disposal and WallBlend's immediate enable/render path.
        public static function clear(reason:String="external-reset"):void {
            lastReason=reason;
            if(!touched && !presented)return;
            ++resets;
            try {presenter.clear();}
            catch(error:Error){faulted=true;lastError=error.message;throw error;}
            touched=false;presented=false;
        }

        private static function fail(error:Error):void {
            faulted=true;lastError=error.message;
            try {clear("failed");}catch(cleanupError:Error){}
        }

        // Non-persistent runtime switch for a native/candidate comparison;
        // disabling changes presentation only and always restores native alpha.
        public static function setEnabled(value:Boolean):void {
            if(enabled==value)return;
            clear("enabled-changed");enabled=value;
            if(value && main && worldClass)update(worldClass["w"]);
        }

        public static function stats():Object {
            return {version:"scene-presentation-coordinator-1",enabled:enabled,faulted:faulted,
                presented:presented,touched:touched,lastReason:lastReason,lastError:lastError,
                updates:updates,earlyClears:earlyClears,resets:resets,settingsReads:settingsReads,
                settingsBound:switches.length==4,settingsRevision:settingsRevision,
                helper:presenter.stats()};
        }
    }
}
