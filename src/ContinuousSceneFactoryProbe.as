package {
    import flash.desktop.NativeApplication;
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.display.DisplayObject;
    import flash.display.PNGEncoderOptions;
    import flash.events.Event;
    import flash.events.MouseEvent;
    import flash.events.UncaughtErrorEvent;
    import flash.filesystem.File;
    import flash.filesystem.FileMode;
    import flash.filesystem.FileStream;
    import flash.geom.Matrix;
    import flash.geom.Point;
    import flash.geom.Rectangle;
    import flash.net.SharedObject;
    import flash.system.System;
    import flash.utils.getDefinitionByName;
    import flash.utils.getTimer;

    public class ContinuousSceneFactoryProbe {
        private static var main:*,w:*,phase:int=0,ticks:int=0,at:int=0,ready:int=0,started:int;
        private static var report:Object={version:"0.4.0",mode:"factory",preload:true,assertions:[],samples:[]};
        private static var scene:*, expected:String, rooms:XML, index:int=0;
        private static var points:Array=[], done:Boolean=false;
        private static var redraws:int,misses:int,enemy:*,bullet:*,beforeHP:Number,crossed:Boolean=false;
        private static var moveTimes:Array=[],lastMove:int;
        public static function init(host:*):void {
            main=host; started=getTimer();
            write("ContinuousSceneFactoryProbe.log","factory probe\n",false);
            main.stage.addEventListener(Event.ENTER_FRAME,tick,false,-400);
            main.loaderInfo.uncaughtErrorEvents.addEventListener(UncaughtErrorEvent.UNCAUGHT_ERROR,function(e:UncaughtErrorEvent):void {finish(false,String(e.error));});
        }
        private static function write(path:String,value:String,append:Boolean=false):void {
            var fs:FileStream=new FileStream(); fs.open(File.applicationStorageDirectory.resolvePath(path),append?FileMode.APPEND:FileMode.WRITE);
            fs.writeUTFBytes(value); fs.close();
        }
        private static function read(path:String):XML {
            var fs:FileStream=new FileStream(); fs.open(File.applicationDirectory.resolvePath(path),FileMode.READ);
            var xml:XML=new XML(fs.readUTFBytes(fs.bytesAvailable)); fs.close(); return xml;
        }
        private static function log(s:String):void {write("ContinuousSceneFactoryProbe.log",getTimer()+" "+s+"\n",true);}
        private static function check(name:String,ok:Boolean,detail:*=null):void {
            report.assertions.push({name:name,ok:ok,detail:detail}); log((ok?"PASS ":"FAIL ")+name+" "+JSON.stringify(detail));
            if(!ok) throw new Error(name);
        }
        private static function next(p:int):void {phase=p; at=ticks; log("PHASE "+p);}
        private static function finish(ok:Boolean,error:String=null):void {
            if(done) return; done=true; report.ok=ok; report.error=error; report.elapsedMs=getTimer()-started;
            report.memoryMB=System.totalMemoryNumber/1048576;
            write("result.json",JSON.stringify(report,null,2)); log("RESULT "+ok+" "+error);
            NativeApplication.nativeApplication.exit(ok?0:1);
        }
        private static function savePng(name:String,b:BitmapData):void {
            var fs:FileStream=new FileStream(); fs.open(File.applicationStorageDirectory.resolvePath(name+".png"),FileMode.WRITE);
            fs.writeBytes(b.encode(b.rect,new PNGEncoderOptions())); fs.close();
        }
        private static function capture(name:String):void {
            var b:BitmapData=new BitmapData(main.stage.stageWidth,main.stage.stageHeight,false,0); b.draw(main.stage); savePng(name,b); b.dispose();
        }
        private static function openTravel():void {
            expected=w.game.curLandId=="continuous_scene"?w.game.baseId:"continuous_scene";
            w.pers.healAll(); w.pip.onoff(3); w.pip.setPage(0); next(phase+1);
        }
        private static function clickTravel():void {
            if(ticks-at<12) return;
            var b:*=w.vpip.getChildByName("ContinuousSceneTravel");
            check("settled-menu-button",b && w.allStat==2 && !w.pip.noAct);
            b.dispatchEvent(new MouseEvent(MouseEvent.CLICK,true));
            check("travel-request",w.game.curLandId==expected,expected); next(phase+1);
        }
        private static function landed():Boolean {return w.land && w.land.act.id==expected && w.game.curLandId==expected && w.t_exit==0 && w.allStat==1;}
        private static function overlays(show:Boolean):Array {
            var hidden:Array=[];
            for each(var parent:* in [w.grafon.visFront,w.grafon.visBack]) for(var j:int=0;j<parent.numChildren;j++) {
                var child:DisplayObject=parent.getChildAt(j);
                if(child.name.indexOf("WallBlendScene")==0 && child.visible) {hidden.push(child); child.visible=show;}
            }
            return hidden;
        }
        private static function inspectLayers(name:String):void {
            capture(name);
            var vi:int=w.grafon.visual.getChildIndex(w.grafon.visLight);
            var fog:DisplayObject=w.grafon.visual.getChildAt(vi+1);
            var wasFog:Boolean=fog.visible,wasLight:Boolean=w.grafon.visLight.visible;
            try {
                fog.visible=false; w.grafon.visLight.visible=false;
                capture(name+"-no-vision");
                var hidden:Array=overlays(false); capture(name+"-native-terrain");
                for each(var child:DisplayObject in hidden) child.visible=true;
            } finally {fog.visible=wasFog; w.grafon.visLight.visible=wasLight;}
        }
        private static function compareFirstRoom():void {
            // Compare the same tiles and BackObjs through native single-room rendering.
            var cached:Array=[];
            for(var layer:int=0;layer<4;layer++) cached.push(new BitmapData(1920,1000,true,0));
            for each(var s:Object in w.grafon.sceneSurfaces()) {
                var dst:Point=new Point(s.x+s.gutter,s.y+s.gutter);
                if(dst.x>=1920 || dst.y>=1000) continue;
                for(layer=0;layer<4;layer++) cached[layer].copyPixels(s.nativeBuffers[layer],new Rectangle(s.gutter,s.gutter,s.side,s.side),dst);
            }
            var sx:int=scene.spaceX,sy:int=scene.spaceY;
            scene.spaceX=48; scene.spaceY=25;
            try {
                w.grafon.drawLoc(scene);
                var native:Array=[];
                for each(var parent:* in [w.grafon.visFront,w.grafon.visBack,w.grafon.visBack2,w.grafon.visVoda])
                    native.push(Bitmap(parent.getChildAt(0)).bitmapData);
                report.nativeRasterComparison=[];
                for(layer=0;layer<4;layer++) {
                    var delta:*=cached[layer].compare(native[layer]);
                    var detail:Object={layer:layer,equal:delta===0};
                    if(delta is BitmapData) {detail.bounds=BitmapData(delta).getColorBoundsRect(0xffffffff,0,false).toString(); savePng("raster-diff-"+layer,delta); delta.dispose();}
                    report.nativeRasterComparison.push(detail); log("RASTER "+JSON.stringify(detail));
                    savePng("raster-cached-"+layer,cached[layer]);savePng("raster-native-"+layer,native[layer]);
                    cached[layer].dispose();
                }
            } finally {scene.spaceX=sx; scene.spaceY=sy; w.grafon.drawLoc(scene);}
        }
        private static function tick(e:Event):void {
            if(done) return; ++ticks;
            try {
                w=getDefinitionByName("fe.World")["w"];
                if(w && w.verror && w.verror.visible) throw new Error(w.verror.txt.text);
                if(getTimer()-started>600000) throw new Error("Timeout phase "+phase);
                if(w && w.gg) {w.godMode=phase!=13;w.gg.invulner=phase!=13;}
                if(phase==0 && w && w.mm && w.mm.loaded && w.allLandsLoaded && w.textLoaded && main.getChildByName("ContinuousSceneCarrier") && main.getChildByName("ContinuousSceneCarrier")["sceneAPI"].ready) {
                    rooms=read("mods/ContinuousScene/release/scene.xml");
                    var originals:XML=read("Rooms/rooms_plant.xml");
                    for each(var region:XML in rooms.room.sceneRegions.region) {
                        var spawn:XML=originals.room[int(region.@index)].obj.(@id=="player")[0];
                        points.push({x:(int(region.@x)+int(spawn.@x)+0.5)*40,y:(int(region.@y)+int(spawn.@y)+1)*40-1});
                    }
                    w.mm.active=false; w.newGame(-1,"Continuous Factory",{propusk:true}); next(1);
                } else if(phase==1 && w.ng_wait==0 && w.allStat==1 && w.gg && w.loc) {
                    if(!w.gg.ggControl || w.pip.noAct) {ready=0;w.ctr.keyPressed=w.ctr.keyPressed2=true;return;}
                    if(++ready<30) return;
                    var status:Object=SharedObject.getLocal("ModLoader","/").data;
                    var modules:Array=["ContinuousSceneMod","RealisticVisionMod","WallBlendMod"];
                    for each(var module:String in modules) check("loaded-"+module,Boolean(status["ok_"+module]) && !status["err_"+module]);
                    openTravel();
                } else if(phase==2 || phase==6 || phase==8) clickTravel();
                else if(phase==3 && landed()) {
                    scene=w.loc;
                    check("factory-dimensions",scene.spaceX==192 && scene.spaceY==75);
                    check("factory-12-original-regions",rooms.room.sceneRegions.region.length()==12);
                    check("factory-decorations-loaded",scene.backobjs.length==603,scene.backobjs.length);
                    check("factory-single-location",scene===w.land.locs[0][0][0]);
                    check("factory-all-240-surfaces-preloaded",w.grafon.sceneResident==240,w.grafon.sceneResident);
                    report.entryMs=getTimer()-started;
                    report.nativeUnits=scene.units.length;
                    compareFirstRoom();
                    redraws=w.grafon.sceneRedraws;misses=w.grafon.sceneMisses;
                    w.ctr.clearAll(); w.gg.setLocPos(points[0].x,points[0].y); w.cam.setZoom(0); next(4);
                } else if(phase==4 && ticks-at>=18) {
                    check("factory-view-"+index,w.loc===scene && w.gg.loc===scene && w.gg.hp>0,{x:w.gg.X,y:w.gg.Y,resident:w.grafon.sceneResident});
                    if(index==0 || index==5 || index==11) inspectLayers("factory-"+index);
                    else capture("factory-"+index);
                    if(++index<points.length) {w.gg.setLocPos(points[index].x,points[index].y);w.gg.dx=w.gg.dy=0;at=ticks;}
                    else {
                        check("factory-exploration-keeps-preloaded-map",w.grafon.sceneRedraws==redraws && w.grafon.sceneMisses==misses);
                        w.ctr.clearAll();w.gg.setLocPos(1820,639);w.gg.dx=w.gg.dy=0;
                        w.gg.ggControl=true;w.ctr.active=true;lastMove=getTimer();next(11);
                    }
                } else if(phase==11) {
                    moveTimes.push(getTimer()-lastMove);lastMove=getTimer();w.ctr.keyRight=true;
                    if(w.gg.X>2020) {
                        w.ctr.clearAll();
                        check("factory-player-walks-original-passage",w.loc===scene && w.gg.Y<641,{x:w.gg.X,y:w.gg.Y,cameraX:w.cam.vx});
                        report.walkFrameMs=moveTimes;capture("factory-passage-walk");
                        w.gg.setLocPos(1780,639);w.gg.dx=0;
                        enemy=scene.createUnit("raider",2080,639,true,<obj tr="1" code="factory-probe-target"/>);
                        enemy.controlOn=false;enemy.hp=enemy.maxhp=300;beforeHP=enemy.hp;
                        var Bullet:Class=getDefinitionByName("fe.weapon.Bullet") as Class;
                        bullet=new Bullet(w.gg,1820,(enemy.Y1+enemy.Y2)/2,getDefinitionByName("visualBullet"));
                        bullet.dx=30;bullet.vel=30;bullet.damage=80;bullet.liv=60;bullet.precision=0;next(12);
                    } else if(ticks-at>180) throw new Error("Factory passage blocked at "+w.gg.X+","+w.gg.Y);
                } else if(phase==12) {
                    if(bullet.X>1920 && bullet.loc===scene) crossed=true;
                    if(enemy.hp<beforeHP) {
                        check("factory-bullet-crosses-passage-and-hits",crossed && w.loc===scene,{hp:enemy.hp,x:bullet.X});
                        scene.remObj(enemy);scene.units.splice(scene.units.indexOf(enemy),1);
                        w.gg.setLocPos(2080,639);w.gg.dx=0;w.enemyAct=2;w.gg.obs=w.gg.maxObs;
                        enemy=scene.createUnit("rat",1820,639,true,<obj code="factory-probe-chaser"/>);
                        enemy.alarma(w.gg.X,w.gg.Y);enemy.setCel(w.gg);next(13);
                    } else if(ticks-at>90) throw new Error("Factory projectile failed to hit target");
                } else if(phase==13) {
                    if(enemy.X>1980 && enemy.celUnit===w.gg) {
                        check("factory-enemy-chases-across-passage",enemy.loc===scene && w.loc===scene,{x:enemy.X});
                        check("factory-combat-keeps-preloaded-map",w.grafon.sceneRedraws==redraws && w.grafon.sceneResident==240);
                        scene.remObj(enemy);scene.units.splice(scene.units.indexOf(enemy),1);next(5);
                    } else if(ticks-at>240) throw new Error("Factory enemy failed to cross at "+enemy.X);
                } else if(phase==5 && ticks-at>=20) openTravel();
                else if(phase==7 && landed()) {check("factory-return-base",!w.grafon.sceneLarge);openTravel();}
                else if(phase==9 && landed()) {
                    check("factory-new-mission-refreshes",w.loc!==scene && w.loc.backobjs.length==603); scene=w.loc;w.saveGame(1);w.comLoad=1;next(10);
                } else if(phase==10 && ticks-at>20 && w.comLoad==-1 && w.t_exit==0 && w.allStat==1 && w.loc!==scene) {
                    check("factory-native-save-load",w.game.curLandId=="continuous_scene" && w.loc.backobjs.length==603 && w.loc.spaceY==75);
                    capture("factory-reloaded"); finish(true);
                }
            } catch(error:Error) {finish(false,error.message+"\n"+error.getStackTrace());}
        }
    }
}
