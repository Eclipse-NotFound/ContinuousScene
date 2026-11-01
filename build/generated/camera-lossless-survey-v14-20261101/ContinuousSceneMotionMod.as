package {
    import flash.geom.Rectangle;
    import flash.display.BitmapData;
    import flash.geom.Matrix;
    import flash.display.DisplayObject;
    import flash.display.DisplayObjectContainer;
    import flash.desktop.NativeApplication;
    import flash.events.Event;
    import flash.filesystem.File;
    import flash.filesystem.FileMode;
    import flash.filesystem.FileStream;
    import flash.media.SoundMixer;
    import flash.media.SoundTransform;
    import flash.system.System;
    import flash.utils.getDefinitionByName;
    import flash.utils.getQualifiedClassName;
    import flash.utils.getTimer;

    /** Isolated diagnostic. No pixel hashing, extra sceneTick, or disk I/O in timed blocks. */
    public class ContinuousSceneMotionMod {
        private static var main:*,w:*,g:*,cam:*,player:*,loc:*,options:Object={};
        private static var phase:int=0,age:int=0,ready:int=0,started:int,preAt:int,previousAt:int;
        private static var centerX:Number,centerY:Number,done:Boolean=false;
        private static var schedule:Array=[],index:int=0,warmPass:int=0,warmCount:int;
        private static var block:Object,route:String="static",mode:String="full";
        private static var rows:Array=[],layers:Array=[],originalVisibility:Array=[],objectVisibility:Array=[];
        private static var lightVisible:Boolean;
        private static var tdfc:*,tdfcBridge:*;
        private static var drawing:String="full",visualChecked:Boolean=false;
        private static var report:Object={ok:false,diagnosticOnly:true,version:"camera-lossless-survey-14",assertions:[],samples:[],blocks:[],warm:[],warmFrames:[]};

        public static function init(host:*):void {
            if(!/^pfe-modsettings-continuous-motion-[0-9a-f]{32}$/.test(NativeApplication.nativeApplication.applicationID))return;
            main=host;started=getTimer();
            main.stage.nativeWindow.visible=true;
            SoundMixer.soundTransform=new SoundTransform(0);
            var f:File=File.applicationDirectory.resolvePath("review-controls.json");
            var s:FileStream=new FileStream();s.open(f,FileMode.READ);options=JSON.parse(s.readUTFBytes(s.bytesAvailable));s.close();
            report.options=options;
            main.stage.addEventListener(Event.ENTER_FRAME,before,false,1001);
            main.stage.addEventListener(Event.ENTER_FRAME,after,false,-3000);
        }
        private static function assertThat(name:String,value:Boolean,detail:*=null):void {
            report.assertions.push({name:name,ok:value,detail:detail});
            if(!value)throw new Error(name+": "+JSON.stringify(detail));
        }
        private static function setting(mod:String,key:String,value:*):void {
            var carrier:*=main.getChildByName("ModSettingsCarrier");
            for each(var p:Object in carrier["modAPI"].getPages())if(p.modId==mod)
                for each(var item:Object in p.items)if(item.key==key){item["set"](value);assertThat(mod+":"+key,item["get"]()===value);return;}
            throw new Error("Missing setting "+mod+":"+key);
        }
        private static function settingsReady():Boolean {
            var carrier:*=main.getChildByName("ModSettingsCarrier");
            if(!carrier || !carrier["modAPI"])return false;
            var found:int=0;
            for each(var page:Object in carrier["modAPI"].getPages())
                if(["continuousscene","wallblend","realisticvision","light-and-darkness"].indexOf(page.modId)>=0)++found;
            return found==4;
        }
        private static function counters():Object {
            var a:Object={};
            for each(var k:String in ["sceneWarmCount","sceneWarmForced","sceneDrawMs","sceneRedraws","sceneMisses","sceneResident","sceneEvictions"])
                if(k in g)a[k]=g[k];
            return a;
        }
        private static function tree(c:DisplayObjectContainer,depth:int=0):Array {
            var a:Array=[];
            for(var i:int=0;i<c.numChildren;++i){var d:DisplayObject=c.getChildAt(i);a.push({name:d.name,type:String(d),visible:d.visible,x:d.x,y:d.y,alpha:d.alpha,cacheAsBitmap:d.cacheAsBitmap,filters:d.filters.length,scrollRect:d.scrollRect,children:d is DisplayObjectContainer?DisplayObjectContainer(d).numChildren:0});}
            return a;
        }
        private static function target(axis:String,n:int):void {
            cam.camRun=true;cam.quakeX=cam.quakeY=0;cam.otryv=0;cam.showOn=false;
            var wave:Number=Math.sin(n*2*Math.PI/90);
            cam.X=Math.round(centerX+(axis=="x"?160*wave:0));
            cam.Y=Math.round(centerY+(axis=="y"?96*wave:0));
            w.ctr.keyLook=false;w.ctr.keyZoom=false;
        }
        private static function menuLayer():Object {
            for(var i:int=0;i<main.numChildren;++i) {
                var child:*=main.getChildAt(i);
                if(getQualifiedClassName(child)=="visMainMenu")return {attached:true,visible:child.visible,index:i};
            }
            return {attached:false};
        }
        private static function before(e:Event):void {
            preAt=getTimer();
            if(done || !cam)return;
            try {
                if(phase==10)target(int(age/90)%2==0?"x":"y",age);
                if(phase==20)target(route,age);
            }catch(error:Error){finish(error.message+"\n"+error.getStackTrace());}
        }
        private static function begin():void {
            g=w.grafon;cam=w.cam;loc=w.loc;player=w.gg;
            assertThat("large-scene",g.sceneLarge && loc.limX>3000 && loc.limY>2000);
            if(!options.defaultWindow)cam.setZoom(0);
            var placement:Object=CameraProbePlatform.select(w,2200,2200);
            report.placement=placement;
            player.setPos(placement.x,placement.y);player.dx=player.dy=0;
            cam.camRun=false;cam.calc(player);phase=3;age=0;
        }
        private static function prepared():void {
            centerX=player.X*cam.scaleV;centerY=player.Y*cam.scaleV-100;
            // Camera Y includes the native +100 vertical offset. Keep the actor near the center.
            centerX=Math.max(cam.screenX/2+180,Math.min(loc.limX*cam.scaleV-cam.screenX/2-180,centerX));
            centerY=Math.max(cam.screenY/2+210,Math.min(loc.limY*cam.scaleV-cam.screenY/2-10,centerY));
            target("static",0);cam.calc(player);
            report.entry={x:player.X,y:player.Y,width:loc.limX,height:loc.limY,units:loc.units.length,
                stageWidth:main.stage.stageWidth,stageHeight:main.stage.stageHeight,scale:cam.scaleV,
                frameRate:main.stage.frameRate,quality:main.stage.quality,centerX:centerX,centerY:centerY,
                mainChildren:tree(main),worldChildren:tree(w.visual),counters:counters()};
            report.menuBefore=menuLayer();
            if(options.legacyMenu){var waitVisible:Boolean=w.vwait.visible;w.mm.mainMenuOff();w.vwait.visible=waitVisible;}
            report.menuAfter=menuLayer();
            assertThat("main-menu-detached",!report.menuAfter.attached);
            // Visibility ownership check uses a real native hidden actor, without stepping or altering combat.
            var Spectre:Class=getDefinitionByName("fe.unit.UnitSpectre") as Class;
            var hidden:*=new Spectre();hidden.X=player.X;hidden.Y=player.Y;hidden.loc=loc;
            var nativeHidden:Boolean=hidden.vis.visible;
            loc.units.push(hidden);
            try {g.sceneTick();report.nativeHiddenActor={className:"UnitSpectre",before:nativeHidden,after:hidden.vis.visible};}
            finally {loc.units.splice(loc.units.indexOf(hidden),1);}
            assertThat("native-hidden-preserved",report.nativeHiddenActor.after===false);
            report.objectCensus=[];
            var view:Rectangle=new Rectangle(-cam.vx/cam.scaleV,-cam.vy/cam.scaleV,cam.screenX/cam.scaleV,cam.screenY/cam.scaleV);
            for each(var objectLayer:* in g.visObjs) {
                var census:Object={total:objectLayer.numChildren,visibleInView:0,classes:{},cachedInView:0};
                for(var ci:int=0;ci<objectLayer.numChildren;++ci) {
                    var child:DisplayObject=objectLayer.getChildAt(ci);
                    if(!child.visible || !view.intersects(child.getBounds(g.visual)))continue;
                    ++census.visibleInView;
                    if(child.cacheAsBitmap)++census.cachedInView;
                    var cn:String=getQualifiedClassName(child);
                    census.classes[cn]=int(census.classes[cn])+1;
                }
                report.objectCensus.push(census);
            }
            report.unitCensus={};
            for each(var unit:* in loc.units){cn=getQualifiedClassName(unit);report.unitCensus[cn]=int(report.unitCensus[cn])+1;}

            layers=[g.visFront,g.visBack,g.visBack2,g.visVoda];
            for each(var layer:* in layers)originalVisibility.push(layer.visible);
            for each(layer in g.visObjs)objectVisibility.push(layer.visible);
            lightVisible=g.visLight.visible;
            if(options.nativePresentation)main.getChildByName("ContinuousSceneCarrier")["nativeAPI"].scenePresentationEnabledV1(false);
            var tcarrier:*=main.getChildByName("ContinuousSceneTdfcThreat");
            assertThat("tdfc-candidate-interface",tcarrier && tcarrier.runtime);
            tdfc=tcarrier.runtime;tdfcBridge=tcarrier.api;tdfc.scenePoolEnabled=true;tdfc.sceneValidate=true;
            snapshotChecks();environmentSurvey();auxiliarySurvey();
            main.stage.frameRate=120;phase=10;age=0;warmCount=g.sceneWarmCount;previousAt=getTimer();
        }
        private static function makeSchedule():void {
            assertThat("runtime-snapshot-equivalence",tdfc.sceneChecks>0 && tdfc.sceneFailures==0,tdfc.sceneStats());
            tdfc.sceneValidate=false;
            for each(var axis:String in ["static","x","y"])
                for each(var draw:String in ["base","pool","pool","base"])
                    schedule.push({fps:options.fps || 120,axis:axis,mode:draw,frames:300});
            report.schedule=schedule;index=0;enterBlock();
        }
        private static function enterBlock():void {
            block=schedule[index];route=block.axis;mode=block.mode;main.stage.frameRate=block.fps;
            age=0;previousAt=0;rows=[];phase=20;tdfc.scenePoolEnabled=(mode=="pool");
            var api:*=main.getChildByName("ContinuousSceneCarrier")["nativeAPI"];
            report.blocks.push({index:index,settings:block,start:getTimer(),startCounters:counters(),presentation:api.scenePresentationStatsV1(),activity:api.activityStats()});
        }
        private static function after(e:Event):void {
            if(done)return;
            var now:int=getTimer();
            try {
                w=getDefinitionByName("fe.World")["w"];
                if(now-started>540000)throw new Error("Timed out phase "+phase);
                if(w && w.verror && w.verror.visible)throw new Error(w.verror.txt.text);
                if(w && w.gg){w.godMode=true;w.gg.invulner=true;}
                if(phase==0 && w && w.mm && w.mm.loaded && w.allLandsLoaded && w.textLoaded && settingsReady()) {
                    if(++ready<20)return;
                    setting("continuousscene","nativeEnabled",true);setting("wallblend","enabled",false);
                    setting("realisticvision","enabled",false);setting("realisticvision","wallbright",false);setting("light-and-darkness","enabled",false);
                    if(options.legacyMenu)w.mm.active=false;else w.mm.mainMenuOff();
                    w.newGame(-1,"Camera review private fixture",{propusk:true});phase=1;ready=0;
                } else if(phase==1 && w.ng_wait==0 && w.allStat==1 && w.gg && w.loc && w.t_exit==0) {
                    if(!w.gg.ggControl || w.pip.noAct){ready=0;w.ctr.keyPressed=w.ctr.keyPressed2=true;return;}
                    if(++ready<30)return;ready=0;w.ctr.clearAll();w.pers.healAll();
                    w.game.lands["random_mane"].landStage=4;
                    getDefinitionByName("fe.loc.Land")["rconnectSeedSource"]=function(value:*):uint{return 4077752896;};
                    w.game.beginMission("random_mane");phase=2;
                } else if(phase==2 && w.land && w.land.act.id=="random_mane" && w.t_exit==0 && w.allStat==1) {
                    if(++ready<60)return;begin();
                } else if(phase==3) {if(++age>=45)prepared();}
                else if(phase==10) {
                    report.warmFrames.push([warmPass,age,now-previousAt,now-preAt,w.visual.x,w.visual.y,g.sceneWarmCount,g.sceneResident,main.stage.frameRate]);previousAt=now;
                    if(++age==180){report.warm.push({pass:++warmPass,delta:g.sceneWarmCount-warmCount,counters:counters()});
                        if(g.sceneWarmCount==warmCount && g.sceneViewReady())makeSchedule();
                        else {assertThat("bounded-warm",warmPass<24);age=0;warmCount=g.sceneWarmCount;}}
                } else if(phase==20) {
                    var ts:Object=tdfc.sceneStats();
                    var px:Number=player.X*w.visual.scaleX+w.visual.x,py:Number=player.Y*w.visual.scaleY+w.visual.y;
                    rows.push([age,previousAt?now-previousAt:-1,now-preAt,cam.X,cam.Y,w.visual.x,w.visual.y,
                        player.X,player.Y,g.sceneWarmCount,g.sceneDrawMs,px,py,getTimer()-now,System.totalMemory,ts.cost,ts.active,ts.calls,ts.reuses]);
                    previousAt=now;
                    if(++age>=block.frames){
                        var mark:Object=report.blocks[index];mark.end=getTimer();mark.endCounters=counters();mark.rows=rows;mark.tdfc=tdfc.sceneStats();
                        mark.actualFrameRate=main.stage.frameRate;
                        if(++index>=schedule.length){finish();return;}enterBlock();
                    }
                }
            }catch(error:Error){finish(error.message+"\n"+error.getStackTrace());}
        }
        private static function snapshotChecks():void {
            var calls:int=0,fields:int=0;
            var values:Array=loc.units.concat([null,{}, {X:NaN,Y:25,scX:70,storona:-1,currentWeapon:{tip:3,hold:0,rot:NaN}}, {X:-200,Y:-3,fraction:100,sost:1,npc:true}]);
            for each(var u:* in values) {
                var a:Object=tdfcBridge.snapshot(u),b:Object=tdfcBridge.snapshotInto(u,{});
                for(var k:String in a) {
                    var av:*=a[k],bv:*=b[k];
                    if(av!==bv && !(av is Number && bv is Number && isNaN(av) && isNaN(bv)))throw new Error("snapshot mismatch "+k);
                    ++fields;
                }
                if(tdfcBridge.snapshot(u)===a)throw new Error("public snapshot must remain fresh");
                ++calls;
            }
            report.snapshotChecks={units:calls,fields:fields};
            assertThat("snapshot-field-equivalence",calls>50 && fields>2000,report.snapshotChecks);
        }
        private static function environmentSurvey():void {
            var objects:Array=[],skip:Array=[],counts:Object={},o:*=loc.firstObj,n:int=0;
            while(o && ++n<10000) {
                var cn:String=getQualifiedClassName(o);
                var excluded:Boolean=cn=="fe.loc::Box" && o.dead && o.invis;
                objects.push(o);skip.push(excluded);counts[cn]=int(counts[cn])+1;o=o.nobj;
            }
            assertThat("bounded-environment-census",n<10000);
            report.environmentSurvey={objects:objects.length,classes:counts,noopBoxes:0,trials:[]};
            for each(var value:Boolean in skip)if(value)++report.environmentSurvey.noopBoxes;
            try {
                for each(var fast:Boolean in [false,true,true,false]) {
                    var start:int=getTimer(),calls:int=0;
                    for(var repeat:int=0;repeat<100;++repeat) {
                        g.sceneNativeEnvironment(loc,player.X,player.Y);
                        for(var i:int=0;i<objects.length;++i)if(!fast || !skip[i]) {
                            o=objects[i];g.sceneNativeEnvironment(loc,o.X,o.Y);++calls;
                        }
                        g.sceneNativeEnvironment(loc,player.X,player.Y);
                    }
                    report.environmentSurvey.trials.push({skipNoop:fast,iterations:100,calls:calls,ms:getTimer()-start});
                }
            } finally {g.sceneNativeEnvironment(loc,player.X,player.Y);}
        }
        private static function auxiliarySurvey():void {
            report.auxiliarySurvey={};
            var carrier:*=main.getChildByName("AddictionSystemCarrier");
            if(carrier && carrier.api && carrier.api.engine) {
                var engine:*=carrier.api.engine,start:int=getTimer(),bytes:int=0;
                for(var i:int=0;i<1000;++i)bytes+=engine.json().length;
                report.auxiliarySurvey.addictionJson={iterations:1000,ms:getTimer()-start,characters:bytes};
            }
        }
        private static function finish(error:String=null):void {
            if(done)return;done=true;
            if(tdfc)tdfc.scenePoolEnabled=false;
            main.stage.removeEventListener(Event.ENTER_FRAME,before);main.stage.removeEventListener(Event.ENTER_FRAME,after);
            report.ok=error==null;report.error=error;report.elapsedMs=getTimer()-started;
            report.columns=["age","intervalMs","prePostMs","camX","camY","visualX","visualY","playerX","playerY","warmCount","drawMs","screenPlayerX","screenPlayerY","probePostMs","memoryBytes","tdfcCostMs","tdfcActive","tdfcCalls","tdfcReuses"];
            var stream:FileStream=new FileStream();stream.open(File.applicationStorageDirectory.resolvePath("result.json"),FileMode.WRITE);
            stream.writeUTFBytes(JSON.stringify(report));stream.close();NativeApplication.nativeApplication.exit(error?1:0);
        }
    }
}
