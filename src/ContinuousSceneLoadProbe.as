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

    /** Isolated first-entry timings; production host and modules need no probes. */
    public class ContinuousSceneLoadProbe {
        private static var main:*,w:*,phase:int=0,ready:int=0,ticks:int=0,at:int=0;
        private static var started:int,travelAt:int,frameStart:int,mid:int,late:int;
        private static var row:Object,done:Boolean=false;
        private static var report:Object={version:"0.6-load-probe",mode:"loading",preload:true,assertions:[],samples:[],frames:[]};
        public static function init(host:*):void {
            main=host;started=getTimer();
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
                    setting("wallblend","enabled",true);setting("realisticvision","enabled",true);
                    w.ctr.clearAll();w.pers.healAll();travelAt=getTimer();w.game.gotoLand("continuous_scene");phase=2;
                } else if(phase==2 && w.land && w.land.act.id=="continuous_scene" && w.t_exit==0 && w.allStat==1) {
                    report.samples.push({name:"first-entry",ms:getTimer()-travelAt,resident:w.grafon.sceneResident,redraws:w.grafon.sceneRedraws,regionPasses:w.grafon.sceneRegionPasses,units:w.loc.units.length});
                    report.nativeLightSmoothing=w.grafon.visLight.getChildAt(0).smoothing;
                    if(w.grafon.sceneResident!=240) throw new Error("Factory was not fully resident");
                    w.ctr.clearAll();at=ticks;phase=3;
                } else if(phase==3 && ticks-at>=30) {
                    // Explicit synchronous calls isolate terrain drawing from the
                    // following ENTER_FRAME overlay update. No images are encoded.
                    if("sceneProfileBuffers" in w.grafon) report.beforeRepaint=w.grafon.sceneProfileBuffers();
                    var shot:BitmapData=new BitmapData(main.stage.stageWidth,main.stage.stageHeight,false,0);
                    shot.draw(main.stage);
                    var fs:FileStream=new FileStream();fs.open(File.applicationStorageDirectory.resolvePath("loading-before-repaint.png"),FileMode.WRITE);
                    fs.writeBytes(shot.encode(shot.rect,new PNGEncoderOptions()));fs.close();shot.dispose();
                    if("sceneProfilePixels" in w.grafon) report.rasterComparison=w.grafon.sceneProfilePixels();
                    var start:int=getTimer(),redraws:int=w.grafon.sceneRedraws;
                    w.grafon.drawLoc(w.loc);
                    report.samples.push({name:"native-full-repaint",ms:getTimer()-start,resident:w.grafon.sceneResident,passes:w.grafon.sceneRedraws-redraws});
                    start=getTimer();setting("wallblend","enabled",false);
                    report.samples.push({name:"drop-wall-overlays",ms:getTimer()-start});
                    start=getTimer();setting("wallblend","enabled",true);
                    report.samples.push({name:"build-wall-overlays",ms:getTimer()-start});
                    at=ticks;phase=4;
                } else if(phase==4 && ticks-at>=30) finish(true);
            } catch(error:Error) {finish(false,error.message+"\n"+error.getStackTrace());}
        }
    }
}
