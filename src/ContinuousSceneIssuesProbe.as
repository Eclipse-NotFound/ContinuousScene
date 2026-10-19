package {
    import flash.desktop.NativeApplication;
    import flash.display.BitmapData;
    import flash.display.DisplayObject;
    import flash.display.DisplayObjectContainer;
    import flash.display.MovieClip;
    import flash.display.PNGEncoderOptions;
    import flash.geom.Rectangle;
    import flash.events.Event;
    import flash.events.UncaughtErrorEvent;
    import flash.filesystem.File;
    import flash.filesystem.FileMode;
    import flash.filesystem.FileStream;
    import flash.utils.getDefinitionByName;
    import flash.utils.getQualifiedClassName;
    import flash.utils.getTimer;

    /** Player-reported native Manehattan doors, border state and stationary cost.
     * Only reached by the isolated probe entry; never linked into production. */
    public class ContinuousSceneIssuesProbe {
        private static var main:*,w:*,phase:int=0,age:int=0,ready:int=0;
        private static var started:int,frameStart:int,band50:int,band150:int,band250:int,last:int;
        private static var done:Boolean=false,caseIndex:int=0,row:Object;
        private static var renderControls:Boolean=false,hidden:Array=[];
        private static var clipControls:Boolean=false;
        private static var mechanics:Boolean=false;
        private static var animationControls:Boolean=false;
        private static var activityControls:Boolean=false;
        private static var userVision:Boolean=false;
        private static var targetStage:int=1;
        private static var wrapperControls:Boolean=false;
        private static var combatControls:Boolean=false;
        private static var largeChunks:Boolean=false;
        private static var nativeRooms:Boolean=false;
        private static var lightControls:Boolean=false;
        private static var impactControls:Boolean=false;
        private static var entryAt:int;
        private static var objectCulling:SceneObjectCulling=new SceneObjectCulling();
        private static var report:Object={version:"0.8-issues-probe",assertions:[],samples:[],doors:[],borders:[]};
        private static var cases:Array=["all-default-walls-idle","all-bright-walls-idle","no-lad-idle","no-lad-wall-idle","no-vision-light-wall-idle","no-world-draw-control"];
        public static function init(host:*):void {
            main=host;started=getTimer();
            renderControls=File.applicationDirectory.resolvePath("render-controls.flag").exists;
            if(renderControls)cases=["native-render-baseline","offscreen-children-hidden","viewport-scroll-clip","native-light-hidden"];
            clipControls=File.applicationDirectory.resolvePath("clip-controls.flag").exists;
            mechanics=File.applicationDirectory.resolvePath("mechanics-controls.flag").exists;
            animationControls=File.applicationDirectory.resolvePath("animation-controls.flag").exists;
            activityControls=File.applicationDirectory.resolvePath("activity-controls.flag").exists;
            userVision=File.applicationDirectory.resolvePath("user-vision-controls.flag").exists;
            if(File.applicationDirectory.resolvePath("stage5-controls.flag").exists)targetStage=5;
            wrapperControls=File.applicationDirectory.resolvePath("wrapper-controls.flag").exists;
            if(wrapperControls)cases=["objects-all-a","objects-viewport-a","objects-all-b","objects-viewport-b"];
            combatControls=File.applicationDirectory.resolvePath("combat-controls.flag").exists;
            largeChunks=File.applicationDirectory.resolvePath("large-chunks-controls.flag").exists;
            nativeRooms=File.applicationDirectory.resolvePath("native-rooms-controls.flag").exists;
            lightControls=File.applicationDirectory.resolvePath("light-controls.flag").exists;
            impactControls=File.applicationDirectory.resolvePath("impact-controls.flag").exists;
            if(impactControls)combatControls=true;
            if(combatControls)cases=["assault-rifle-idle","assault-rifle-fire","minigun-idle","minigun-fire"];
            if(activityControls)cases=["distant-paused-a","all-enemies-running-a","distant-paused-b","all-enemies-running-b"];
            if(animationControls)cases=["original-idle-animation-a","reuse-idle-animation-a","original-idle-animation-b","reuse-idle-animation-b"];
            if(lightControls)cases=["light-redraw-a","light-reuse-a","light-redraw-b","light-reuse-b"];
            if(impactControls)cases=["full-impact-a","small-impact-a","full-impact-b","small-impact-b"];
            if(animationControls && activityControls)throw new Error("Conflicting comparison flags");
            report.controls={animation:animationControls,activity:activityControls,userVision:userVision,targetStage:targetStage};
            if(clipControls){renderControls=true;cases=["native-render-baseline","offscreen-empty-clip","native-light-clip","both-layer-clips"];}
            main.stage.addEventListener(Event.ENTER_FRAME,begin,false,1000);
            main.stage.addEventListener(Event.ENTER_FRAME,function(e:Event):void {band50=getTimer();},false,-50);
            main.stage.addEventListener(Event.ENTER_FRAME,function(e:Event):void {band150=getTimer();},false,-150);
            main.stage.addEventListener(Event.ENTER_FRAME,function(e:Event):void {band250=getTimer();},false,-250);
            main.stage.addEventListener(Event.ENTER_FRAME,tick,false,-1000);
            main.loaderInfo.uncaughtErrorEvents.addEventListener(UncaughtErrorEvent.UNCAUGHT_ERROR,function(e:UncaughtErrorEvent):void {finish(String(e.error));});
        }
        private static function begin(e:Event):void {frameStart=band50=band150=band250=getTimer();}
        private static function write(name:String,value:String):void {
            var fs:FileStream=new FileStream();fs.open(File.applicationStorageDirectory.resolvePath(name),FileMode.WRITE);
            fs.writeUTFBytes(value);fs.close();
        }
        private static function check(name:String,ok:Boolean,detail:*=null):void {report.assertions.push({name:name,ok:ok,detail:detail});}
        private static function setting(mod:String,key:String,value:*):void {
            var api:*=main.getChildByName("ModSettingsCarrier")["modAPI"];
            for each(var page:Object in api.getPages())if(page.modId==mod)
                for each(var item:Object in page.items)if(item.key==key) {item["set"](value);return;}
            throw new Error("Missing setting "+mod+"."+key);
        }
        private static function finish(error:String=null):void {
            if(done)return;done=true;report.error=error;report.elapsedMs=getTimer()-started;
            report.ok=error==null;
            for each(var a:Object in report.assertions)if(!a.ok)report.ok=false;
            write("result.json",JSON.stringify(report,null,2));
            NativeApplication.nativeApplication.exit(report.ok?0:1);
        }
        private static function border(label:String):void {
            var c:*=w.cam,g:*=w.grafon,s:Number=c.scaleV;
            var expected:Object={left:c.screenX>c.maxsx*s?-(c.screenX-c.maxsx*s)/100/s-0.5:-0.5/s,
                right:c.screenX>c.maxsx*s?(c.screenX-c.maxsx*s+5)/100/s+0.5:0.5/s,
                top:c.screenY>c.maxsy*s?-(c.screenY-c.maxsy*s)/100/s-0.5:-0.5/s,
                bottom:c.screenY>c.maxsy*s?(c.screenY-c.maxsy*s+5)/100/s+0.5:0.6/s};
            var actual:Object={left:g.ramL.scaleX,right:g.ramR.scaleX,top:g.ramT.scaleY,bottom:g.ramB.scaleY};
            var ok:Boolean=Math.abs(g.ramR.x-(w.loc.limX-1))<0.01 && Math.abs(g.ramB.y-(w.loc.limY-1))<0.01;
            for(var k:String in actual)if(Math.abs(actual[k]-expected[k])>0.001)ok=false;
            report.borders.push({label:label,actual:actual,expected:expected,rightX:g.ramR.x,bottomY:g.ramB.y,zoom:c.isZoom});
            check("native-border-"+label,ok);
        }
        private static function doors():void {
            var count:int=0,misplaced:int=0,detached:int=0;
            for each(var b:* in w.loc.objs) {
                if(!b || !("door" in b) || b.door<=0 || b.dead || b.invis)continue;
                ++count;
                var same:Boolean=b.vis && Math.abs(b.vis.x-b.X)<0.01 && Math.abs(b.vis.y-b.Y)<0.01;
                if(!same)++misplaced;
                if(!b.vis || !b.vis.stage)++detached;
                report.doors.push({id:b.id,x:b.X,y:b.Y,visX:b.vis?b.vis.x:null,visY:b.vis?b.vis.y:null,
                    stage:b.vis && b.vis.stage!=null,frame:b.vis?b.vis.currentFrame:null,
                    shadowX:b.shad?b.shad.x:null,shadowY:b.shad?b.shad.y:null});
            }
            check("native-mane-contains-doors",count>0,count);
            check("all-native-door-visuals-follow-logical-position",misplaced==0,misplaced);
            check("all-live-door-visuals-attached",detached==0,detached);
        }
        private static function screenshot():void {
            var shot:BitmapData=new BitmapData(main.stage.stageWidth,main.stage.stageHeight,false,0);
            shot.draw(main.stage);
            var fs:FileStream=new FileStream();fs.open(File.applicationStorageDirectory.resolvePath("issues-entry.png"),FileMode.WRITE);
            fs.writeBytes(shot.encode(shot.rect,new PNGEncoderOptions()));fs.close();shot.dispose();
        }
        private static function fixedVisuals():void {
            var types:Array=["fe.loc.Bonus","fe.loc.Trap","fe.loc.CheckPoint","fe.unit.UnitTurret"];
            report.fixedVisuals=[];
            for each(var type:String in types) {
                var cls:Class=getDefinitionByName(type) as Class,count:int=0,bad:int=0,examples:Array=[];
                for(var obj:*=w.loc.firstObj;obj;obj=obj.nobj)if(obj is cls && obj.vis) {
                    ++count;if(Math.abs(obj.vis.x-obj.X)>0.01 || Math.abs(obj.vis.y-obj.Y)>0.01) {
                        ++bad;examples.push({id:obj.id,x:obj.X,y:obj.Y,visX:obj.vis.x,visY:obj.vis.y,
                            dx:obj.dx,dy:obj.dy,disabled:("disabled" in obj)?obj.disabled:null,sost:("sost" in obj)?obj.sost:null});
                    }
                    if("vis2" in obj && obj.vis2 && (Math.abs(obj.vis2.x-obj.X)>0.01 || Math.abs(obj.vis2.y-obj.Y)>0.01))++bad;
                }
                report.fixedVisuals.push({type:type,count:count,misplaced:bad});
                check("fixed-visuals-"+type,bad==0,{count:count,misplaced:bad,examples:examples});
            }
        }
        private static function animationInventory():Object {
            var result:Object={clips:0,playing:0,offscreenPlaying:0,types:{}};
            var view:Rectangle=w.grafon.sceneViewport();
            var queue:Array=[w.visual];
            while(queue.length) {
                var node:DisplayObject=queue.pop() as DisplayObject;
                var mc:MovieClip=node as MovieClip;
                if(mc) {
                    ++result.clips;
                    if(mc.isPlaying && mc.totalFrames>1) {
                        ++result.playing;
                        if(view && !view.intersects(mc.getBounds(w.visual))) {
                            ++result.offscreenPlaying;
                            var name:String=getQualifiedClassName(mc);result.types[name]=int(result.types[name])+1;
                        }
                    }
                }
                var container:DisplayObjectContainer=node as DisplayObjectContainer;
                if(container)for(var i:int=0;i<container.numChildren;++i)queue.push(container.getChildAt(i));
            }
            return result;
        }
        private static function startCase():void {
            if(combatControls) {
                var desired:String=impactControls?"minigun":caseIndex<2?"assr":"minigun";
                if(!w.gg.currentWeapon || w.gg.currentWeapon.id!=desired)w.gg.changeWeapon(desired);
                if(impactControls)w.grafon.sceneCompactImpacts=(caseIndex%2)==1;
            }
            if(lightControls)main.getChildByName("LightAndDarknessCarrier")["ladAPI"].runtime.field.reuseSceneFrames=(caseIndex%2)==1;
            else if(wrapperControls || combatControls){}
            else if(activityControls)w.grafon.scenePauseDistant=(caseIndex%2)==0;
            else if(animationControls)w.grafon.sceneReuseIdleFrame=(caseIndex%2)==1;
            else if(renderControls) {
                if(caseIndex==0) {
                    setting("light-and-darkness","enabled",false);setting("wallblend","enabled",false);setting("realisticvision","enabled",false);
                }
                if(!clipControls && caseIndex==1) {
                    var v:Rectangle=new Rectangle(-w.cam.vx/w.cam.scaleV-100,-w.cam.vy/w.cam.scaleV-100,
                        w.cam.screenX/w.cam.scaleV+200,w.cam.screenY/w.cam.scaleV+200);
                    for each(var layer:* in w.grafon.visObjs)for(var j:int=0;j<layer.numChildren;++j) {
                        var child:DisplayObject=layer.getChildAt(j);
                        if(child.visible && !v.intersects(child.getBounds(w.visual))){hidden.push(child);child.visible=false;}
                    }
                    report.hiddenChildren=hidden.length;
                }
                if(!clipControls && caseIndex==2) {for each(child in hidden)child.visible=true;hidden=[];}
                if(!clipControls && caseIndex==3) {w.visual.scrollRect=null;w.grafon.visLight.visible=false;}
                if(clipControls && caseIndex==1) {
                    v=new Rectangle(-w.cam.vx/w.cam.scaleV-150,-w.cam.vy/w.cam.scaleV-150,
                        w.cam.screenX/w.cam.scaleV+300,w.cam.screenY/w.cam.scaleV+300);
                    for each(layer in w.grafon.visObjs)for(j=0;j<layer.numChildren;++j) {
                        child=layer.getChildAt(j);
                        if(child.scrollRect==null && !v.intersects(child.getBounds(w.visual))){hidden.push(child);child.scrollRect=new Rectangle();}
                    }
                    report.clippedChildren=hidden.length;
                }
                if(clipControls && caseIndex==2) {for each(child in hidden)child.scrollRect=null;hidden=[];}
            } else {
            if(caseIndex==1) {
                setting("realisticvision","wallbright",true);
            }
            if(caseIndex==2) {setting("realisticvision","wallbright",false);setting("light-and-darkness","enabled",false);}
            if(caseIndex==3)setting("wallblend","enabled",false);
            if(caseIndex==4)setting("realisticvision","enabled",false);
            if(caseIndex==5)w.grafon.visual.visible=false;
            }
            row={name:cases[caseIndex],frames:[],listeners:[],defaultBand:[],wallBand:[],sceneBand:[],otherBand:[],
                units:w.loc.units.length,objects:w.loc.objs.length,residentStart:w.grafon.sceneResident,
                redrawsStart:w.grafon.sceneRedraws,stageFps:main.stage.frameRate,shots:0,
                chunkSide:w.grafon.sceneLarge?w.grafon.sceneSurfaces()[0].side:0,
                mode:w.grafon.sceneLarge?"large":"native",warmCountStart:w.grafon.sceneWarmCount};
            age=0;last=getTimer();phase=4;
        }
        private static function tick(e:Event):void {
            if(done)return;
            try {
                w=getDefinitionByName("fe.World")["w"];
                if(w && w.verror && w.verror.visible)throw new Error(w.verror.txt.text);
                if(getTimer()-started>500000)throw new Error("Timed out phase "+phase);
                if(w && w.gg){w.godMode=true;w.gg.invulner=true;}
                if(phase==0 && w && w.mm && w.mm.loaded && w.allLandsLoaded && w.textLoaded &&
                    main.getChildByName("ContinuousSceneCarrier") && main.getChildByName("ContinuousSceneCarrier")["sceneAPI"].ready) {
                    w.mm.active=false;w.newGame(-1,"Scene issues",{propusk:true});phase=1;
                }else if(phase==1 && w.ng_wait==0 && w.allStat==1 && w.gg && w.loc) {
                    if(!w.gg.ggControl || w.pip.noAct){ready=0;w.ctr.keyPressed=w.ctr.keyPressed2=true;return;}
                    if(++ready<30)return;
                    setting("continuousscene","nativeEnabled",!nativeRooms);
                    setting("wallblend","enabled",true);setting("realisticvision","enabled",!userVision);setting("light-and-darkness","enabled",true);
                    setting("realisticvision","wallbright",false);
                    report.visionSettings={enabled:!userVision,mode:"current",wallbright:false,brightControl:true};
                    if(mechanics)ContinuousSceneMechanicsChecks.prepare(main);
                    if(largeChunks)w.grafon.sceneChunkSide=640;
                    w.grafon.scenePreload=false;w.ctr.clearAll();w.game.lands["random_mane"].landStage=targetStage-1;
                    entryAt=getTimer();w.game.beginMission("random_mane");phase=2;
                }else if(phase==2 && w.land && w.land.act.id=="random_mane" && w.t_exit==0 && w.allStat==1) {
                    report.world={width:w.loc.spaceX,height:w.loc.spaceY,units:w.loc.units.length,objects:w.loc.objs.length};
                    report.entryMs=getTimer()-entryAt;
                    if(combatControls){
                        w.invent.addWeapon("assr");
                        var stressGun:*=w.invent.addWeapon("minigun");
                        // The isolated level-one character must be allowed to
                        // operate the native gun; cadence/projectiles are unchanged.
                        stressGun.lvl=0;stressGun.perslvl=0;
                        report.combatFixture="native assault rifle/minigun; minigun skill/level requirements waived; ammo and durability refilled";
                    }
                    check("actual-mane-expected-mode",nativeRooms?(!w.grafon.sceneLarge && w.loc.spaceX==48):(w.grafon.sceneLarge && w.loc.spaceX>48));
                    doors();border("entry");screenshot();age=0;phase=3;
                }else if(phase==3) {
                    w.ctr.clearAll();if(++age<120)return;
                    border("settled");fixedVisuals();
                    report.animations=animationInventory();
                    if(File.applicationDirectory.resolvePath("light-ray-controls.flag").exists) {
                        report.lightRays=ContinuousSceneLightRayChecks.run(main,w,check);finish();return;
                    }
                    if(File.applicationDirectory.resolvePath("wall-trim-controls.flag").exists) {
                        report.wallTrim=ContinuousSceneWallTrimChecks.run(w,check);finish();return;
                    }
                    if(lightControls)ContinuousSceneLightChecks.run(main,w,check);
                    if(mechanics){report.activity=ContinuousSceneActivityChecks.run(main,w,check);report.mechanics=ContinuousSceneMechanicsChecks.run(main,w,check);finish();return;}
                    startCase();
                }else if(phase==4) {
                    if(wrapperControls) {
                        var beforePixels:BitmapData=null,afterPixels:BitmapData=null;
                        if(age==0) {beforePixels=new BitmapData(main.stage.stageWidth,main.stage.stageHeight,false,0);beforePixels.draw(main.stage);}
                        objectCulling.update(w,(caseIndex%2)==1);
                        if(beforePixels) {
                            afterPixels=new BitmapData(beforePixels.width,beforePixels.height,false,0);afterPixels.draw(main.stage);
                            var difference:*=beforePixels.compare(afterPixels);
                            check("viewport-culling-identical-pixels-"+caseIndex,difference===0);
                            if(difference is BitmapData)difference.dispose();beforePixels.dispose();afterPixels.dispose();
                        }
                    }
                    w.ctr.clearAll();++age;
                    if(combatControls) {
                        var weapon:*=w.gg.currentWeapon;
                        if(weapon && weapon.hold<weapon.holder && age>30)++row.shots;
                        w.cam.celX=w.gg.X*w.cam.scaleV+w.cam.vx+450;
                        w.cam.celY=(w.gg.Y-30)*w.cam.scaleV+w.cam.vy;
                        w.ctr.keyAttack=impactControls || (caseIndex%2)==1;
                        if(weapon){weapon.hold=weapon.holder;weapon.hp=weapon.maxhp;}
                    }
                    var now:int=getTimer();
                    if(age==30 && "csIssueProfile" in w.loc)w.loc.csIssueProfile={};
                    if(age==30 && "csIssueProfile" in w.grafon)w.grafon.csIssueProfile={};
                    var UnitType:Class=getDefinitionByName("fe.unit.Unit") as Class;
                    if(age==30 && "csPlayerProfile" in UnitType)UnitType["csPlayerProfile"]={};
                    var ladRuntime:*=main.getChildByName("LightAndDarknessCarrier")["ladAPI"].runtime;
                    if(age==30 && "csProfile" in ladRuntime)ladRuntime.csProfile={};
                    var rv:*=main.getChildByName("CSIssuesVision");
                    if(age==30 && rv)rv["reset"]();
                    if(age>30) {
                        row.frames.push(now-last);row.listeners.push(now-frameStart);
                        row.defaultBand.push(band50-frameStart);row.wallBand.push(band150-band50);
                        row.sceneBand.push(band250-band150);row.otherBand.push(now-band250);
                    }
                    last=now;
                    if(renderControls && !clipControls && caseIndex==2) {
                        var clip:Rectangle=new Rectangle((-w.cam.vx-w.cam.quakeX)/w.cam.scaleV,
                            (-w.cam.vy-w.cam.quakeY)/w.cam.scaleV,w.cam.screenX/w.cam.scaleV,w.cam.screenY/w.cam.scaleV);
                        w.visual.scrollRect=clip;w.visual.x=0;w.visual.y=0;
                    }
                    if(clipControls)applyClips(caseIndex==3,caseIndex>=2);
                    if(age<150)return;
                    if(combatControls) {
                        row.weapon=w.gg.currentWeapon?w.gg.currentWeapon.id:null;
                        row.weaponStatus={auto:weapon.auto,rapid:weapon.rapid,ready:weapon.ready,prep:weapon.t_prep,attack:weapon.t_attack,status:weapon.status()};
                        check("expected-weapon-"+caseIndex,row.weapon==(impactControls?"minigun":caseIndex<2?"assr":"minigun"),row.weapon);
                        if(impactControls || (caseIndex%2)==1)check("real-player-weapon-fired-"+caseIndex,row.shots>0,row.shots);
                    }
                    row.residentEnd=w.grafon.sceneResident;row.redrawsEnd=w.grafon.sceneRedraws;
                    row.warmCountEnd=w.grafon.sceneWarmCount;row.warmMaxMs=w.grafon.sceneWarmMaxMs;
                    row.activity=main.getChildByName("ContinuousSceneCarrier")["nativeAPI"].activityStats();
                    row.hiddenObjects=objectCulling.hidden;
                    if(lightControls)row.reusedLightFrames=main.getChildByName("LightAndDarknessCarrier")["ladAPI"].runtime.field.reusedFrames;
                    if("csIssueProfile" in w.loc)row.nativeProfile=JSON.parse(JSON.stringify(w.loc.csIssueProfile));
                    if("csIssueProfile" in w.grafon)row.rendererProfile=JSON.parse(JSON.stringify(w.grafon.csIssueProfile));
                    if(rv)row.visionProfile=JSON.parse(JSON.stringify(rv["snapshot"]()));
                    if("csPlayerProfile" in UnitType)row.playerProfile=JSON.parse(JSON.stringify(UnitType["csPlayerProfile"]));
                    if("csProfile" in ladRuntime)row.ladProfile=JSON.parse(JSON.stringify(ladRuntime.csProfile));
                    report.samples.push(row);write("issues-progress.json",JSON.stringify(report,null,2));
                    // Instrumented attribution needs one full-effects window;
                    // final production measurements retain all five controls.
                    if(++caseIndex<cases.length && !rv && (combatControls || !("csPlayerProfile" in UnitType)))startCase();else {
                        w.grafon.visual.visible=true;
                        objectCulling.clear();
                        w.visual.scrollRect=null;w.grafon.visLight.visible=true;
                        if(clipControls)applyClips(false,false);
                        setting("light-and-darkness","enabled",true);setting("wallblend","enabled",true);setting("realisticvision","enabled",true);
                        for(var z:int=0;z<3;++z) {
                            w.cam.setZoom(z);w.gg.setLocPos(w.loc.limX-220,w.gg.Y);w.cam.calc(w.gg);border("right-zoom"+z);
                            w.gg.setLocPos(220,w.gg.Y);w.cam.calc(w.gg);border("left-zoom"+z);
                        }
                        finish();
                    }
                }
            }catch(error:Error){finish(error.message+"\n"+error.getStackTrace());}
        }
        private static function applyClips(objects:Boolean,light:Boolean):void {
            var c:*=w.cam;
            var view:Rectangle=new Rectangle((-c.vx-c.quakeX)/c.scaleV-100,(-c.vy-c.quakeY)/c.scaleV-100,
                c.screenX/c.scaleV+200,c.screenY/c.scaleV+200);
            for each(var layer:* in w.grafon.visObjs) {
                layer.scrollRect=objects?view:null;layer.x=objects?view.x:0;layer.y=objects?view.y:0;
            }
            var b:*=w.grafon.visLight.getChildAt(0);
            var r:Rectangle=new Rectangle(Math.max(0,Math.floor((view.x+20)/40)),Math.max(0,Math.floor((view.y+60)/40)),
                Math.ceil(view.width/40)+2,Math.ceil(view.height/40)+2);
            b.scrollRect=light?r:null;b.x=light?r.x:0;b.y=light?r.y:0;
        }
    }
}
