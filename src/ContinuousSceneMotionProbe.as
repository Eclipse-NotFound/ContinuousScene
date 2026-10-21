package {
    import flash.desktop.NativeApplication;
    import flash.display.BitmapData;
    import flash.display.PNGEncoderOptions;
    import flash.events.Event;
    import flash.events.DataEvent;
    import flash.events.UncaughtErrorEvent;
    import flash.filesystem.File;
    import flash.filesystem.FileMode;
    import flash.filesystem.FileStream;
    import flash.geom.Rectangle;
    import flash.geom.Point;
    import flash.utils.getDefinitionByName;
    import flash.utils.getTimer;
    import tests.SceneFogChecks;
    import tests.SceneEncounter;
    import tests.SceneRasterTiming;
    import tests.SceneThreatChecks;
    import tests.ScenePresentationChecks;
    import tests.SceneActivityCensus;
    import tests.SceneSatsChecks;
    import tests.SceneDecalChecks;
    import tests.SceneImpactChecks;

    /** Isolated movement attribution. Screenshot runs never supply timings. */
    public class ContinuousSceneMotionProbe {
        private static var main:*,w:*,loc:*,cfg:Object,phase:int=0,age:int=0,ready:int=0,index:int=0;
        private static var started:int,last:int,startFrame:int,band50:int,band150:int,band250:int,entryAt:int;
        private static var absoluteStart:int,lastEnd:int,priorAbsolute:int,priorProbe:int;
        private static var renderAt:int,renderMs:int,renderCalls:int,exitAt:int,exitMs:int,exitCalls:int;
        private static var x0:Number,y0:Number,path:Number=2400,done:Boolean=false,row:Object;
        private static var report:Object={version:"motion-0.8.2",assertions:[],samples:[]};
        private static var objectCulling:SceneObjectCulling=new SceneObjectCulling();
        private static var tilePresentation:SceneTilePresentation=new SceneTilePresentation();
        private static var fogPresentation:SceneFogPresentation=new SceneFogPresentation();
        private static var rasterPresentation:SceneRasterPresentation=new SceneRasterPresentation();
        private static var encounter:SceneEncounter;
        private static var cases:Array=["cold-forward","warm-back","warm-forward","idle","no-lad-back","full-forward","no-wall-back","full-forward-restored"];
        public static function init(host:*):void {
            main=host;started=getTimer();var f:FileStream=new FileStream();
            f.open(File.applicationDirectory.resolvePath("motion-controls.json"),FileMode.READ);
            cfg=JSON.parse(f.readUTFBytes(f.bytesAvailable));f.close();report.config=cfg;
            if(cfg.suite=="native"){ContinuousSceneNativeProbe.init(host);return;}
            if(cfg.suite=="experience"){ContinuousSceneExperienceProbe.init(host);return;}
            if(cfg.suite=="factory"){ContinuousSceneFactoryProbe.init(host);return;}
            if(cfg.suite=="upcoming"){ContinuousSceneLoadProbe.init(host);return;}
            if(cfg.suite=="mechanics" || cfg.suite=="combat"){ContinuousSceneIssuesProbe.init(host);return;}
            report.phase="initialized";save("progress.json",report);
            if(cfg.short)cases=["cold-forward","warm-back","warm-forward","idle"];
            if(cfg.culling)cases=["cold-forward","cull-back","uncull-forward","cull-back-repeat"];
            if(cfg.profile)cases=["cold-forward"];
            if(cfg.encounter)cases=["enemy-idle","enemy-fast-forward","enemy-fast-back","enemy-idle-end"];
            if(cfg.fogABBA)cases=["fog-original-a","fog-bounded-b","fog-bounded-b-repeat","fog-original-a-repeat"];
            if(cfg.fogTypedABBA)cases=["fog-deployed-a","fog-typed-b","fog-typed-b-repeat","fog-deployed-a-repeat"];
            if(cfg.drawControl)cases=["draw-baseline-a","draw-control-b","draw-control-b-repeat","draw-baseline-a-repeat"];
            if(cfg.impactABBA)cases=["impact-original-a","impact-candidate-b","impact-candidate-b-repeat","impact-original-a-repeat"];
            main.stage.addEventListener(Event.ENTER_FRAME,function(e:Event):void {absoluteStart=getTimer();rasterPresentation.beginFrame();},false,2147483647);
            main.stage.addEventListener(Event.ENTER_FRAME,function(e:Event):void {lastEnd=getTimer();},false,-2147483647);
            main.stage.addEventListener(Event.RENDER,function(e:Event):void {renderAt=getTimer();},false,2147483647);
            main.stage.addEventListener(Event.RENDER,function(e:Event):void {renderMs+=getTimer()-renderAt;++renderCalls;},false,-2147483647);
            main.stage.addEventListener(Event.EXIT_FRAME,function(e:Event):void {exitAt=getTimer();},false,2147483647);
            main.stage.addEventListener(Event.EXIT_FRAME,function(e:Event):void {exitMs+=getTimer()-exitAt;++exitCalls;},false,-2147483647);
            main.stage.addEventListener(Event.ENTER_FRAME,function(e:Event):void {startFrame=band50=band150=band250=getTimer();},false,1000);
            main.stage.addEventListener(Event.ENTER_FRAME,function(e:Event):void {band50=getTimer();},false,-50);
            main.stage.addEventListener(Event.ENTER_FRAME,function(e:Event):void {band150=getTimer();},false,-150);
            main.stage.addEventListener(Event.ENTER_FRAME,function(e:Event):void {band250=getTimer();},false,-250);
            main.stage.addEventListener(Event.ENTER_FRAME,tick,false,-1000);
            main.loaderInfo.uncaughtErrorEvents.addEventListener(UncaughtErrorEvent.UNCAUGHT_ERROR,function(e:UncaughtErrorEvent):void {finish(String(e.error));});
        }
        private static function save(name:String,value:*):void {var f:FileStream=new FileStream();f.open(File.applicationStorageDirectory.resolvePath(name),FileMode.WRITE);f.writeUTFBytes(JSON.stringify(value,null,2));f.close();}
        private static function check(name:String,ok:Boolean,detail:*=null):void {report.assertions.push({name:name,ok:ok,detail:detail});}
        private static function finish(error:String=null):void {
            if(done)return;done=true;report.error=error;report.elapsedMs=getTimer()-started;report.ok=error==null;
            for each(var a:Object in report.assertions)if(!a.ok)report.ok=false;
            save("result.json",report);NativeApplication.nativeApplication.exit(report.ok?0:1);
        }
        private static function settingsReady():Boolean {
            var c:*=main.getChildByName("ModSettingsCarrier");if(!c)return false;
            var found:int=0;for each(var p:Object in c["modAPI"].getPages())if(["continuousscene","wallblend","realisticvision","light-and-darkness"].indexOf(p.modId)>=0)++found;
            return found==4;
        }
        private static function setting(mod:String,key:String,value:*):void {
            for each(var p:Object in main.getChildByName("ModSettingsCarrier")["modAPI"].getPages())if(p.modId==mod)
                for each(var item:Object in p.items)if(item.key==key){item["set"](value);return;}
            throw new Error("Missing setting "+mod+"."+key);
        }
        private static function signs():void {
            var state:Object=main.getChildByName("ContinuousSceneCarrier")["nativeAPI"].state(w.land);
            var kept:Array=[],removed:Array=[],originalExits:Array=[];
            for each(var entry:Object in state.regions) {
                for each(var arrow:* in entry.arrays.signposts) {
                    var nx:int=entry.lx,ny:int=entry.ly;
                    if(arrow.rotation==0)++nx;else if(Math.abs(arrow.rotation)==180)--nx;
                    else if(arrow.rotation==90)++ny;else if(arrow.rotation==-90)--ny;
                    if(state.byCell[nx+":"+ny])removed.push(arrow);else kept.push(arrow);
                }
                for each(var obj:* in entry.arrays.objs)if(obj && "id" in obj && ["exit","doorout","doorprob","doorboss"].indexOf(obj.id)>=0)originalExits.push(obj);
            }
            report.signs=[];var internal:int=0;
            for each(var s:* in loc.signposts) {
                var inside:Boolean=removed.indexOf(s)>=0;
                if(inside)++internal;
                report.signs.push({x:s.x,y:s.y,rotation:s.rotation,visible:s.visible,parent:!!s.parent,internal:inside});
            }
            report.internalSigns=internal;
            if(cfg.expectNoSigns) {
                check("merged-boundaries-have-no-arrows",internal==0,internal);
                var keptOK:Boolean=true,removedOK:Boolean=true,exitOK:Boolean=true;
                for each(s in kept)if(loc.signposts.indexOf(s)<0)keptOK=false;
                for each(s in removed)if(s.parent)removedOK=false;
                for each(obj in originalExits)if(loc.objs.indexOf(obj)<0)exitOK=false;
                check("external-and-hole-arrows-preserved",keptOK,kept.length);
                check("internal-arrow-displays-detached",removedOK,removed.length);
                check("native-exit-objects-preserved",exitOK,originalExits.length);
            }
            var exits:int=0;for each(var b:* in loc.objs)if(b && "id" in b && ["exit","doorout","doorprob","doorboss"].indexOf(b.id)>=0)++exits;
            report.realExitObjects=exits;
        }
        private static function lightingChecks():void {
            var runtime:*=main.getChildByName("LightAndDarknessCarrier")["ladAPI"].runtime;
            var Field:Class=runtime.field.constructor as Class;
            var original:*=new Field(),cached:*=new Field();original.sceneCache=false;cached.sceneCache=true;
            var base:Rectangle=w.grafon.sceneViewport(),tile:*=loc.space[int((base.x+300)/40)][int((base.y+200)/40)];
            var saved:Object={opac:tile.opac,back:tile.back,lightOn:loc.lightOn};
            report.lightCache={pixels:[],timing:[]};
            try {
                for(var i:int=0;i<72;++i) {
                    var view:Rectangle=new Rectangle(base.x+(i<36?i:72-i)*12,base.y+(i%6)*12,base.width,base.height);
                    var lights:Array=runtime.lights(view);
                    lights.push({id:"fixed-probe",x:base.x+500,y:base.y+300,radius:260,color:0xffdda0,power:0.6,angle:0,cone:Math.PI*2});
                    lights.push({id:"moving-probe",x:base.x+400+i*4,y:base.y+260,radius:180,color:0x80bbff,power:i%7==0?0:0.5,angle:i*Math.PI/90,cone:Math.PI,transient:true});
                    if(i==16)tile.opac=saved.opac>0?0:1;
                    if(i==24)tile.opac=saved.opac;
                    if(i==30)tile.back=saved.back==""?"bwall":"";
                    if(i==36)tile.back=saved.back;
                    if(i==44)loc.lightOn=-1;
                    if(i==52)loc.lightOn=saved.lightOn;
                    if(i==60){view.width*=1.3;view.height*=1.3;}
                    original.render(loc,view,lights,runtime.ambient,runtime.darkZones,1,runtime.environment);
                    cached.render(loc,view,lights,runtime.ambient,runtime.darkZones,1,runtime.environment);
                    var difference:*=cached.data.compare(original.data),same:Boolean=difference===0;
                    var details:Object={step:i,equal:same,bounds:cached.bounds.toString(),oldRebuilds:original.rebuilds,newRebuilds:cached.rebuilds};
                    if(difference is BitmapData) {details.changedBounds=difference.getColorBoundsRect(0xffffff,0,false).toString();difference.dispose();}
                    report.lightCache.pixels.push(details);
                    check("lighting-cache-pixels-"+i,same,details);
                    check("lighting-cache-gameplay-sample-"+i,cached.sample(view.x+200,view.y+200)==original.sample(view.x+200,view.y+200));
                }
                tile.opac=saved.opac;tile.back=saved.back;loc.lightOn=saved.lightOn;
                for(var round:int=0;round<4;++round) {
                    var field:*=new Field();field.sceneCache=round%2==1;
                    var start:int=getTimer();
                    for(i=0;i<80;++i) {
                        view=new Rectangle(base.x+i*8,base.y,base.width,base.height);
                        field.render(loc,view,runtime.lights(view),runtime.ambient,runtime.darkZones,1,runtime.environment);
                    }
                    report.lightCache.timing.push({cached:field.sceneCache,ms:getTimer()-start,rebuilds:field.rebuilds});field.clear();
                }
            } finally {tile.opac=saved.opac;tile.back=saved.back;loc.lightOn=saved.lightOn;original.clear();cached.clear();}
        }
        private static function rasterChecks():void {
            var g:*=w.grafon,first:Object={},surface:Object,n:int;
            for each(surface in g.sceneSurfaces()) {
                var layers:Array=[];
                for(n=0;n<4;++n)layers.push(surface.nativeBuffers[n].clone());
                first[surface.cx+":"+surface.cy]=layers;
            }
            report.raster={surfaces:0,changed:0,pixels:0};
            try {
                g.sceneMaskBitmaps=false;g.drawLoc(loc);w.cam.calc(w.gg);
                for each(surface in g.sceneSurfaces()) {
                    layers=first[surface.cx+":"+surface.cy];if(!layers)continue;
                    ++report.raster.surfaces;
                    for(n=0;n<4;++n) {
                        var result:*=layers[n].compare(surface.nativeBuffers[n]);
                        check("cached-mask-pixels-"+surface.cx+":"+surface.cy+":"+n,result===0);
                        report.raster.pixels+=layers[n].width*layers[n].height;
                        if(result is BitmapData){++report.raster.changed;result.dispose();}
                    }
                }
                check("cached-mask-compared-visible-surfaces",report.raster.surfaces>12,report.raster.surfaces);
            } finally {for each(layers in first)for each(var data:BitmapData in layers)data.dispose();g.sceneMaskBitmaps=true;}
        }
        private static function startCase():void {
            var timing:*=main.getChildByName("ContinuousSceneTdfcProfile");
            if(timing)timing.api.reset();
            if(cfg.fogABBA)main.getChildByName("ContinuousSceneCarrier")["nativeAPI"]["fogBoundsEnabled"]=index==1 || index==2;
            if(cfg.fogTypedABBA)main.getChildByName("ContinuousSceneCarrier")["nativeAPI"]["fogTypedEnabled"]=index==1 || index==2;
            setting("light-and-darkness","enabled",!cfg.noLighting && index!=4);
            setting("wallblend","enabled",!cfg.noWall && index!=6);
            row={name:cases[index],frames:[],nativeBand:[],wallBand:[],sceneBand:[],preBand:[],tailBand:[],afterProbeBand:[],totalScript:[],warm:[],draw:[],empty:0,missStart:w.grafon.sceneMisses,residentStart:w.grafon.sceneResident,camera:[],activity:[]};
            row.renderBand=[];row.exitBand=[];row.renderEvents=[];row.exitEvents=[];
            if(cfg.impactABBA) {
                if(!("sceneImpactArtEnabled" in w.grafon))throw new Error("Impact ABBA needs native impact host");
                w.grafon.sceneImpactArtEnabled=index==1 || index==2;
                row.impactEnabled=w.grafon.sceneImpactArtEnabled;
            }
            renderMs=exitMs=renderCalls=exitCalls=0;
            age=0;last=getTimer();phase=4;
            if("sceneMotionProfile" in w.grafon)w.grafon.sceneMotionProfile={};
            if("csMotionNative" in loc)loc.csMotionNative={};
            if("sceneWarmSlices" in w.grafon){row.slicesStart=w.grafon.sceneWarmSlices;row.forcedStart=w.grafon.sceneWarmForced;}
        }
        private static function tick(e:Event):void {
            if(done)return;
            try {
                w=getDefinitionByName("fe.World")["w"];
                if(getTimer()-lastProgress>5000) {lastProgress=getTimer();save("heartbeat.json",{phase:phase,age:age,index:index});}
                if(w && w.verror && w.verror.visible)throw new Error(w.verror.txt.text);
                if(getTimer()-started>500000)throw new Error("Timeout "+phase);
                if(w && w.gg){w.godMode=true;w.gg.invulner=!cfg.encounter;}
                if(phase==0 && w && w.mm && w.mm.loaded && w.allLandsLoaded && w.textLoaded && settingsReady()) {
                    w.mm.active=false;w.newGame(-1,"Scene Motion",{propusk:true});phase=1;
                }else if(phase==1 && w.ng_wait==0 && w.allStat==1 && w.gg && w.loc) {
                    if(!w.gg.ggControl || w.pip.noAct){ready=0;w.ctr.keyPressed=w.ctr.keyPressed2=true;return;}
                    if(++ready<30)return;
                    setting("continuousscene","nativeEnabled",cfg.benchmark!="normal");setting("wallblend","enabled",!cfg.noWall);
                    setting("realisticvision","enabled",Boolean(cfg.vision));setting("realisticvision","wallbright",false);setting("light-and-darkness","enabled",!cfg.noLighting);
                    w.grafon.scenePreload=false;w.ctr.clearAll();
                    if("sceneAsyncWarm" in w.grafon)w.grafon.sceneAsyncWarm=!cfg.syncWarm;
                    if(cfg.rasterCheck && "sceneWarmVerify" in w.grafon)w.grafon.sceneWarmVerify=true;
                    w.game.lands[cfg.land?cfg.land:"random_mane"].landStage=(cfg.stage?int(cfg.stage):1)-1;
                    getDefinitionByName("fe.loc.Land")["rconnectSeedSource"]=function():uint{return 20261019;};
                    entryAt=getTimer();w.game.beginMission(cfg.land?cfg.land:"random_mane");phase=2;
                }else if(phase==2 && w.land && w.land.act.id==(cfg.land?cfg.land:"random_mane") && w.t_exit==0 && w.allStat==1) {
                    loc=w.loc;report.entryMs=getTimer()-entryAt;report.world={width:loc.spaceX,height:loc.spaceY,units:loc.units.length,black:loc.black,retDark:loc.retDark,lDist1:loc.lDist1,lDist2:loc.lDist2};
                    check("actual-expected-native-map",cfg.benchmark=="normal"?(!w.grafon.sceneLarge && loc.spaceX==48):(w.grafon.sceneLarge && loc.spaceX>48));
                    if(cfg.benchmark)path=1200;
                    x0=Math.max(200,Math.min(loc.limX-path-200,w.gg.X));y0=w.gg.Y;
                    // Compare the same local route within the entry room. A
                    // merged room uses global coordinates; native uses local.
                    x0=int(w.gg.X/1920)*1920+200;
                    y0=int(w.gg.Y/1000)*1000+800;
                    w.gg.setLocPos(x0,y0);w.gg.dx=w.gg.dy=0;w.cam.calc(w.gg);
                    var roomX:int=int(x0/1920)*48,roomY:int=int(y0/1000)*25,layout:uint=0;
                    for(var lx:int=0;lx<48;++lx)for(var ly:int=0;ly<25;++ly) {
                        var tile:*=loc.space[roomX+lx][roomY+ly];
                        var cell:String=[tile.front,tile.back,tile.phis,tile.diagon,tile.zForm,tile.door].join(":");
                        for(var ci:int=0;ci<cell.length;++ci)layout=uint(layout*31+cell.charCodeAt(ci));
                    }
                    report.world.entryRoomTiles=layout;report.world.layoutSeed=w.land.rconnectLayoutSeed;
                    report.viewport={stageWidth:main.stage.stageWidth,stageHeight:main.stage.stageHeight,
                        cameraWidth:w.cam.screenX,cameraHeight:w.cam.screenY,zoom:w.cam.scaleV};
                    report.path={startX:x0,endX:x0+path,y:y0};if(w.grafon.sceneLarge)signs();
                    if(cfg.encounter){encounter=new SceneEncounter(w);report.encounter=encounter.prepare(x0,y0,Boolean(cfg.fixedEnemies),Boolean(cfg.localEnemies));y0=report.encounter.playerY;report.path.y=y0;check("encounter-has-native-armed-enemies",report.encounter.units.length>=(cfg.fixedEnemies?6:3),report.encounter);}
                    age=0;phase=3;
                }else if(phase==3) {
                    w.ctr.clearAll();if(++age<20)return;
                    // Prepare the same route before an in-process ABBA timing.
                    if((cfg.fogABBA || cfg.fogTypedABBA) && age<620) {
                        var warmAge:int=age-20;
                        var warmForward:Boolean=warmAge<300;
                        w.gg.setLocPos(x0+(warmForward?warmAge:600-warmAge)*path/300,y0);
                        w.gg.dx=warmForward?path/300:-path/300;w.gg.dy=0;return;
                    }
                    if(cfg.impactCheck){
                        w.swfStage.removeEventListener(Event.DEACTIVATE,w.onDeactivate);
                        var impactCamera:Object={vx:w.cam.vx,vy:w.cam.vy,s:w.cam.scaleV,x:w.cam.screenX,y:w.cam.screenY};
                        w.cam.vx=0;w.cam.vy=0;w.cam.scaleV=1;w.cam.screenX=1280;w.cam.screenY=960;
                        w.grafon.sceneTick();
                        w.cam.vx=-1920;w.cam.vy=0;w.cam.scaleV=1;w.cam.screenX=3200;w.cam.screenY=2400;
                        w.grafon.sceneTick();
                        w.cam.vx=impactCamera.vx;w.cam.vy=impactCamera.vy;w.cam.scaleV=impactCamera.s;w.cam.screenX=impactCamera.x;w.cam.screenY=impactCamera.y;
                        report.impact=SceneImpactChecks.run(w,check);
                        for each(var impactResult:Object in SceneDecalChecks.run(w))check(impactResult.name,impactResult.ok,impactResult.detail);
                        finish();return;
                    }
                    if(cfg.satsCheck){report.sats=SceneSatsChecks.run(w,check);report.sats.od=w.sats.od;w.ctr.keySats=true;phase=90;return;}
                    if(cfg.fogCheck){report.fog=SceneFogChecks.run(w,check);finish();return;}
                    if(cfg.fogPerf){report.fogTiming=SceneFogChecks.benchmark(w);finish();return;}
                    if(cfg.renderPerf){report.renderTiming=SceneRasterTiming.run(w,fogPresentation);finish();return;}
                    if(cfg.threatCheck){report.threat=SceneThreatChecks.run(w,check);finish();return;}
                    if(cfg.presentationCheck){
                        var presenter:*=cfg.drawControl=="atlas"?rasterPresentation:cfg.drawControl=="fogpixels"?fogPresentation:tilePresentation;
                        report.presentation=ScenePresentationChecks.run(w,presenter,check,cfg.drawControl!="atlas" && cfg.drawControl!="fogpixels");finish();return;
                    }
                    if(cfg.wallCheck){main.dispatchEvent(new DataEvent("continuousSceneWallMotion",false,false,"verify"));}
                    if(cfg.lightingCheck) {lightingChecks();finish();return;}
                    if(cfg.rasterCheck && !("sceneWarmVerify" in w.grafon)) {rasterChecks();finish();return;}
                    if(cfg.visual) {
                        for(var tx:int=0;tx<loc.spaceX;++tx)for(var ty:int=0;ty<loc.spaceY;++ty)loc.space[tx][ty].visi=loc.space[tx][ty].t_visi=1;
                        w.grafon.setLight();report.visualRevealedNativeFog=true;
                        w.gg.setLocPos(1920,y0);w.cam.calc(w.gg);
                        if(age<24)return;
                        var image:BitmapData=new BitmapData(main.stage.stageWidth,main.stage.stageHeight,false,0);image.draw(main.stage);
                        var stream:FileStream=new FileStream();stream.open(File.applicationStorageDirectory.resolvePath("boundary.png"),FileMode.WRITE);stream.writeBytes(image.encode(image.rect,new PNGEncoderOptions()));stream.close();image.dispose();
                        check("visible-surface-ready",w.grafon.sceneViewReady());finish();return;
                    }
                    report.lastWarm=w.grafon.sceneWarmCount;report.lastDraw=w.grafon.sceneDrawMs;startCase();
                }else if(phase==90) {
                    check("sats-v-opens-native-ui",w.sats.active && w.sats.vis.visible && w.grafon.visSats.visible && w.allStat==2);
                    check("sats-opening-does-not-charge-ap",w.sats.od==report.sats.od);
                    w.ctr.keySats=true;phase=91;return;
                }else if(phase==91) {
                    check("sats-v-closes-and-resumes",!w.sats.active && !w.grafon.visSats.visible && w.grafon.visObjs[2].visible && w.allStat==1);
                    check("sats-close-does-not-charge-ap",w.sats.od==report.sats.od);
                    // Terminal-only: these isolated artwork fixtures must not
                    // be auto-saved or replayed into a subsequent location.
                    w.swfStage.removeEventListener(Event.DEACTIVATE,w.onDeactivate);
                    var decalCamera:Object={vx:w.cam.vx,vy:w.cam.vy,s:w.cam.scaleV,x:w.cam.screenX,y:w.cam.screenY};
                    w.cam.vx=-1920;w.cam.vy=0;w.cam.scaleV=1;w.cam.screenX=3200;w.cam.screenY=2400;
                    w.grafon.sceneTick();
                    w.cam.vx=decalCamera.vx;w.cam.vy=decalCamera.vy;w.cam.scaleV=decalCamera.s;w.cam.screenX=decalCamera.x;w.cam.screenY=decalCamera.y;
                    for each(var decalResult:Object in SceneDecalChecks.run(w))
                        check(decalResult.name,decalResult.ok,decalResult.detail);
                    finish();return;
                }else if(phase==4) {
                    if(w.allStat!=1 || w.onPause || w.t_exit!=0)
                        throw new Error("Timing invalid: native simulation paused/menu/travel state "+w.allStat);
                    if(cfg.wallCheck) {
                        var wallEvent:DataEvent=new DataEvent("continuousSceneWallMotion",false,false,"read");main.dispatchEvent(wallEvent);
                        var wallResults:Object=JSON.parse(wallEvent.data);
                        if(wallResults.comparisons.length>=40) {
                            var priorRebuilds:int=wallResults.rebuilds;
                            // Redispatching an Event clones it in Flash; a reply
                            // on that clone would leave this request unchanged.
                            wallEvent=new DataEvent("continuousSceneWallMotion",false,false,"invalidate");main.dispatchEvent(wallEvent);
                            wallResults=JSON.parse(wallEvent.data);
                            check("wall-explicit-refresh-rebuilds-complete-passes",int(wallResults.rebuilds)>priorRebuilds,{before:priorRebuilds,after:wallResults.rebuilds});
                            report.wallPixels=wallResults;
                            for each(var wallComparison:Object in wallResults.comparisons)check("wall-slice-pixels-"+wallComparison.cx+":"+wallComparison.cy+":"+wallComparison.layer,wallComparison.equal);
                            finish();return;
                        }
                    }
                    if(cfg.rasterCheck && "sceneWarmVerify" in w.grafon && w.grafon.sceneWarmComparisons.length>=10) {
                        report.warmPixels=w.grafon.sceneWarmComparisons;
                        for each(var comparison:Object in report.warmPixels)check("warm-slice-pixels-"+comparison.cx+":"+comparison.cy,comparison.equal,comparison);
                        finish();return;
                    }
                    if(cfg.culling)objectCulling.update(w,index%2==1);
                    if(cfg.drawControl){
                        var altered:Boolean=index==1 || index==2;
                        if(cfg.drawControl=="tilecrop")tilePresentation.update(w,altered);
                        if(cfg.drawControl=="fogpixels")fogPresentation.update(w,altered);
                        if(cfg.drawControl=="atlas")rasterPresentation.update(w,altered);
                        if(cfg.drawControl=="world")w.visual.visible=!altered;
                        if(cfg.drawControl=="fog")w.grafon.visLight.visible=!altered && loc.black && w.black;
                        if(cfg.drawControl=="objects")for each(var objectLayer:* in w.grafon.visObjs)objectLayer.visible=!altered;
                    }
                    var now:int=getTimer();row.frames.push(now-last);last=now;
                    row.renderBand.push(renderMs);row.exitBand.push(exitMs);row.renderEvents.push(renderCalls);row.exitEvents.push(exitCalls);
                    renderMs=exitMs=renderCalls=exitCalls=0;
                    row.preBand.push(startFrame-absoluteStart);row.tailBand.push(now-band250);
                    if(priorAbsolute>0){row.afterProbeBand.push(lastEnd-priorProbe);row.totalScript.push(lastEnd-priorAbsolute);}
                    priorAbsolute=absoluteStart;priorProbe=now;
                    if(encounter)encounter.sample();
                    row.nativeBand.push(band50-startFrame);row.wallBand.push(band150-band50);row.sceneBand.push(band250-band150);
                    row.warm.push(w.grafon.sceneWarmCount-report.lastWarm);report.lastWarm=w.grafon.sceneWarmCount;
                    row.draw.push(row.warm[row.warm.length-1]>0?w.grafon.sceneDrawMs:0);
                    if(!w.grafon.sceneViewReady())++row.empty;
                    if(age%30==0) {row.camera.push({x:w.cam.vx,y:w.cam.vy});row.activity.push(main.getChildByName("ContinuousSceneCarrier")["nativeAPI"].activityStats());}
                    w.ctr.clearAll();++age;
                    var forward:Boolean=index==0 || index==2 || index==5 || index==7;
                    var speed:Number=cfg.benchmark?path/300:(cfg.speed>0?cfg.speed:8);
                    if(cfg.fixedEnemies && cfg.speed>0)speed=cfg.speed;
                    var travel:Number=age*speed;
                    var distance:Number=travel%(path*2);if(distance>path)distance=path*2-distance;
                    var idle:Boolean=index==3 && !cfg.culling && !cfg.fogABBA && !cfg.fogTypedABBA;
                    if(cfg.encounter){idle=index==0 || index==3;forward=index==1;}
                    if(cfg.drawControl || cfg.impactABBA){idle=false;forward=true;}
                    var x:Number=idle?x0+path:x0+(forward?distance:path-distance);
                    if(cfg.encounter && idle)x=x0;
                    var goingForward:Boolean=forward;if(int(travel/path)%2==1)goingForward=!goingForward;
                    w.gg.setLocPos(x,y0);w.gg.dx=idle?0:goingForward?speed:-speed;w.gg.dy=0;
                    if(age<300)return;
                    row.misses=w.grafon.sceneMisses-row.missStart;row.residentEnd=w.grafon.sceneResident;row.warmMaxMs=w.grafon.sceneWarmMaxMs;
                    if(cfg.drawControl=="tilecrop")row.presentation={copies:tilePresentation.copies,allocated:tilePresentation.allocated};
                    if(cfg.drawControl=="atlas")row.presentation={copies:rasterPresentation.copies,rebuilds:rasterPresentation.rebuilds};
                    if("sceneMotionProfile" in w.grafon)row.hostProfile=w.grafon.sceneMotionProfile;
                    if("csMotionNative" in loc)row.nativeProfile=loc.csMotionNative;
                    var timing:*=main.getChildByName("ContinuousSceneTdfcProfile");
                    if(timing)row.tdfcProfile=timing.api.snapshot();
                    if(encounter)row.encounter=encounter.snapshot();
                    if(w.grafon.sceneLarge)row.activityCensus=SceneActivityCensus.read(w);
                    if("sceneWarmSlices" in w.grafon){row.slices=w.grafon.sceneWarmSlices-row.slicesStart;row.forced=w.grafon.sceneWarmForced-row.forcedStart;}
                    check("same-logical-map-"+index,w.loc===loc);check("complete-viewport-"+index,row.empty==0,row.empty);
                    report.samples.push(row);save("progress.json",report);
                    if(++index<cases.length)startCase();else {
                        if(encounter){check("enemies-targeted-player",encounter.targetFrames>30,encounter.targetFrames);check("enemies-fired",encounter.shots>0,encounter.shots);}
                        finish();
                    }
                }
            }catch(error:Error){finish(error.message+"\n"+error.getStackTrace());}
        }
        private static var lastProgress:int=0;
    }
}
