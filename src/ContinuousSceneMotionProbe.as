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

    /** Isolated movement attribution. Screenshot runs never supply timings. */
    public class ContinuousSceneMotionProbe {
        private static var main:*,w:*,loc:*,cfg:Object,phase:int=0,age:int=0,ready:int=0,index:int=0;
        private static var started:int,last:int,startFrame:int,band50:int,band150:int,band250:int,entryAt:int;
        private static var x0:Number,y0:Number,path:Number=2400,done:Boolean=false,row:Object;
        private static var report:Object={version:"motion-0.8.2",assertions:[],samples:[]};
        private static var objectCulling:SceneObjectCulling=new SceneObjectCulling();
        private static var cases:Array=["cold-forward","warm-back","warm-forward","idle","no-lad-back","full-forward","no-wall-back","full-forward-restored"];
        public static function init(host:*):void {
            main=host;started=getTimer();var f:FileStream=new FileStream();
            f.open(File.applicationDirectory.resolvePath("motion-controls.json"),FileMode.READ);
            cfg=JSON.parse(f.readUTFBytes(f.bytesAvailable));f.close();report.config=cfg;
            if(cfg.suite=="native"){ContinuousSceneNativeProbe.init(host);return;}
            if(cfg.suite=="experience"){ContinuousSceneExperienceProbe.init(host);return;}
            if(cfg.suite=="factory"){ContinuousSceneFactoryProbe.init(host);return;}
            if(cfg.suite=="upcoming"){ContinuousSceneLoadProbe.init(host);return;}
            if(cfg.suite=="mechanics"){ContinuousSceneIssuesProbe.init(host);return;}
            report.phase="initialized";save("progress.json",report);
            if(cfg.short)cases=["cold-forward","warm-back","warm-forward","idle"];
            if(cfg.culling)cases=["cold-forward","cull-back","uncull-forward","cull-back-repeat"];
            if(cfg.profile)cases=["cold-forward"];
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
            setting("light-and-darkness","enabled",!cfg.noLighting && index!=4);
            setting("wallblend","enabled",index!=6);
            row={name:cases[index],frames:[],nativeBand:[],wallBand:[],sceneBand:[],warm:[],draw:[],empty:0,missStart:w.grafon.sceneMisses,residentStart:w.grafon.sceneResident,camera:[],activity:[]};
            age=0;last=getTimer();phase=4;
            if("sceneMotionProfile" in w.grafon)w.grafon.sceneMotionProfile={};
            if("sceneWarmSlices" in w.grafon){row.slicesStart=w.grafon.sceneWarmSlices;row.forcedStart=w.grafon.sceneWarmForced;}
        }
        private static function tick(e:Event):void {
            if(done)return;
            try {
                w=getDefinitionByName("fe.World")["w"];
                if(getTimer()-lastProgress>5000) {lastProgress=getTimer();report.phase=phase;report.age=age;save("progress.json",report);}
                if(w && w.verror && w.verror.visible)throw new Error(w.verror.txt.text);
                if(getTimer()-started>500000)throw new Error("Timeout "+phase);
                if(w && w.gg){w.godMode=true;w.gg.invulner=true;}
                if(phase==0 && w && w.mm && w.mm.loaded && w.allLandsLoaded && w.textLoaded && settingsReady()) {
                    w.mm.active=false;w.newGame(-1,"Scene Motion",{propusk:true});phase=1;
                }else if(phase==1 && w.ng_wait==0 && w.allStat==1 && w.gg && w.loc) {
                    if(!w.gg.ggControl || w.pip.noAct){ready=0;w.ctr.keyPressed=w.ctr.keyPressed2=true;return;}
                    if(++ready<30)return;
                    setting("continuousscene","nativeEnabled",true);setting("wallblend","enabled",true);
                    setting("realisticvision","enabled",Boolean(cfg.vision));setting("realisticvision","wallbright",false);setting("light-and-darkness","enabled",!cfg.noLighting);
                    w.grafon.scenePreload=false;w.ctr.clearAll();
                    if("sceneAsyncWarm" in w.grafon)w.grafon.sceneAsyncWarm=!cfg.syncWarm;
                    if(cfg.rasterCheck && "sceneWarmVerify" in w.grafon)w.grafon.sceneWarmVerify=true;
                    w.game.lands["random_mane"].landStage=(cfg.stage?int(cfg.stage):1)-1;
                    getDefinitionByName("fe.loc.Land")["rconnectSeedSource"]=function():uint{return 20261019;};
                    entryAt=getTimer();w.game.beginMission("random_mane");phase=2;
                }else if(phase==2 && w.land && w.land.act.id=="random_mane" && w.t_exit==0 && w.allStat==1) {
                    loc=w.loc;report.entryMs=getTimer()-entryAt;report.world={width:loc.spaceX,height:loc.spaceY,units:loc.units.length};
                    check("actual-continuous-native-map",w.grafon.sceneLarge && loc.spaceX>48);
                    x0=Math.max(200,Math.min(loc.limX-path-200,w.gg.X));y0=w.gg.Y;
                    report.path={startX:x0,endX:x0+path,y:y0};signs();
                    age=0;phase=3;
                }else if(phase==3) {
                    w.ctr.clearAll();if(++age<20)return;
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
                }else if(phase==4) {
                    if(cfg.wallCheck) {
                        var wallEvent:DataEvent=new DataEvent("continuousSceneWallMotion",false,false,"read");main.dispatchEvent(wallEvent);
                        var wallResults:Object=JSON.parse(wallEvent.data);
                        if(wallResults.comparisons.length>=40) {
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
                    var now:int=getTimer();row.frames.push(now-last);last=now;
                    row.nativeBand.push(band50-startFrame);row.wallBand.push(band150-band50);row.sceneBand.push(band250-band150);
                    row.warm.push(w.grafon.sceneWarmCount-report.lastWarm);report.lastWarm=w.grafon.sceneWarmCount;
                    row.draw.push(row.warm[row.warm.length-1]>0?w.grafon.sceneDrawMs:0);
                    if(!w.grafon.sceneViewReady())++row.empty;
                    if(age%30==0) {row.camera.push({x:w.cam.vx,y:w.cam.vy});row.activity.push(main.getChildByName("ContinuousSceneCarrier")["nativeAPI"].activityStats());}
                    w.ctr.clearAll();++age;
                    var forward:Boolean=index==0 || index==2 || index==5 || index==7;
                    var distance:Number=Math.min(path,age*8);
                    var idle:Boolean=index==3 && !cfg.culling;
                    var x:Number=idle?x0+path:x0+(forward?distance:path-distance);
                    w.gg.setLocPos(x,y0);w.gg.dx=idle?0:forward?8:-8;w.gg.dy=0;
                    if(age<300)return;
                    row.misses=w.grafon.sceneMisses-row.missStart;row.residentEnd=w.grafon.sceneResident;row.warmMaxMs=w.grafon.sceneWarmMaxMs;
                    if("sceneMotionProfile" in w.grafon)row.hostProfile=w.grafon.sceneMotionProfile;
                    if("sceneWarmSlices" in w.grafon){row.slices=w.grafon.sceneWarmSlices-row.slicesStart;row.forced=w.grafon.sceneWarmForced-row.forcedStart;}
                    check("same-logical-map-"+index,w.loc===loc);check("complete-viewport-"+index,row.empty==0,row.empty);
                    report.samples.push(row);save("progress.json",report);
                    if(++index<cases.length)startCase();else finish();
                }
            }catch(error:Error){finish(error.message+"\n"+error.getStackTrace());}
        }
        private static var lastProgress:int=0;
    }
}
