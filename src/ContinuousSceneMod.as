package {
    import flash.display.MovieClip;
    import flash.display.Sprite;
    import flash.events.Event;
    import flash.events.MouseEvent;
    import flash.filesystem.File;
    import flash.filesystem.FileMode;
    import flash.filesystem.FileStream;
    import flash.text.TextField;
    import flash.text.TextFormat;
    import flash.utils.getDefinitionByName;
    import flash.utils.getQualifiedClassName;
    import flash.utils.getTimer;

    /** Production entry only: no new game, test enemies, movement or save-slot writes. */
    public class ContinuousSceneMod {
        public static const VERSION:String="0.9.8";
        private static const LAND:String="continuous_scene";
        private static var main:*, w:*, worldClass:Class, gameData:Class;
        private static var pool:XML, definition:XML;
        private static var ready:Boolean=false, failed:Boolean=false;
        private static var button:Sprite, label:TextField, carrier:MovieClip;
        private static var nextLog:int=0;
        private static var centeredMap:*;
        public static var nativeEnabled:Boolean=false;
        public static var alicornRelayPercent:int=0;
        private static var settingsAPI:*;
        private static var nextSettings:int=0;
        private static var fastTransition:Boolean=false;
        private static var authored:Boolean=false;
        private static var nextMapCheck:int=0;
        /** Intent-preserving viewport culling; wrapper visibility only, the
         * game keeps exclusive ownership of every object's own visible state. */
        public static var objectCulling:SceneObjectCulling=new SceneObjectCulling();
        public static var objectCullingEnabled:Boolean=true;
        private static var objectCullingFailed:Boolean=false;
        /** Aim-look pan toward the mouse (continuous scenes only). Runs after
         * the native camera recenter; guarded so a fault only disables itself. */
        public static var aim:SceneAimController=new SceneAimController();
        private static var aimFailed:Boolean=false;
        public static function init(host:*):void {
            if(main) return;
            main=host;
            readPreference();
            worldClass=getDefinitionByName("fe.World") as Class;
            gameData=getDefinitionByName("fe.GameData") as Class;
            carrier=new MovieClip(); carrier.name="ContinuousSceneCarrier";
            carrier["sceneAPI"]={version:VERSION,ready:false,refresh:refresh,travel:travel};
            carrier["nativeAPI"]={prepare:NativeSceneAdapter.prepare,spawn:NativeSceneAdapter.spawn,
                coordinates:NativeSceneAdapter.coordinates,door:NativeSceneAdapter.door,state:NativeSceneAdapter.state,
                moveOffset:NativeSceneAdapter.moveOffset,reward:NativeSceneAdapter.reward,
                takeXP:NativeSceneAdapter.takeXP,detecting:NativeSceneAdapter.detecting,
                activity:NativeSceneActivity.update,sleeping:NativeSceneActivity.sleeping,
                wake:NativeSceneActivity.wake,activityStats:NativeSceneActivity.stats,
                activityBudget:NativeSceneActivity.budget,
                objectCullingEnabled:getObjectCullingEnabled,objectCullingEnabledSet:setObjectCullingEnabled,
                objectCullingStats:getObjectCullingStats,objectCullingController:getObjectCullingController,
                aimStats:getAimStats,aimController:getAimController,
                alicornAllow:SceneAlicornAlerts.allow,alicornReceive:SceneAlicornAlerts.receive,
                alicornClear:SceneAlicornAlerts.clear};
            main.addChild(carrier); log("v"+VERSION+" loaded");
            SatsVisibleGuard.install(main);
            ScenePresentationCoordinator.install(main);
            aim.install(main.stage);
            main.stage.addEventListener(Event.ENTER_FRAME,onFrame,false,-200,true);
        }
        private static function log(message:String):void {
            var stream:FileStream=new FileStream();
            try {
                stream.open(File.applicationStorageDirectory.resolvePath("ContinuousScene.log"),FileMode.APPEND);
                stream.writeUTFBytes(getTimer()+" [ContinuousScene] "+message+"\n");
            } finally { stream.close(); }
        }
        private static function register():void {
            // Scanner may discover this on other versions: refuse an unpatched host.
            if(!("sceneTrack" in w.grafon)) {
                failed=true; log("host patch missing: scene entry disabled"); return;
            }
            if("scenePreload" in w.grafon) w.grafon.scenePreload=false;
            try {pool=readScene();}
            catch(mapError:Error) {
                log("authored map invalid at startup: "+mapError.message);
                pool=readScene(true);
            }
            definition=<land id="continuous_scene" dif="0" locx="0" locy="0" stage="1" tip="test" acc="1" list="0"><options backwall="tBackWall" fon="fonDarkClouds" music="music_plant_2"/></land>;
            applyEnvironment();
            var exists:Boolean=false;
            for each(var land:XML in gameData["d"].land) if(String(land.@id)==LAND) exists=true;
            if(!exists) gameData["d"].appendChild(definition);
            w.landData[LAND]={allroom:pool,loaded:true};
            var res:*=getDefinitionByName("fe.Res");
            res["d"].appendChild(<map id="continuous_scene"><n>{String(pool.room.@name)||"大地图"}</n></map>);
            ready=true; carrier["sceneAPI"].ready=true;
            log("registered "+pool.room.@sceneWidth+"x"+pool.room.@sceneHeight+" native land kind="+pool.@sceneKind);
        }
        private static function onFrame(event:Event):void {
            if(failed) return;
            try {
                w=worldClass["w"];
                if(!w || !w.grafon || !w.landData || !w.allLandsLoaded || !w.textLoaded) return;
                if(!ready) register();
                if(!ready) return;
                NativeSceneAdapter.attach(w);
                connectSettings();
                advanceSceneFade();
                if(w.game && !w.game.lands[LAND]) {
                    var LandAct:Class=getDefinitionByName("fe.loc.LandAct") as Class;
                    var act:*=new LandAct(definition);
                    act.allroom=pool; act.loaded=true; w.game.lands[LAND]=act;
                }
                refresh();
                ScenePresentationCoordinator.update(w);
                // Before the culling pass: its viewport rect must follow the
                // panned view, not the un-panned player-centered one.
                if(!aimFailed) {
                    try {aim.update(w,main.stage.mouseX,main.stage.mouseY);}
                    catch(aimError:Error) {
                        // Same containment rule as culling: a fault disables
                        // only this feature, never the whole entry.
                        aimFailed=true;aim.enabled=false;aim.reset("fault");
                        log("aim look disabled: "+aimError.message);
                    }
                }
                if(!objectCullingFailed) {
                    try {objectCulling.update(w,objectCullingEnabled && w.allStat==1 && w.t_exit==0);}
                    catch(cullingError:Error) {
                        // A culling fault must never take down the whole entry.
                        objectCullingFailed=true;objectCullingEnabled=false;
                        try {objectCulling.clear();} catch(cleanupError:Error) {}
                        log("object culling disabled: "+cullingError.message);
                    }
                }
                if(getTimer()>nextLog) {
                    nextLog=getTimer()+30000;
                    log("heartbeat land="+(w.game?w.game.curLandId:"menu"));
                }
            } catch(error:Error) {
                try {ScenePresentationCoordinator.clear("entry-error");} catch(ignorePresentation:Error) {}
                failed=true; carrier["sceneAPI"].ready=false;
                if(button && button.parent) button.parent.removeChild(button);
                log("ERROR "+error.message+" "+error.getStackTrace());
            }
        }
        public static function refresh():void {
            if(!ready || !w || !w.game || !w.pip || !w.pip.active || getQualifiedClassName(w.pip.currentPage)!="fe.inter::PipPageInfo") {
                centeredMap=null;
                if(button && button.parent) button.parent.removeChild(button);
                return;
            }
            if(!button) {
                button=new Sprite(); button.name="ContinuousSceneTravel";
                button.graphics.beginFill(0x111b18,0.95);
                button.graphics.lineStyle(1,0x91bc94); button.graphics.drawRect(0,0,170,26); button.graphics.endFill();
                button.buttonMode=true; button.mouseChildren=false;
                label=new TextField(); label.width=170; label.height=26; label.selectable=false;
                label.defaultTextFormat=new TextFormat("Microsoft YaHei",13,0xd5ebbc,false,null,null,null,null,"center");
                button.addChild(label); button.addEventListener(MouseEvent.CLICK,onClick);
            }
            if(getTimer()>nextMapCheck) {nextMapCheck=getTimer()+1000;authored=File.applicationDirectory.resolvePath("mods/ContinuousScene/maps/active.xml").exists;}
            label.text=w.game.curLandId==LAND?"大地图 · 返回基地":(authored?"大地图 · 编辑地图":"大场景 · 工厂测试");
            button.x=540; button.y=30;
            if(!button.parent) w.vpip.addChild(button);
            // The native page carries its previous pan between lands. Center a
            // newly opened large map once; subsequent manual pan/zoom stays free.
            var page:*=w.pip.currentPage;
            var map:*=page.map;
            if(w.grafon.sceneLarge && map && map.parent && map.parent.parent.visible) {
                if(centeredMap!==map) {
                    page.funCenter(null);
                    // If an axis fits, show its whole extent. Centering only
                    // the player at an edge would needlessly crop a small map.
                    var mapFrame:*=map.parent.parent.getChildByName("fon");
                    if(mapFrame) {
                        if(map.width<=mapFrame.width) map.parent.x=(mapFrame.width-map.width)/2-map.x;
                        if(map.height<=mapFrame.height) map.parent.y=(mapFrame.height-map.height)/2-map.y;
                    }
                    centeredMap=map;
                }
            } else centeredMap=null;
        }
        private static function advanceSceneFade():void {
            if(!w.game || !w.cam || !w.vblack || !w.gg) return;
            if(w.t_exit==0) {fastTransition=false;return;}
            if(w.t_exit>20 && !fastTransition) {
                var target:*=w.game.lands[w.game.curLandId];
                fastTransition=w.grafon.sceneLarge || w.game.curLandId==LAND ||
                    (nativeEnabled && target && target.tip!="base");
            }
            if(!fastTransition) return;
            if(w.t_exit==1) {w.t_exit=0;fastTransition=false;return;} // Native HUD restoration already ran.
            if(w.t_exit==18 && w.clickReq<=0) w.t_exit=17; // No click gate to wait at 17.
            // Native exitStep still executes every lifecycle milestone: 20
            // shows loading, 19 generates, 18/17 wait for required input,
            // 16 restores control, and 1 restores the HUD. Only the decorative
            // fade's idle ticks are shortened; no simulation/render work moves
            // out of the measured entry or into startup.
            if(w.t_exit>21) {
                if(w.vblack.alpha>=1) w.t_exit=21;
                else if(w.cam.dblack>0) w.cam.dblack=100;
            } else if(w.t_exit<=16 && w.t_exit>2) {
                if(w.cam.dblack<0) w.cam.dblack=-100;
                if(!w.vblack.visible || w.vblack.alpha<=0) w.t_exit=2;
            }
        }
        private static function onClick(event:MouseEvent):void { event.stopPropagation(); travel(); }
        public static function travel():void {
            if(!ready || failed || !w || !w.game || !w.gg || !w.land || w.t_exit!=0 || w.game.curLandId!=w.land.act.id) return;
            // World.step sets allStat=2 while PipBuck is open: that is the normal button state.
            var infoMenu:Boolean=w.pip && w.pip.active && getQualifiedClassName(w.pip.currentPage)=="fe.inter::PipPageInfo";
            if((w.allStat!=1 && !(w.allStat==2 && infoMenu)) || w.sats.active || w.stand.active || w.gui.guiPause) {
                w.gui.messText("","请先结束当前操作，再使用大场景旅行"); return;
            }
            if(w.pip.noAct) { w.gui.infoText("noAct"); return; }
            var leaving:Boolean=w.game.curLandId==LAND;
            var target:String=leaving?w.game.baseId:LAND;
            if(!w.game.lands[target] || !w.game.checkTravel(target) || (!leaving && w.game.triggers["noreturn"]>0)) {
                w.gui.messText("","当前剧情暂不能旅行"); return;
            }
            if(leaving) w.game.gotoLand(target); else {
                // Re-read the authored file on each fresh expedition; editing never changes a live map.
                try {
                    var next:XML=readScene();
                    pool=next;applyEnvironment();
                    var res:*=getDefinitionByName("fe.Res");
                    for each(var title:XML in res["d"].map) if(String(title.@id)==LAND) title.n=String(pool.room.@name)||"大地图";
                    w.landData[LAND]={allroom:pool,loaded:true};
                    var LandAct:Class=getDefinitionByName("fe.loc.LandAct") as Class;
                    var act:*=new LandAct(definition);act.allroom=pool;act.loaded=true;
                    w.game.lands[LAND]=act;
                } catch(error:Error) {w.gui.messText("","大地图载入失败："+error.message);log("map rejected "+error.message);return;}
                w.game.beginMission(target);
            }
            if(w.game.curLandId==target) { w.pip.onoff(-1); log("travel requested "+target); }
        }
        private static function readScene(fallback:Boolean=false):XML {
            var file:File=File.applicationDirectory.resolvePath("mods/ContinuousScene/maps/active.xml");
            authored=file.exists;
            if(!authored || fallback) file=File.applicationDirectory.resolvePath("mods/ContinuousScene/release/scene.xml");
            if(file.size>16*1024*1024) throw new Error("地图文件超过 16 MB。");
            var stream:FileStream=new FileStream();var doc:XML;
            try {stream.open(file,FileMode.READ);doc=new XML(stream.readUTFBytes(stream.bytesAvailable));}
            finally {stream.close();}
            var room:XML=SingleSceneDocument.validate(doc);
            return SingleSceneDocument.pack(room,doc.land[0]);
        }
        private static function applyEnvironment():void {
            if(!definition) return;
            definition.options=<options backwall="tBackWall" fon="fonDarkClouds" music="music_plant_2"/>;
            if(pool.land.options.length()) for each(var a:XML in pool.land.options[0].attributes()) definition.options[0].@[a.name()]=a;
        }
        private static function readPreference():void {
            var file:File=File.applicationStorageDirectory.resolvePath("ContinuousScene.preferences.json");
            if(!file.exists)return;
            var fs:FileStream=new FileStream();
            try {fs.open(file,FileMode.READ);var data:Object=JSON.parse(fs.readUTFBytes(fs.bytesAvailable));
                nativeEnabled=data.nativeEnabled===true;alicornRelayPercent=normalizePercent(Number(data.alicornRelayPercent));
                applyAimPreferences(data);}
            catch(error:Error) {nativeEnabled=false;alicornRelayPercent=0;}
            finally {try {fs.close();}catch(ignore:Error) {}}
        }
        /** Backward compatible: a preferences file from before 0.9.8 has no
         * aim fields and keeps the in-code defaults. */
        private static function applyAimPreferences(data:Object):void {
            if(!data)return;
            if("aimEnabled" in data)aim.enabled=data.aimEnabled===true;
            if("aimTrigger" in data) {
                var trigger:Number=Number(data.aimTrigger);
                aim.triggerModifier=(trigger>=0&&trigger<=2&&trigger==int(trigger))?int(trigger):0;
            }
            aim.keybind=sanitizeKeybind(data.aimKeybind);
            if("aimToggle" in data)aim.toggleMode=data.aimToggle===true;
            if("aimDistancePercent" in data) {
                var percent:Number=Number(data.aimDistancePercent);
                aim.distanceScale=isFinite(percent)?Math.max(0.5,Math.min(1.5,percent/100)):1;
            }
            if("aimSpeed" in data) {
                var speed:Number=Number(data.aimSpeed);
                aim.speedIndex=(speed>=1&&speed<=3&&speed==int(speed))?int(speed):2;
            }
        }
        /** Mirrors the loader's keybind normalization: plain key codes only
         * (8..222), bare modifiers 16/17/18 and 91/92/93 rejected, code 0
         * meaning "unbound". Anything else falls back to unbound. */
        private static function sanitizeKeybind(value:*):Object {
            if(value==null)return null;
            var n:Number=Number(value.code);
            if(!isFinite(n)||n!=int(n))return null;
            var code:int=int(n);
            if(code==0)return {code:0,ctrl:false,alt:false,shift:false};
            if(code<8||code>222||code==16||code==17||code==18||code==91||code==92||code==93)return null;
            return {code:code,ctrl:value.ctrl===true,alt:value.alt===true,shift:value.shift===true};
        }
        public static function setNativeEnabled(value:Boolean):void {
            nativeEnabled=value;
            writePreference();
        }
        private static function normalizePercent(value:Number):int {
            return isFinite(value)?int(Math.max(0,Math.min(100,Math.round(value)))):0;
        }
        public static function setAlicornRelayPercent(value:Number):void {
            alicornRelayPercent=normalizePercent(value);
            writePreference();
        }
        private static function writePreference():void {
            var fs:FileStream=new FileStream();
            var temp:File=File.applicationStorageDirectory.resolvePath("ContinuousScene.preferences.tmp");
            try {fs.open(temp,FileMode.WRITE);fs.writeUTFBytes(JSON.stringify({nativeEnabled:nativeEnabled,alicornRelayPercent:alicornRelayPercent,
                aimEnabled:aim.enabled,aimTrigger:aim.triggerModifier,
                aimKeybind:aim.keybind||{code:0,ctrl:false,alt:false,shift:false},
                aimToggle:aim.toggleMode,aimDistancePercent:Math.round(aim.distanceScale*100),aimSpeed:aim.speedIndex}));fs.close();
                temp.moveTo(File.applicationStorageDirectory.resolvePath("ContinuousScene.preferences.json"),true);}
            finally {try {fs.close();}catch(ignore:Error) {}}
        }
        private static function getObjectCullingController():* {return objectCulling;}
        private static function getObjectCullingEnabled():* {return objectCullingEnabled;}
        private static function setObjectCullingEnabled(value:*):void {
            objectCullingEnabled=Boolean(value);
            if(!objectCullingEnabled)objectCulling.clear();
        }
        private static function getObjectCullingStats():* {
            return objectCulling.stats();
        }
        private static function getAimStats():* {return aim.statsSnapshot();}
        private static function getAimController():* {return aim;}
        private static function connectSettings():void {
            if(getTimer()<nextSettings)return;nextSettings=getTimer()+1000;
            var holder:*=main.getChildByName("ModSettingsCarrier");
            if(!holder || !holder["modAPI"] || settingsAPI===holder["modAPI"])return;
            var api:*=holder["modAPI"];
            api.registerPage("continuousscene","连续大场景",[{
                key:"nativeEnabled",label:"以连续大场景载入原版地图",kind:"check",def:false,
                hint:"开启后，原版任务生成的主地图合并为连续场景，镜头、敌人和子弹可以跨房。\n在下次生成地图或读取存档时生效；基地、门后的独立房间和挑战区域保留原版入口。地图刷新遵循原版任务规则。",
                get:function():* {return nativeEnabled;},set:function(value:*):void {setNativeEnabled(Boolean(value));}
            },{
                key:"alicornRelayPercent",label:"天角兽接力报警概率",kind:"slider",def:0,min:0,max:100,step:1,suffix:"%",
                hint:"仅影响连续大场景。每次报警覆盖以发送者为中心的一间原版房间范围，可跨旧房间边界。\n0%：接报者不再转发；100%：接力不限次数，每一跳仍受范围限制。\n每只接报天角兽在本轮警戒中只判定一次，重复接报或随后看见玩家不会重抽；原版警戒结束后可重新判定。修改对下次接报生效。",
                get:function():* {return alicornRelayPercent;},set:function(value:*):void {setAlicornRelayPercent(Number(value));}
            },{
                key:"aimEnabled",label:"瞄准模式（视野随准星延展）",kind:"check",def:true,
                hint:"仅连续大场景生效。按住触发键时，镜头朝鼠标方向平滑延展视野，松开自动回中；\n用于找回单房间模式下的远距离视野。射击与拾取判定保持精确。",
                get:function():* {return aim.enabled;},set:function(value:*):void {aim.enabled=Boolean(value);writePreference();}
            },{
                key:"aimTrigger",label:"内建触发键",kind:"slider",min:0,max:2,step:1,def:0,
                hint:"0=左Alt（默认）；1=左Ctrl；2=停用内建键（仅用自定义键触发）。\nAlt/Ctrl 为裸修饰键，不占用原版任何按键绑定。",
                get:function():* {return aim.triggerModifier;},set:function(value:*):void {aim.triggerModifier=int(Number(value));writePreference();}
            },{
                key:"aimKey",label:"自定义触发键（可选）",kind:"keybind",def:{code:0,ctrl:false,alt:false,shift:false},
                hint:"额外的瞄准触发键，可与内建键并存，默认未绑定。\n鼠标侧键不受运行时支持，请选键盘键；单键会自动避开原版已占用键。",
                get:function():* {return aim.keybind?{code:aim.keybind.code,ctrl:aim.keybind.ctrl,alt:aim.keybind.alt,shift:aim.keybind.shift}:{code:0,ctrl:false,alt:false,shift:false};},
                set:function(value:*):void {aim.keybind=sanitizeKeybind(value);writePreference();}
            },{
                key:"aimToggleMode",label:"切换模式（默认长按）",kind:"check",def:false,
                hint:"长按：按住触发看远处，松开立即回中。\n切换：按一次进入瞄准，再按一次退出；窗口失焦时自动复位。",
                get:function():* {return aim.toggleMode;},set:function(value:*):void {aim.toggleMode=Boolean(value);writePreference();}
            },{
                key:"aimDistance",label:"视野延展幅度",kind:"slider",min:50,max:150,step:5,def:100,suffix:"%",
                hint:"镜头最多偏离角色的距离比例。100%=横向约700像素、纵向约380像素（默认）。\n50%轻探视野，150%适合狙击枪远距索敌。",
                get:function():* {return Math.round(aim.distanceScale*100);},set:function(value:*):void {aim.distanceScale=Math.max(0.5,Math.min(1.5,Number(value)/100));writePreference();}
            },{
                key:"aimSpeed",label:"推移速度（1慢 2中 3快）",kind:"slider",min:1,max:3,step:1,def:2,
                hint:"视野延展与回中的响应速度，默认 2（中）。",
                get:function():* {return aim.speedIndex;},set:function(value:*):void {aim.speedIndex=Math.max(1,Math.min(3,int(Number(value))));writePreference();}
            }],null,"连续大场景 · 当前地图保持原有模式；设置自动保存。");
            settingsAPI=api;log("settings registered continuousscene");
        }
    }
}
