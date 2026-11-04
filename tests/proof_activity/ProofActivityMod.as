package {
    import flash.desktop.NativeApplication;
    import flash.display.BitmapData;
    import flash.display.PNGEncoderOptions;
    import flash.events.Event;
    import flash.events.KeyboardEvent;
    import flash.filesystem.File;
    import flash.filesystem.FileMode;
    import flash.filesystem.FileStream;
    import flash.media.SoundMixer;
    import flash.media.SoundTransform;
    import flash.net.SharedObject;
    import flash.system.System;
    import flash.utils.Dictionary;
    import flash.utils.getDefinitionByName;
    import flash.utils.getQualifiedClassName;
    import flash.utils.getTimer;
    public class ProofActivityMod {
        private static var main:*,w:*,api:*,aim:*,cfg:Object,cls:Class;
        private static var phase:int=0,started:int,ready:int=0,age:int=0,warmAt:int,measureAt:int,previous:int,done:Boolean=false;
        private static var samples:Array=[],distribution:Array=[],keys:int=0,shotLast:*,shots:int=0,hpBefore:Number,damageEvents:int=0,lastHP:Dictionary=new Dictionary(true);
        private static var x0:Number,y0:Number,maxMove:Number=0,maxAim:Number=0,aiming:Boolean=false;
        private static var initial:Object,checks:Array=[],memoryBefore:Number,earlyTicks:int=0,measureFrames:int=0;
        private static var measuredInitial:Object;
        private static var total:Object={},lastCounter:int=0,startUnits:Array=[],seedRequested:Boolean=false;
        private static var sound:SoundTransform=new SoundTransform(0);
        private static var focusEvents:Array=[];
        private static var preparationResets:Array=[];
        private static function readJSON(file:File):Object {
            var f:FileStream=new FileStream(),result:Object;try {f.open(file,FileMode.READ);result=JSON.parse(f.readUTFBytes(f.bytesAvailable));}finally{f.close();}return result;
        }
        private static function log(s:String):void {
            var f:FileStream=new FileStream();try {f.open(File.applicationStorageDirectory.resolvePath("ProofActivity.log"),FileMode.APPEND);f.writeUTFBytes(getTimer()+" "+s+"\n");}finally{f.close();}
        }
        private static function check(name:String,ok:Boolean,detail:*=null):void {checks.push({name:name,ok:ok,detail:detail});if(!ok)throw new Error(name+" "+JSON.stringify(detail));}
        private static function capture(name:String):void {
            var bitmap:BitmapData=new BitmapData(main.stage.stageWidth,main.stage.stageHeight,false,0);
            var stream:FileStream=new FileStream();
            try {bitmap.draw(main.stage);stream.open(File.applicationStorageDirectory.resolvePath(name+".png"),FileMode.WRITE);stream.writeBytes(bitmap.encode(bitmap.rect,new PNGEncoderOptions()));}
            finally {stream.close();bitmap.dispose();}
        }
        public static function init(host:*):void {
            if(!/^pfe-proof-[0-9a-f]{32}$/.test(NativeApplication.nativeApplication.applicationID))return;
            main=host;started=getTimer();cfg=readJSON(File.applicationDirectory.resolvePath("proof-controls.json"));
            SoundMixer.soundTransform=sound;
            main.stage.nativeWindow.visible=true;
            main.stage.addEventListener(Event.ENTER_FRAME,before,false,501);
            main.stage.addEventListener(Event.ENTER_FRAME,afterAim,false,-250);
            main.stage.addEventListener(Event.ENTER_FRAME,tick,false,-1000);
            main.stage.addEventListener(Event.ACTIVATE,onFocus);
            main.stage.addEventListener(Event.DEACTIVATE,onFocus);
            main.stage.addEventListener(Event.RESIZE,onFocus);
            NativeApplication.nativeApplication.addEventListener(Event.ACTIVATE,onFocus);
            NativeApplication.nativeApplication.addEventListener(Event.DEACTIVATE,onFocus);
            log("loaded "+JSON.stringify(cfg));
        }
        private static function onFocus(e:Event):void {focusEvents.push({type:e.type,target:String(e.target),time:getTimer(),phase:phase,frame:measureFrames});}
        private static function worldStatus():Object {
            return w?{allStat:w.allStat,exit:w.t_exit,die:w.t_die,pause:w.onPause,
                pip:w.pip?{active:w.pip.active,noAct:w.pip.noAct}:null,
                player:w.gg?{x:w.gg.X,y:w.gg.Y,hp:w.gg.hp,sost:w.gg.sost,control:w.gg.ggControl}:null}:null;
        }
        private static function key(code:int,down:Boolean):void {main.stage.dispatchEvent(new KeyboardEvent(down?KeyboardEvent.KEY_DOWN:KeyboardEvent.KEY_UP,true,false,0,code));}
        private static function settingNative():Boolean {
            var c:*=main.getChildByName("ModSettingsCarrier");if(!c||!c["modAPI"])return false;
            for each(var page:Object in c["modAPI"].getPages())if(page.modId=="continuousscene")
                for each(var item:Object in page.items)if(item.key=="nativeEnabled") {item["set"](true);return item["get"]()===true;}
            return false;
        }
        private static function before(e:Event):void {
            if(done)return;
            ++earlyTicks;
            try {
                if(phase<4)return;
                var mode:String=cfg.scenario;
                var direction:int=(int(age/90)%2==0)?68:65;
                if(keys!=direction){if(keys)key(keys,false);key(direction,true);keys=direction;}
                if(mode=="fire"||mode=="diagnostic") {
                    var gun:*=w.gg.currentWeapon;
                    w.cam.celX=w.gg.X*w.cam.scaleV+w.cam.vx+450;
                    w.cam.celY=(w.gg.Y-30)*w.cam.scaleV+w.cam.vy;
                    w.ctr.keyAttack=true;
                    if(gun){gun.hold=gun.holder;gun.hp=gun.maxhp;}
                }
                if(mode=="aim"||mode=="diagnostic") {
                    var hold:Boolean=int(age/180)%2==0;
                    if(hold!=aiming){aiming=hold;if(hold)aim.keyDown(18,false,false,false);else aim.keyUp(18);}
                }
            }catch(err:Error){finish("before "+err.message+" "+err.getStackTrace());}
        }
        private static function afterAim(e:Event):void {
            if(done||phase<4||!aiming)return;
            // Deterministic controller input on the private desktop. Both arms
            // receive the same extra update; this is scripted aim, not a human mouse.
            try {aim.update(w,main.stage.stageWidth*(.5+.48*Math.sin(age*Math.PI/90)),main.stage.stageHeight*.5);}
            catch(err:Error){finish("aim "+err.message);}
        }
        private static function sampleObjects():void {
            var n:int=0,t:int=0,signature:uint=2166136261;
            for(var p:*=w.loc.firstObj;p;p=p.nobj){++n;if(p is cls&&!p.off)++t;signature=(signature^uint(p.X)) * 16777619;}
            distribution.push({frame:measureFrames,N:n,T:t,units:w.loc.units.length,signature:signature});
        }
        private static function unitSnapshot():Array {
            var units:Array=[];
            for each(var u:* in w.loc.units)units.push(u?{id:u.id,x:u.X,y:u.Y,hp:u.hp,sost:u.sost,type:String(u)}:null);
            return units;
        }
        private static function begin():void {
            api=main.getChildByName("ContinuousSceneCarrier")["nativeAPI"];aim=api.aimController();
            check("measured-product-api",api.proofActivityStats!=null);
            check("actual-arm",api.proofActivityStats().arm==cfg.arm);
            check("diagnostic-mode",api.proofActivityStats().diagnostic===Boolean(cfg.diagnostic));
            check("native-large",w.grafon.sceneLarge===true);
            check("native-adapter-active",api.state(w.land)!=null);
            check("visible-window",main.stage.nativeWindow.visible);
            var menus:int=0;
            for(var child:int=0;child<main.numChildren;++child)if(getQualifiedClassName(main.getChildAt(child)).indexOf("visMainMenu")>=0)++menus;
            check("main-menu-display-detached",menus==0,menus);
            w.ctr.clearAll();w.cam.camRun=false;w.cam.showOn=false;
            // Same seeded native map and initial one-time corridor placement.
            w.gg.setPos(841.8,4960);w.gg.dx=w.gg.dy=0;w.cam.calc(w.gg);
            x0=w.gg.X;y0=w.gg.Y;hpBefore=w.gg.hp;
            if(cfg.scenario=="fire"||cfg.scenario=="diagnostic") {
                var gun:*=w.invent.addWeapon("lmg");gun.lvl=0;gun.perslvl=0;w.gg.changeWeapon("lmg");
            }
            cls=getDefinitionByName("fe.weapon.Bullet") as Class;
            for each(var u:* in w.loc.units)if(u)startUnits.push({id:u.id,x:u.X,y:u.Y,hp:u.hp,type:String(u)});
            initial={land:w.land.act.id,stage:w.land.act.landStage,seed:w.land.rconnectLayoutSeed,units:startUnits,
                limX:w.loc.limX,limY:w.loc.limY,width:main.stage.stageWidth,height:main.stage.stageHeight,
                frameRate:main.stage.frameRate,quality:main.stage.quality,scaleV:w.cam.scaleV,csVersion:main.getChildByName("ContinuousSceneCarrier")["sceneAPI"].version,
                menuActive:w.mm.active,worldVisible:w.grafon.visual.visible,worldOnStage:w.grafon.visual.stage!=null};
            check("menu-closed",!w.mm.active);
            check("world-visible",initial.worldVisible&&initial.worldOnStage);
            if(cfg.diagnostic)capture("world-start");
            log("native world ready "+JSON.stringify({seed:initial.seed,units:startUnits.length,frameRate:initial.frameRate}));
            phase=4;warmAt=getTimer();age=0;
        }
        private static function tick(e:Event):void {
            if(done)return;
            var now:int=getTimer();
            try {
                w=getDefinitionByName("fe.World")["w"];
                if(now-started>int(cfg.seconds*1000+cfg.warmup*1000+270000))throw new Error("phase timeout "+phase);
                if(w&&w.verror&&w.verror.visible)throw new Error(w.verror.txt.text);
                if(w&&w.gg){w.godMode=true;w.gg.invulner=false;}
                if(phase==0) {
                    SoundMixer.soundTransform=sound;
                    if(w&&w.mm&&w.mm.loaded&&w.allLandsLoaded&&w.textLoaded&&settingNative()){
                        w.mm.mainMenuOff();w.newGame(-1,"Proof activity controlled validation",{propusk:true});phase=1;log("new game");
                    }
                } else if(phase==1&&w.ng_wait==0&&w.allStat==1&&w.gg&&w.loc&&w.t_exit==0){
                    if(!w.gg.ggControl||w.pip.noAct){ready=0;w.ctr.keyPressed=w.ctr.keyPressed2=true;return;}
                    if(++ready<30)return;ready=0;w.ctr.clearAll();w.pers.healAll();
                    w.game.lands["random_mane"].landStage=4;
                    getDefinitionByName("fe.loc.Land")["rconnectSeedSource"]=function(value:*):uint{return uint(cfg.seed);};
                    w.game.beginMission("random_mane");phase=2;log("travel");
                } else if(phase==2&&w.land&&w.land.act.id=="random_mane"&&w.t_exit==0&&w.allStat==1){
                    if(++ready<60)return;ready=0;begin();
                } else if(phase>=4) {
                    ++age;
                    if(w.allStat!=1||w.t_exit!=0) {
                        // Dismiss a startup menu only before measurement, then
                        // restart the entire warmup. A measured interruption fails.
                        if(phase==4&&w.pip.active&&w.t_exit==0&&preparationResets.length<2) {
                            preparationResets.push({time:now,age:age,state:worldStatus()});
                            if(keys)key(keys,false);keys=0;aim.keyUp(18);aiming=false;
                            w.pip.onoff(-1);w.ctr.clearAll();age=0;return;
                        }
                        throw new Error("world interrupted "+JSON.stringify(worldStatus()));
                    }
                    var a:Object=api.proofActivityStats();
                    var currentGun:*=w.gg.currentWeapon;
                    if(currentGun&&currentGun.b&&currentGun.b!==shotLast){++shots;shotLast=currentGun.b;}
                    for each(var u:* in w.loc.units)if(u) {
                        if(lastHP[u]!==undefined&&u.hp<lastHP[u])++damageEvents;lastHP[u]=u.hp;
                    }
                    maxMove=Math.max(maxMove,Math.abs(w.gg.X-x0));
                    var aimStats:Object=aim.statsSnapshot();maxAim=Math.max(maxAim,Math.abs(aimStats.offsetX));
                    if(phase==4&&age>=int(cfg.warmup*main.stage.frameRate)) {
                        check("target-called-in-warmup",a.updates>0,a);
                        measuredInitial={units:unitSnapshot(),world:worldStatus(),awake:api.activityStats().awake,asleep:api.activityStats().asleep};
                        api.proofActivityReset();lastCounter=0;memoryBefore=System.totalMemory;shots=damageEvents=0;age=0;
                        x0=w.gg.X;y0=w.gg.Y;maxMove=maxAim=0;
                        log("MEASURE begins");phase=5;measureAt=previous=getTimer();return;
                    }
                    if(phase==5){
                        ++measureFrames;
                        samples.push([now-previous,a.ms,a.q,a.builds,a.updates-lastCounter,api.activityStats().awake,api.activityStats().asleep,api.activityStats().leashed,w.gg.X,w.gg.Y]);
                        lastCounter=a.updates;previous=now;
                        if(measureFrames%30==1)sampleObjects();
                        if(measureFrames>=int(cfg.seconds*main.stage.frameRate)){
                            total=a;check("target-each-measured-frame",a.updates==measureFrames,{updates:a.updates,frames:measureFrames});
                            check("player-moved",maxMove>20,maxMove);
                            if(cfg.scenario=="fire"||cfg.scenario=="diagnostic")check("native-shots",shots>5,shots);
                            if(cfg.scenario=="aim"||cfg.scenario=="diagnostic")check("aim-applied",maxAim>100,maxAim);
                            if(cfg.diagnostic){check("read-timing-stable",a.changed==0,a.changed);check("shadow-state-equivalent",a.mismatches==0,a);for each(var test:Object in a.cases)check(test.name,test.ok);}
                            finish(null);return;
                        }
                    }
                }
            }catch(err:Error){finish(err.message+" "+err.getStackTrace());}
        }
        private static function finish(error:String):void {
            if(done)return;done=true;
            var elapsed:int=getTimer()-measureAt;
            try {
                if(keys)key(keys,false);if(w&&w.ctr)w.ctr.keyAttack=false;if(aim)aim.keyUp(18);
                if(api&&api.proofActivityStats)total=api.proofActivityStats();
                var result:Object={ok:error==null,error:error,config:cfg,initial:initial,checks:checks,samples:samples,
                    loader:SharedObject.getLocal("ModLoader","/").data,focusEvents:focusEvents,
                    preparationResets:preparationResets,finalWorld:worldStatus(),
                    measuredInitial:measuredInitial,
                    columns:["intervalMs","activityMs","q","builds","calls","awake","asleep","leashed","x","y"],
                    objects:distribution,elapsedMs:elapsed,earlyTicks:earlyTicks,frames:measureFrames,
                    activity:total,shots:shots,damageEvents:damageEvents,maxMove:maxMove,maxAim:maxAim,
                    memoryBefore:memoryBefore,memoryAfter:System.totalMemory,audioVolume:SoundMixer.soundTransform.volume,
                    limitation:"Private desktop, scripted native movement and optional synthetic controller aim, 1ms timer; sampled N/T; net memory is not allocation bytes."};
                var f:FileStream=new FileStream();try {f.open(File.applicationStorageDirectory.resolvePath("ProofActivity.json"),FileMode.WRITE);f.writeUTFBytes(JSON.stringify(result));}finally{f.close();}
                log("RESULT "+(error?error:"PASS")+" frames="+measureFrames);
                if(cfg.diagnostic&&initial)capture("world-end");
            }finally{NativeApplication.nativeApplication.exit(error?1:0);}
        }
    }
}
