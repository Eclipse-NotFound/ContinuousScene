package {
    import flash.desktop.NativeApplication;
    import flash.display.Bitmap;
    import flash.geom.Rectangle;
    import flash.events.Event;
    import flash.events.KeyboardEvent;
    import flash.events.UncaughtErrorEvent;
    import flash.filesystem.File;
    import flash.filesystem.FileMode;
    import flash.filesystem.FileStream;
    import flash.system.System;
    import flash.utils.getDefinitionByName;
    import flash.utils.getTimer;

    /** Real ENTER_FRAME timing; no PNG encoding or scene repaint during samples. */
    public class ContinuousScenePerfProbe {
        private static var main:*,w:*,phase:int=0,ticks:int=0,at:int=0,ready:int=0;
        private static var started:int,last:int,frameStart:int,travelAt:int;
        private static var worldIndex:int=0,caseIndex:int=0,row:Object,done:Boolean=false;
        private static var cases:Array=["idle","fire","idle-after","culled-fire","no-lad-fire","no-lad-wall-fire","no-lad-wall-rv-fire"];
        private static var report:Object={version:"0.5-probe",mode:"performance",preload:true,assertions:[],samples:[]};
        public static function init(host:*):void {
            main=host;started=getTimer();last=started;
            write("ContinuousScenePerfProbe.log","performance probe\n",false);
            main.stage.addEventListener(Event.ENTER_FRAME,begin,false,1000);
            main.stage.addEventListener(Event.ENTER_FRAME,tick,false,-400);
            main.loaderInfo.uncaughtErrorEvents.addEventListener(UncaughtErrorEvent.UNCAUGHT_ERROR,function(e:UncaughtErrorEvent):void {finish(false,String(e.error));});
        }
        private static function begin(e:Event):void {frameStart=getTimer();}
        private static function cls(s:String):Class {return getDefinitionByName(s) as Class;}
        private static function write(path:String,s:String,append:Boolean=true):void {
            var fs:FileStream=new FileStream();fs.open(File.applicationStorageDirectory.resolvePath(path),append?FileMode.APPEND:FileMode.WRITE);fs.writeUTFBytes(s);fs.close();
        }
        private static function log(s:String):void {write("ContinuousScenePerfProbe.log",getTimer()+" "+s+"\n");}
        private static function finish(ok:Boolean,error:String=null):void {
            if(done)return;done=true;report.ok=ok;report.error=error;report.elapsedMs=getTimer()-started;
            try {if(w && w.gg) {setting("light-and-darkness","enabled",true);setting("wallblend","enabled",true);setting("realisticvision","enabled",true);}} catch(ignore:Error) {}
            report.memoryMB=System.totalMemoryNumber/1048576;write("result.json",JSON.stringify(report,null,2),false);
            log("RESULT "+ok+" "+error);NativeApplication.nativeApplication.exit(ok?0:1);
        }
        private static function registerNative():void {
            var fs:FileStream=new FileStream();fs.open(File.applicationDirectory.resolvePath("Rooms/rooms_plant.xml"),FileMode.READ);
            var rooms:XML=new XML(fs.readUTFBytes(fs.bytesAvailable));fs.close();
            var pool:XML=<all/>;pool.appendChild(rooms.room[12].copy());
            var def:XML=<land id="scene_perf_native" dif="0" locx="0" locy="0" stage="1" tip="test" acc="1" list="0"><options backwall="tBackWall" fon="fonDarkClouds" music="music_plant_2"/></land>;
            cls("fe.GameData")["d"].appendChild(def);w.landData.scene_perf_native={allroom:pool,loaded:true};
            var Act:Class=cls("fe.loc.LandAct");var act:*=new Act(def);act.allroom=pool;act.loaded=true;w.game.lands.scene_perf_native=act;
        }
        private static function travel():void {
            if("sceneCullRender" in w.grafon) w.grafon.sceneCullRender=File.applicationDirectory.resolvePath("cull.flag").exists;
            w.ctr.clearAll();w.pers.healAll();travelAt=getTimer();
            w.game.gotoLand(worldIndex==0?"scene_perf_native":"continuous_scene");phase=2;log("TRAVEL "+worldIndex);
        }
        private static function setting(mod:String,key:String,value:*):void {
            var api:*=w.main.getChildByName("ModSettingsCarrier")["modAPI"];
            for each(var page:Object in api.getPages()) if(page.modId==mod)
                for each(var item:Object in page.items) if(item.key==key) {
                    item["set"](value); if(item["get"]()!==value) throw new Error("Setting rejected: "+mod+"."+key);return;
                }
            throw new Error("Setting unavailable: "+mod+"."+key);
        }
        private static function startCase():void {
            if("sceneCullRender" in w.grafon) w.grafon.sceneCullRender=File.applicationDirectory.resolvePath("cull.flag").exists || (worldIndex==1 && caseIndex>=3);
            if(caseIndex==4) setting("light-and-darkness","enabled",false);
            if(caseIndex==5) setting("wallblend","enabled",false);
            if(caseIndex==6) setting("realisticvision","enabled",false);
            row={world:worldIndex==0?"native":"large",name:cases[caseIndex],frames:[],script:[],shots:0,
                units:w.loc.units.length,scale:w.cam.scaleV,redrawsStart:w.grafon.sceneRedraws,dirtyMax:0,
                stageFps:main.stage.frameRate,renderBounds:w.visual.getBounds(w.visual).toString(),
                renderFilters:w.visual.filters.length,renderCache:w.visual.cacheAsBitmap};
            at=ticks;last=getTimer();phase=3;log("CASE "+row.world+" "+row.name);
        }
        private static function tick(e:Event):void {
            if(done)return;++ticks;
            try {
                w=cls("fe.World")["w"];
                if(worldIndex==1 && caseIndex>=3 && w && w.grafon && w.grafon.sceneLarge && !("sceneCullRender" in w.grafon)) cullSurfaces();
                if(w && w.verror && w.verror.visible) throw new Error(w.verror.txt.text);
                if(getTimer()-started>580000) throw new Error("Timeout phase "+phase);
                if(w && w.gg) {w.godMode=true;w.gg.invulner=true;}
                if(phase==0 && w && w.mm && w.mm.loaded && w.allLandsLoaded && w.textLoaded && main.getChildByName("ContinuousSceneCarrier") && main.getChildByName("ContinuousSceneCarrier")["sceneAPI"].ready) {
                    w.grafon.scenePreload=File.applicationDirectory.resolvePath("preload.flag").exists;report.preload=w.grafon.scenePreload;
                    w.mm.active=false;w.newGame(-1,"Scene Perf",{propusk:true});phase=1;
                } else if(phase==1 && w.ng_wait==0 && w.allStat==1 && w.gg && w.loc) {
                    if(!w.gg.ggControl || w.pip.noAct) {ready=0;w.ctr.keyPressed=w.ctr.keyPressed2=true;return;}
                    if(++ready<30)return;setting("wallblend","enabled",true);setting("realisticvision","enabled",true);registerNative();travel();
                } else if(phase==2 && w.land && w.land.act.id==(worldIndex==0?"scene_perf_native":"continuous_scene") && w.t_exit==0 && w.allStat==1) {
                    report.samples.push({world:worldIndex==0?"native":"large",entryMs:getTimer()-travelAt,resident:w.grafon.sceneResident});
                    w.ctr.clearAll();w.gg.ggControl=true;w.ctr.active=true;w.cam.setZoom(0);caseIndex=0;startCase();
                } else if(phase==3) {
                    var now:int=getTimer(),age:int=ticks-at;
                    var profiler:*=main.getChildByName("ContinuousSceneVisionProfile");
                    if(age==30 && profiler) profiler["api"].reset();
                    var weapon:*=w.gg.currentWeapon;
                    if(age>30) {
                        row.frames.push(now-last);row.script.push(now-frameStart);
                        if(weapon && weapon.hold<weapon.holder)++row.shots;
                        row.dirtyMax=Math.max(row.dirtyMax,w.grafon.sceneLastDirtyCount);
                    }
                    last=now;
                    w.cam.celX=w.gg.X*w.cam.scaleV+w.cam.vx+450;
                    w.cam.celY=(w.gg.Y-30)*w.cam.scaleV+w.cam.vy;
                    var firing:Boolean=String(row.name).indexOf("fire")>=0;
                    w.ctr.keyAttack=firing && age%Math.max(4,int(weapon.rapid)+1)==0;
                    if(weapon) {weapon.hold=weapon.holder;weapon.hp=weapon.maxhp;}
                    if(age>=150) {
                        if(firing && row.shots==0) throw new Error("No real weapon shots in "+row.world+" "+row.name);
                        w.ctr.clearAll();row.redrawsEnd=w.grafon.sceneRedraws;
                        var revisions:int=0;for each(var surface:Object in w.grafon.sceneSurfaces()) revisions+=surface.revision;
                        row.surfaceRevisions=revisions;report.samples.push(row);
                        if(profiler) row.visionProfile=profiler["api"].snapshot();
                        log("SAMPLE "+JSON.stringify(row));
                        if(++caseIndex<(worldIndex==0?3:cases.length)) startCase();
                        else if(worldIndex++==0) travel();else finish(true);
                    }
                }
            } catch(error:Error) {finish(false,error.message+"\n"+error.getStackTrace());}
        }
        private static function cullSurfaces():void {
            var scale:Number=w.cam.scaleV>0?w.cam.scaleV:1;
            var view:Rectangle=new Rectangle(-w.cam.vx/scale-80,-w.cam.vy/scale-80,
                w.cam.screenX/scale+160,w.cam.screenY/scale+160);
            for each(var surface:Object in w.grafon.sceneSurfaces()) {
                var show:Boolean=view.intersects(new Rectangle(surface.x+surface.gutter,surface.y+surface.gutter,surface.side,surface.side));
                for each(var bitmap:Bitmap in surface.bitmaps) bitmap.visible=show;
            }
            for each(var parent:* in [w.grafon.visFront,w.grafon.visBack])
                for(var k:int=0;k<parent.numChildren;++k) {
                    bitmap=parent.getChildAt(k) as Bitmap;
                    if(bitmap && (bitmap.name=="WallBlendSceneFront" || bitmap.name=="WallBlendSceneBack"))
                        bitmap.visible=view.intersects(new Rectangle(bitmap.x,bitmap.y,320,320));
                }
        }
    }
}
