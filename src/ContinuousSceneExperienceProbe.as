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
    import flash.system.System;
    import flash.utils.getDefinitionByName;
    import flash.utils.getTimer;
    import tests.SceneMapChecks;
    import tests.SceneInteractionChecks;
    import tests.SceneRenderChecks;
    import tests.SceneDecalChecks;

    /** Gameplay checks and screenshots run separately from the frame benchmark. */
    public class ContinuousSceneExperienceProbe {
        private static var main:*,w:*,phase:int=0,ticks:int=0,at:int=0,ready:int=0,started:int;
        private static var worldIndex:int=0,zoomIndex:int=0,interactionPass:int=0,done:Boolean=false,checker:SceneInteractionChecks;
        private static var points:Array=[],pointIndex:int=0,decalOnly:Boolean=false;
        private static var report:Object={mode:"experience",assertions:[],interactions:[],views:[]};
        public static function init(host:*):void {
            main=host;started=getTimer();write("ContinuousSceneExperienceProbe.log","experience probe\n");
            decalOnly=File.applicationDirectory.resolvePath("decal-only.flag").exists;
            report.decalOnly=decalOnly;
            main.stage.addEventListener(Event.ENTER_FRAME,before,false,1000);
            main.stage.addEventListener(Event.ENTER_FRAME,tick,false,-400);
            main.loaderInfo.uncaughtErrorEvents.addEventListener(UncaughtErrorEvent.UNCAUGHT_ERROR,function(e:UncaughtErrorEvent):void {finish(false,String(e.error));});
        }
        private static function cls(s:String):Class {return getDefinitionByName(s) as Class;}
        private static function read(path:String):XML {
            var fs:FileStream=new FileStream();fs.open(File.applicationDirectory.resolvePath(path),FileMode.READ);
            var xml:XML=new XML(fs.readUTFBytes(fs.bytesAvailable));fs.close();return xml;
        }
        private static function write(path:String,s:String,append:Boolean=false):void {
            var fs:FileStream=new FileStream();fs.open(File.applicationStorageDirectory.resolvePath(path),append?FileMode.APPEND:FileMode.WRITE);fs.writeUTFBytes(s);fs.close();
        }
        private static function log(s:String):void {write("ContinuousSceneExperienceProbe.log",getTimer()+" "+s+"\n",true);}
        private static function check(name:String,ok:Boolean,detail:*=null):void {
            report.assertions.push({name:(worldIndex?"large-":"native-")+name,ok:ok,detail:detail});
            log((ok?"PASS ":"FAIL ")+name+" "+JSON.stringify(detail));
            if(!ok) throw new Error(name);
        }
        private static function finish(ok:Boolean,error:String=null):void {
            if(done)return;done=true;if(checker)checker.dispose();
            report.ok=ok;report.error=error;report.elapsedMs=getTimer()-started;report.memoryMB=System.totalMemoryNumber/1048576;
            write("result.json",JSON.stringify(report,null,2));log("RESULT "+ok+" "+error);NativeApplication.nativeApplication.exit(ok?0:1);
        }
        private static function capture(name:String):void {
            var b:BitmapData=new BitmapData(main.stage.stageWidth,main.stage.stageHeight,false,0);b.draw(main.stage);
            var fs:FileStream=new FileStream();fs.open(File.applicationStorageDirectory.resolvePath(name+".png"),FileMode.WRITE);
            fs.writeBytes(b.encode(b.rect,new PNGEncoderOptions()));fs.close();b.dispose();
        }
        private static function setting(mod:String,key:String,value:*):void {
            var api:*=w.main.getChildByName("ModSettingsCarrier")["modAPI"];
            for each(var page:Object in api.getPages()) if(page.modId==mod)
                for each(var item:Object in page.items) if(item.key==key) {item["set"](value);return;}
            throw new Error("Setting unavailable: "+mod+"."+key);
        }
        private static function register():void {
            var rooms:XML=read("Rooms/rooms_plant.xml"),pool:XML=<all/>;pool.appendChild(rooms.room[12].copy());
            var def:XML=<land id="scene_experience_native" dif="0" locx="0" locy="0" stage="1" tip="test" acc="1" list="0"><options backwall="tBackWall" fon="fonDarkClouds" music="music_plant_2"/></land>;
            cls("fe.GameData")["d"].appendChild(def);w.landData.scene_experience_native={allroom:pool,loaded:true};
            var Act:Class=cls("fe.loc.LandAct");var act:*=new Act(def);act.allroom=pool;act.loaded=true;w.game.lands.scene_experience_native=act;
            var scene:XML=read("mods/ContinuousScene/release/scene.xml");
            for each(var region:XML in scene.room.sceneRegions.region) {
                var spawn:XML=rooms.room[int(region.@index)].obj.(@id=="player")[0];
                points.push({index:int(region.@index),x:(int(region.@x)+int(spawn.@x)+.5)*40,y:(int(region.@y)+int(spawn.@y)+1)*40-1});
            }
        }
        private static function next(p:int):void {phase=p;at=ticks;log("PHASE "+p);}
        private static function travel():void {
            w.ctr.clearAll();w.pers.healAll();w.game.gotoLand(worldIndex?"continuous_scene":"scene_experience_native");next(2);
        }
        private static function before(e:Event):void {if(checker && !checker.done)checker.beforeFrame();}
        private static function tick(e:Event):void {
            if(done)return;++ticks;
            try {
                w=cls("fe.World")["w"];
                if(w && w.verror && w.verror.visible)throw new Error(w.verror.txt.text);
                if(getTimer()-started>580000)throw new Error("Timeout phase "+phase);
                if(w && w.gg) {w.godMode=true;w.gg.invulner=true;}
                if(phase==0 && w && w.mm && w.mm.loaded && w.allLandsLoaded && w.textLoaded && main.getChildByName("ContinuousSceneCarrier") && main.getChildByName("ContinuousSceneCarrier")["sceneAPI"].ready) {
                    w.grafon.scenePreload=true;
                    w.mm.active=false;w.newGame(-1,"Scene Experience",{propusk:true});next(1);
                } else if(phase==1 && w.ng_wait==0 && w.allStat==1 && w.gg && w.loc) {
                    if(!w.gg.ggControl || w.pip.noAct) {ready=0;w.ctr.keyPressed=w.ctr.keyPressed2=true;return;}
                    if(++ready<30)return;
                    setting("wallblend","enabled",true);setting("realisticvision","enabled",true);register();if(decalOnly)worldIndex=1;travel();
                } else if(phase==2 && w.land && w.land.act.id==(worldIndex?"continuous_scene":"scene_experience_native") && w.t_exit==0 && w.allStat==1) {
                    w.ctr.clearAll();w.gg.ggControl=true;w.ctr.active=true;w.cam.setZoom(0);next(decalOnly?10:3);
                } else if(phase==3 && ticks-at>=15) {
                    w.pip.onoff(3,1);next(4);
                } else if(phase==4 && ticks-at>=3) {
                    for each(var item:Object in SceneMapChecks.run(w))check(item.name,item.ok,item.detail);
                    capture((worldIndex?"large":"native")+"-map");w.pip.onoff();next(5);
                } else if(phase==5 && ticks-at>=15) {
                    interactionPass=0;checker=new SceneInteractionChecks(w);next(6);
                } else if(phase==6) {
                    checker.afterFrame();
                    if(checker.done) {
                        report.interactions.push({world:worldIndex?"large":"native",result:checker.result});
                        check("native-interaction-execution-"+interactionPass,checker.result.ok,checker.result);checker=null;
                        if(interactionPass++==0) {checker=new SceneInteractionChecks(w,-1,"extended");next(6);}
                        else {w.cam.setZoom(0);zoomIndex=0;next(7);}
                    }
                } else if(phase==7 && ticks-at>=18) {
                    var expected:Number=zoomIndex==0?1:zoomIndex==1?Math.max(w.cam.screenX/1920,w.cam.screenY/1000):Math.min(w.cam.screenX/1920,w.cam.screenY/1000);
                    check("zoom-"+zoomIndex+"-persists",w.cam.isZoom==zoomIndex && Math.abs(w.cam.scaleV-expected)<.0001,{mode:w.cam.isZoom,scale:w.cam.scaleV,expected:expected});
                    var bounds:Rectangle=w.grafon.visFon.getBounds(main.stage);
                    check("background-covers-screen-zoom-"+zoomIndex,bounds.left<=.1 && bounds.top<=.1 && bounds.right>=main.stage.stageWidth-.1 && bounds.bottom>=main.stage.stageHeight-.1,bounds.toString());
                    capture((worldIndex?"large":"native")+"-zoom-"+zoomIndex);
                    if(++zoomIndex<3) {w.ctr.keyZoom=true;at=ticks;}
                    else if(worldIndex==0) {worldIndex=1;travel();}
                    else {
                        w.cam.setZoom(0);
                        for each(item in SceneRenderChecks.run(w))check(item.name,item.ok,item.detail);
                        pointIndex=0;move();next(8);
                    }
                } else if(phase==8 && ticks-at>=18) {
                    var p:Object=points[pointIndex];
                    report.views.push({room:p.index,x:w.gg.X,y:w.gg.Y,zoom:w.cam.scaleV});
                    capture("region-"+p.index);
                    if(++pointIndex<points.length) {move();at=ticks;}
                    else {check("all-surfaces-resident",w.grafon.sceneResident==240,w.grafon.sceneResident);w.pip.onoff(3,1);next(9);}
                } else if(phase==9 && ticks-at>=3) {
                    for each(item in SceneMapChecks.run(w))check("explored-"+item.name,item.ok,item.detail);
                    capture("large-map-explored");
                    w.drawAllMap=true;w.land.drawMap();capture("large-map-debug-full");w.drawAllMap=false;w.land.drawMap();
                    w.pip.onoff();next(10);
                } else if(phase==10 && ticks-at>=3) {
                    // Terminal-only native-art tests leave transient wrapper
                    // classes in private decal history. Never auto-save them
                    // on an AIR deactivation during immediate process exit.
                    w.swfStage.removeEventListener(Event.DEACTIVATE,w.onDeactivate);
                    if(!decalOnly) for each(item in SceneRenderChecks.runPower(w))check(item.name,item.ok,item.detail);
                    for each(item in SceneDecalChecks.run(w))check(item.name,item.ok,item.detail);
                    finish(true);
                }
            } catch(error:Error) {finish(false,error.message+"\n"+error.getStackTrace());}
        }
        private static function move():void {w.ctr.clearAll();w.gg.setLocPos(points[pointIndex].x,points[pointIndex].y);w.gg.dx=w.gg.dy=0;}
    }
}
