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
        public static const VERSION:String="0.7.0";
        private static const LAND:String="continuous_scene";
        private static var main:*, w:*, worldClass:Class, gameData:Class;
        private static var pool:XML, definition:XML;
        private static var ready:Boolean=false, failed:Boolean=false;
        private static var button:Sprite, label:TextField, carrier:MovieClip;
        private static var nextLog:int=0;
        private static var centeredMap:*;
        public static var nativeEnabled:Boolean=false;
        private static var settingsAPI:*;
        private static var nextSettings:int=0;
        private static var fastTransition:Boolean=false;
        public static function init(host:*):void {
            if(main) return;
            main=host;
            readPreference();
            worldClass=getDefinitionByName("fe.World") as Class;
            gameData=getDefinitionByName("fe.GameData") as Class;
            carrier=new MovieClip(); carrier.name="ContinuousSceneCarrier";
            carrier["sceneAPI"]={version:VERSION,ready:false,refresh:refresh,travel:travel};
            carrier["nativeAPI"]={prepare:NativeSceneAdapter.prepare,spawn:NativeSceneAdapter.spawn,
                coordinates:NativeSceneAdapter.coordinates,door:NativeSceneAdapter.door,state:NativeSceneAdapter.state};
            main.addChild(carrier); log("v"+VERSION+" loaded");
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
            var stream:FileStream=new FileStream();
            try {
                stream.open(File.applicationDirectory.resolvePath("mods/ContinuousScene/release/scene.xml"),FileMode.READ);
                pool=new XML(stream.readUTFBytes(stream.bytesAvailable));
            } finally { stream.close(); }
            definition=<land id="continuous_scene" dif="0" locx="0" locy="0" stage="1" tip="test" acc="1" list="0"><options backwall="tBackWall" fon="fonDarkClouds" music="music_plant_2"/></land>;
            var exists:Boolean=false;
            for each(var land:XML in gameData["d"].land) if(String(land.@id)==LAND) exists=true;
            if(!exists) gameData["d"].appendChild(definition);
            w.landData[LAND]={allroom:pool,loaded:true};
            var res:*=getDefinitionByName("fe.Res");
            res["d"].appendChild(<map id="continuous_scene"><n>大场景 · 工厂</n></map>);
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
                if(getTimer()>nextLog) {
                    nextLog=getTimer()+30000;
                    log("heartbeat land="+(w.game?w.game.curLandId:"menu"));
                }
            } catch(error:Error) {
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
            label.text=w.game.curLandId==LAND?"大场景 · 返回基地":"大场景 · 工厂测试";
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
            if(leaving) w.game.gotoLand(target); else w.game.beginMission(target);
            if(w.game.curLandId==target) { w.pip.onoff(-1); log("travel requested "+target); }
        }
        private static function readPreference():void {
            var file:File=File.applicationStorageDirectory.resolvePath("ContinuousScene.preferences.json");
            if(!file.exists)return;
            var fs:FileStream=new FileStream();
            try {fs.open(file,FileMode.READ);var data:Object=JSON.parse(fs.readUTFBytes(fs.bytesAvailable));nativeEnabled=data.nativeEnabled===true;}
            catch(error:Error) {nativeEnabled=false;}
            finally {try {fs.close();}catch(ignore:Error) {}}
        }
        public static function setNativeEnabled(value:Boolean):void {
            nativeEnabled=value;
            var fs:FileStream=new FileStream();
            var temp:File=File.applicationStorageDirectory.resolvePath("ContinuousScene.preferences.tmp");
            try {fs.open(temp,FileMode.WRITE);fs.writeUTFBytes(JSON.stringify({nativeEnabled:value}));fs.close();
                temp.moveTo(File.applicationStorageDirectory.resolvePath("ContinuousScene.preferences.json"),true);}
            finally {try {fs.close();}catch(ignore:Error) {}}
        }
        private static function connectSettings():void {
            if(getTimer()<nextSettings)return;nextSettings=getTimer()+1000;
            var holder:*=main.getChildByName("ModSettingsCarrier");
            if(!holder || !holder["modAPI"] || settingsAPI===holder["modAPI"])return;
            var api:*=holder["modAPI"];
            api.registerPage("continuousscene","连续大场景",[{
                key:"nativeEnabled",label:"以连续大场景载入原版地图",kind:"check",def:false,
                hint:"开启后，原版任务生成的主地图合并为连续场景，镜头、敌人和子弹可以跨房。\n在下次生成地图或读取存档时生效；基地、门后的独立房间和挑战区域保留原版入口。地图刷新遵循原版任务规则。",
                get:function():* {return nativeEnabled;},set:function(value:*):void {setNativeEnabled(Boolean(value));}
            }],null,"连续大场景 · 当前地图保持原有模式；设置自动保存。");
            settingsAPI=api;log("settings registered continuousscene");
        }
    }
}
