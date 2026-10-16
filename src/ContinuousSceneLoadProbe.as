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
    import flash.utils.getDefinitionByName;
    import flash.utils.getTimer;
    import tests.SceneUpcomingChecks;

    /** Isolated first-entry timings; production host and modules need no probes. */
    public class ContinuousSceneLoadProbe {
        private static var main:*,w:*,phase:int=0,ready:int=0,ticks:int=0,at:int=0;
        private static var started:int,travelAt:int,frameStart:int,mid:int,late:int;
        private static var row:Object,done:Boolean=false;
        private static var nativeEntry:Boolean=false,entryOnly:Boolean=false;
        private static var landId:String="continuous_scene";
        private static var walkAge:int=0,walkLast:int,walkMisses:int,walkEvictions:int;
        private static var walkLoc:*,walkX:Number,walkY:Number;
        private static var report:Object={version:"0.6-load-probe",mode:"loading",preload:true,assertions:[],samples:[],frames:[]};
        public static function init(host:*):void {
            main=host;started=getTimer();
            nativeEntry=File.applicationDirectory.resolvePath("load-native.flag").exists;
            entryOnly=File.applicationDirectory.resolvePath("entry-only.flag").exists;
            if(nativeEntry)landId="random_plant";
            report.nativeEntry=nativeEntry;report.entryOnly=entryOnly;
            main.stage.addEventListener(Event.ENTER_FRAME,begin,false,1000);
            main.stage.addEventListener(Event.ENTER_FRAME,afterNative,false,-50);
            main.stage.addEventListener(Event.ENTER_FRAME,afterWall,false,-150);
            main.stage.addEventListener(Event.ENTER_FRAME,tick,false,-400);
            main.loaderInfo.uncaughtErrorEvents.addEventListener(UncaughtErrorEvent.UNCAUGHT_ERROR,function(e:UncaughtErrorEvent):void {finish(false,String(e.error));});
        }
        private static function cls(s:String):Class {return getDefinitionByName(s) as Class;}
        private static function save():void {
            var fs:FileStream=new FileStream();fs.open(File.applicationStorageDirectory.resolvePath("result.json"),FileMode.WRITE);
            fs.writeUTFBytes(JSON.stringify(report,null,2));fs.close();
        }
        private static function finish(ok:Boolean,error:String=null):void {
            if(done)return;done=true;report.ok=ok;report.error=error;report.elapsedMs=getTimer()-started;
            try {if(w && w.grafon && "sceneLoadProfile" in w.grafon)report.nativeProfile=w.grafon.sceneLoadProfile;}catch(ignore:Error){}
            try {report.wallStatus=cls("WallBlendMod")["status"];}catch(ignoreWall:Error){}
            try {report.gameError=w.verror.txt.text;}catch(ignoreError:Error){}
            report.memoryMB=System.totalMemoryNumber/1048576;save();NativeApplication.nativeApplication.exit(ok?0:1);
        }
        private static function begin(e:Event):void {
            frameStart=getTimer();mid=late=frameStart;
            row={time:frameStart-started,phase:phase};
            if(w && w.grafon) {row.redrawsBefore=w.grafon.sceneRedraws;row.residentBefore=w.grafon.sceneResident;}
        }
        private static function afterNative(e:Event):void {mid=getTimer();}
        private static function afterWall(e:Event):void {late=getTimer();}
        private static function setting(mod:String,key:String,value:*):void {
            var api:*=w.main.getChildByName("ModSettingsCarrier")["modAPI"];
            for each(var page:Object in api.getPages()) if(page.modId==mod)
                for each(var item:Object in page.items) if(item.key==key) {
                    item["set"](value);if(item["get"]()!==value) throw new Error("Setting rejected: "+mod+"."+key);return;
                }
            throw new Error("Setting unavailable: "+mod+"."+key);
        }
        private static function tick(e:Event):void {
            if(done)return;++ticks;
            try {
                var now:int=getTimer();
                row.nativeAndDefaultListenersMs=mid-frameStart;row.wallListenerBandMs=late-mid;row.remainingListenersMs=now-late;
                if(w && w.grafon) {row.redrawsAfter=w.grafon.sceneRedraws;row.residentAfter=w.grafon.sceneResident;row.maxDrawMs=w.grafon.sceneMaxDrawMs;}
                if(phase==2 || now-frameStart>100) report.frames.push(row);
                w=cls("fe.World")["w"];
                if(w && w.verror && w.verror.visible) throw new Error(w.verror.txt.text);
                if(now-started>580000) throw new Error("Timeout phase "+phase);
                if(w && w.gg) {w.godMode=true;w.gg.invulner=true;}
                if(phase==0 && w && w.mm && w.mm.loaded && w.allLandsLoaded && w.textLoaded && main.getChildByName("ContinuousSceneCarrier") && main.getChildByName("ContinuousSceneCarrier")["sceneAPI"].ready) {
                    w.mm.active=false;w.newGame(-1,"Scene Load",{propusk:true});phase=1;
                } else if(phase==1 && w.ng_wait==0 && w.allStat==1 && w.gg && w.loc) {
                    if(!w.gg.ggControl || w.pip.noAct) {ready=0;w.ctr.keyPressed=w.ctr.keyPressed2=true;return;}
                    if(++ready<30)return;
                    w.grafon.scenePreload=File.applicationDirectory.resolvePath("preload.flag").exists;
                    report.preload=w.grafon.scenePreload;
                    setting("wallblend","enabled",true);setting("realisticvision","enabled",true);
                    setting("light-and-darkness","enabled",true);
                    if(nativeEntry)setting("continuousscene","nativeEnabled",true);
                    if(!entryOnly && "sceneProfileWantOracle" in w.grafon) {
                        w.grafon.sceneProfileWantOracle=true;
                        report.diagnosticsDuringEntry=true; // Pixel oracle precedes all gameplay/damage.
                    }
                    w.ctr.clearAll();w.pers.healAll();travelAt=getTimer();
                    if(nativeEntry)w.game.beginMission(landId);else w.game.gotoLand(landId);
                    report.dispatchMs=getTimer()-travelAt;phase=2;
                } else if(phase==2 && w.land && w.land.act.id==landId && w.t_exit==0 && w.allStat==1) {
                    report.samples.push({name:"first-entry",ms:getTimer()-travelAt,resident:w.grafon.sceneResident,redraws:w.grafon.sceneRedraws,regionPasses:w.grafon.sceneRegionPasses,units:w.loc.units.length});
                    if("sceneLoadProfile" in w.grafon) report.firstNativeProfile=JSON.parse(JSON.stringify(w.grafon.sceneLoadProfile));
                    try {report.firstWallStatus=JSON.parse(JSON.stringify(cls("WallBlendMod")["status"]));} catch(ignoreStatus:Error) {}
                    report.nativeLightSmoothing=w.grafon.visLight.getChildAt(0).smoothing;
                    if(report.preload && w.grafon.sceneResident!=240) throw new Error("Factory was not fully resident");
                    if(!report.preload && (!w.grafon.sceneViewReady() || w.loc.spaceX!=192 || w.loc.spaceY!=75 || w.loc.units.length<100))
                        throw new Error("Progressive entry lost visible surfaces or full-map logical objects");
                    save(); // Preserve completed entry timings before optional pixel diagnostics.
                    if(entryOnly) {finish(true);return;}
                    w.ctr.clearAll();at=ticks;phase=3;
                } else if(phase==3) {
                    // Explicit synchronous calls isolate terrain drawing from the
                    // following ENTER_FRAME overlay update. No images are encoded.
                    if("sceneProfileBuffers" in w.grafon) report.beforeRepaint=w.grafon.sceneProfileBuffers();
                    var shot:BitmapData=new BitmapData(main.stage.stageWidth,main.stage.stageHeight,false,0);
                    shot.draw(main.stage);
                    var fs:FileStream=new FileStream();fs.open(File.applicationStorageDirectory.resolvePath("loading-before-repaint.png"),FileMode.WRITE);
                    fs.writeBytes(shot.encode(shot.rect,new PNGEncoderOptions()));fs.close();shot.dispose();
                    if(!report.preload) {
                        report.upcomingPixels=SceneUpcomingChecks.pixels(w);
                        if(!report.upcomingPixels.passed)throw new Error("Initial viewport differs from full regional rendering");
                        walkLoc=w.loc;walkX=w.gg.X;walkY=w.gg.Y;
                        walkMisses=w.grafon.sceneMisses;walkEvictions=w.grafon.sceneEvictions;
                        report.upcoming={frames:[],emptyFrames:0,entries:w.grafon.sceneResident,missesStart:walkMisses};
                        walkLast=getTimer();phase=4;return;
                    }
                    if("sceneProfileRasterResult" in w.grafon) report.rasterComparison=w.grafon.sceneProfileRasterResult;
                    if(report.rasterComparison && report.rasterComparison.coreAbove8>0)
                        throw new Error("Optimized material bounds differ from native rendering on the same regional canvas");
                    finish(true);
                } else if(phase==4) {
                    if(w.loc!==walkLoc) throw new Error("Raster preparation replaced the logical location");
                    if(!w.grafon.sceneViewReady()) {++report.upcoming.emptyFrames;throw new Error("Camera exposed an unprepared surface");}
                    report.upcoming.frames.push(getTimer()-walkLast);walkLast=getTimer();
                    ++walkAge;
                    // Move the camera continuously across material/room joins.
                    // Position driving isolates rendering from blocked corridors;
                    // the factory regression separately verifies actual walking.
                    var direction:int=walkAge<300?1:-1;
                    walkX=Math.max(120,Math.min(w.loc.limX-120,walkX+direction*8));
                    w.gg.setLocPos(walkX,walkY);w.gg.dx=direction*8;w.gg.dy=0;
                    if(walkAge==150 || walkAge==450) w.cam.setZoom(2);
                    if(walkAge==200 || walkAge==500) w.cam.setZoom(0);
                    if(walkAge>=600) {
                        report.upcoming.resident=w.grafon.sceneResident;
                        report.upcoming.misses=w.grafon.sceneMisses-walkMisses;
                        report.upcoming.warmCount=w.grafon.sceneWarmCount;
                        report.upcoming.warmMaxMs=w.grafon.sceneWarmMaxMs;
                        if(w.grafon.sceneEvictions!=walkEvictions) throw new Error("Travel discarded already prepared surfaces");
                        finish(true);
                    }
                }
            } catch(error:Error) {finish(false,error.message+"\n"+error.getStackTrace());}
        }
    }
}
