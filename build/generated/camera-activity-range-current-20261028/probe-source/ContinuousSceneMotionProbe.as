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
    import tests.SceneDenseCombatMetrics;
    import tests.SceneRasterTiming;
    import tests.SceneThreatChecks;
    import tests.ScenePresentationChecks;
    import tests.SceneNativeCropChecks;
    import tests.SceneAtlasChecks;
    import tests.SceneStoppedThreatChecks;
    import tests.SceneBlitReuse;
    import tests.SceneSleepingTimelineChecks;
    import tests.SceneImplicitFreezeProbe;
    import tests.SceneDisplayAttribution;
    import tests.SceneWorldLayerAttribution;
    import tests.SceneHudTextChecks;
    import tests.SceneEmptyTerrainProbe;
    import tests.SceneBackgroundCompositeProbe;
    import tests.SceneSleepingRootPresentation;
    import tests.ScenePlayerTimelineChecks;
    import tests.SceneCombatRoute;
    import tests.SceneUnitLayerCensus;
    import tests.SceneBulletBlendProbe;
    import tests.ScenePlayerCacheProbe;
    import tests.SceneActivityCensus;
    import tests.SceneActivityRangeProbe;
    import tests.SceneSatsChecks;
    import tests.SceneDecalChecks;
    import tests.SceneImpactChecks;

    /** Isolated movement attribution. Screenshot runs never supply timings. */
    public class ContinuousSceneMotionProbe {
        private static var main:*,w:*,loc:*,cfg:Object,phase:int=0,age:int=0,ready:int=0,index:int=0;
        private static var started:int,last:int,startFrame:int,band50:int,band150:int,band250:int,entryAt:int;
        private static var absoluteStart:int,lastEnd:int,priorAbsolute:int,priorProbe:int;
        private static var continuousPreviousSampleAt:int=-1;
        private static var activityRangeProbe:SceneActivityRangeProbe=new SceneActivityRangeProbe();
        private static var probeTimingRow:Object=null,probeTimingPending:Object=null;
        private static var probeTimingFrame:int,probeTimingSampleIndex:int,probeTimingEntered:int,probeTimingSampleAt:int;
        private static var probeTimingCensus:int,probeTimingSave:int,probeTimingProgressSave:int,probeTimingHeartbeatSave:int,probeTimingStartCase:int;
        private static var probeTimingPendingIndex:int,probeTimingExited:int;
        private static var renderAt:int,renderMs:int,renderCalls:int,exitAt:int,exitMs:int,exitCalls:int;
        private static var x0:Number,y0:Number,path:Number=2400,done:Boolean=false,row:Object;
        private static var report:Object={version:"motion-0.8.2",assertions:[],samples:[]};
        private static var objectCulling:SceneObjectCulling=new SceneObjectCulling();
        private static var tilePresentation:SceneTilePresentation=new SceneTilePresentation();
        private static var fogPresentation:SceneFogPresentation=new SceneFogPresentation();
        private static var rasterPresentation:SceneRasterPresentation=new SceneRasterPresentation();
        private static var rasterRowsPresentation:SceneRasterRowsPresentation=new SceneRasterRowsPresentation();
        private static var emptyTerrain:SceneEmptyTerrainProbe=new SceneEmptyTerrainProbe();
        private static var backgroundComposite:SceneBackgroundCompositeProbe=new SceneBackgroundCompositeProbe();
        private static var sleepingRoots:SceneSleepingRootPresentation=new SceneSleepingRootPresentation();
        private static var encounter:SceneEncounter;
        private static var denseMetrics:SceneDenseCombatMetrics=new SceneDenseCombatMetrics();
        private static var blitReuse:SceneBlitReuse=new SceneBlitReuse();
        private static var sleepingTimelines:SceneSleepingTimelineChecks=new SceneSleepingTimelineChecks();
        private static var implicitFreeze:SceneImplicitFreezeProbe=new SceneImplicitFreezeProbe();
        private static var mouseTreeOriginal:Object=null;
        private static var displayAttribution:*=new SceneDisplayAttribution();
        private static var playerShotFrames:int=0,driverCalls:int=0,driverMs:int=0;
        private static var playerWarmFrames:int=0,playerWarmShots:int=0;
        private static var playerWarmReady:Boolean=false,warmLastCount:int=-1,warmQuietFrames:int=0;
        private static var nativeRoomMoved:Boolean=false,nativeRoomWait:int=0;
        private static var nativeInputReady:Boolean=false,nativeDirection:int=1,nativeTurns:int=0,nativeRoundTrips:int=0;
        private static var nativeSawRight:Boolean=false,nativeGroundRun:int=0,nativeGroundMax:int=0;
        private static var nativeFloorY:Number,nativeInputPlayer:*,nativeInputRoute:Object;
        private static var compactOriginal:Object=null;
        private static var rcOffline:*;
        private static var bulletBlend:SceneBulletBlendProbe=new SceneBulletBlendProbe();
        private static var playerCache:ScenePlayerCacheProbe=new ScenePlayerCacheProbe();
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
            if(cfg.drawControl!="rcnative" || cfg.benchmark!="scene" || !cfg.nativeInputMotion || !cfg.nativeSprint ||
                !cfg.playerFire || !cfg.fixedEnemies || !cfg.combatRoute || !cfg.stableMotion || cfg.presentationCheck ||
                cfg.sleepingRootShort || cfg.satsCheck || !cfg.noLighting || !cfg.noWall || cfg.vision)
                throw new Error("Activity range requires exact native LMG fixture with visual mods off");
            report.activityRange={version:"activity-camera-range-1",diagnosticOnly:true,performanceEligible:false,
                order:[false,true,true,false],limits:"No real input or production gameplay qualification; all verification and switching costs retained."};
            if(cfg.sleepingRootShort) {
                if(cfg.drawControl!="sleepingroots" || !cfg.nativeInputMotion)
                    throw new Error("Short sleeping-root comparison requires native input and sleepingroots control");
                cases=[];
                for(var shortCase:int=0;shortCase<20;++shortCase)
                    cases.push("sleeping-root-"+((shortCase%4==1 || shortCase%4==2)?"b":"a")+"-"+shortCase);
            }
            if(cfg.drawControl=="rcoffline" || cfg.drawControl=="rcnative") {
                if(!cfg.nativeInputMotion || !cfg.playerFire || !cfg.fixedEnemies || !cfg.combatRoute || cfg.sleepingRootShort)
                    throw new Error("RC comparison requires the native-input combat fixture only");
                cases=[];
                for(var rcCase:int=0;rcCase<4;++rcCase)
                    cases.push(cfg.drawControl=="rcnative"?"dense-native-"+rcCase:"rc-offline-"+((rcCase%4==1 || rcCase%4==2)?"b":"a")+"-"+rcCase);
            }
            if(cfg.drawControl=="objectgroups")cases=["all-object-layers-a","hide-box-layers","hide-unit-layer","all-object-layers-a-repeat"];
            if(cfg.impactABBA)cases=["impact-original-a","impact-candidate-b","impact-candidate-b-repeat","impact-original-a-repeat"];
            main.stage.addEventListener(Event.ENTER_FRAME,function(e:Event):void {absoluteStart=getTimer();rasterPresentation.beginFrame();rasterRowsPresentation.beginFrame();if(cfg.drawControl=="emptyterrain")emptyTerrain.beginFrame();if(cfg.drawControl=="backgrounds")backgroundComposite.prepareFrame(w);},false,2147483647);
            main.stage.addEventListener(Event.ENTER_FRAME,function(e:Event):void {lastEnd=getTimer();completeProbeTimingTail(lastEnd);},false,-2147483647);
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
        private static function save(name:String,value:*):void {
            var timed:Boolean=probeTimingRow!=null,begin:int=getTimer();
            try {
                var f:FileStream=new FileStream();f.open(File.applicationStorageDirectory.resolvePath(name),FileMode.WRITE);f.writeUTFBytes(JSON.stringify(value,null,2));f.close();
            } finally {
                if(timed) {
                    var elapsed:int=getTimer()-begin;probeTimingSave+=elapsed;
                    if(name=="progress.json")probeTimingProgressSave+=elapsed;
                    if(name=="heartbeat.json")probeTimingHeartbeatSave+=elapsed;
                }
            }
        }
        private static function beginProbeTiming():void {
            if(phase!=4 || !row)return;
            // Retain this row across startCase(), which replaces the global row.
            probeTimingRow=row;probeTimingFrame=age;probeTimingSampleIndex=-1;
            probeTimingEntered=getTimer();probeTimingSampleAt=-1;
            probeTimingCensus=probeTimingSave=probeTimingProgressSave=probeTimingHeartbeatSave=probeTimingStartCase=0;
        }
        private static function closeProbeTiming(terminal:Boolean=false):void {
            if(probeTimingRow==null)return;
            var end:int=getTimer(),target:Object=probeTimingRow.probeTiming;
            var total:int=end-probeTimingEntered,slot:int=target.frame.length;
            target.frame.push(probeTimingFrame);target.frameIndex.push(probeTimingSampleIndex);
            target.totalMs.push(total);
            target.workMs.push(total-probeTimingCensus-probeTimingSave-probeTimingStartCase);
            target.preSampleMs.push(probeTimingSampleAt<0?null:probeTimingSampleAt-probeTimingEntered);
            target.postSampleMs.push(probeTimingSampleAt<0?null:end-probeTimingSampleAt);
            target.censusMs.push(probeTimingCensus);target.saveMs.push(probeTimingSave);
            target.progressSaveMs.push(probeTimingProgressSave);target.heartbeatSaveMs.push(probeTimingHeartbeatSave);
            target.startCaseMs.push(probeTimingStartCase);target.laterListenersMs.push(null);target.terminal.push(terminal);
            if(terminal && report.samples.indexOf(probeTimingRow)<0)
                report.probeTimingPartial={name:probeTimingRow.name,timing:target};
            probeTimingRow=null;probeTimingPending=target;probeTimingPendingIndex=slot;
            probeTimingExited=getTimer();target.bookkeepingMs.push(probeTimingExited-end);
        }
        private static function completeProbeTimingTail(end:int):void {
            if(probeTimingPending==null)return;
            // Same-frame attribution, including the last frame of each segment.
            probeTimingPending.laterListenersMs[probeTimingPendingIndex]=end-probeTimingExited;
            probeTimingPending=null;
        }
        private static function check(name:String,ok:Boolean,detail:*=null):void {report.assertions.push({name:name,ok:ok,detail:detail});}
        private static function finish(error:String=null):void {
            if(done)return;done=true;
            // exit() may end the process before tick's finally can serialize
            // this final sample. Cleanup and the final report save are excluded.
            closeProbeTiming(true);
            report.activityRangeCleanup=activityRangeProbe.clear();
            if(!report.activityRangeCleanup.cleared || report.activityRangeCleanup.errors.length!=0)
                error=(error?error+"\n":"")+"Activity range mode cleanup failed";
            if(error==null && report.samples.length==4 && w && w.grafon.sceneLarge) {
                try {
                    report.finalActivityCensus={startedAtMs:getTimer(),afterFinalSample:true};
                    report.finalActivityCensus.data=SceneActivityCensus.read(w);
                    report.finalActivityCensus.endedAtMs=getTimer();
                } catch(finalCensusError:*) {error="Final dense census failed: "+String(finalCensusError);}
            }
            if(rcOffline) {
                try {
                    report.rcOfflineCleanup={};
                    try {report.rcOfflineCleanup.before=rcOffline.snapshot();}
                    finally {rcOffline.setEnabled(false);report.rcOfflineCleanup.after=readRcOffline(false);}
                } catch(rcCleanup:*) {error=(error?error+"\n":"")+"RC offline cleanup: "+String(rcCleanup);}
            }
            var displayCleanup:Object=displayAttribution.clear();
            if(displayCleanup.started && !displayCleanup.restored)error=(error?error+"\n":"")+"Display attribution cleanup did not restore original layers";
            if(compactOriginal && w && w.grafon===compactOriginal.root)w.grafon.sceneCompactImpacts=compactOriginal.value;
            if(mouseTreeOriginal && w && w.visual===mouseTreeOriginal.root) {
                w.visual.mouseChildren=mouseTreeOriginal.children;w.visual.mouseEnabled=mouseTreeOriginal.enabled;
            }
            try {implicitFreeze.clear();}
            catch(cleanup:*) {error=(error?error+"\n":"")+"Implicit probe cleanup: "+String(cleanup);}
            try {objectCulling.clear();}
            catch(cullCleanup:*) {error=(error?error+"\n":"")+"Object culling cleanup: "+String(cullCleanup);}
            try {rasterRowsPresentation.clear();}
            catch(rowsCleanup:*) {error=(error?error+"\n":"")+"Raster rows cleanup: "+String(rowsCleanup);}
            if(cfg.drawControl=="emptyterrain") {
                try {emptyTerrain.clear();report.emptyTerrainCleanup=emptyTerrain.snapshot();}
                catch(emptyCleanup:*) {error=(error?error+"\n":"")+"Empty terrain cleanup: "+String(emptyCleanup);}
                if(!report.emptyTerrainCleanup || !report.emptyTerrainCleanup.valid || report.emptyTerrainCleanup.pendingRestore!=0)
                    error=(error?error+"\n":"")+"Empty terrain cleanup/conflict failure";
            }
            if(cfg.drawControl=="backgrounds") {
                try {backgroundComposite.clear();report.backgroundCompositeCleanup=backgroundComposite.snapshot();}
                catch(backgroundCleanup:*) {error=(error?error+"\n":"")+"Background composite cleanup: "+String(backgroundCleanup);}
                if(!report.backgroundCompositeCleanup || report.backgroundCompositeCleanup.errors!=0 ||
                    report.backgroundCompositeCleanup.conflicts!=0 || report.backgroundCompositeCleanup.heldParents!=0 ||
                    report.backgroundCompositeCleanup.liveCopies!=0 || report.backgroundCompositeCleanup.attachedCompositeBitmaps!=0)
                    error=(error?error+"\n":"")+"Background composite cleanup/conflict failure";
            }
            if(cfg.sleepingRootCheck || cfg.drawControl=="sleepingroots") {
                try {sleepingRoots.clear();report.sleepingRootCleanup=sleepingRoots.snapshot();}
                catch(rootCleanup:*) {error=(error?error+"\n":"")+"Sleeping root cleanup: "+String(rootCleanup);}
                if(!report.sleepingRootCleanup || !report.sleepingRootCleanup.valid || report.sleepingRootCleanup.pendingRestore!=0)
                    error=(error?error+"\n":"")+"Sleeping root cleanup/conflict failure";
            }
            if(cfg.drawControl=="bulletblend") {
                bulletBlend.clear();report.bulletBlendCleanup=bulletBlend.snapshot();
                if(!report.bulletBlendCleanup.valid || report.bulletBlendCleanup.pendingRestore!=0)
                    error=(error?error+"\n":"")+"Bullet blend cleanup/conflict failure";
            }
            if(cfg.drawControl=="playercache") {
                playerCache.clear();report.playerCacheCleanup=playerCache.snapshot();
                if(!report.playerCacheCleanup.valid || report.playerCacheCleanup.pendingRestore!=0)
                    error=(error?error+"\n":"")+"Player cache cleanup/conflict failure";
            }
            report.error=error;report.elapsedMs=getTimer()-started;report.ok=error==null;
            report.playerFire={enabled:Boolean(cfg.playerFire),shotFrames:playerShotFrames,weapon:w && w.gg && w.gg.currentWeapon?w.gg.currentWeapon.id:null};
            report.driver={stableMotion:Boolean(cfg.stableMotion),calls:driverCalls,ms:driverMs,perFrameMethod:cfg.stableMotion?"Unit.setPos (position/bounds/target only)":"UnitPlayer.setLocPos (resets weapon and filters)"};
            if(cfg.nativeInputMotion) {
                report.driver.nativeInputMotion=true;
                report.driver.perFrameMethod="Ctr.keyLeft/keyRight/keyRun; native acceleration, vertical physics and collision";
                report.driver.forcedPositionCalls=0;
            }
            for each(var a:Object in report.assertions)if(!a.ok)report.ok=false;
            save("result.json",report);NativeApplication.nativeApplication.exit(report.ok?0:1);
        }
        private static function settingsReady():Boolean {
            var c:*=main.getChildByName("ModSettingsCarrier");if(!c)return false;
            var found:int=0;for each(var p:Object in c["modAPI"].getPages())if(["continuousscene","wallblend","realisticvision","light-and-darkness"].indexOf(p.modId)>=0)++found;
            return found==4;
        }
        private static function setting(mod:String,key:String,value:*):void {
            if(continuousPreviousSampleAt>=0)throw new Error("Dense v2 forbids settings mutation after timing starts");
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
            var caseTimed:Boolean=probeTimingRow!=null,caseBegin:int=getTimer();
            try {
            if(continuousPreviousSampleAt<0) {
                continuousPreviousSampleAt=caseBegin;
                report.continuousSampling={version:"motion-continuous-wall-1",startedAtMs:caseBegin};
            }
            var rcSwitch:Object=null;
            if(cfg.drawControl=="rcoffline") {
                var rcEnabled:Boolean=index%4==1 || index%4==2;
                rcSwitch={enabled:rcEnabled,before:rcOffline.snapshot(),caseBeginAtMs:caseBegin,beginAt:getTimer(),windows:[]};
                rcOffline.setEnabled(rcEnabled);rcSwitch.after=readRcOffline(rcEnabled);
                rcSwitch.switchAfterAtMs=getTimer();rcSwitch.switchMs=rcSwitch.switchAfterAtMs-rcSwitch.beginAt;
            }
            if(cfg.drawControl=="compact") {
                if(compactOriginal==null)compactOriginal={root:w.grafon,value:w.grafon.sceneCompactImpacts};
                w.grafon.sceneCompactImpacts=index==0 || index==3;
            }
            if(cfg.drawControl=="mousetree") {
                if(mouseTreeOriginal==null)mouseTreeOriginal={root:w.visual,children:w.visual.mouseChildren,enabled:w.visual.mouseEnabled};
                if(w.visual!==mouseTreeOriginal.root)throw new Error("Mouse attribution root changed");
                w.visual.mouseChildren=index==1 || index==2 ? false : mouseTreeOriginal.children;
                w.visual.mouseEnabled=index==1 || index==2 ? false : mouseTreeOriginal.enabled;
            }
            if(cfg.drawControl=="unitblit") {
                blitReuse.reset(index==1 || index==2,Boolean(cfg.blitVerify));
                main.getChildByName("ContinuousSceneCarrier")["nativeAPI"].unitBlitGate=blitReuse.gate;
            }
            if(cfg.bulletSegments)main.getChildByName("ContinuousSceneCarrier")["nativeAPI"].bulletSegments={};
            if(cfg.worldProfile)main.getChildByName("ContinuousSceneCarrier")["nativeAPI"].worldStepProfile={};
            if(cfg.locationProfile)main.getChildByName("ContinuousSceneCarrier")["nativeAPI"].locationStepProfile={};
            if(cfg.guiWeaponProfile)main.getChildByName("ContinuousSceneCarrier")["nativeAPI"].guiWeaponProfile={};
            if(cfg.playerStepProfile)main.getChildByName("ContinuousSceneCarrier")["nativeAPI"].playerStepProfile={};
            if(cfg.playerAnimateProfile)main.getChildByName("ContinuousSceneCarrier")["nativeAPI"].playerAnimateProfile={};
            if(cfg.drawControl=="stationary") {
                var activityAPI:*=main.getChildByName("ContinuousSceneCarrier")["nativeAPI"];
                if(activityAPI.activityStats().version!="stationary-threats-1")throw new Error("Stationary threat candidate required");
                activityAPI.stationaryThreatsEnabled=index==1 || index==2;
            }
            if(cfg.drawControl=="nativecrop") {
                if(!("sceneCropPresentation" in w.grafon))throw new Error("Native crop host required");
                w.grafon.sceneCropPresentation=index==1 || index==2;
                w.grafon.sceneTick();
            }
            var timing:*=main.getChildByName("ContinuousSceneTdfcProfile");
            if(timing)timing.api.reset();
            if(cfg.fogABBA)main.getChildByName("ContinuousSceneCarrier")["nativeAPI"]["fogBoundsEnabled"]=index==1 || index==2;
            if(cfg.fogTypedABBA)main.getChildByName("ContinuousSceneCarrier")["nativeAPI"]["fogTypedEnabled"]=index==1 || index==2;
            // Dense v2: phase1 settings remain unchanged through all windows.
            row={name:cases[index],frames:[],nativeBand:[],wallBand:[],sceneBand:[],preBand:[],tailBand:[],afterProbeBand:[],totalScript:[],warm:[],draw:[],empty:0,missStart:w.grafon.sceneMisses,residentStart:w.grafon.sceneResident,camera:[],activity:[]};
            row.sampleAtMs=[];row.continuousFramesMs=[];row.caseBeginAtMs=caseBegin;
            row.activityRangeSwitch=activityRangeProbe.select(w,index);
            row.activityRange=[];
            if(rcSwitch)row.rcOffline=rcSwitch;
            row.probeTiming={version:"probe-self-time-1",diagnosticOnly:true,frame:[],frameIndex:[],totalMs:[],workMs:[],preSampleMs:[],postSampleMs:[],censusMs:[],saveMs:[],progressSaveMs:[],heartbeatSaveMs:[],startCaseMs:[],laterListenersMs:[],bookkeepingMs:[],terminal:[]};
            if(cfg.activityTelemetry)row.activityStart=main.getChildByName("ContinuousSceneCarrier")["nativeAPI"].activityStats();
            row.renderBand=[];row.exitBand=[];row.renderEvents=[];row.exitEvents=[];
            if(cfg.drawControl=="implicitpause")row.implicitHeld=[];
            if(cfg.drawControl=="mousetree")row.mouseTree={children:w.visual.mouseChildren,enabled:w.visual.mouseEnabled,stageX:main.stage.mouseX,stageY:main.stage.mouseY};
            row.playerShotStart=playerShotFrames;
            row.enemyShotStart=encounter?encounter.actualShotFrames:0;
            row.combatWindows=[];row.denseFrames=denseMetrics.bucket();
            if(cfg.nativeInputMotion) {
                row.nativeInputMotion=newNativeMotionBucket();
                row.nativeInputMotion.movementRequested=nativeCaseMoving();
                w.ctr.clearAll();driveNativeInput(nativeCaseMoving());drivePlayerFire();
                row.nativeInputMotion.inputAtStart=nativeMotionState();
            }
            if(cfg.drawControl=="compact")row.compactImpacts=w.grafon.sceneCompactImpacts;
            if(cfg.impactABBA) {
                if(!("sceneImpactArtEnabled" in w.grafon))throw new Error("Impact ABBA needs native impact host");
                w.grafon.sceneImpactArtEnabled=index==1 || index==2;
                row.impactEnabled=w.grafon.sceneImpactArtEnabled;
            }
            renderMs=exitMs=renderCalls=exitCalls=0;
            // RC switching occurs before its later ENTER_FRAME collectors. The
            // next frame's wall time includes this complete startCase call.
            age=0;last=cfg.drawControl=="rcoffline"?caseBegin:getTimer();phase=4;
            // rcnative changes no runtime behavior or RC API state. Include
            // its bookkeeping boundary just as in the diagnostic RC arm.
            if(cfg.drawControl=="rcnative")last=caseBegin;
            if("sceneMotionProfile" in w.grafon)w.grafon.sceneMotionProfile={};
            if("csMotionNative" in loc)loc.csMotionNative={};
            if("sceneWarmSlices" in w.grafon){row.slicesStart=w.grafon.sceneWarmSlices;row.forcedStart=w.grafon.sceneWarmForced;}
            } finally {if(caseTimed)probeTimingStartCase+=getTimer()-caseBegin;}
        }
        private static function tick(e:Event):void {
            if(done)return;
            beginProbeTiming();
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
                    if(cfg.chunkSide==640)w.grafon.sceneChunkSide=640;
                    if("sceneAsyncWarm" in w.grafon)w.grafon.sceneAsyncWarm=!cfg.syncWarm;
                    if(cfg.rasterCheck && "sceneWarmVerify" in w.grafon)w.grafon.sceneWarmVerify=true;
                    w.game.lands[cfg.land?cfg.land:"random_mane"].landStage=(cfg.stage?int(cfg.stage):1)-1;
                    getDefinitionByName("fe.loc.Land")["rconnectSeedSource"]=function():uint{return 20261019;};
                    entryAt=getTimer();w.game.beginMission(cfg.land?cfg.land:"random_mane");phase=2;
                }else if(phase==2 && w.land && w.land.act.id==(cfg.land?cfg.land:"random_mane") && w.t_exit==0 && w.allStat==1) {
                    if(cfg.nativeRoomX>=0 || cfg.nativeRoomY>=0) {
                        if(cfg.benchmark!="normal" || cfg.nativeRoomX<0 || cfg.nativeRoomY<0 ||
                            cfg.nativeRouteX<0 || cfg.nativeRouteY<0 || w.grafon.sceneLarge)
                            throw new Error("Native room baseline requires a freshly unmerged map and explicit local route");
                        if(!nativeRoomMoved) {
                            w.land.gotoXY(int(cfg.nativeRoomX),int(cfg.nativeRoomY));
                            nativeRoomMoved=true;return;
                        }
                        if(++nativeRoomWait<20)return;
                        if(w.land.locX!=cfg.nativeRoomX || w.land.locY!=cfg.nativeRoomY || w.loc!==w.land.loc)
                            throw new Error("Native room target was clamped or did not activate");
                        report.nativeRoom={x:w.land.locX,y:w.land.locY,z:w.land.locZ,
                            routeX:cfg.nativeRouteX,routeY:cfg.nativeRouteY,settleFrames:nativeRoomWait,
                            limitation:"Native room camera bounds differ from the continuous map; not a pure scheduler cost comparison"};
                    }
                    loc=w.loc;report.entryMs=getTimer()-entryAt;report.world={width:loc.spaceX,height:loc.spaceY,units:loc.units.length,black:loc.black,retDark:loc.retDark,lDist1:loc.lDist1,lDist2:loc.lDist2};
                    if(cfg.drawControl=="rcoffline") {
                        var rcCarrier:*=main.getChildByName("RConnectOfflineProbeCarrier");
                        if(!rcCarrier)throw new Error("RC offline diagnostic carrier missing");
                        rcOffline=rcCarrier["rcOfflineProbeAPI"];
                        if(!rcOffline || !(rcOffline.setEnabled is Function) || !(rcOffline.snapshot is Function))
                            throw new Error("RC offline diagnostic API missing");
                        report.rcOfflineInitial=readRcOffline(false);
                        rcOffline.setEnabled(false);
                    }
                    check("actual-expected-native-map",cfg.benchmark=="normal"?(!w.grafon.sceneLarge && loc.spaceX==48):(w.grafon.sceneLarge && loc.spaceX>48));
                    if(w.grafon.sceneLarge) {
                        var initialSurfaces:Array=w.grafon.sceneSurfaces();
                        report.chunkGeometry={requested:cfg.chunkSide,property:w.grafon.sceneChunkSide,
                            actualSide:initialSurfaces.length?initialSurfaces[0].side:0,surfaces:initialSurfaces.length};
                        check("actual-requested-chunk-side",initialSurfaces.length>0 &&
                            initialSurfaces[0].side==(cfg.chunkSide==640?640:320),report.chunkGeometry);
                    }
                    if(cfg.benchmark)path=1200;
                    x0=Math.max(200,Math.min(loc.limX-path-200,w.gg.X));y0=w.gg.Y;
                    // Compare the same local route within the entry room. A
                    // merged room uses global coordinates; native uses local.
                    x0=int(w.gg.X/1920)*1920+200;
                    y0=int(w.gg.Y/1000)*1000+800;
                    if(nativeRoomMoved){x0=Number(cfg.nativeRouteX);y0=Number(cfg.nativeRouteY);}
                    if(!cfg.nativeInputMotion){w.gg.setLocPos(x0,y0);w.gg.dx=w.gg.dy=0;w.cam.calc(w.gg);}
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
                    if(cfg.combatRoute) {
                        if(!cfg.fixedEnemies || !cfg.stableMotion || !cfg.playerFire)throw new Error("Combat route requires fixed armed actors, stable movement and player fire");
                        report.combatRoute=SceneCombatRoute.select(w,x0,y0,int(cfg.combatRouteLength));
                        x0=report.combatRoute.x;y0=report.combatRoute.y;path=report.combatRoute.path;
                        if(cfg.nativeInputMotion)prepareNativeInputRoute();else cfg.speed=path/50;
                        report.path={startX:x0,endX:x0+path,y:y0,speed:cfg.nativeInputMotion?null:cfg.speed};
                        if(!cfg.nativeInputMotion){w.gg.setPos(x0,y0);w.cam.calc(w.gg);}
                        var combatRoomX:int=int(x0/1920)*48,combatRoomY:int=int(y0/1000)*25,combatLayout:uint=0;
                        for(var combatX:int=0;combatX<48;++combatX)for(var combatY:int=0;combatY<25;++combatY) {
                            var combatTile:*=loc.space[combatRoomX+combatX][combatRoomY+combatY];
                            var combatCell:String=[combatTile.front,combatTile.back,combatTile.phis,combatTile.diagon,combatTile.zForm,combatTile.door].join(":");
                            for(var combatC:int=0;combatC<combatCell.length;++combatC)combatLayout=uint(combatLayout*31+combatCell.charCodeAt(combatC));
                        }
                        report.selectedCombatRoomTiles=combatLayout;
                        report.selectedCombatRoom={x:combatRoomX/48,y:combatRoomY/25,
                            localX:x0-combatRoomX*40,localY:y0-combatRoomY*40,
                            timing:"Before actors and weapon warmup; boundary openings can differ between modes"};
                        var corridorBounds:Object=report.combatRoute.corridor,corridorHash:uint=0,corridorCells:int=0;
                        for(combatX=int(corridorBounds.left/40);combatX<Math.ceil(corridorBounds.right/40);++combatX)
                            for(combatY=int(corridorBounds.top/40);combatY<=int(corridorBounds.floor/40);++combatY) {
                                combatTile=loc.space[combatX][combatY];
                                combatCell=[combatTile.front,combatTile.back,combatTile.phis,combatTile.diagon,combatTile.zForm,combatTile.door].join(":");
                                for(combatC=0;combatC<combatCell.length;++combatC)corridorHash=uint(corridorHash*31+combatCell.charCodeAt(combatC));
                                ++corridorCells;
                            }
                        report.selectedCombatCorridorTiles={hash:corridorHash,cells:corridorCells};
                    }
                    if(cfg.drawControl=="stationary") {
                        var initialActivityAPI:*=main.getChildByName("ContinuousSceneCarrier")["nativeAPI"];
                        if(initialActivityAPI.activityStats().version!="stationary-threats-1")throw new Error("Stationary threat candidate required before warmup");
                        initialActivityAPI.stationaryThreatsEnabled=false;
                    }
                    if(cfg.encounter){encounter=new SceneEncounter(w);report.encounter=encounter.prepare(x0,y0,Boolean(cfg.fixedEnemies),Boolean(cfg.localEnemies),Boolean(cfg.playerFire),report.combatRoute);y0=report.encounter.playerY;report.path.y=y0;check("encounter-has-native-armed-enemies",report.encounter.units.length>=(cfg.fixedEnemies?6:3),report.encounter);}
                    if(cfg.nativeInputMotion) {
                        if(!nativeInputRoute)throw new Error("Native input requires a verified combat route");
                        // The only positioning operation in this mode. All subsequent
                        // movement, including the first landing, belongs to native physics.
                        w.gg.setLocPos(x0,y0);w.gg.dx=w.gg.dy=0;w.cam.calc(w.gg);
                        nativeInputPlayer=w.gg;
                        denseMetrics.bind(w,encounter.actorUnits());
                        report.denseFixture={version:"dense-sprint-2",actors:6,enemyWeapon:"lmg",playerWeapon:"assr",jumpInput:false,staminaRefilled:false,positioning:"one spawn only",sampling:"read-only per-frame object scan; cost retained",limitations:"Six durable HP100000 actors with damage2; player ammo/durability refill and godMode inherited; native firing cadence, reload, physics and AI retained"};
                        report.observerPolicy={version:"dense-observer-lean-2",settingsDuringTiming:false,segmentProgressWrites:false,segmentCensus:false,finalCensus:true,heartbeatIntervalMs:5000,continuousFramesRetained:true};
                        report.nativeInputMotion.spawn={calls:1,x:x0,y:y0};
                    }
                    if(cfg.playerFire) {
                        if(!cfg.stableMotion)throw new Error("Player fire fixture requires movement without setNull");
                        var fixtureGun:*=w.invent.addWeapon("assr");fixtureGun.lvl=0;fixtureGun.perslvl=0;
                        w.gg.changeWeapon("assr");
                        report.playerFireFixture="Native assault rifle; requirements waived, ammo/durability refilled; native cadence/projectiles/damage retained";
                    }
                    age=0;phase=3;
                }else if(phase==3) {
                    if(cfg.nativeInputMotion) {
                        var warmMotion:Object=recordNativeMotion(report.nativeInputMotion.warmup,30);
                        nativeGroundRun=warmMotion.floorContact?nativeGroundRun+1:0;
                        nativeGroundMax=Math.max(nativeGroundMax,nativeGroundRun);
                        if(nativeGroundRun>=10)nativeInputReady=true;
                    }
                    w.ctr.clearAll();
                    if(cfg.drawControl=="backgrounds") {
                        if(!cfg.presentationCheck || !cfg.nativeInputMotion || !cfg.noLighting || !cfg.noWall || cfg.vision)
                            throw new Error("Background composite supports only early native-input pixels with presentation mods disabled");
                        if(w.loc!==loc || w.allStat!=1 || w.onPause || w.t_exit!=0)
                            throw new Error("Background composite check lost active native simulation");
                        if(nativeGroundRun>=10 && w.grafon.sceneViewReady()) {
                            report.backgroundCompositeEarlyCheck={version:"background-composite-early-check-1",diagnosticOnly:true,
                                groundContactRun:nativeGroundRun,startPose:warmMotion,requiredHoldFrames:10,
                                nativeHeldFrames:0,holdSamples:[]};
                            backgroundComposite.update(w,true);
                            report.backgroundCompositeEarlyCheck.startSnapshot=backgroundComposite.snapshot();
                            phase=88;age=0;return;
                        }
                        if(++age>240)throw new Error("Background composite check did not reach a real floor contact");
                        return;
                    }
                    if(cfg.sleepingRootEarlyCheck) {
                        if(!cfg.sleepingRootCheck || !cfg.nativeInputMotion)
                            throw new Error("Early sleeping-root check requires native input and terminal verification");
                        if(w.loc!==loc || w.allStat!=1 || w.onPause || w.t_exit!=0)
                            throw new Error("Early sleeping-root check lost active native simulation");
                        if(nativeGroundRun>=10 && w.grafon.sceneViewReady()) {
                            report.sleepingRootEarlyCheck={version:"sleeping-root-early-check-1",diagnosticOnly:true,
                                groundContactRun:nativeGroundRun,startPose:warmMotion,requiredHoldFrames:10,
                                nativeHeldFrames:0,holdSamples:[]};
                            sleepingRoots.update(w,true);phase=89;age=0;return;
                        }
                        if(++age>240)throw new Error("Early sleeping-root check did not reach a real floor contact");
                        return;
                    }
                    if(++age<20){if(cfg.nativeInputMotion)driveNativeInput(false);return;}
                    if(cfg.playerFire && !playerWarmReady) {
                        var warmGun:*=w.gg.currentWeapon;
                        if(!warmGun || warmGun.id!="assr" || w.gg.t_work>0) {
                            if(age>240)throw new Error("Player weapon did not finish switching before warm-up");
                            return;
                        }
                        if(samplePlayerFire())++playerWarmShots;
                        if(encounter)encounter.sample();
                        ++playerWarmFrames;
                        if(cfg.nativeInputMotion)driveNativeInput(nativeInputReady);
                        else {
                            var fireWarmTravel:Number=playerWarmFrames*cfg.speed;
                            var fireWarmDistance:Number=fireWarmTravel%(path*2);
                            if(fireWarmDistance>path)fireWarmDistance=path*2-fireWarmDistance;
                            movePlayer(x0+fireWarmDistance,y0);
                            w.gg.dx=int(fireWarmTravel/path)%2==0?cfg.speed:-cfg.speed;w.gg.dy=0;
                        }
                        drivePlayerFire();
                        if(warmLastCount!=w.grafon.sceneWarmCount){warmLastCount=w.grafon.sceneWarmCount;warmQuietFrames=0;}
                        else ++warmQuietFrames;
                        if(playerWarmFrames>1200)throw new Error("Scene prewarming did not settle before combat timing");
                        if(cfg.nativeInputMotion) {
                            report.nativeInputMotion.warmup.roundTrips=nativeRoundTrips;
                            report.nativeInputMotion.warmup.turns=nativeTurns;
                            report.nativeInputMotion.warmup.groundContactRun=nativeGroundMax;
                            if(playerWarmFrames<100 || !nativeInputReady || nativeRoundTrips<1 ||
                                !warmMotion.floorContact || warmQuietFrames<100)return;
                            report.nativeInputMotion.warmup.ready=true;
                            report.nativeInputMotion.timingStart=warmMotion;
                        } else if(playerWarmFrames<100 || cfg.combatRoute && (warmQuietFrames<100 || playerWarmFrames%100!=0))return;
                        if(playerWarmShots<5)throw new Error("Insufficient actual player shots during warm-up");
                        report.playerFireWarmup={frames:playerWarmFrames,quietWarmFrames:warmQuietFrames,warmCount:warmLastCount,shotFrames:playerWarmShots,encounter:encounter?encounter.snapshot():null};
                        playerWarmReady=true;
                        playerShotFrames=0;
                    }
                    if(cfg.drawControl=="playercache" && !cfg.presentationCheck) {
                        if(!cfg.stableMotion || !cfg.combatRoute)throw new Error("Player cache comparison requires stable shared combat route");
                        report.playerCache={order:[false,true,true,false,true,false,false,true],windowFrames:100,frames:[],windows:[],empty:0,missStart:w.grafon.sceneMisses,warmStart:w.grafon.sceneWarmCount};
                        playerCache.update(w,false);
                        age=0;last=getTimer();phase=96;return;
                    }
                    if(cfg.drawControl=="bulletblend") {
                        if(!cfg.stableMotion || !cfg.combatRoute)throw new Error("Bullet blend comparison requires stable shared combat route");
                        report.bulletBlend={order:[false,true,true,false,true,false,false,true],windowFrames:100,frames:[],windows:[],empty:0,missStart:w.grafon.sceneMisses,warmStart:w.grafon.sceneWarmCount};
                        bulletBlend.update(w,false);
                        age=0;last=getTimer();phase=95;return;
                    }
                    if(cfg.drawControl=="compactshort") {
                        if(!cfg.stableMotion)throw new Error("Compact comparison requires stable motion driver");
                        compactOriginal={root:w.grafon,value:w.grafon.sceneCompactImpacts};
                        report.compactShort={order:[true,false,false,true,false,true,true,false],windowFrames:100,frames:[],empty:0,missStart:w.grafon.sceneMisses};
                        w.grafon.sceneCompactImpacts=true;
                        age=0;last=getTimer();phase=94;return;
                    }
                    if(cfg.drawControl=="shortlayers" || cfg.drawControl=="worldlayers") {
                        if(!cfg.stableMotion)throw new Error("Short attribution requires stable motion driver");
                        if(cfg.drawControl=="worldlayers")displayAttribution=new SceneWorldLayerAttribution();
                        report.displayStart=displayAttribution.start(w);
                        report.displayFrames=[];report.displayEmpty=0;
                        report.displayMissStart=w.grafon.sceneMisses;
                        report.displayView={width:main.stage.stageWidth,height:main.stage.stageHeight,quality:main.stage.quality,filters:w.visual.filters.length,cached:w.visual.cacheAsBitmap};
                        age=0;last=getTimer();phase=93;return;
                    }
                    if(cfg.drawControl=="sleepclips" || cfg.drawControl=="implicitpause") {
                        sleepingTimelines.begin(w);phase=92;return;
                    }
                    // Prepare the same route before an in-process ABBA timing.
                    if(!cfg.nativeInputMotion && (cfg.fogABBA || cfg.fogTypedABBA) && age<620) {
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
                        if(cfg.drawControl=="playercache") {
                            report.presentation=playerCache.verify(w);
                            check("player-cache-same-frame-pixels",report.presentation.valid && report.presentation.equal,report.presentation);
                            finish();return;
                        }
                        if(cfg.drawControl=="stationary") {
                            w.swfStage.removeEventListener(Event.DEACTIVATE,w.onDeactivate);
                            main.getChildByName("ContinuousSceneCarrier")["nativeAPI"].stationaryThreatsEnabled=true;
                            report.stationaryThreats=SceneStoppedThreatChecks.run(main,w,check);finish();return;
                        }
                        if(cfg.drawControl=="nativecrop") {
                            report.presentation=SceneNativeCropChecks.run(w,check);
                            report.sats={od:report.presentation.od};w.ctr.keySats=true;phase=90;return;
                        }
                        if(cfg.drawControl=="atlas") {
                            report.presentation=SceneAtlasChecks.run(w,rasterPresentation,check);
                            report.sats={od:report.presentation.od};w.ctr.keySats=true;phase=90;return;
                        }
                        var presenter:*=cfg.drawControl=="objectviewport"?objectCulling:cfg.drawControl=="atlas"?rasterPresentation:cfg.drawControl=="fogpixels"?fogPresentation:tilePresentation;
                        report.presentation=ScenePresentationChecks.run(w,presenter,check,cfg.drawControl!="atlas" && cfg.drawControl!="fogpixels" && cfg.drawControl!="objectviewport");finish();return;
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
                }else if(phase==96) {
                    if(w.allStat!=1 || w.onPause || w.t_exit!=0 || w.loc!==loc)
                        throw new Error("Player cache timing lost active original location");
                    var cacheNow:int=getTimer(),cacheIndex:int=int(age/100);
                    var cacheFrame:Object={frame:age,window:cacheIndex,enabled:report.playerCache.order[cacheIndex],transition:age%100==0,dt:cacheNow-last,native:band50-startFrame,scriptBeforeProbe:cacheNow-absoluteStart,warmCount:w.grafon.sceneWarmCount};
                    last=cacheNow;report.playerCache.frames.push(cacheFrame);
                    if(!w.grafon.sceneViewReady())++report.playerCache.empty;
                    sampleCombat(cacheFrame,age%100==0 || age%100==99);
                    if(age%100==99)report.playerCache.windows.push(playerCache.snapshot());
                    w.ctr.clearAll();++age;
                    if(age==800) {
                        report.playerCache.misses=w.grafon.sceneMisses-report.playerCache.missStart;
                        report.playerCache.warmed=w.grafon.sceneWarmCount-report.playerCache.warmStart;
                        check("player-cache-complete",report.playerCache.frames.length==800);
                        check("player-cache-complete-view",report.playerCache.empty==0 && report.playerCache.misses==0);
                        check("player-cache-valid",playerCache.snapshot().valid,playerCache.snapshot());
                        check("player-cache-applied",playerCache.snapshot().changed>0,playerCache.snapshot().changed);
                        if(cfg.playerFire)check("player-cache-player-fired",playerShotFrames>30,playerShotFrames);
                        finish();return;
                    }
                    var cacheUpdate:int=getTimer();
                    playerCache.update(w,report.playerCache.order[int(age/100)]);
                    cacheFrame.probeMs=getTimer()-cacheUpdate;
                    var cacheTravel:Number=age*cfg.speed;
                    var cacheDistance:Number=cacheTravel%(path*2);if(cacheDistance>path)cacheDistance=path*2-cacheDistance;
                    if(cfg.nativeInputMotion)driveNativeInput(true);
                    else {movePlayer(x0+cacheDistance,y0);w.gg.dx=int(cacheTravel/path)%2==0?cfg.speed:-cfg.speed;w.gg.dy=0;}
                    drivePlayerFire();
                }else if(phase==95) {
                    if(w.allStat!=1 || w.onPause || w.t_exit!=0 || w.loc!==loc)
                        throw new Error("Bullet blend timing lost active original location");
                    var blendNow:int=getTimer(),blendIndex:int=int(age/100);
                    var blendFrame:Object={frame:age,window:blendIndex,enabled:report.bulletBlend.order[blendIndex],transition:age%100==0,dt:blendNow-last,native:band50-startFrame,scriptBeforeProbe:blendNow-absoluteStart,warmCount:w.grafon.sceneWarmCount};
                    last=blendNow;report.bulletBlend.frames.push(blendFrame);
                    if(!w.grafon.sceneViewReady())++report.bulletBlend.empty;
                    sampleCombat(blendFrame,age%100==0 || age%100==99);
                    if(age%100==99)report.bulletBlend.windows.push(bulletBlend.snapshot());
                    w.ctr.clearAll();++age;
                    if(age==800) {
                        report.bulletBlend.misses=w.grafon.sceneMisses-report.bulletBlend.missStart;
                        report.bulletBlend.warmed=w.grafon.sceneWarmCount-report.bulletBlend.warmStart;
                        check("bullet-blend-complete",report.bulletBlend.frames.length==800);
                        check("bullet-blend-complete-view",report.bulletBlend.empty==0 && report.bulletBlend.misses==0);
                        check("bullet-blend-valid",bulletBlend.snapshot().valid,bulletBlend.snapshot());
                        check("bullet-blend-applied",bulletBlend.snapshot().changed>0,bulletBlend.snapshot().changed);
                        if(cfg.playerFire)check("bullet-blend-player-fired",playerShotFrames>30,playerShotFrames);
                        finish();return;
                    }
                    var blendUpdate:int=getTimer();
                    bulletBlend.update(w,report.bulletBlend.order[int(age/100)]);
                    blendFrame.probeMs=getTimer()-blendUpdate;
                    var blendTravel:Number=age*cfg.speed;
                    var blendDistance:Number=blendTravel%(path*2);if(blendDistance>path)blendDistance=path*2-blendDistance;
                    if(cfg.nativeInputMotion)driveNativeInput(true);
                    else {movePlayer(x0+blendDistance,y0);w.gg.dx=int(blendTravel/path)%2==0?cfg.speed:-cfg.speed;w.gg.dy=0;}
                    drivePlayerFire();
                }else if(phase==94) {
                    if(w.allStat!=1 || w.onPause || w.t_exit!=0 || w.loc!==loc)
                        throw new Error("Compact timing lost active original location");
                    var compactNow:int=getTimer();
                    var compactIndex:int=int(age/100);
                    if(w.grafon.sceneCompactImpacts!==report.compactShort.order[compactIndex])throw new Error("Compact mode changed externally");
                    var compactFrame:Object={frame:age,window:compactIndex,compact:w.grafon.sceneCompactImpacts,transition:age%100==0,dt:compactNow-last,native:band50-startFrame,scriptBeforeProbe:compactNow-absoluteStart,playerShot:cfg.playerFire && w.gg.currentWeapon.hold<w.gg.currentWeapon.holder};
                    last=compactNow;report.compactShort.frames.push(compactFrame);
                    if(!w.grafon.sceneViewReady())++report.compactShort.empty;
                    sampleCombat(compactFrame,age%100==0 || age%100==99);
                    w.ctr.clearAll();++age;
                    if(age==800) {
                        report.compactShort.misses=w.grafon.sceneMisses-report.compactShort.missStart;
                        report.encounterEnd=encounter?encounter.snapshot():null;
                        check("compact-short-complete",report.compactShort.frames.length==800);
                        check("compact-short-complete-view",report.compactShort.empty==0 && report.compactShort.misses==0);
                        if(cfg.playerFire)check("compact-short-player-fired",playerShotFrames>30,playerShotFrames);
                        if(encounter)check("compact-short-enemies-fired",encounter.shots>30,encounter.shots);
                        finish();return;
                    }
                    if(age%100==0)w.grafon.sceneCompactImpacts=report.compactShort.order[int(age/100)];
                    var compactTravel:Number=age*cfg.speed;
                    var compactDistance:Number=compactTravel%(path*2);if(compactDistance>path)compactDistance=path*2-compactDistance;
                    if(cfg.nativeInputMotion)driveNativeInput(true);
                    else {movePlayer(x0+compactDistance,y0);w.gg.dx=int(compactTravel/path)%2==0?cfg.speed:-cfg.speed;w.gg.dy=0;}
                    drivePlayerFire();
                }else if(phase==93) {
                    if(w.allStat!=1 || w.onPause || w.t_exit!=0 || w.loc!==loc)
                        throw new Error("Short display timing lost active original location");
                    var displayNow:int=getTimer();
                    var displayRow:Object=displayAttribution.sample(w,displayNow-last,band50-startFrame);last=displayNow;
                    displayRow.currentScriptBeforeProbe=displayNow-absoluteStart;
                    report.displayFrames.push(displayRow);
                    if(displayRow.aborted)throw new Error("Short display attribution aborted: "+JSON.stringify(displayRow));
                    if(!w.grafon.sceneViewReady())++report.displayEmpty;
                    sampleCombat(displayRow,age%30==0 || age%30==29);
                    if(displayAttribution.done) {
                        report.displaySummary=displayAttribution.snapshot();
                        report.displayMisses=w.grafon.sceneMisses-report.displayMissStart;
                        report.encounterEnd=encounter?encounter.snapshot():null;
                        report.activityCensus=SceneActivityCensus.read(w);
                        report.unitLayerCensus=SceneUnitLayerCensus.read(w);
                        check("short-display-complete",report.displaySummary.complete && report.displaySummary.sampledFrames==1500,report.displaySummary);
                        check("short-display-restored",report.displaySummary.cleanup.restored);
                        check("short-display-no-missing-view",report.displayEmpty==0 && report.displayMisses==0);
                        if(cfg.playerFire)check("real-player-fired-without-reset",playerShotFrames>30,playerShotFrames);
                        finish();return;
                    }
                    w.ctr.clearAll();++age;
                    var displayTravel:Number=age*(cfg.speed>0?cfg.speed:24);
                    var displayDistance:Number=displayTravel%(path*2);if(displayDistance>path)displayDistance=path*2-displayDistance;
                    if(cfg.nativeInputMotion)driveNativeInput(true);
                    else {movePlayer(x0+displayDistance,y0);w.gg.dx=int(displayTravel/path)%2==0?cfg.speed:-cfg.speed;w.gg.dy=0;}
                    drivePlayerFire();
                }else if(phase==92) {
                    w.ctr.clearAll();
                    check("timeline-simulation-active-"+age,w.loc===loc && w.allStat==1 && !w.onPause && w.t_exit==0);
                    ++age;
                    if(sleepingTimelines.sample(w)) {
                        report.sleepingTimelines=sleepingTimelines.report();
                        check("timeline-completed-eight-frames",report.sleepingTimelines.complete);
                        check("timeline-has-stable-sleeping-units",report.sleepingTimelines.stableSleepingOwners>0);
                        if(cfg.drawControl=="implicitpause") {
                            var implicitCandidates:Array=sleepingTimelines.observedCandidates();
                            check("timeline-found-implicit-candidates",implicitCandidates.length>0,implicitCandidates.length);
                            implicitFreeze.seed(implicitCandidates);
                            report.lastWarm=w.grafon.sceneWarmCount;report.lastDraw=w.grafon.sceneDrawMs;startCase();return;
                        }
                        finish();return;
                    }
                }else if(phase==90) {
                    check("sats-v-opens-native-ui",w.sats.active && w.sats.vis.visible && w.grafon.visSats.visible && w.allStat==2);
                    check("sats-opening-does-not-charge-ap",w.sats.od==report.sats.od);
                    if(cfg.presentationCheck && cfg.drawControl=="atlas")report.presentation.satsOpened=SceneAtlasChecks.onSatsOpened(w,rasterPresentation,check);
                    w.ctr.keySats=true;phase=91;return;
                }else if(phase==91) {
                    check("sats-v-closes-and-resumes",!w.sats.active && !w.grafon.visSats.visible && w.grafon.visObjs[2].visible && w.allStat==1);
                    check("sats-close-does-not-charge-ap",w.sats.od==report.sats.od);
                    if(cfg.presentationCheck && cfg.drawControl=="atlas") {
                        report.presentation.satsClosed=SceneAtlasChecks.onSatsClosed(w,rasterPresentation,check);
                        rasterPresentation.clear();
                    }
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
                }else if(phase==88) {
                    w.ctr.clearAll();
                    if(w.loc!==loc || w.allStat!=1 || w.onPause || w.t_exit!=0)
                        throw new Error("Background composite hold lost active native simulation");
                    backgroundComposite.update(w,true);++age;
                    report.backgroundCompositeEarlyCheck.nativeHeldFrames=age;
                    report.backgroundCompositeEarlyCheck.holdSamples.push({frame:age,pose:nativeMotionState(),snapshot:backgroundComposite.snapshot()});
                    if(age<report.backgroundCompositeEarlyCheck.requiredHoldFrames)return;
                    check("background-composite-unit-scale",w.cam.scaleV==1 && w.visual.scaleX==1 && w.visual.scaleY==1,
                        {camera:w.cam.scaleV,worldX:w.visual.scaleX,worldY:w.visual.scaleY});
                    report.backgroundCompositeVerification=backgroundComposite.verify(w);
                    check("background-composite-applied",report.backgroundCompositeVerification.applied,report.backgroundCompositeVerification);
                    check("background-composite-same-frame-pixels",report.backgroundCompositeVerification.equal,report.backgroundCompositeVerification);
                    check("background-composite-restored",report.backgroundCompositeVerification.restored && report.backgroundCompositeVerification.bindingsRestored,
                        report.backgroundCompositeVerification);
                    finish();return;
                }else if(phase==89) {
                    if(cfg.sleepingRootEarlyCheck) {
                        w.ctr.clearAll();
                        if(w.loc!==loc || w.allStat!=1 || w.onPause || w.t_exit!=0)
                            throw new Error("Early sleeping-root hold lost active native simulation");
                        ++age;
                        report.sleepingRootEarlyCheck.nativeHeldFrames=age;
                        report.sleepingRootEarlyCheck.holdSamples.push({frame:age,snapshot:sleepingRoots.snapshot()});
                        if(age<report.sleepingRootEarlyCheck.requiredHoldFrames)return;
                    } else
                    if(++age<2)return;
                    report.sleepingRootVerification=sleepingRoots.verify(w);
                    check("sleeping-root-verification",report.sleepingRootVerification.passed,report.sleepingRootVerification);
                    finish();return;
                }else if(phase==4) {
                    if(w.allStat!=1 || w.onPause || w.t_exit!=0)
                        throw new Error("Timing invalid: native simulation paused/menu/travel state "+w.allStat);
                    if(nativeRoomMoved && (w.loc!==loc || w.land.locX!=cfg.nativeRoomX || w.land.locY!=cfg.nativeRoomY))
                        throw new Error("Native combat baseline changed rooms during timing");
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
                    if(cfg.drawControl && cfg.drawControl!="rcnative"){
                        var controlIndex:int=cfg.sleepingRootShort?index%4:index;
                        var altered:Boolean=controlIndex==1 || controlIndex==2;
                        if(cfg.drawControl=="tilecrop")tilePresentation.update(w,altered);
                        if(cfg.drawControl=="fogpixels")fogPresentation.update(w,altered);
                        if(cfg.drawControl=="atlas")rasterPresentation.update(w,altered);
                        if(cfg.drawControl=="atlasrows")rasterRowsPresentation.update(w,altered);
                        if(cfg.drawControl=="emptyterrain")emptyTerrain.update(w,altered);
                        if(cfg.drawControl=="sleepingroots")sleepingRoots.update(w,altered);
                        if(cfg.drawControl=="objectviewport")objectCulling.update(w,altered);
                        if(cfg.drawControl=="unitviewport")objectCulling.update(w,altered,true);
                        if(cfg.drawControl=="implicitpause") {
                            implicitFreeze.update(w,altered);row.implicitHeld.push(implicitFreeze.snapshot().held);
                        }
                        if(cfg.drawControl=="world")w.visual.visible=!altered;
                        if(cfg.drawControl=="fog")w.grafon.visLight.visible=!altered && loc.black && w.black;
                        if(cfg.drawControl=="objects")for each(var objectLayer:* in w.grafon.visObjs)objectLayer.visible=!altered;
                        if(cfg.drawControl=="effects")for(var effectLayer:int=0;effectLayer<w.grafon.visObjs.length;++effectLayer)
                            w.grafon.visObjs[effectLayer].visible=!(altered && effectLayer>=3);
                        if(cfg.drawControl=="objectgroups")for(var groupIndex:int=0;groupIndex<w.grafon.visObjs.length;++groupIndex)
                            w.grafon.visObjs[groupIndex].visible=!(index==1 && groupIndex<2) && !(index==2 && groupIndex==2);
                    }
                    row.activityRange.push(activityRangeProbe.sample(w));
                    var now:int=getTimer();
                    if(continuousPreviousSampleAt<0)throw new Error("Continuous sampling did not initialize before phase4");
                    row.sampleAtMs.push(now);row.continuousFramesMs.push(now-continuousPreviousSampleAt);
                    continuousPreviousSampleAt=now;
                    if(probeTimingRow!=null){probeTimingSampleAt=now;probeTimingSampleIndex=row.frames.length;}
                    row.frames.push(now-last);last=now;
                    row.renderBand.push(renderMs);row.exitBand.push(exitMs);row.renderEvents.push(renderCalls);row.exitEvents.push(exitCalls);
                    renderMs=exitMs=renderCalls=exitCalls=0;
                    row.preBand.push(startFrame-absoluteStart);row.tailBand.push(now-band250);
                    if(priorAbsolute>0){row.afterProbeBand.push(lastEnd-priorProbe);row.totalScript.push(lastEnd-priorAbsolute);}
                    priorAbsolute=absoluteStart;priorProbe=now;
                    if(encounter)encounter.sample();
                    samplePlayerFire();
                    if(cfg.nativeInputMotion) {
                        var densePose:Object=recordNativeMotion(row.nativeInputMotion,30);
                        denseMetrics.sample(w,row.denseFrames,densePose);
                    }
                    if(encounter && (age%30==0 || age%30==29))row.combatWindows.push({frame:age,playerShots:playerShotFrames,encounter:encounter.snapshot()});
                    if(cfg.drawControl=="rcoffline" && (age%30==0 || age%30==29))
                        row.rcOffline.windows.push({frame:age,snapshot:readRcOffline(row.rcOffline.enabled)});
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
                    if(cfg.nativeInputMotion)driveNativeInput(nativeCaseMoving());
                    else {movePlayer(x,y0);w.gg.dx=idle?0:goingForward?speed:-speed;w.gg.dy=0;}
                    drivePlayerFire();
                    if(age<(cfg.sleepingRootShort || cfg.drawControl=="rcoffline"?60:300))return;
                    if(cfg.drawControl=="rcoffline") {
                        row.rcOffline.end=readRcOffline(row.rcOffline.enabled);row.rcOffline.endAtMs=getTimer();
                    }
                    row.caseEndAtMs=getTimer();
                    row.misses=w.grafon.sceneMisses-row.missStart;row.residentEnd=w.grafon.sceneResident;row.warmMaxMs=w.grafon.sceneWarmMaxMs;
                    row.playerShotFrames=playerShotFrames-row.playerShotStart;
                    row.enemyShotFrames=encounter?encounter.actualShotFrames-row.enemyShotStart:0;
                    if(cfg.playerFire)check("actual-player-fire-"+index,row.playerShotFrames>0,row.playerShotFrames);
                    if(cfg.combatRoute && encounter) {
                        if(cfg.sleepingRootShort || cfg.drawControl=="rcoffline" || cfg.drawControl=="rcnative")check("live-armed-enemies-short-"+index,encounter.snapshot().alive==6 && encounter.snapshot().armed==6,{shots:row.enemyShotFrames,mayContainNativeReload:true});
                        else check("actual-enemy-fire-"+index,row.enemyShotFrames>0 && encounter.snapshot().alive==6 && encounter.snapshot().armed==6,row.enemyShotFrames);
                    }
                    if(cfg.drawControl=="tilecrop")row.presentation={copies:tilePresentation.copies,allocated:tilePresentation.allocated};
                    if(cfg.drawControl=="nativecrop")row.presentation={enabled:w.grafon.sceneCropPresentation,copies:w.grafon.sceneCropCopies,allocated:w.grafon.sceneCropAllocations};
                    if(cfg.drawControl=="atlas")row.presentation={copies:rasterPresentation.copies,rebuilds:rasterPresentation.rebuilds};
                    if(cfg.drawControl=="atlasrows")row.presentation={copies:rasterRowsPresentation.copies,rebuilds:rasterRowsPresentation.rebuilds,diagnosticOnly:true};
                    if(cfg.drawControl=="emptyterrain")row.emptyTerrain=emptyTerrain.snapshot();
                    if(cfg.drawControl=="sleepingroots")row.sleepingRoots=sleepingRoots.snapshot();
                    if(cfg.drawControl=="objectviewport")row.presentation={hidden:objectCulling.hidden};
                    if(cfg.drawControl=="unitviewport")row.presentation={hidden:objectCulling.hidden,layer:2,diagnosticOnly:true};
                    if(cfg.drawControl=="implicitpause") {
                        row.presentation=implicitFreeze.snapshot();
                        if(index==1 || index==2)check("observed-implicit-pause-applied-"+index,row.presentation.stopped>0,row.presentation);
                    }
                    if(cfg.drawControl=="mousetree") {
                        row.mouseTree.endX=main.stage.mouseX;row.mouseTree.endY=main.stage.mouseY;
                        check("mouse-tree-policy-stable-"+index,w.visual.mouseChildren===row.mouseTree.children && w.visual.mouseEnabled===row.mouseTree.enabled,row.mouseTree);
                    }
                    if(cfg.drawControl=="unitblit") {
                        row.blit=blitReuse.snapshot();
                        check("blit-callback-active-"+index,row.blit.calls>0 && row.blit.repeats>0,row.blit);
                        if(cfg.blitVerify)check("blit-repeat-pixels-"+index,row.blit.verified>0 && row.blit.mismatches==0,row.blit);
                    }
                    if("sceneMotionProfile" in w.grafon)row.hostProfile=w.grafon.sceneMotionProfile;
                    if("csMotionNative" in loc)row.nativeProfile=loc.csMotionNative;
                    var timing:*=main.getChildByName("ContinuousSceneTdfcProfile");
                    if(timing)row.tdfcProfile=timing.api.snapshot();
                    if(encounter)row.encounter=encounter.snapshot();
                    if(cfg.bulletSegments)row.bulletSegments=main.getChildByName("ContinuousSceneCarrier")["nativeAPI"].bulletSegments;
                    if(cfg.worldProfile)row.worldProfile=main.getChildByName("ContinuousSceneCarrier")["nativeAPI"].worldStepProfile;
                    if(cfg.locationProfile)row.locationProfile=main.getChildByName("ContinuousSceneCarrier")["nativeAPI"].locationStepProfile;
                    if(cfg.guiWeaponProfile)row.guiWeaponProfile=main.getChildByName("ContinuousSceneCarrier")["nativeAPI"].guiWeaponProfile;
                    if(cfg.playerStepProfile)row.playerStepProfile=main.getChildByName("ContinuousSceneCarrier")["nativeAPI"].playerStepProfile;
                    if(cfg.playerAnimateProfile)row.playerAnimateProfile=main.getChildByName("ContinuousSceneCarrier")["nativeAPI"].playerAnimateProfile;
                    if(w.grafon.sceneLarge) {
                        // Dense v2: one full census after the last wall-time sample.
                        // Keep the final 29 frames: the periodic samples stop
                        // at age270, while the last phase has no next sample.
                        row.activityEnd=main.getChildByName("ContinuousSceneCarrier")["nativeAPI"].activityStats();
                    }
                    if("sceneWarmSlices" in w.grafon){row.slices=w.grafon.sceneWarmSlices-row.slicesStart;row.forced=w.grafon.sceneWarmForced-row.forcedStart;}
                    check("same-logical-map-"+index,w.loc===loc);check("complete-viewport-"+index,row.empty==0,row.empty);
                    report.samples.push(row); // Dense v2: short heartbeat only during sampling.
                    if(++index<cases.length)startCase();else {
                        if(encounter){check("enemies-targeted-player",encounter.targetFrames>30,encounter.targetFrames);check("enemies-fired",encounter.shots>0,encounter.shots);}
                        if(cfg.drawControl=="unitviewport")report.unitLayerCensus=SceneUnitLayerCensus.read(w);
                        if(cfg.guiWeaponProfile)report.guiTextSentinel=SceneHudTextChecks.run(w,check);
                        if(cfg.playerAnimateProfile)report.playerTimelineChecks=ScenePlayerTimelineChecks.run(w);
                        if(cfg.sleepingRootCheck) {
                            sleepingRoots.update(w,true);phase=89;age=0;return;
                        }
                        finish();
                    }
                }
            }catch(error:Error){finish(error.message+"\n"+error.getStackTrace());}
            finally {closeProbeTiming();}
        }
        private static function readRcOffline(enabled:Boolean):Object {
            var carrier:*=main.getChildByName("RConnectOfflineProbeCarrier");
            if(!carrier || carrier["rcOfflineProbeAPI"]!==rcOffline)throw new Error("RC offline diagnostic API changed");
            var state:Object=rcOffline.snapshot();
            if(state.version!="rc-offline-probe-1" || !state.diagnosticOnly || state.performanceAcceptance ||
                state.enabled!==enabled || state.eligible!==enabled || state.mode!="offline" || state.networkAttempted ||
                state.eligibilityErrors!=0 || state.perceptionSkipped!=0 || state.perceptionGated)
                throw new Error("RC offline diagnostic is not safely eligible: "+JSON.stringify(state));
            return state;
        }
        private static function prepareNativeInputRoute():void {
            if(!cfg.encounter || !cfg.fixedEnemies || !cfg.playerFire || !cfg.stableMotion || cfg.visual || !cfg.nativeSprint)
                throw new Error("Dense fixture requires native sprint, fixed native shooters, and no visual teleport");
            var route:Object=report.combatRoute,span:Object=route.originalFreeSpan;
            var originalX:Number=x0,margin:Number=80,half:Number=Number(w.gg.scX)/2;
            if(!span || !isFinite(half) || half<=0 || !isFinite(path) || path<=0)
                throw new Error("Native input route has no valid platform/body dimensions");
            // Keep all native weapon/knockback behavior. The player walks in
            // the middle of the real platform, with three actors on each side.
            // This replaces the one-sided firing line that pushed the player
            // out of the braking margin before timing could begin.
            var originalEnemies:Array=[],enemies:Array=[],enemyMargin:Number=40,spacing:Number=80;
            for each(var originalEnemy:Object in route.enemies)
                originalEnemies.push({x:originalEnemy.x,y:originalEnemy.y});
            x0=Math.floor((Number(span.left)+Number(span.right)-path)/80)*40;
            nativeFloorY=Number(span.floor);
            var leftEnemy:Number=Math.ceil((Number(span.left)+enemyMargin)/40)*40;
            var rightEnemy:Number=Math.floor((Number(span.right)-enemyMargin)/40)*40-2*spacing;
            for(var enemyIndex:int=0;enemyIndex<3;++enemyIndex)
                enemies.push({x:leftEnemy+enemyIndex*spacing,y:nativeFloorY-1});
            for(enemyIndex=0;enemyIndex<3;++enemyIndex)
                enemies.push({x:rightEnemy+enemyIndex*spacing,y:nativeFloorY-1});
            var playerLeft:Number=x0-margin-half-1,playerRight:Number=x0+path+margin+half+1;
            var left:Number=Math.min(playerLeft,Number(enemies[0].x)-enemyMargin);
            var right:Number=Math.max(playerRight,Number(enemies[5].x)+enemyMargin);
            var top:Number=nativeFloorY-Number(route.bodyClearance);
            var leftGap:Number=x0-Number(enemies[2].x),rightGap:Number=Number(enemies[3].x)-(x0+path);
            var gap:Number=Math.min(leftGap,rightGap);
            if(!isFinite(nativeFloorY) || !isFinite(top) || left<span.left || right>span.right || gap<=margin+half+enemyMargin)
                throw new Error("Existing platform cannot fit two native firing groups and player braking margin: "+JSON.stringify({originalX:originalX,x:x0,path:path,left:left,right:right,span:span,leftEnemyGap:leftGap,rightEnemyGap:rightGap,enemies:enemies}));
            var hash:uint=0,cells:int=0,floorRow:int=int(nativeFloorY/40);
            for(var col:int=int(Math.floor(left/40));col<Math.ceil(right/40);++col) {
                if(col<0 || col>=loc.spaceX || floorRow<0 || floorRow>=loc.spaceY)
                    throw new Error("Native input corridor is outside real terrain");
                var floor:*=loc.space[col][floorRow];
                if(!floor || int(floor.phis)!=1 || floor.shelf || floor.diagon || floor.door || floor.trap || floor.stair || floor.water ||
                    !isFinite(Number(floor.phX1)) || !isFinite(Number(floor.phX2)) || !isFinite(Number(floor.phY1)) || !isFinite(Number(floor.phY2)) ||
                    Number(floor.phX1)>col*40 || Number(floor.phX2)<(col+1)*40 ||
                    Math.abs(Number(floor.phY1)-nativeFloorY)>.001 || Number(floor.phY2)<=nativeFloorY)
                    throw new Error("Native input corridor lacks continuous flat floor at column "+col);
                for(var ty:int=int(Math.floor(top/40));ty<=floorRow;++ty) {
                    if(ty<0)throw new Error("Native input corridor lacks headroom");
                    var tile:*=loc.space[col][ty];
                    if(!tile)throw new Error("Native input corridor contains a missing tile");
                    if(ty<floorRow && (tile.door || tile.trap || tile.stair || tile.water ||
                        ((int(tile.phis)!=0 || tile.shelf || tile.diagon) && Number(tile.phY1)<nativeFloorY && Number(tile.phY2)>top)))
                        throw new Error("Native input corridor has a wall, step or hazard at "+col+":"+ty);
                    var physical:Boolean=int(tile.phis)!=0 || Boolean(tile.shelf) || Boolean(tile.diagon);
                    var signature:String=[tile.front,tile.back,tile.phis,tile.diagon,tile.zForm,tile.door,
                        physical?tile.phX1-col*40:0,physical?tile.phX2-col*40:0,
                        physical?tile.phY1-nativeFloorY:0,physical?tile.phY2-nativeFloorY:0].join(":");
                    for(var c:int=0;c<signature.length;++c)hash=uint(hash*31+signature.charCodeAt(c));
                    ++cells;
                }
            }
            for each(var obj:* in loc.objs) {
                if(!obj || obj===w.gg || ("dead" in obj && obj.dead))continue;
                if(!(("phis" in obj && obj.phis>0) || ("shelf" in obj && obj.shelf) ||
                    ("wall" in obj && obj.wall>0) || ("door" in obj && obj.door>0)))continue;
                if(!isFinite(Number(obj.X1)) || !isFinite(Number(obj.X2)) || !isFinite(Number(obj.Y1)) || !isFinite(Number(obj.Y2)))
                    throw new Error("Native input corridor physical object has invalid bounds");
                if(obj.X1<right && obj.X2>left && obj.Y1<nativeFloorY && obj.Y2>top)
                    throw new Error("Native input corridor intersects a physical object");
            }
            var sightLines:int=0;
            for(var pose:int=0;pose<=4;++pose)for each(var enemy:Object in enemies) {
                ++sightLines;
                if(!loc.isLine(x0+path*pose/4,nativeFloorY-61,enemy.x,enemy.y-60))
                    throw new Error("Adjusted native input route has obstructed enemy sight line");
            }
            nativeInputRoute={originalPlayerX:originalX,playerX:x0,endX:x0+path,floorY:nativeFloorY,
                safeCenterRange:{left:left+half,right:right-half},
                turnMarginRange:{left:x0-margin,right:x0+path+margin},margin:margin,bodyHalfWidth:half,
                verifiedBounds:{left:left,right:right,top:top,bottom:nativeFloorY},originalFreeSpan:span,
                actualEnemyGap:gap,leftEnemyGap:leftGap,rightEnemyGap:rightGap,enemyBodyMargin:enemyMargin,
                originalEnemies:originalEnemies,enemies:enemies,enemiesMoved:true,terrainVerified:true,nativeSightLines:sightLines,
                hash:hash,cells:cells,hashScope:"Full two-sided actor platform including player braking margin and actor body widths; collision coordinates normalized per tile/floor",
                reason:"Keep the 200 px input turn targets; allow native knockback throughout the independently verified full platform, including the full body width"};
            report.nativeInputMotion={version:"native-input-dense-sprint-2",enabled:true,diagnosticFixture:true,
                route:nativeInputRoute,warmup:newNativeMotionBucket(),measurement:newNativeMotionBucket(),
                limitation:"Native sprint input and combat knockback; stamina unchanged; no jump, fixed speed, or position reset"};
            route.nativeInputAdjustment=nativeInputRoute;
            route.evidence.appliesTo="Original selection before explicit nativeInputAdjustment; new position was independently reverified";
            route.x=x0;route.enemies=enemies;route.enemySpacing=spacing;
            route.gapFromPlayerPathStart=leftGap;route.gapFromPlayerPathEnd=rightGap;
            route.corridor={left:left,right:right,top:top,floor:nativeFloorY};
            check("native-input-existing-corridor",true,nativeInputRoute);
        }
        private static function nativeCaseMoving():Boolean {
            if(cfg.drawControl || cfg.impactABBA || cfg.fogABBA || cfg.fogTypedABBA)return true;
            if(cfg.encounter)return index!=0 && index!=3;
            return index!=3;
        }
        private static function driveNativeInput(moving:Boolean):void {
            var begin:int=getTimer();
            if(w.gg!==nativeInputPlayer || w.loc!==loc)throw new Error("Native input actor/location changed");
            if(moving) {
                if(nativeDirection>0 && w.gg.X>=x0+path){nativeDirection=-1;nativeSawRight=true;++nativeTurns;}
                else if(nativeDirection<0 && w.gg.X<=x0) {
                    nativeDirection=1;++nativeTurns;
                    if(nativeSawRight){++nativeRoundTrips;nativeSawRight=false;}
                }
            }
            // No clearAll here: callers clear first, then set movement and
            // attack together for the next native ENTER_FRAME.
            w.ctr.keyLeft=moving && nativeDirection<0;w.ctr.keyRight=moving && nativeDirection>0;
            w.ctr.keyRun=moving && Boolean(cfg.nativeSprint);w.ctr.keyJump=false;w.ctr.keyDash=false;
            w.ctr.keyDubLeft=false;w.ctr.keyDubRight=false;
            ++driverCalls;driverMs+=getTimer()-begin;
        }
        private static function nativeMotionState():Object {
            var u:*=w.gg;
            if(u!==nativeInputPlayer || w.loc!==loc)throw new Error("Native input actor/location changed during observation");
            if(!isFinite(u.X) || !isFinite(u.Y) || !isFinite(u.dx) || !isFinite(u.dy) ||
                u.X<nativeInputRoute.safeCenterRange.left || u.X>nativeInputRoute.safeCenterRange.right)
                throw new Error("Native input left the verified full platform; no position reset: "+JSON.stringify({X:u.X,Y:u.Y,dx:u.dx,dy:u.dy,route:nativeInputRoute}));
            var floor:*=loc.getAbsTile(u.X,nativeFloorY+.01);
            var floorContact:Boolean=Boolean(u.stay) && Math.abs(Number(u.Y)-nativeFloorY)<.01 && Math.abs(Number(u.dy))<.01 &&
                floor && int(floor.phis)==1 && Math.abs(Number(floor.phY1)-nativeFloorY)<.01;
            var osn:*=u.vis?u.vis.osn:null,body:*=osn?osn.body:null;
            return {X:u.X,Y:u.Y,dx:u.dx,dy:u.dy,stay:Boolean(u.stay),walk:u.walk,
                floorY:nativeFloorY,collisionFloorY:floor?floor.phY1:null,floorContact:floorContact,
                bodypose:{osnLabel:osn?osn.currentLabel:null,frame:body?body.currentFrame:null,
                    label:body?body.currentLabel:null,playing:body?body.isPlaying:null},
                keys:{left:Boolean(w.ctr.keyLeft),right:Boolean(w.ctr.keyRight),attack:Boolean(w.ctr.keyAttack),run:Boolean(w.ctr.keyRun),jump:Boolean(w.ctr.keyJump)},
                turns:nativeTurns,roundTrips:nativeRoundTrips,work:u.work,control:Boolean(u.ggControl)};
        }
        private static function newNativeMotionBucket():Object {
            return {samples:0,groundedSamples:0,airborneSamples:0,movingSamples:0,floorContactSamples:0,
                minX:null,maxX:null,minY:null,maxY:null,windows:[]};
        }
        private static function addNativeMotionSample(bucket:Object,state:Object):void {
            if(bucket.samples==0){bucket.first=state;bucket.minX=bucket.maxX=state.X;bucket.minY=bucket.maxY=state.Y;}
            ++bucket.samples;bucket.last=state;
            if(state.stay)++bucket.groundedSamples;else ++bucket.airborneSamples;
            if(Math.abs(Number(state.dx))>.1)++bucket.movingSamples;
            if(state.floorContact)++bucket.floorContactSamples;
            bucket.minX=Math.min(bucket.minX,state.X);bucket.maxX=Math.max(bucket.maxX,state.X);
            bucket.minY=Math.min(bucket.minY,state.Y);bucket.maxY=Math.max(bucket.maxY,state.Y);
            bucket.turns=state.turns-bucket.first.turns;bucket.roundTrips=state.roundTrips-bucket.first.roundTrips;
        }
        private static function recordNativeMotion(bucket:Object,windowSize:int):Object {
            var state:Object=nativeMotionState(),window:Object;
            if(bucket.samples%windowSize==0) {
                window=newNativeMotionBucket();delete window.windows;
                window.startSample=bucket.samples;bucket.windows.push(window);
            } else window=bucket.windows[bucket.windows.length-1];
            addNativeMotionSample(window,state);addNativeMotionSample(bucket,state);
            return state;
        }
        private static function movePlayer(x:Number,y:Number):void {
            if(cfg.nativeInputMotion)throw new Error("Native input mode attempted forced player positioning");
            var begin:int=getTimer();
            if(cfg.stableMotion)w.gg.setPos(x,y);else w.gg.setLocPos(x,y);
            ++driverCalls;driverMs+=getTimer()-begin;
        }
        private static function sampleCombat(frame:Object,boundary:Boolean):void {
            if(cfg.nativeInputMotion) {
                var motion:Object=recordNativeMotion(report.nativeInputMotion.measurement,30);
                if(boundary)frame.nativeInputMotion=motion;
            }
            frame.playerShot=samplePlayerFire();
            if(encounter) {
                var oldShots:int=encounter.actualShotFrames,oldTargets:int=encounter.targetFrames;
                encounter.sample();
                frame.enemyShots=encounter.actualShotFrames-oldShots;
                frame.enemyTargets=encounter.targetFrames-oldTargets;
                if(boundary)frame.encounter=encounter.snapshot();
            }
        }
        private static function samplePlayerFire():Boolean {
            if(!cfg.playerFire)return false;
            var gun:*=w.gg.currentWeapon;
            if(!gun || gun.id!="assr")throw new Error("Player fixture weapon changed");
            var fired:Boolean=gun.hold<gun.holder;
            if(fired)++playerShotFrames;
            return fired;
        }
        private static function drivePlayerFire():void {
            if(!cfg.playerFire)return;
            var gun:*=w.gg.currentWeapon;
            w.cam.celX=w.gg.X*w.cam.scaleV+w.cam.vx+450*nativeDirection;
            w.cam.celY=(w.gg.Y-30)*w.cam.scaleV+w.cam.vy;
            w.ctr.keyAttack=true;
            gun.hold=gun.holder;gun.hp=gun.maxhp;
        }
        private static var lastProgress:int=0;
    }
}
