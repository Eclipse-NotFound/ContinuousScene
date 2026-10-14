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
        public static const VERSION:String="0.3.0";
        private static const LAND:String="continuous_scene";
        private static var main:*, w:*, worldClass:Class, gameData:Class;
        private static var pool:XML, definition:XML;
        private static var ready:Boolean=false, failed:Boolean=false;
        private static var button:Sprite, label:TextField, carrier:MovieClip;
        private static var nextLog:int=0;
        public static function init(host:*):void {
            if(main) return;
            main=host;
            worldClass=getDefinitionByName("fe.World") as Class;
            gameData=getDefinitionByName("fe.GameData") as Class;
            carrier=new MovieClip(); carrier.name="ContinuousSceneCarrier";
            carrier["sceneAPI"]={version:VERSION,ready:false,refresh:refresh,travel:travel};
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
            if("scenePreload" in w.grafon) w.grafon.scenePreload=true;
            var stream:FileStream=new FileStream();
            try {
                stream.open(File.applicationDirectory.resolvePath("mods/ContinuousScene/release/scene.xml"),FileMode.READ);
                pool=new XML(stream.readUTFBytes(stream.bytesAvailable));
            } finally { stream.close(); }
            definition=<land id="continuous_scene" dif="0" locx="0" locy="0" stage="1" tip="test" acc="1" list="0"><options backwall="tBackWall" fon="fonWay" color="yellow" darkness="-120"/></land>;
            var exists:Boolean=false;
            for each(var land:XML in gameData["d"].land) if(String(land.@id)==LAND) exists=true;
            if(!exists) gameData["d"].appendChild(definition);
            w.landData[LAND]={allroom:pool,loaded:true};
            var res:*=getDefinitionByName("fe.Res");
            res["d"].appendChild(<map id="continuous_scene"><n>大场景 · 连续探索</n></map>);
            ready=true; carrier["sceneAPI"].ready=true;
            log("registered 192x60 native land");
        }
        private static function onFrame(event:Event):void {
            if(failed) return;
            try {
                w=worldClass["w"];
                if(!w || !w.grafon || !w.landData || !w.allLandsLoaded || !w.textLoaded) return;
                if(!ready) register();
                if(!ready) return;
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
            label.text=w.game.curLandId==LAND?"大场景 · 返回基地":"大场景 · 连续探索";
            button.x=540; button.y=30;
            if(!button.parent) w.vpip.addChild(button);
        }
        private static function onClick(event:MouseEvent):void { event.stopPropagation(); travel(); }
        public static function travel():void {
            if(!ready || failed || !w.game || !w.gg || !w.land || w.allStat!=1 || w.t_exit!=0 || w.game.curLandId!=w.land.act.id) return;
            var leaving:Boolean=w.game.curLandId==LAND;
            var target:String=leaving?w.game.baseId:LAND;
            if(!w.game.lands[target] || !w.game.checkTravel(target) || (!leaving && w.game.triggers["noreturn"]>0)) {
                w.gui.messText("","当前剧情暂不能旅行"); return;
            }
            w.game.gotoLand(target);
            if(w.game.curLandId==target) { w.pip.onoff(-1); log("travel requested "+target); }
        }
    }
}
