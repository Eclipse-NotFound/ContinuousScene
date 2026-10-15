package {
    import flash.desktop.NativeApplication;
    import flash.display.BitmapData;
    import flash.display.PNGEncoderOptions;
    import flash.events.Event;
    import flash.events.UncaughtErrorEvent;
    import flash.filesystem.File;
    import flash.filesystem.FileMode;
    import flash.filesystem.FileStream;
    import flash.system.System;
    import flash.utils.Dictionary;
    import flash.utils.getDefinitionByName;
    import flash.utils.getTimer;
    import tests.SceneMapChecks;
    public class ContinuousSceneNativeProbe {
        private static var main:*,w:*,phase:int=0,ready:int=0,at:int=0,start:int,done:Boolean=false,prior:*;
        private static var report:Object={mode:"native-map",preload:true,assertions:[],entries:[]};
        private static var damagedLampKey:String;
        public static function init(host:*):void {
            main=host;start=getTimer();
            main.stage.addEventListener(Event.ENTER_FRAME,tick,false,-400);
            main.loaderInfo.uncaughtErrorEvents.addEventListener(UncaughtErrorEvent.UNCAUGHT_ERROR,function(e:UncaughtErrorEvent):void {finish(false,String(e.error));});
        }
        private static function log(message:String):void {
            var fs:FileStream=new FileStream();fs.open(File.applicationStorageDirectory.resolvePath("ContinuousSceneNativeProbe.log"),FileMode.APPEND);
            fs.writeUTFBytes(getTimer()+" "+message+"\n");fs.close();
        }
        private static function check(name:String,ok:Boolean,detail:*=null):void {
            report.assertions.push({name:name,ok:ok,detail:detail});log((ok?"PASS ":"FAIL ")+name+" "+JSON.stringify(detail));
            if(!ok)throw new Error(name);
        }
        private static function finish(ok:Boolean,error:String=null):void {
            if(done)return;done=true;report.ok=ok;report.error=error;report.elapsedMs=getTimer()-start;report.memoryMB=System.totalMemoryNumber/1048576;
            var fs:FileStream=new FileStream();fs.open(File.applicationStorageDirectory.resolvePath("result.json"),FileMode.WRITE);
            fs.writeUTFBytes(JSON.stringify(report,null,2));fs.close();log("RESULT "+ok+" "+error);NativeApplication.nativeApplication.exit(ok?0:1);
        }
        private static function setting(enabled:Boolean):void {
            var api:*=main.getChildByName("ModSettingsCarrier")["modAPI"];
            for each(var page:Object in api.getPages()) if(page.modId=="continuousscene")
                for each(var item:Object in page.items) if(item.key=="nativeEnabled") {
                    item["set"](enabled);check("setting-"+enabled,item["get"]()===enabled);return;
                }
            throw new Error("Native mode setting missing");
        }
        private static function travel(id:String,mission:Boolean,next:int):void {
            w.ctr.clearAll();w.pers.healAll();
            if(mission)w.game.beginMission(id);else w.game.gotoLand(id);
            at=getTimer();phase=next;ready=0;log("TRAVEL "+id+" phase="+phase);
        }
        private static function arrived(id:String):Boolean {
            if(!w.land || w.land.act.id!=id || w.game.curLandId!=id || w.t_exit!=0 || w.allStat!=1)return false;
            return ++ready>=20;
        }
        private static function inspect():void {
            var s:Object=main.getChildByName("ContinuousSceneCarrier")["nativeAPI"].state(w.land);
            check("native-generated-land",w.land.rnd && w.land.act.id=="random_plant");
            check("native-merged",s && s.loc===w.loc && s.regions.length>1);
            check("native-dimensions",w.loc.spaceX==s.width && w.loc.spaceY==s.height,{width:s.width,height:s.height,regions:s.regions.length});
            check("native-full-preload",w.grafon.sceneResident==Math.ceil(w.loc.limX/320)*Math.ceil(w.loc.limY/320));
            check("native-map-canvas",w.land.map.width==s.width && w.land.map.height==s.height);
            var units:int=0,objects:int=0,backdrops:int=0,aliases:Boolean=true,coordinates:Boolean=true;
            var expected:Dictionary=new Dictionary(true);
            for each(var r:Object in s.regions) {
                aliases=aliases && w.land.locs[r.lx][r.ly][0]===w.loc;
                for each(var unit:* in r.arrays.units) if(unit && unit!==w.gg && unit!==w.gg.defpet && !expected[unit]) {expected[unit]=true;++units;}
                objects+=r.arrays.objs.length;backdrops+=r.arrays.backobjs.length;
                var tile:*=w.loc.space[r.tx+10][r.ty+10];coordinates=coordinates && tile.X==r.tx+10 && tile.Y==r.ty+10;
            }
            check("native-grid-aliases",aliases);
            check("native-tile-coordinates",coordinates);
            check("native-object-population",w.loc.objs.length==objects && w.loc.backobjs.length==backdrops,{objects:objects,backdrops:backdrops,units:units});
            var linked:Dictionary=new Dictionary(true),count:int=0;
            for(var obj:*=w.loc.firstObj;obj;obj=obj.nobj) {if(linked[obj])throw new Error("Object-chain cycle");linked[obj]=true;++count;checkOwner(obj);}
            check("native-live-chain",count>objects,{linked:count});
            check("native-spawn-region",int(w.gg.X/1920)+w.land.minLocX==w.land.act.begLocX && int(w.gg.Y/1000)+w.land.minLocY==w.land.act.begLocY,{x:w.gg.X,y:w.gg.Y});
            report.entries.push({phase:phase,ms:getTimer()-at,width:s.width,height:s.height,regions:s.regions.length,units:w.loc.units.length,objects:objects,linked:count});
            if(phase==2) doors(s);
        }
        private static function doors(s:Object):void {
            var large:*=w.loc,ox:Number=w.gg.X,oy:Number=w.gg.Y,found:Boolean=false,backRooms:int=0;
            for each(var region:Object in s.regions) if(w.land.locs[region.lx][region.ly][1])++backRooms;
            for each(var object:* in large.objs) {
                if(!object.inter || object.inter.allact!="comein")continue;
                var px:Number=object.inter.X,py:Number=object.inter.Y;
                var lx:int=int(px/1920)+w.land.minLocX,ly:int=int(py/1000)+w.land.minLocY;
                region=s.byCell[lx+":"+ly];if(!region)continue;
                var back:*=w.land.locs[lx][ly][1];if(!back)continue;
                var localX:Number=px-region.tx*40,localY:Number=py-region.ty*40;
                if(back.collisionUnit(localX,localY,w.gg.scX-4,w.gg.scY) || large.collisionUnit(px,py,w.gg.scX-4,w.gg.scY))continue;
                w.gg.setLocPos(px,py);var outbound:Object=w.land.gotoLoc(5,px,py);
                check("native-back-room-entry",outbound && w.loc===back && Math.abs(w.gg.X-localX)<0.1 && Math.abs(w.gg.Y-localY)<0.1);
                var inbound:Object=w.land.gotoLoc(5,localX,localY);
                check("native-back-room-return",inbound && w.loc===large && Math.abs(w.gg.X-px)<0.1 && Math.abs(w.gg.Y-py)<0.1);
                found=true;break;
            }
            check("native-back-room-coverage",found || backRooms==0,{availableBackRooms:backRooms,tested:found});
            w.gg.setLocPos(ox,oy);
            var pixels:BitmapData=new BitmapData(main.stage.stageWidth,main.stage.stageHeight,false,0);
            pixels.draw(main.stage);
            var fs:FileStream=new FileStream();fs.open(File.applicationStorageDirectory.resolvePath("native-scene.png"),FileMode.WRITE);
            fs.writeBytes(pixels.encode(pixels.rect,new PNGEncoderOptions()));fs.close();pixels.dispose();
        }
        private static function checkOwner(obj:*):void {if(obj.loc!==w.loc)throw new Error("Object retained old location");}
        private static function tick(event:Event):void {
            if(done)return;
            try {
                w=(getDefinitionByName("fe.World") as Class)["w"];
                if(getTimer()-start>360000)throw new Error("Timeout phase="+phase);
                if(w && w.verror && w.verror.visible)throw new Error(w.verror.txt.text);
                if(w && w.gg) {w.godMode=true;w.gg.invulner=true;}
                if(phase==0 && w && w.mm && w.mm.loaded && w.allLandsLoaded && w.textLoaded && main.getChildByName("ContinuousSceneCarrier") && main.getChildByName("ContinuousSceneCarrier")["sceneAPI"].ready) {
                    setting(true);w.mm.active=false;w.newGame(-1,"Native Scene",{propusk:true});phase=1;
                } else if(phase==1 && w.ng_wait==0 && w.allStat==1 && w.gg && w.loc) {
                    if(!w.gg.ggControl || w.pip.noAct) {ready=0;w.ctr.keyPressed=w.ctr.keyPressed2=true;return;}
                    if(++ready<30)return;check("base-remains-native",!w.grafon.sceneLarge);travel("random_plant",true,2);
                } else if(phase==2 && arrived("random_plant")) {
                    inspect();prior=w.land;
                    var lampRuntime:*=main.getChildByName("LightAndDarknessCarrier")["ladAPI"].runtime;
                    if(lampRuntime.lamps.length) {
                        damagedLampKey=lampRuntime.lamps[0].key;
                        lampRuntime.hitLamp(lampRuntime.lamps[0],40);
                        check("native-lamp-damage-recorded",lampRuntime.lamps[0].state.hp==0);
                    }
                    travel(w.game.baseId,false,3);
                } else if(phase==3 && arrived(w.game.baseId)) {
                    travel("random_plant",false,4);
                } else if(phase==4 && arrived("random_plant")) {
                    check("ordinary-return-keeps-native-generation",w.land===prior);
                    lampRuntime=main.getChildByName("LightAndDarknessCarrier")["ladAPI"].runtime;
                    if(damagedLampKey) {
                        var found:Boolean=false;
                        for each(var lamp:Object in lampRuntime.lamps) if(lamp.key==damagedLampKey) {found=true;check("ordinary-return-keeps-lamp-damage",lamp.state.hp==0);}
                        check("ordinary-return-finds-same-lamp",found);
                    }
                    travel(w.game.baseId,false,5);
                } else if(phase==5 && arrived(w.game.baseId)) {
                    travel("random_plant",true,6);
                } else if(phase==6 && arrived("random_plant")) {
                    check("new-mission-refreshes-generation",w.land!==prior);inspect();
                    lampRuntime=main.getChildByName("LightAndDarknessCarrier")["ladAPI"].runtime;
                    var allFresh:Boolean=true;
                    for each(lamp in lampRuntime.lamps) allFresh=allFresh && lamp.state.hp==40;
                    check("new-mission-refreshes-lamps",allFresh);
                    prior=w.land;w.saveGame(3);w.comLoad=3;phase=9;ready=0;at=getTimer();
                } else if(phase==9 && w.comLoad==-1 && w.land!==prior && arrived(w.game.baseId)) {
                    // Vanilla Game reconstructs random missions at the base on load.
                    // Keep that rule; the next native entry must still use the setting.
                    check("native-save-load-preserves-random-return-rule",w.game.curLandId==w.game.baseId && !w.grafon.sceneLarge);
                    travel("random_plant",true,11);
                } else if(phase==11 && arrived("random_plant")) {
                    var restored:Object=main.getChildByName("ContinuousSceneCarrier")["nativeAPI"].state(w.land);
                    check("native-save-load-regenerates-large-mode",restored && restored.loc===w.loc && w.grafon.sceneLarge && w.grafon.sceneResident==240);
                    w.pip.onoff(3,1);phase=10;ready=0;
                } else if(phase==10 && ++ready>=5) {
                    for each(var row:Object in SceneMapChecks.run(w)) check("native-"+row.name,row.ok,row.detail);
                    var mapPixels:BitmapData=new BitmapData(main.stage.stageWidth,main.stage.stageHeight,false,0);
                    mapPixels.draw(main.stage);
                    var mapFile:FileStream=new FileStream();mapFile.open(File.applicationStorageDirectory.resolvePath("native-map.png"),FileMode.WRITE);
                    mapFile.writeBytes(mapPixels.encode(mapPixels.rect,new PNGEncoderOptions()));mapFile.close();mapPixels.dispose();
                    w.pip.onoff();travel(w.game.baseId,false,7);
                } else if(phase==7 && arrived(w.game.baseId)) {
                    setting(false);travel("random_plant",true,8);
                } else if(phase==8 && arrived("random_plant")) {
                    check("disabled-native-room-size",w.loc.spaceX==48 && w.loc.spaceY==25 && !w.grafon.sceneLarge);finish(true);
                }
            } catch(error:Error) {finish(false,error.message+"\n"+error.getStackTrace());}
        }
    }
}
