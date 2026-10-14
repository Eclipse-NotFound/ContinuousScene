package {
    import flash.desktop.NativeApplication;
    import flash.display.BitmapData;
    import flash.display.PNGEncoderOptions;
    import flash.events.Event;
    import flash.events.UncaughtErrorEvent;
    import flash.filesystem.File;
    import flash.filesystem.FileMode;
    import flash.filesystem.FileStream;
    import flash.geom.Rectangle;
    import flash.geom.Matrix;
    import flash.system.System;
    import flash.utils.ByteArray;
    import flash.utils.getDefinitionByName;
    import flash.utils.getTimer;

    public class ContinuousSceneMod {
        private static var main:*;
        private static var w:*;
        private static var phase:int = 0;
        private static var ticks:int = 0;
        private static var phaseTick:int = 0;
        private static var phaseTime:int = 0;
        private static var started:int;
        private static var lastTime:int;
        private static var deltas:Array = [];
        private static var walkingDeltas:Array = [];
        private static var report:Object = {version:"0.1.0", assertions:[], samples:[]};
        private static var scene:*;
        private static var initialPlayer:*;
        private static var manual:Boolean = false;
        private static var stopped:Boolean = false;
        private static var enemy:*;
        private static var bullet:*;
        private static var grenade:*;
        private static var damageTile:*;
        private static var previousHP:Number;
        private static var crossedBullet:Boolean = false;
        private static var crossedGrenade:Boolean = false;
        private static var crossedVertical:Boolean = false;
        private static var walkingMisses:int;
        private static var shots:int = 0;
        private static var quick:Boolean = false;

        public static function init(host:*):void {
            var descriptor:XML = NativeApplication.nativeApplication.applicationDescriptor;
            var ns:Namespace = descriptor.namespace();
            if(String(descriptor.ns::id) != "remains.continuousscene.dev") return;
            main = host;
            File.applicationStorageDirectory.createDirectory();
            manual = File.applicationDirectory.resolvePath("manual.flag").exists;
            quick = File.applicationDirectory.resolvePath("quick.flag").exists;
            report.mode = manual ? "manual" : quick ? "combat-only" : "full";
            report.startedUTC = new Date().toUTCString();
            started = lastTime = getTimer();
            write("ContinuousScene.log","[ContinuousScene] v0.1.0 init manual=" + manual + "\n",false);
            host.stage.addEventListener(Event.ENTER_FRAME,tick,false,0,true);
            host.loaderInfo.uncaughtErrorEvents.addEventListener(UncaughtErrorEvent.UNCAUGHT_ERROR,onError);
        }
        private static function onError(e:UncaughtErrorEvent):void {
            fail("uncaught",String(e.error) + (e.error is Error ? Error(e.error).getStackTrace() : ""));
        }
        private static function cls(name:String):Class { return getDefinitionByName(name) as Class; }
        private static function read(path:String):String {
            var fs:FileStream = new FileStream();
            fs.open(File.applicationDirectory.resolvePath(path),FileMode.READ);
            var text:String = fs.readUTFBytes(fs.bytesAvailable); fs.close(); return text;
        }
        private static function write(path:String,text:String,append:Boolean=true):void {
            var fs:FileStream = new FileStream();
            fs.open(File.applicationStorageDirectory.resolvePath(path),append?FileMode.APPEND:FileMode.WRITE);
            fs.writeUTFBytes(text); fs.close();
        }
        private static function log(message:String):void { write("ContinuousScene.log",getTimer()+" "+message+"\n"); }
        private static function assertThat(name:String,ok:Boolean,detail:* = null):void {
            report.assertions.push({name:name,ok:ok,detail:detail});
            log((ok?"PASS ":"FAIL ")+name+" "+JSON.stringify(detail));
            if(!ok) throw new Error("Assertion failed: "+name);
        }
        private static function next(value:int):void { phase=value; phaseTick=ticks; phaseTime=getTimer(); log("PHASE "+value); }
        private static function fail(name:String,detail:String):void {
            if(stopped) return;
            log("ERROR "+name+" "+detail);
            report.error={name:name,detail:detail}; finish(false);
        }
        private static function capture(name:String):void {
            var bitmap:BitmapData = new BitmapData(main.stage.stageWidth,main.stage.stageHeight,false,0);
            bitmap.draw(main.stage);
            var bytes:ByteArray = bitmap.encode(bitmap.rect,new PNGEncoderOptions());
            var fs:FileStream=new FileStream();
            fs.open(File.applicationStorageDirectory.resolvePath(name+".png"),FileMode.WRITE);
            fs.writeBytes(bytes); fs.close(); bitmap.dispose();
        }
        private static function finish(ok:Boolean):void {
            stopped=true;
            if(w && w.ctr) w.ctr.clearAll();
            report.ok=ok; report.elapsedMs=getTimer()-started;
            report.frameDeltas=deltas;
            report.walkingFrameDeltas=walkingDeltas;
            report.memoryMB=System.totalMemoryNumber/1048576;
            write("result.json",JSON.stringify(report,null,2),false);
            log("RESULT "+(ok?"PASS":"FAIL"));
            main.stage.removeEventListener(Event.ENTER_FRAME,tick);
            if(!manual) NativeApplication.nativeApplication.exit(ok?0:1);
        }
        private static function registerScene():void {
            var definition:XML=<land id="continuous_scene" dif="0" locx="0" locy="0" stage="1" tip="test" acc="1"><options backwall="tBackWall" fon="fonWay" color="yellow" darkness="-120"/></land>;
            // Register before Game constructs its lands, including on native save reload.
            cls("fe.GameData")["d"].appendChild(definition);
            w.landData["continuous_scene"]={allroom:new XML(read("scene.xml")),loaded:true};
            log("scene definition registered");
        }
        private static function sample():void {
            var row:Object={tick:ticks,x:w.gg.X,y:w.gg.Y,cameraX:w.cam.vx,cameraY:w.cam.vy,
                originX:w.grafon.sceneX,originY:w.grafon.sceneY,redraws:w.grafon.sceneRedraws,
                drawMs:w.grafon.sceneDrawMs,memMB:System.totalMemoryNumber/1048576,
                resident:w.grafon.sceneResident,misses:w.grafon.sceneMisses,
                pose:w.gg.animState,animOff:w.gg.animOff,alive:w.gg.sost,hp:w.gg.hp};
            report.samples.push(row); log("SAMPLE "+JSON.stringify(row));
        }
        private static function tick(event:Event):void {
            if(stopped) return;
            ++ticks;
            var now:int=getTimer();
            if(!manual && phase>=3) deltas.push(now-lastTime);
            if(!manual && (phase==3 || phase==4) && ticks-phaseTick>32) walkingDeltas.push(now-lastTime);
            lastTime=now;
            try {
                w=cls("fe.World")["w"];
                if(ticks%300==0) log("HEARTBEAT phase="+phase+" allStat="+w.allStat+" ng="+w.ng_wait+" exit="+w.t_exit+" land="+(w.land?w.land.act.id:"null")+" requested="+(w.game?w.game.curLandId:"null"));
                if(w.verror && w.verror.visible) { fail("game-dialog",String(w.verror.txt.text)); return; }
                if(!manual && now-started>240000) throw new Error("Timed out phase="+phase);
                if(!manual && phase>=11 && now-phaseTime>18000) throw new Error("Travel/load timed out phase="+phase);
                if(phase==0 && w.landData && w.mm && w.mm.loaded && w.allLandsLoaded && w.textLoaded) {
                    registerScene();
                    w.mm.active=false;
                    w.newGame(-1,"Continuous Scene",{propusk:true});
                    next(1);
                } else if(phase==1 && w.ng_wait==0 && w.allStat==1 && w.gg && w.loc) {
                    w.pers.healAll(); w.game.gotoLand("continuous_scene"); next(2);
                } else if(phase==2 && w.land && w.land.act.id=="continuous_scene" && w.game.curLandId=="continuous_scene" && w.allStat==1 && w.t_exit==0) {
                    scene=w.loc; initialPlayer=w.gg;
                    assertThat("scene-size",scene.spaceX==192 && scene.spaceY==60,{x:scene.limX,y:scene.limY});
                    assertThat("single-location",scene==w.land.locs[0][0][0]);
                    w.catPause=false; w.gg.ggControl=true; w.ctr.active=true;
                    w.gg.setLocPos(320,2159); w.gg.dx=0; w.gg.dy=0;
                    w.cam.setZoom(0); w.vblack.alpha=0; w.vblack.visible=false;
                    if(manual) {
                        for each(var enemyX:int in [2100,4300,6500]) scene.createUnit("rat",enemyX,2159,true,<obj/>);
                        main.stage.nativeWindow.visible=true;
                        main.stage.nativeWindow.activate();
                        log("MANUAL READY: native controls, three rats, fresh isolated game");
                    }
                    next(3);
                } else if(phase==3) {
                    if(ticks-phaseTick==30) { capture("scene-start"); sample(); walkingMisses=w.grafon.sceneMisses; }
                    if(manual) return;
                    if(quick && ticks-phaseTick>=30) { startCombat(); return; }
                    w.ctr.keyRight=true;
                    if(ticks%60==0) sample();
                    assertIdentity();
                    if(w.gg.X>6500) {
                        w.ctr.keyRight=false;
                        assertThat("walk-across-three-old-rooms",w.gg.X>5760,w.gg.X);
                        assertThat("window-updated",w.grafon.sceneRedraws>3,w.grafon.sceneRedraws);
                        capture("scene-east"); next(4);
                    }
                } else if(phase==4) {
                    w.ctr.keyLeft=true;
                    assertIdentity();
                    if(ticks%60==0) sample();
                    if(w.gg.X<400) {
                        w.ctr.keyLeft=false;
                        assertThat("walk-back",true,w.gg.X);
                        assertThat("scroll-preload-no-misses",w.grafon.sceneMisses==walkingMisses,{start:walkingMisses,end:w.grafon.sceneMisses});
                        assertThat("bounded-resident-chunks",w.grafon.sceneResident<=40,w.grafon.sceneResident);
                        capture("scene-return"); sample();
                        startCombat();
                    }
                } else if(phase==5) {
                    assertIdentity();
                    if(ticks%30==0) log("CHASE x="+enemy.X+" target="+(enemy.celUnit===w.gg));
                    if(enemy.X>2050 && enemy.celUnit===w.gg) {
                        assertThat("enemy-chases-across-room-and-render-boundaries",enemy.loc===scene && enemy.celUnit===w.gg,{x:enemy.X,start:1780});
                        capture("enemy-crossing");
                        scene.remObj(enemy); scene.units.splice(scene.units.indexOf(enemy),1);
                        w.gg.setLocPos(1700,2159); w.gg.dx=0;
                        enemy=scene.createUnit("raider",2200,2159,true,<obj tr="1" code="cs-target"/>);
                        enemy.controlOn=false; enemy.hp=enemy.maxhp=300;
                        previousHP=enemy.hp; fireTestBullet();
                        var Phis:Class=cls("fe.weapon.PhisBullet");
                        grenade=new Phis(w.gg,1780,2040,null);
                        grenade.dx=25; grenade.dy=-6; grenade.vel=25; grenade.liv=150;
                        next(6);
                    } else if(ticks-phaseTick>360) throw new Error("Enemy did not cross seam: x="+enemy.X);
                } else if(phase==6) {
                    assertIdentity();
                    if(bullet.X>2000 && bullet.loc===scene) crossedBullet=true;
                    if(grenade.X>2000 && grenade.loc===scene) crossedGrenade=true;
                    if(ticks-phaseTick==40 && enemy.hp==previousHP) fireTestBullet();
                    if(ticks-phaseTick>45 && enemy.hp<previousHP) {
                        assertThat("bullet-crosses-and-damages",crossedBullet,{before:previousHP,after:enemy.hp,x:bullet.X});
                        assertThat("physical-projectile-crosses",crossedGrenade,{x:grenade.X,y:grenade.Y});
                        capture("projectile-hit"); scene.remObj(grenade);
                        w.godMode=true;
                        w.gg.setLocPos(1760,850); w.gg.dx=0; w.gg.dy=0;
                        next(7);
                    } else if(ticks-phaseTick>100) throw new Error("Bullet did not damage live target");
                } else if(phase==7) {
                    assertIdentity();
                    if(w.gg.Y>1000 && w.gg.Y<2000) crossedVertical=true;
                    if(w.gg.Y>=2159 && ticks-phaseTick>30) {
                        assertThat("vertical-continuity-and-floor",crossedVertical && w.gg.Y<2162,{y:w.gg.Y,cameraY:w.cam.vy});
                        w.godMode=false; w.pers.healAll();
                        w.gg.setLocPos(3020,2159); w.gg.dx=0;
                        damageTile=scene.getTile(80,48);
                        assertThat("destructible-tile-exists",damageTile.phis>0,damageTile.front);
                        assertThat("native-destruction-threshold",!damageTile.indestruct && damageTile.thre<=1500,{hp:damageTile.hp,threshold:damageTile.thre});
                        var Bullet:Class=cls("fe.weapon.Bullet");
                        bullet=new Bullet(w.gg,3220,2040,cls("visualBullet"));
                        bullet.dy=-30; bullet.vel=30; bullet.destroy=1500; bullet.damage=25; bullet.liv=80; bullet.tipDecal=1;
                        next(8);
                    }
                } else if(phase==8) {
                    if(ticks-phaseTick>20 && damageTile.phis==0) {
                        assertThat("projectile-destroys-tile",damageTile.front=="");
                        capture("terrain-destroyed");
                        w.gg.setLocPos(7100,2159); w.gg.dx=0; next(9);
                    } else if(ticks-phaseTick>70) throw new Error("Terrain projectile did not break tile");
                } else if(phase==9 && ticks-phaseTick>30) {
                    assertThat("chunks-evicted",w.grafon.sceneEvictions>0,w.grafon.sceneEvictions);
                    w.gg.setLocPos(3020,2159); w.gg.dx=0; next(10);
                } else if(phase==10 && ticks-phaseTick>30) {
                    assertThat("destroyed-collision-survives-cache-eviction",scene.getTile(80,48)===damageTile && damageTile.phis==0);
                    var pixel:BitmapData=new BitmapData(1,1,true,0);
                    pixel.draw(w.grafon.visFront,new Matrix(1,0,0,1,-3220,-1940));
                    var alpha:uint=pixel.getPixel32(0,0)>>>24; pixel.dispose();
                    assertThat("destroyed-visual-survives-cache-eviction",alpha==0,alpha);
                    capture("terrain-return");
                    w.pers.healAll(); w.game.gotoLand("rbl"); next(11);
                } else if(phase==11 && w.land.act.id=="rbl" && w.game.curLandId=="rbl" && w.allStat==1 && w.t_exit==0) {
                    assertThat("normal-room-renderer-restored",!w.grafon.sceneLarge && w.grafon.frontBmp.width==1920);
                    w.pers.healAll(); w.game.gotoLand("continuous_scene"); next(12);
                } else if(phase==12 && w.land.act.id=="continuous_scene" && w.game.curLandId=="continuous_scene" && w.allStat==1 && w.t_exit==0) {
                    assertThat("scene-reentry-preserves-location",w.loc===scene && scene.getTile(80,48).phis==0);
                    report.maxChunkDrawMs=w.grafon.sceneMaxDrawMs;
                    sample(); w.saveGame(1);
                    assertThat("native-save-records-scene",w.getSave(1).game.land=="continuous_scene");
                    w.comLoad=1; next(13);
                } else if(phase==13 && ticks-phaseTick>15 && w.comLoad==-1 && w.allStat==1 && w.loc!==scene) {
                    assertThat("native-save-reloads-large-scene",w.game.curLandId=="continuous_scene" && w.loc.spaceX==192 && w.loc.spaceY==60 && w.grafon.sceneLarge);
                    assertThat("reload-player-alive",w.gg.hp>0 && w.gg.sost==1);
                    capture("scene-reloaded"); sample(); finish(true);
                }
            } catch(error:Error) { fail("driver",error.message+"\n"+error.getStackTrace()); }
        }
        private static function fireTestBullet():void {
            var Bullet:Class=cls("fe.weapon.Bullet");
            bullet=new Bullet(w.gg,1780,(enemy.Y1+enemy.Y2)/2,cls("visualBullet"));
            bullet.dx=60; bullet.vel=60; bullet.damage=80; bullet.liv=90;
            // Native precision is an effective range, not a 0..1 probability.
            // Zero disables random misses; the native collision and damage path remains active.
            bullet.precision=0; ++shots;
            log("SHOT "+shots+" targetHP="+enemy.hp+" bounds="+[enemy.X1,enemy.Y1,enemy.X2,enemy.Y2]+" bulletY="+bullet.Y);
        }
        private static function startCombat():void {
            w.ctr.clearAll(); w.gg.setLocPos(2300,2159); w.gg.dx=0;
            enemy=scene.createUnit("rat",1780,2159,true,<obj code="cs-chase"/>);
            assertThat("native-enemy-created",enemy!=null);
            w.enemyAct=2; w.godMode=false; w.gg.invulner=false;
            w.gg.obs=w.gg.maxObs;
            enemy.alarma(w.gg.X,w.gg.Y); enemy.setCel(w.gg); next(5);
        }
        private static function assertIdentity():void {
            if(w.loc!==scene || w.gg!==initialPlayer || w.gg.loc!==scene)
                throw new Error("Location or player identity changed during continuous travel");
        }
    }
}
