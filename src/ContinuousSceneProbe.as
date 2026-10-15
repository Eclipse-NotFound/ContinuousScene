package {
    import flash.desktop.NativeApplication;
    import flash.display.BitmapData;
    import flash.display.Bitmap;
    import flash.display.PNGEncoderOptions;
    import flash.events.Event;
    import flash.events.UncaughtErrorEvent;
    import flash.filesystem.File;
    import flash.filesystem.FileMode;
    import flash.filesystem.FileStream;
    import flash.geom.Rectangle;
    import flash.geom.Matrix;
    import flash.geom.Point;
    import flash.net.SharedObject;
    import flash.system.System;
    import flash.utils.ByteArray;
    import flash.utils.getDefinitionByName;
    import flash.utils.getTimer;

    public class ContinuousSceneProbe {
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
        private static var report:Object = {version:"0.4.0", assertions:[], samples:[]};
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
        private static var benchmark:Boolean = false;
        private static var previousRedraws:int = 0;
        private static var walkingRenderFrames:Array = [];
        private static var walkingCachedFrames:Array = [];
        private static var frameStarted:int;
        private static var walkingScriptFrames:Array = [];
        private static var cull:Boolean;
        private static var farSurface:Object;
        private static var farRevision:int;
        private static var pendingEntry:Object;
        private static var readyFrames:int=0;

        public static function init(host:*):void {
            var descriptor:XML = NativeApplication.nativeApplication.applicationDescriptor;
            var ns:Namespace = descriptor.namespace();
            if(String(descriptor.ns::id) != "pfe-modsettings-continuous-scene") return;
            if(File.applicationDirectory.resolvePath("factory.flag").exists) {ContinuousSceneFactoryProbe.init(host);return;}
            main = host;
            File.applicationStorageDirectory.createDirectory();
            manual = File.applicationDirectory.resolvePath("manual.flag").exists;
            quick = File.applicationDirectory.resolvePath("quick.flag").exists;
            benchmark = File.applicationDirectory.resolvePath("benchmark.flag").exists;
            cull = File.applicationDirectory.resolvePath("cull.flag").exists;
            report.mode = manual ? "manual" : benchmark ? "benchmark" : quick ? "combat-only" : "full";
            report.startedUTC = new Date().toUTCString();
            started = lastTime = getTimer();
            write("ContinuousSceneProbe.log","[ContinuousScene] v0.4.0 init manual=" + manual + "\n",false);
            host.stage.addEventListener(Event.ENTER_FRAME,tick,false,0,true);
            host.stage.addEventListener(Event.ENTER_FRAME,beginFrame,false,1000,true);
            host.stage.addEventListener(Event.ENTER_FRAME,endFrame,false,-300,true);
            host.loaderInfo.uncaughtErrorEvents.addEventListener(UncaughtErrorEvent.UNCAUGHT_ERROR,onError);
        }
        private static function beginFrame(e:Event):void { frameStarted=getTimer(); }
        private static function endFrame(e:Event):void {
            if(cull && w && w.grafon && w.grafon.sceneLarge) {
                var view:Rectangle=new Rectangle(-w.cam.vx-80,-w.cam.vy-80,w.cam.screenX+160,w.cam.screenY+160);
                for each(var surface:Object in w.grafon.sceneSurfaces()) {
                    var visible:Boolean=view.intersects(new Rectangle(surface.x+surface.gutter,surface.y+surface.gutter,surface.side,surface.side));
                    for each(var bm:Bitmap in surface.bitmaps) bm.visible=visible;
                }
                for each(var parent:* in [w.grafon.visFront,w.grafon.visBack]) for(var k:int=0;k<parent.numChildren;++k) {
                    bm=parent.getChildAt(k) as Bitmap;
                    if(bm && (bm.name=="WallBlendSceneFront" || bm.name=="WallBlendSceneBack"))
                        bm.visible=view.intersects(new Rectangle(bm.x,bm.y,320,320));
                }
            }
            if(!manual && !stopped && (phase==3 || phase==4) && ticks-phaseTick>32)
                walkingScriptFrames.push(getTimer()-frameStarted);
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
        private static function log(message:String):void { write("ContinuousSceneProbe.log",getTimer()+" "+message+"\n"); }
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
            report.walkingRenderFrames=walkingRenderFrames;
            report.walkingCachedFrames=walkingCachedFrames;
            report.walkingScriptFrames=walkingScriptFrames;
            report.memoryMB=System.totalMemoryNumber/1048576;
            write("result.json",JSON.stringify(report,null,2),false);
            log("RESULT "+(ok?"PASS":"FAIL"));
            main.stage.removeEventListener(Event.ENTER_FRAME,tick);
            main.stage.removeEventListener(Event.ENTER_FRAME,beginFrame);
            main.stage.removeEventListener(Event.ENTER_FRAME,endFrame);
            if(!manual) NativeApplication.nativeApplication.exit(ok?0:1);
        }
        private static function api():* { return main.getChildByName("ContinuousSceneCarrier")["sceneAPI"]; }
        private static function clickEntry():void {
            w.pip.onoff(3);
            w.pip.setPage(0);
            api().refresh();
            // A real player clicks after World.step has paused the open menu.
            pendingEntry={tick:ticks,phase:phase,target:w.game.curLandId=="continuous_scene"?w.game.baseId:"continuous_scene"};
        }
        private static function clickSettledEntry():void {
            if(ticks-pendingEntry.tick<12) return;
            var button:*=w.vpip.getChildByName("ContinuousSceneTravel");
            assertThat("native-travel-button-visible",button!=null && button.visible);
            assertThat("menu-settled-before-click",w.pip.active && w.allStat==2,{allStat:w.allStat,frames:ticks-pendingEntry.tick});
            log("TRAVEL STATE "+JSON.stringify({noAct:w.pip.noAct,control:w.gg.ggControl,catPause:w.catPause,rat:w.gg.rat,sats:w.sats.active,stand:w.stand.active,guiPause:w.gui.guiPause,noreturn:w.game.triggers["noreturn"],canTravel:w.game.checkTravel(pendingEntry.target),healthy:w.pers.dopusk(),weight:w.pers.speedShtr,exit:w.t_exit}));
            var center:Point=button.localToGlobal(new Point(85,13));
            assertThat("button-hit-area",button.hitTestPoint(center.x,center.y,true) && button.mouseEnabled && !button.mouseChildren);
            if(pendingEntry.phase==1) checkTravelRestrictions(button);
            capture("entry-"+pendingEntry.phase);
            button.dispatchEvent(new flash.events.MouseEvent(flash.events.MouseEvent.CLICK,true));
            assertThat("settled-menu-travel-requested",w.game.curLandId==pendingEntry.target,{expected:pendingEntry.target,actual:w.game.curLandId});
            assertThat("travel-closes-menu",!w.pip.active);
            var exitCountdown:int=w.t_exit;
            button.dispatchEvent(new flash.events.MouseEvent(flash.events.MouseEvent.CLICK,true));
            assertThat("duplicate-click-keeps-travel",w.game.curLandId==pendingEntry.target && w.t_exit==exitCountdown);
            pendingEntry=null;
        }
        private static function checkTravelRestrictions(button:*):void {
            var land:String=w.game.curLandId;
            var oldNoAct:Boolean=w.pip.noAct;
            var oldPause:Boolean=w.gui.guiPause;
            var oldNoReturn:*=w.game.triggers["noreturn"];
            var oldHeadHP:Number=w.pers.headHP;
            var oldSpeedShtr:Number=w.pers.speedShtr;
            try {
                w.pip.noAct=true;
                button.dispatchEvent(new flash.events.MouseEvent(flash.events.MouseEvent.CLICK,true));
                assertThat("travel-respects-noAct",w.game.curLandId==land && w.pip.active && w.t_exit==0);
                w.pip.noAct=false;
                w.gui.guiPause=true;
                button.dispatchEvent(new flash.events.MouseEvent(flash.events.MouseEvent.CLICK,true));
                assertThat("travel-respects-other-pause",w.game.curLandId==land && w.pip.active && w.t_exit==0);
                w.gui.guiPause=false;
                w.game.triggers["noreturn"]=1;
                button.dispatchEvent(new flash.events.MouseEvent(flash.events.MouseEvent.CLICK,true));
                assertThat("travel-respects-story",w.game.curLandId==land && w.pip.active && w.t_exit==0);
                w.game.triggers["noreturn"]=oldNoReturn;
                w.pers.headHP=1;
                button.dispatchEvent(new flash.events.MouseEvent(flash.events.MouseEvent.CLICK,true));
                assertThat("travel-respects-injury",w.game.curLandId==land && w.pip.active && w.t_exit==0);
                w.pers.headHP=oldHeadHP;
                w.pers.speedShtr=3;
                button.dispatchEvent(new flash.events.MouseEvent(flash.events.MouseEvent.CLICK,true));
                assertThat("travel-respects-weight",w.game.curLandId==land && w.pip.active && w.t_exit==0);
            } finally {
                w.pip.noAct=oldNoAct; w.gui.guiPause=oldPause;
                w.game.triggers["noreturn"]=oldNoReturn;
                w.pers.headHP=oldHeadHP; w.pers.speedShtr=oldSpeedShtr;
            }
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
            if(!manual && (phase==3 || phase==4) && ticks-phaseTick>32) {
                walkingDeltas.push(now-lastTime);
                (w.grafon.sceneRedraws>previousRedraws?walkingRenderFrames:walkingCachedFrames).push(now-lastTime);
            }
            if(w && w.grafon) previousRedraws=w.grafon.sceneRedraws;
            lastTime=now;
            try {
                w=cls("fe.World")["w"];
                if(ticks%300==0) log("HEARTBEAT phase="+phase+" allStat="+w.allStat+" ng="+w.ng_wait+" exit="+w.t_exit+" land="+(w.land?w.land.act.id:"null")+" requested="+(w.game?w.game.curLandId:"null"));
                if(w.verror && w.verror.visible) { fail("game-dialog",String(w.verror.txt.text)); return; }
                if(!manual && now-started>360000) throw new Error("Timed out phase="+phase);
                if(!manual && (phase==1 || phase>=11) && now-phaseTime>45000) throw new Error("Travel/load timed out phase="+phase);
                if(pendingEntry) { clickSettledEntry(); return; }
                if(phase==0 && w.landData && w.mm && w.mm.loaded && w.allLandsLoaded && w.textLoaded && main.getChildByName("ContinuousSceneCarrier") && api().ready) {
                    w.mm.active=false;
                    w.newGame(-1,"Continuous Scene",{propusk:true});
                    next(1);
                } else if(phase==1 && w.ng_wait==0 && w.allStat==1 && w.gg && w.loc) {
                    // Finish the new-game dialogue through native controls before opening travel.
                    if(!w.gg.ggControl || w.pip.noAct) {
                        readyFrames=0; w.ctr.keyPressed=w.ctr.keyPressed2=true; return;
                    }
                    if(++readyFrames<30) return;
                    report.loader=SharedObject.getLocal("ModLoader","/").data;
                    for each(var manifestLine:String in read("mods/loader-manifest.txt").split("\n")) {
                        var manifestFields:Array=manifestLine.replace(/\r/g,"").split("|");
                        if(manifestFields.length==5 && manifestFields[2]=="1")
                            assertThat("native-loader-"+manifestFields[1],Boolean(report.loader["ok_"+manifestFields[1]]),report.loader["err_"+manifestFields[1]]);
                    }
                    if("scenePreload" in w.grafon) w.grafon.scenePreload=manual || File.applicationDirectory.resolvePath("preload.flag").exists;
                    report.preload=("scenePreload" in w.grafon) && w.grafon.scenePreload;
                    w.pers.healAll(); clickEntry(); next(2);
                } else if(phase==2 && w.land && w.land.act.id=="continuous_scene" && w.game.curLandId=="continuous_scene" && w.allStat==1 && w.t_exit==0) {
                    scene=w.loc; initialPlayer=w.gg;
                    report.entryMs=getTimer()-phaseTime;
                    report.entryRedraws=w.grafon.sceneRedraws;
                    report.entryMemoryMB=System.totalMemoryNumber/1048576;
                    assertThat("scene-size",scene.spaceX==192 && scene.spaceY==60,{x:scene.limX,y:scene.limY});
                    assertThat("single-location",scene==w.land.locs[0][0][0]);
                    if(report.preload) {
                        assertThat("whole-map-ready-before-play",w.grafon.sceneResident==192,w.grafon.sceneResident);
                        var sharedPixels:Boolean=true;
                        for each(var stored:Object in w.grafon.sceneSurfaces()) {
                            for(var layer:int=0;layer<4;++layer) if(stored.bitmaps[layer].bitmapData!==stored.nativeBuffers[layer]) sharedPixels=false;
                            if(stored.cx==23 && stored.cy==7) farSurface=stored;
                        }
                        farRevision=farSurface.revision;
                        assertThat("display-and-native-raster-share-storage",sharedPixels);
                    }
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
                    if(benchmark && ticks-phaseTick>=360) { sample(); capture("benchmark-end"); finish(true); return; }
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
                        if(report.preload) assertThat("walk-does-not-regenerate-map",w.grafon.sceneResident==192 && w.grafon.sceneRedraws==report.entryRedraws,w.grafon.sceneRedraws);
                        else assertThat("bounded-resident-chunks",w.grafon.sceneResident<=64,w.grafon.sceneResident);
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
                        w.saveGame(2);
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
                    if(report.preload) assertThat("whole-map-survives-teleports",w.grafon.sceneResident==192 && w.grafon.sceneRedraws==report.entryRedraws,w.grafon.sceneRedraws);
                    else assertThat("chunks-evicted",w.grafon.sceneEvictions>0,w.grafon.sceneEvictions);
                    w.gg.setLocPos(3020,2159); w.gg.dx=0; next(10);
                } else if(phase==10 && ticks-phaseTick>30) {
                    if(report.loader.ok_WallBlendMod) {
                        var blendFront:int=0,blendBack:int=0;
                        for(var child:int=0;child<w.grafon.visFront.numChildren;++child) {
                            var overlay:Bitmap=w.grafon.visFront.getChildAt(child) as Bitmap;
                            if(overlay && overlay.name=="WallBlendSceneFront")
                                for each(var color:uint in overlay.bitmapData.getVector(overlay.bitmapData.rect)) if(color>>>24) ++blendFront;
                        }
                        for(child=0;child<w.grafon.visBack.numChildren;++child) {
                            overlay=w.grafon.visBack.getChildAt(child) as Bitmap;
                            if(overlay && overlay.name=="WallBlendSceneBack")
                                for each(color in overlay.bitmapData.getVector(overlay.bitmapData.rect)) if(color>>>24) ++blendBack;
                        }
                        assertThat("wallblend-large-scene-foreground",blendFront>0,blendFront);
                        assertThat("wallblend-large-scene-background",blendBack>0,blendBack);
                    }
                    assertThat("destroyed-collision-survives-cache-eviction",scene.getTile(80,48)===damageTile && damageTile.phis==0);
                    if(report.preload) assertThat("distant-raster-untouched-by-local-combat",farSurface.revision==farRevision,{start:farRevision,end:farSurface.revision});
                    var pixel:BitmapData=new BitmapData(1,1,true,0);
                    pixel.draw(w.grafon.visFront,new Matrix(1,0,0,1,-3220,-1940));
                    var alpha:uint=pixel.getPixel32(0,0)>>>24; pixel.dispose();
                    assertThat("destroyed-visual-survives-cache-eviction",alpha==0,alpha);
                    capture("terrain-return");
                    w.pers.healAll(); clickEntry(); next(11);
                } else if(phase==11 && w.land.act.id=="rbl" && w.game.curLandId=="rbl" && w.allStat==1 && w.t_exit==0) {
                    assertThat("normal-room-renderer-restored",!w.grafon.sceneLarge && w.grafon.frontBmp.width==1920);
                    w.pers.healAll(); clickEntry(); next(12);
                } else if(phase==12 && w.land.act.id=="continuous_scene" && w.game.curLandId=="continuous_scene" && w.allStat==1 && w.t_exit==0) {
                    assertThat("scene-reentry-preserves-location",w.loc===scene && scene.getTile(80,48).phis==0);
                    report.maxChunkDrawMs=w.grafon.sceneMaxDrawMs;
                    sample(); w.saveGame(1);
                    assertThat("native-save-records-scene",w.getSave(1).game.land=="continuous_scene");
                    w.comLoad=1; next(13);
                } else if(phase==13 && ticks-phaseTick>15 && w.comLoad==-1 && w.allStat==1 && w.loc!==scene) {
                    assertThat("native-save-reloads-large-scene",w.game.curLandId=="continuous_scene" && w.loc.spaceX==192 && w.loc.spaceY==60 && w.grafon.sceneLarge);
                    assertThat("reload-player-alive",w.gg.hp>0 && w.gg.sost==1);
                    assertThat("destroyed-terrain-survives-native-load",w.loc.getTile(80,48).phis==0 && w.loc.getTile(80,48).front=="");
                    w.gg.setLocPos(3020,2159); w.gg.dx=0;
                    next(14);
                } else if(phase==14 && ticks-phaseTick>15) {
                    var savedPixel:BitmapData=new BitmapData(1,1,true,0);
                    savedPixel.draw(w.grafon.visFront,new Matrix(1,0,0,1,-3220,-1940));
                    assertThat("destroyed-visual-survives-native-load",(savedPixel.getPixel32(0,0)>>>24)==0);
                    savedPixel.dispose();
                    w.grafon.drawSats(); w.grafon.onSats(true);
                    assertThat("sats-chunks-cover-resident-region",w.grafon.visSats.numChildren>=w.grafon.sceneResident);
                    capture("scene-sats"); w.grafon.onSats(false);
                    w.saveGame(3); w.comLoad=2; next(15);
                } else if(phase==15 && ticks-phaseTick>15 && w.comLoad==-1 && w.allStat==1 && w.t_exit==0) {
                    assertThat("older-slot-retains-undamaged-terrain",w.loc.getTile(80,48).phis>0 && w.loc.getTile(80,48).front=="C");
                    w.comLoad=3; next(16);
                } else if(phase==16 && ticks-phaseTick>15 && w.comLoad==-1 && w.allStat==1 && w.t_exit==0) {
                    assertThat("resaved-slot-retains-damage",w.loc.getTile(80,48).phis==0);
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
