package tests {
    import flash.desktop.NativeApplication;
    import flash.display.PNGEncoderOptions;
    import flash.filesystem.File;
    import flash.filesystem.FileMode;
    import flash.filesystem.FileStream;
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.display.DisplayObject;
    import flash.display.Stage;
    import flash.events.Event;
    import flash.geom.Matrix;
    import flash.geom.Rectangle;
    import flash.system.System;
    import flash.utils.getDefinitionByName;
    import flash.utils.getQualifiedClassName;
    import flash.utils.getTimer;

    /** Live simulation, no hostile actors, native scripted camera; not jump/combat acceptance. */
    public class SceneCameraRasterTrial {
        private var world:*;
        private var cam:*;
        private var grafon:*;
        private var player:*;
        private var location:*;
        private var presenter:*;
        private var stage:Stage;
        private var snd:Class;
        private var api:*;
        private var saved:Object;
        private var report:Object;
        private var displays:Array=[];
        private var originalTiles:Array=[];
        private var owned:Array=[];
        private var views:Array=[];
        private var route:Array=[];
        private var prepareRoute:Array=[];
        private var order:Array=[0,1,2,3,3,2,1,0];
        private var phase:int=0;
        private var cursor:int=0;
        private var retries:int=0;
        private var preparePass:int=0;
        private var prepareBaseline:Object;
        private var settle:int=0;
        private var segment:int=0;
        private var age:int=0;
        private var previous:int=0;
        private var beginAt:int=0;
        private var prepareAt:int=0;
        private var pixelAt:int=0;
        private var pending:Object;
        private var row:Object;
        private var closed:Boolean=false;
        private var cameraHookAdded:Boolean=false;
        private var plannedSegment:int=-1;
        private var plannedAge:int=-1;
        private const CAMERA:Array=["moved","screenX","screenY","X","Y","vx","vy","ovy","maxsx","maxsy","maxvx","maxvy","celX","celY","camRun","otryv","quakeX","quakeY","isZoom","scaleV","scaleS","dblack","showOn","showX","showY"];
        private const COUNTERS:Array=["sceneRedraws","sceneDrawMs","sceneMaxDrawMs","sceneResident","sceneEvictions","sceneMisses","sceneWarmCount","sceneWarmSlices","sceneWarmForced","sceneLastDirtyCount"];

        public function begin(w:*,p:*):Object {
            if(report!=null)throw new Error("Camera raster trial is single-use");
            beginAt=getTimer();
            report={version:"camera-native-once-1",diagnosticOnly:true,performanceEligible:false,
                terminalOnly:true,complete:false,passed:false,pixelsValid:false,errors:[],pixels:[],windows:[],
                framesMs:[],sampleAtMs:[],prepareMs:0,prepareWorkMs:0,pixelMs:0,
                nativeSchedules:0,nativeCaptures:0,helperTimedCalcCalls:0,
                pixelBitmapsCreated:0,pixelBitmapsDisposed:0,pixelDisposeErrors:[],pixelBufferPeakBytes:0,measurementFrames:960,
                intervalMeaning:"Outgoing native camera state, frame presentation, then next native step and observer entry. Boundary intervals retained; no extra timed helper Camera.calc or segment-clock resets.",
                limits:["Native simulation remains active; hostile actors and existing projectiles are removed only in this private fixture.",
                    "120fps diagnostic; native simulation and Flash callbacks continue, not ordinary gameplay FPS.",
                    "The same native camera script replays horizontal/vertical/combined paths in each map mode.",
                    "No player teleport during measurement; this is not a natural jump test.",
                    "Camera/cache restoration is checked; deliberately removed fixture enemies are not restored.",
                    "All intervals and observer work retained; no new rendering optimization applied."]};
            world=w;presenter=p;
            try {
                require(w!=null && p!=null,"Missing world/presenter");
                cam=w.cam;grafon=w.grafon;player=w.gg;location=w.loc;stage=w.main.stage as Stage;
                require(stage!=null && w.swfStage===stage && w.allStat==1 && w.t_exit==0,"Unstable world/stage");
                require(cam.moved && (!grafon.sceneLarge || grafon.sceneChunkSide==320),"Requires native camera and optional 320px scene");
                require(getQualifiedClassName(p)=="SceneTilePresentation","Wrong presentation helper");
                require(w.sats!=null && w.sats.vis!=null && w.visual!=null,"Missing camera targets");
                snd=w.main.loaderInfo.applicationDomain.getDefinition("fe.Snd") as Class;
                var carrier:*=w.main.getChildByName("ContinuousSceneCarrier");
                api=carrier!=null && "nativeAPI" in carrier?carrier["nativeAPI"]:null;
                require(api!=null && api.constructor===Object,"Missing native camera state API");
                saved={pause:w.onPause,worldVisible:w.visual.visible,nativeWindowVisible:stage.nativeWindow.visible,camera:fields(cam,CAMERA),gg:playerState(),celX:w.celX,celY:w.celY,
                    look:w.ctr.keyLook,zoom:w.ctr.keyZoom,frameRate:stage.frameRate,
                    sndX:snd[new QName("","centrX")],sndY:snd[new QName("","centrY")],
                    blackVisible:w.vblack.visible,blackAlpha:w.vblack.alpha,
                    hasState:api.hasOwnProperty("verticalCameraState"),state:api["verticalCameraState"]};
                saved.stateFields=saved.state!=null && saved.state.constructor===Object?plain(saved.state):null;
                saveDisplay(w.visual);saveDisplay(w.sats.vis);saveDisplay(w.vscene);
                saveDisplay(grafon.ramT);saveDisplay(grafon.ramB);saveDisplay(grafon.ramL);saveDisplay(grafon.ramR);
                rememberTiles();
                saved.ready=true;
                require(/^pfe-modsettings-continuous-motion-[0-9a-f]{32}$/.test(NativeApplication.nativeApplication.applicationID),"Isolated motion application required");
                require(saved.worldVisible===true,"World must start visible");
                require(stage.nativeWindow.visible,"Show private window before native game initialization");
                for(var menuIndex:int=0;menuIndex<world.main.numChildren;++menuIndex)require(getQualifiedClassName(world.main.getChildAt(menuIndex))!="visMainMenu","Native menu remains attached");
                require(stage.nativeWindow.visible===true,"Owned private window did not become visible");
                report.originalFrameRate=saved.frameRate;report.testFrameRate=120;
                report.stage={width:stage.stageWidth,height:stage.stageHeight,quality:stage.quality};
                report.initial=snapshot();
                report.originalZoom=cam.scaleV;
                cam.setZoom(0);
                require(Number(cam.scaleV)==1,"Native unit zoom selection failed");
                report.testZoom=cam.scaleV;
                require(cam.screenX==stage.stageWidth && cam.screenY==stage.stageHeight,"Stage/camera size mismatch");
                require(w.onPause===false && w.gg===player && w.loc===location,"Native simulation must remain active");
                stripHostiles();
                stage.frameRate=120;require(stage.frameRate==120,"120fps setting not accepted");
                cam.camRun=true;cam.quakeX=0;cam.quakeY=0;cam.otryv=0;cam.showOn=false;cam.dblack=0;
                w.ctr.keyLook=false;w.ctr.keyZoom=false;
                selectReferenceSite();
                report.environmentChecks=environmentCheck();
                makeRoute();
                report.views=views;report.route=route;
                prepareRoute=views.concat(route);prepareAt=getTimer();
                report.prepareStart=snapshot();
                prepareBaseline=counters();report.preparePasses=[];
                // Native MainMenu.mainStep listens on this same Stage at priority 0.
                // Actual camera coordinates are checked after World.step, at priority -1000.
                stage.addEventListener(Event.ENTER_FRAME,beforeNative,false,500);
                cameraHookAdded=true;
            } catch(error:Error) {fail(error);}
            return report;
        }

        public function step(w:*):Boolean {
            if(closed)return true;
            try {
                require(w===world,"World argument replaced");guard();++report.simulationTicks;
                require(getTimer()-beginAt<180000,"Camera raster timeout");
                if(phase==0) {
                    var workAt:int=getTimer();
                    var point:Object=prepareRoute[cursor];
                    applyCamera(point.x,point.y);
                    ++report.prepareCalls;
                    if(grafon.sceneViewReady()) {++cursor;retries=0;} else if(++retries>300)throw new Error("Native viewport did not finish preparing");
                    report.prepareWorkMs+=getTimer()-workAt;
                    if(cursor==prepareRoute.length) {
                        var preparationEnd:Object=counters(),quiet:Boolean=true,changes:Object={};
                        for each(var key:String in ["sceneRedraws","sceneDrawMs","sceneResident","sceneEvictions","sceneMisses","sceneWarmCount","sceneWarmSlices","sceneWarmForced"]) {
                            if(key in preparationEnd && key in prepareBaseline) {
                                changes[key]=Number(preparationEnd[key])-Number(prepareBaseline[key]);
                                if(changes[key]!=0)quiet=false;
                            }
                        }
                        ++preparePass;report.preparePasses.push({pass:preparePass,quiet:quiet,delta:changes});
                        cursor=0;
                        if(quiet) {
                            report.prepareMs=getTimer()-prepareAt;report.prepareEnd=snapshot();
                            phase=1;pixelAt=getTimer();
                        } else {
                            require(preparePass<12,"Native route did not settle in 12 complete passes");
                            prepareBaseline=preparationEnd;
                        }
                    }
                } else if(phase==1) {
                    pixelCase(views[cursor],cursor);++cursor;
                    if(cursor==views.length) {
                        report.pixelMs=getTimer()-pixelAt;
                        report.pixelsValid=true;
                        presenter.clear();applyCamera(views[0].x,views[0].y);
                        phase=2;settle=0;
                    }
                } else if(phase==2) {
                    applyCamera(views[0].x,views[0].y);
                    require(grafon.sceneViewReady(),"Prepared view became incomplete");
                    ++settle;
                    if(settle==60) {
                        report.stabilizationFrames=settle;phase=31;
                    }
                } else if(phase==31) {
                    // Prime one native frame before starting the measured outgoing intervals.
                    report.fogTimingStart=fogState();report.timingStart=snapshot();
                    phase=3;previous=getTimer();report.timingStartAtMs=previous;
                    startWindow();applyFrame();
                } else if(phase==3) {
                    // Timestamp precedes any new camera/presentation work; pending is the
                    // exact state whose renderer had the intervening ENTER_FRAME interval.
                    require(world.visual.visible===pending.worldVisible,"World visibility changed during measured interval");
                    var now:int=getTimer();
                    var interval:int=now-previous;previous=now;
                    require(interval>=0,"Non-monotonic timer");
                    report.framesMs.push(interval);report.sampleAtMs.push(now);
                    row.framesMs.push(interval);row.sampleAtMs.push(now);
                    row.vx.push(pending.vx);row.vy.push(pending.vy);
                    row.cameraX.push(pending.x);row.cameraY.push(pending.y);
                    row.gg.push(pending.gg);row.scene.push(pending.scene);
                    row.workMs.push(pending.workMs);row.worldVisible.push(pending.worldVisible);row.windowVisible.push(pending.windowVisible);
                    ++age;
                    if(age==120) {
                        row.endAtMs=now;row.end=snapshot();row.copiesEnd=presenter.copies;row.allocatedEnd=presenter.allocated;
                        ++segment;
                        if(segment==order.length) {
                            report.timingEndAtMs=now;report.timingElapsedMs=now-report.timingStartAtMs;
                            report.timingEnd=row.end;report.timingRasterDelta={};report.zeroRasterWork=true;
                            for each(var rasterCounter:String in ["sceneRedraws","sceneDrawMs","sceneResident","sceneEvictions","sceneMisses","sceneWarmCount","sceneWarmSlices","sceneWarmForced"]) {
                                if(rasterCounter in row.end.scene && rasterCounter in report.timingStart.scene) {
                                    var delta:Number=Number(row.end.scene[rasterCounter])-Number(report.timingStart.scene[rasterCounter]);
                                    report.timingRasterDelta[rasterCounter]=delta;
                                    if(delta!=0)report.zeroRasterWork=false;
                                }
                            }
                            require(report.nativeSchedules==961 && report.nativeCaptures==960 && report.helperTimedCalcCalls==0,"Native camera schedule/count mismatch");
                            report.fogTimingEnd=fogState();report.complete=true;report.passed=true;clear(w);
                        } else {startWindow();applyFrame();}
                    } else applyFrame();
                }
            } catch(error:Error) {fail(error);}
            return closed;
        }

        private function environmentCheck():Object {
            var out:Object={sceneLarge:Boolean(grafon.sceneLarge),passed:false,cases:[],fieldsChecked:0,
                cachePresent:false,mapEntryRestored:false,originRestored:false,environmentRestored:false};
            if(!grafon.sceneLarge) {out.passed=true;out.skipped="ordinary-room";return out;}
            var land:*=location.land;
            var state:Object=api.state(land);
            require(state!=null && state.loc===location && state.byCell!=null && state.regions.length>1,"Missing native environment state");
            var names:Array=[];
            for(var envName:String in state.regions[0].environment)names.push(envName);
            grafon.sceneNativeEnvironment(location,player.X,player.Y);
            out.playerRegionSynchronized=true;
            var initial:Object=fields(location,names),oldX:*=land.minLocX,oldY:*=land.minLocY;
            var playerX:Number=player.X,playerY:Number=player.Y;
            var playerKey:String=(land.minLocX+int(Math.max(0,playerX)/1920))+":"+(land.minLocY+int(Math.max(0,playerY)/1000));
            var originalEntry:Object=state.byCell[playerKey];
            require(originalEntry!=null && names.length>0,"Player has no native environment");
            var checkPoint:Function=function(x:Number,y:Number,label:String):void {
                var key:String=(land.minLocX+int(Math.max(0,x)/1920))+":"+(land.minLocY+int(Math.max(0,y)/1000));
                var region:Object=state.byCell[key];
                var expected:Object=region==null?fields(location,names):region.environment;
                grafon.sceneNativeEnvironment(location,x,y);
                for each(var field:String in names) {
                    require(location[field]===expected[field],"Environment mismatch "+label+" / "+key+" / "+field);
                    ++out.fieldsChecked;
                }
                out.cases.push({label:label,x:isFinite(x)?x:String(x),y:isFinite(y)?y:String(y),key:key,found:region!=null,matched:true});
            };
            try {
                for each(var region:Object in state.regions) {
                    var left:Number=(Number(region.lx)-Number(land.minLocX))*1920;
                    var top:Number=(Number(region.ly)-Number(land.minLocY))*1000;
                    checkPoint(left+960,top+500,"region-center");
                    checkPoint(left,top,"inclusive-corner");
                    checkPoint(left+1919.999,top+999.999,"inside-corner");
                    checkPoint(left+1920,top+500,"next-x-boundary");
                    checkPoint(left+960,top+1000,"next-y-boundary");
                }
                var edges:Array=[-Infinity,-1,-0,0,NaN,Infinity,Number.MAX_VALUE,255*1920,256*1920,4294967296*1920];
                for each(var edge:Number in edges)checkPoint(edge,0,"numeric-x");
                edges=[-Infinity,-1,-0,0,NaN,Infinity,Number.MAX_VALUE,255000,256000,4294967296000];
                for each(edge in edges)checkPoint(0,edge,"numeric-y");
                // No native update runs between this temporary metadata change and restoration.
                land.minLocX=Number(oldX)+1;checkPoint(0,0,"changed-origin-x");
                land.minLocY=Number(oldY)+1;checkPoint(0,0,"changed-origin-y");
                land.minLocX=oldX;land.minLocY=oldY;checkPoint(playerX,playerY,"restored-origin");
                var changedEnvironment:Object={};
                for each(envName in names)changedEnvironment[envName]=originalEntry.environment[envName];
                require(isFinite(Number(changedEnvironment.maxdy)),"Expected finite native maxdy");
                changedEnvironment.maxdy=Number(changedEnvironment.maxdy)+1;
                state.byCell[playerKey]={environment:changedEnvironment};
                checkPoint(playerX,playerY,"replaced-entry-same-key");
                state.byCell[playerKey]=originalEntry;
                checkPoint(playerX,playerY,"restored-entry-same-key");
                var cache:Array=state._csEnvironmentCellKeysV1 as Array;
                out.cachePresent=cache!=null;
                if(cache!=null) {
                    require(cache[0]===oldX && cache[1]===oldY && cache[2] is Array,"Cache origin not restored");
                    var columns:Array=cache[2] as Array;
                    out.cachedKeys=0;
                    for(var cx:String in columns) {
                        require(int(cx)>=0 && int(cx)<=255 && String(int(cx))==cx,"Unbounded cache column");
                        var column:Array=columns[cx] as Array;require(column!=null,"Cache column type");
                        for(var cy:String in column) {
                            require(int(cy)>=0 && int(cy)<=255 && String(int(cy))==cy,"Unbounded cache row");
                            require(column[cy]===(Number(oldX)+int(cx))+":"+(Number(oldY)+int(cy)),"Stale cached key");
                            ++out.cachedKeys;
                        }
                    }
                }
                out.passed=true;
            } finally {
                land.minLocX=oldX;land.minLocY=oldY;state.byCell[playerKey]=originalEntry;
                grafon.sceneNativeEnvironment(location,playerX,playerY);
                out.mapEntryRestored=state.byCell[playerKey]===originalEntry;
                out.originRestored=land.minLocX===oldX && land.minLocY===oldY;
                out.environmentRestored=sameFields(location,initial);
                require(out.mapEntryRestored && out.originRestored && out.environmentRestored,"Environment component restoration failed");
            }
            return out;
        }

        public function clear(w:*):Object {
            if(closed)return report!=null?report.cleanup:{restored:true,notStarted:true};
            closed=true;
            if(cameraHookAdded && stage!=null)stage.removeEventListener(Event.ENTER_FRAME,beforeNative);
            cameraHookAdded=false;
            var at:int=getTimer();
            var cleanup:Object={restored:true,errors:[],nativeCachesRetained:true,pendingOwnedBitmaps:0};
            try {if(presenter!=null)presenter.clear();} catch(e0:Error){cleanup.errors.push("presenter: "+e0.message);}
            disposeOwned();
            if(saved!=null && saved.ready) {
                try {
                    require(world===w && world.cam===cam && world.grafon===grafon && world.loc===location && world.gg===player,"Identity changed during cleanup");
                    // Native culling is restored using the saved viewport before restoring
                    // all scalar/matrix state that sceneTick -> setZoom itself touches.
                    assign(cam,saved.camera);grafon.sceneTick();
                } catch(e1:Error){cleanup.errors.push("native culling: "+e1.message);}
                try {assign(cam,saved.camera);} catch(e2:Error){cleanup.errors.push("camera: "+e2.message);}
                for each(var display:Object in displays)try {display.target.transform.matrix=display.matrix;}catch(e3:Error){cleanup.errors.push("matrix: "+e3.message);}
                try {
                    world.celX=saved.celX;world.celY=saved.celY;
                    world.ctr.keyLook=saved.look;world.ctr.keyZoom=saved.zoom;
                    world.vblack.visible=saved.blackVisible;world.vblack.alpha=saved.blackAlpha;
                    snd[new QName("","centrX")]=saved.sndX;snd[new QName("","centrY")]=saved.sndY;
                    if(saved.stateFields!=null) {for(var oldKey:String in saved.state)delete saved.state[oldKey];assign(saved.state,saved.stateFields);}
                    if(saved.hasState)api["verticalCameraState"]=saved.state;else delete api["verticalCameraState"];
                } catch(e4:Error){cleanup.errors.push("ancillary state: "+e4.message);}
                try {
                    for each(var original:Object in originalTiles) {
                        var bitmap:Bitmap=original.bitmap;
                        require(bitmap.parent===original.parent && bitmap.bitmapData===original.data,"Original native tile identity not restored");
                        bitmap.visible=original.visible;bitmap.smoothing=original.smoothing;bitmap.pixelSnapping=original.pixelSnapping;
                        bitmap.scrollRect=original.scrollRect;
                    }
                    checkNativeBindings();
                } catch(e5:Error){cleanup.errors.push("native tile: "+e5.message);}
                try {world.visual.visible=saved.worldVisible;stage.nativeWindow.visible=saved.nativeWindowVisible;}
                catch(eVisibility:Error){cleanup.errors.push("visibility: "+eVisibility.message);}
                // These restoration operations must still run if an earlier check failed.
                try {stage.frameRate=saved.frameRate;}catch(e6:Error){cleanup.errors.push("frameRate: "+e6.message);}
                try {world.onPause=saved.pause;}catch(e7:Error){cleanup.errors.push("pause: "+e7.message);}
                try {
                    require(sameFields(cam,saved.camera) && world.onPause===saved.pause && stage.frameRate==saved.frameRate,"Camera/pause/frameRate restore mismatch");
                    require(world.gg===player && isFinite(player.X+player.Y+player.hp),"Player identity changed during live fixture");
                    require(world.visual.visible===saved.worldVisible && stage.nativeWindow.visible===saved.nativeWindowVisible,"World/window visibility restore mismatch");
                    for each(display in displays)require(sameMatrix(display.target.transform.matrix,display.matrix),"Display transform restore mismatch");
                    require(world.celX===saved.celX && world.celY===saved.celY && world.ctr.keyLook===saved.look && world.ctr.keyZoom===saved.zoom,"Controller/aim restore mismatch");
                    require(world.vblack.visible===saved.blackVisible && world.vblack.alpha===saved.blackAlpha,"Black overlay restore mismatch");
                    require(snd[new QName("","centrX")]===saved.sndX && snd[new QName("","centrY")]===saved.sndY,"Sound center restore mismatch");
                    require(api.hasOwnProperty("verticalCameraState")===saved.hasState && (!saved.hasState || api["verticalCameraState"]===saved.state),"Camera API identity restore mismatch");
                    if(saved.stateFields!=null)require(sameFields(saved.state,saved.stateFields),"Camera API fields restore mismatch");
                } catch(e8:Error){cleanup.errors.push("verify: "+e8.message);}
            }
            cleanup.cameraHookRemoved=!cameraHookAdded;
            cleanup.pendingOwnedBitmaps=owned.length;cleanup.elapsedMs=getTimer()-at;cleanup.fixturePopulationNotRestored=true;
            if(report.pixelDisposeErrors.length)cleanup.errors.push("Owned pixel bitmap disposal failed");
            cleanup.restored=cleanup.errors.length==0 && owned.length==0;
            report.cleanup=cleanup;report.elapsedMs=getTimer()-beginAt;
            if(!cleanup.restored){report.passed=false;report.errors.push("Cleanup failed");}
            return cleanup;
        }

        private function fogState():Object {
            var site:Object=report.referenceSite;
            require(site!=null && site.selected!=null,"Fog observation requires selected reference room");
            var ox:int=grafon.sceneLarge?site.roomX*48:0,oy:int=grafon.sceneLarge?site.roomY*25:0;
            var cells:Array=[];
            for(var x:int=0;x<48;++x)for(var y:int=0;y<25;++y) {
                var tile:*=location.space[ox+x][oy+y];
                cells.push({x:x,y:y,visi:tile.visi,target:tile.t_visi,opacity:tile.opac,
                    mask:grafon.lightBmp.getPixel32(ox+x,oy+y+1),water:tile.water});
            }
            return {width:grafon.lightBmp.width,height:grafon.lightBmp.height,
                localCells:cells,lightVisible:grafon.visLight.visible,lightAlpha:grafon.visLight.alpha,
                lightScaleX:grafon.visLight.scaleX,lightScaleY:grafon.visLight.scaleY,
                relight:location.isRelight,relightTicks:location.relight_t,
                player:{x:player.X,y:player.Y,y1:player.Y1,stayY:player.stayY,direction:player.storona},
                black:location.black,retDark:location.retDark,lDist1:location.lDist1,lDist2:location.lDist2};
        }

        private function selectReferenceSite():void {
            var ox:int=0,oy:int=0;
            var candidates:Array=[],best:Object=null;
            // Keep both axes inside the native room's camera limits. A full body
            // fits on three solid cells with three cells of clear space above.
            for(var ry:int=0;ry<(grafon.sceneLarge?5:1);++ry)for(var rx:int=0;rx<(grafon.sceneLarge?5:1);++rx) {
            ox=rx*48;oy=ry*25;
            for(var cy:int=8;cy<=22;++cy)for(var cx:int=20;cx<=28;++cx) {
                var good:Boolean=true;
                for(var dx:int=-1;dx<=1 && good;++dx) {
                    var tile:*=location.space[ox+cx+dx][oy+cy];
                    if(!tile || tile.phis!=1 || tile.diagon || tile.shelf || tile.door || tile.water || tile.trap || tile.stair ||
                       tile.phY1!=(oy+cy)*40 || tile.phX1>(ox+cx+dx)*40 || tile.phX2<(ox+cx+dx+1)*40) {good=false;break;}
                    for(var dy:int=1;dy<=3;++dy) {
                        tile=location.space[ox+cx+dx][oy+cy-dy];
                        if(!tile || tile.phis || tile.diagon || tile.shelf || tile.door || tile.water || tile.trap || tile.stair){good=false;break;}
                    }
                }
                var x:Number=(ox+cx)*40+20,y:Number=(oy+cy)*40;
                for each(var obj:* in location.objs) {
                    if(!good)break;
                    if(!obj || ("dead" in obj && obj.dead))continue;
                    if(!(("phis" in obj && obj.phis>0)||("shelf" in obj && obj.shelf)||("wall" in obj && obj.wall>0)||("door" in obj && obj.door>0)))continue;
                    if(Number(obj.X1)<x+25 && Number(obj.X2)>x-25 && Number(obj.Y1)<y && Number(obj.Y2)>y-120)good=false;
                }
                if(!good)continue;
                var roomX:int=grafon.sceneLarge?rx:int(world.land.locX),roomY:int=grafon.sceneLarge?ry:int(world.land.locY);
                var score:Number=(Math.abs(roomX-2)+Math.abs(roomY-3))*10000+Math.abs(cx*40+20-960)+Math.abs(cy*40-600);
                var c:Object={x:x,y:y,localX:cx*40+20,localY:cy*40,roomX:roomX,roomY:roomY,score:score};candidates.push(c);
                if(!best || score<best.score)best=c;
            }
            }
            report.referenceSite={roomX:best?best.roomX:-1,roomY:best?best.roomY:-1,candidates:candidates,selected:best,terrainEdited:false,spawnCalls:0};
            require(best!=null,"No verified visible reference platform in scanned rooms");
            ox=grafon.sceneLarge?best.roomX*48:0;oy=grafon.sceneLarge?best.roomY*25:0;
            var tileHash:uint=0;
            for(cx=0;cx<48;++cx)for(cy=0;cy<25;++cy) {
                tile=location.space[ox+cx][oy+cy];
                var value:String=[tile.front,tile.back,tile.phis,tile.diagon,tile.zForm,tile.door].join(":");
                for(var k:int=0;k<value.length;++k)tileHash=uint(tileHash*31+value.charCodeAt(k));
            }
            report.referenceSite.tileHash=tileHash;
            report.fogHistory={before:fogState(),resetCells:0,nonzeroBeforeReset:0,terminalOnly:true};
            // Setup-only control: both modes must start exploration at the same
            // verified platform, not inherit different room-entry sight history.
            for(var fx:int=0;fx<location.spaceX;++fx)for(var fy:int=0;fy<location.spaceY;++fy) {
                var fogTile:*=location.space[fx][fy];
                if(fogTile.visi!=0 || fogTile.t_visi!=0)++report.fogHistory.nonzeroBeforeReset;
                fogTile.visi=0;fogTile.t_visi=0;++report.fogHistory.resetCells;
            }
            grafon.setLight();report.fogHistory.afterReset=fogState();
            player.setLocPos(best.x,best.y-1);player.dx=player.dy=0;++report.referenceSite.spawnCalls;location.isRelight=true;
            // Measurement waits for full route preparation plus 60 frames.
            // No later positioning, velocity writes or camera-bound changes.
        }
        private function coverage(b:BitmapData):Object {
            var pixels:Vector.<uint>=b.getVector(new Rectangle(96,80,stage.stageWidth-192,stage.stageHeight-160)),count:int=0;
            for(var i:int=0;i<pixels.length;++i) {
                var p:uint=pixels[i];if(Math.max(p>>>16&255,p>>>8&255,p&255)>20)++count;
            }
            return {colored:count,pixels:pixels.length,fraction:count/pixels.length,excludesMainHudMargins:true};
        }
        private function savePNG(name:String,b:BitmapData):void {
            var f:FileStream=new FileStream();
            try {f.open(File.applicationStorageDirectory.resolvePath(name),FileMode.WRITE);f.writeBytes(b.encode(b.rect,new PNGEncoderOptions()));}
            finally {f.close();}
        }

        private function makeRoute():void {
            require(stage.stageWidth==1280 && stage.stageHeight==720,"Matched camera baseline requires 1280x720 content");
            var offsetX:int=grafon.sceneLarge?report.referenceSite.roomX*1920:0,offsetY:int=grafon.sceneLarge?report.referenceSite.roomY*1000:0;
            require(grafon.sceneLarge?(location.spaceX==240 && location.spaceY==125):
                (location.spaceX==48 && location.spaceY==25),"Unexpected matched room dimensions");
            var x:int=Math.round(player.X),y:int=offsetY+Math.max(520,Math.min(700,Math.round(player.Y)-offsetY));
            views=[{x:x,y:y},{x:x+120,y:y},{x:x,y:y+24},{x:x-120,y:y-24},{x:x+120,y:y+24}];
            for(var leg:int=0;leg<5;++leg) {
                var a:Object=views[leg],b:Object=views[(leg+1)%5];
                for(var i:int=0;i<24;++i)route.push({x:a.x+(b.x-a.x)*i/24,y:a.y+(b.y-a.y)*i/24});
            }
            report.roomAxis={continuous:grafon.sceneLarge,offsetX:offsetX,offsetY:offsetY,
                localCenterX:x-offsetX,localCenterY:y-offsetY,roomGridX:report.referenceSite.roomX,roomGridY:report.referenceSite.roomY,roomWidth:1920,roomHeight:1000};
            report.routeTranslationOnly=true;report.playerMovedByHelper=false;report.prepareCalls=0;
        }

        private function startWindow():void {
            var condition:int=order[segment];age=0;
            row={index:segment,condition:condition,mode:["native-static","native-horizontal","native-vertical","native-combined"][condition],
                hidden:false,moving:condition!=0,startAtMs:previous,
                framesMs:[],sampleAtMs:[],vx:[],vy:[],cameraX:[],cameraY:[],gg:[],scene:[],workMs:[],
                worldVisible:[],windowVisible:[],start:snapshot(),copiesStart:presenter.copies,allocatedStart:presenter.allocated};
            report.windows.push(row);
        }

        private function applyFrame():void {
            var at:int=getTimer();
            var target:Object=row.moving?route[age]:views[0];
            var point:Object={x:row.condition==2?views[0].x:target.x,y:row.condition==1?views[0].y:target.y};
            require(plannedSegment==segment && plannedAge==age,"Native schedule was not consumed at the intended sample");
            require(cam.X==point.x && cam.Y==point.y,"Native camera did not consume the scheduled target");
            ++report.nativeCaptures;
            require(grafon.sceneViewReady(),"Unprepared viewport during timing");
            require(world.visual.visible===true,"World visibility changed");
            checkTransform();guard();
            var px:Number=player.X+cam.vx,py:Number=player.Y+cam.vy;
            require(px>=50 && px<stage.stageWidth-50 && py>=120 && py<stage.stageHeight-50,"Player outside verified camera view");
            require(cam.vx==-(point.x-stage.stageWidth/2) && cam.vy==-(point.y-stage.stageHeight/2-100),"Room camera clamped during reference route");
            pending={vx:cam.vx,vy:cam.vy,x:cam.X,y:cam.Y,gg:playerState(),scene:counters(),workMs:getTimer()-at,worldVisible:world.visual.visible,windowVisible:stage.nativeWindow.visible};
        }

        private function beforeNative(event:Event):void {
            if(closed || (phase!=31 && phase!=3))return;
            try {
                require(event.currentTarget===stage,"Wrong native camera event source");
                var nextSegment:int=segment,nextAge:int=phase==31?0:age+1;
                if(nextAge==120) {
                    if(nextSegment+1<order.length){++nextSegment;nextAge=0;}
                    else nextAge=119; // Final interval still includes one native update.
                }
                var condition:int=order[nextSegment];
                var target:Object=condition==0?views[0]:route[nextAge];
                var x:Number=condition==2?views[0].x:target.x;
                var y:Number=condition==1?views[0].y:target.y;
                require(x==Math.floor(x) && y==Math.floor(y),"Non-integer scheduled camera");
                cam.X=x;cam.Y=y;cam.camRun=true;cam.quakeX=0;cam.quakeY=0;
                world.ctr.keyLook=false;world.ctr.keyZoom=false;
                plannedSegment=nextSegment;plannedAge=nextAge;++report.nativeSchedules;
            } catch(error:Error) {fail(error);}
        }

        private function applyCamera(x:Number,y:Number):void {
            if(phase==31 || phase==3) {
                ++report.helperTimedCalcCalls;
                throw new Error("Extra helper Camera.calc during native-only measurement");
            }
            require(x==Math.floor(x) && y==Math.floor(y),"Non-integer camera route");
            cam.X=x;cam.Y=y;cam.camRun=true;cam.quakeX=0;cam.quakeY=0;
            world.ctr.keyLook=false;world.ctr.keyZoom=false;
            cam.calc(player); // Accurate host calc includes exactly one native sceneTick.
            require(cam.X==x && cam.Y==y,"Native camera changed the supplied look target");
            checkTransform();
        }

        private function checkTransform():void {
            require(Number(cam.scaleV)==1 && cam.quakeX==0 && cam.quakeY==0,"Unsupported scale/shake");
            require(cam.screenX==stage.stageWidth && cam.screenY==stage.stageHeight,"Viewport resized");
            var m:Matrix=world.visual.transform.concatenatedMatrix;
            require(m.a==1 && m.d==1 && m.b==0 && m.c==0 && m.tx==Math.floor(m.tx) && m.ty==Math.floor(m.ty),"World-to-Stage transform not unit/integer");
            require(sameMatrix(world.visual.transform.matrix,world.sats.vis.transform.matrix),"SATS camera transform differs");
            require(world.visual.x==cam.vx && world.visual.y==cam.vy,"Native translation differs");
        }

        private function pixelCase(point:Object,index:int):void {
            var at:int=getTimer(),result:Object={index:index,x:point.x,y:point.y,passed:false};
            report.pixels.push(result);
            try {
                require(world.visual.visible===true,"World must remain visible");applyCamera(point.x,point.y);
                require(grafon.sceneViewReady(),"Pixel viewport not prepared");
                var a:BitmapData=capture(),b:BitmapData=capture();
                result.fog=fogState();result.visibleCoverage=coverage(a);savePNG("reference-"+index+".png",a);
                require(result.visibleCoverage.fraction>=0.30,"Reference camera has insufficient visible world content");
                result.nativeRepeat=compare(a,b);result.passed=result.nativeRepeat.equal;
                require(result.passed,"Native consecutive captures changed");
            } finally {disposeOwned();result.elapsedMs=getTimer()-at;}
        }

        private function capture():BitmapData {
            var bitmap:BitmapData=new BitmapData(stage.stageWidth,stage.stageHeight,true,0);
            owned.push(bitmap);++report.pixelBitmapsCreated;
            report.pixelBufferPeakBytes=Math.max(report.pixelBufferPeakBytes,owned.length*stage.stageWidth*stage.stageHeight*4);
            bitmap.draw(stage);return bitmap;
        }
        private function compare(a:BitmapData,b:BitmapData):Object {
            var left:Vector.<uint>=a.getVector(a.rect);var right:Vector.<uint>=b.getVector(b.rect);
            var count:int=0;var alpha:int=0;var maxRGB:int=0;
            for(var i:int=0;i<left.length;++i)if(left[i]!=right[i]) {
                ++count;var x:uint=left[i];var y:uint=right[i];
                alpha=Math.max(alpha,Math.abs(int(x>>>24)-int(y>>>24)));
                maxRGB=Math.max(maxRGB,Math.abs(int(x>>>16&255)-int(y>>>16&255)),Math.abs(int(x>>>8&255)-int(y>>>8&255)),Math.abs(int(x&255)-int(y&255)));
            }
            left=null;right=null;
            return {equal:count==0,differentPixels:count,maxAlpha:alpha,maxRGB:maxRGB,pixels:a.width*a.height};
        }
        private function guard():void {
            require(world.cam===cam && world.grafon===grafon && world.gg===player && world.loc===location && world.main.stage===stage,"World identities changed");
            require(world.onPause===false && world.allStat==1 && world.t_exit==0 && stage.frameRate==120,"Active runtime state changed");
            require(stage.nativeWindow.visible===true,"Owned window visibility changed during diagnosis");
            quietGuard();
        }
        private function stripHostiles():void {
            var removed:Array=[],objects:int=0,seen:int=0;
            for each(var unit:* in location.units.concat()) {
                if(!unit || unit===player || unit.player || unit.npc || unit.fraction<=0 || unit.fraction>=100 || unit.fraction==player.fraction)continue;
                var detail:Object={className:getQualifiedClassName(unit),x:unit.X,y:unit.Y,fraction:unit.fraction,wasInChain:Boolean(unit.in_chain)};
                unit.disabled=true;unit.remVisual();location.remObj(unit);
                var index:int=location.units.indexOf(unit);require(index>=0,"Quiet actor array changed during removal");location.units.splice(index,1);
                require(!unit.vis || unit.vis.stage==null,"Removed actor visual remains on Stage");
                if("hpbar" in unit && unit.hpbar)require(unit.hpbar.stage==null,"Removed actor HP bar remains on Stage");
                removed.push(detail);
            }
            var Bullet:Class=getDefinitionByName("fe.weapon.Bullet") as Class,obj:*=location.firstObj;
            while(obj!=null) {
                require(++seen<50000,"Object chain cycle during quiet fixture setup");
                var next:*=obj.nobj;
                if(obj is Bullet) {obj.off=true;obj.remVisual();location.remObj(obj);++objects;}
                obj=next;
            }
            world.ctr.clearAll();
            report.quietFixture={removedHostiles:removed,removedProjectiles:objects,terminalPopulationChange:true,
                nativeSimulationPaused:false,hostileChecks:0,remainingUnits:location.units.length,
                limitation:"Private diagnostic population only; no death/loot callbacks and no actor restoration. Camera is scripted, not a player jump."};
            report.simulationTicks=0;
        }
        private function quietGuard():void {
            var hostile:int=0;
            for each(var unit:* in location.units)if(unit && unit!==player && !unit.player && !unit.npc && unit.fraction>0 && unit.fraction<100 && unit.fraction!=player.fraction && unit.sost==1)++hostile;
            ++report.quietFixture.hostileChecks;
            require(hostile==0,"Hostile actor entered quiet camera fixture");
            require(world.onPause===false && world.allStat==1 && world.t_exit==0,"Quiet simulation stopped");
            require(isFinite(player.X+player.Y+player.dx+player.dy+player.hp) && player.hp>0,"Quiet player became invalid");
            require(world.gg===player && world.loc===location,"Quiet identities changed");
        }
        private function playerState():Object {return {x:player.X,y:player.Y,dx:player.dx,dy:player.dy,hp:player.hp,stay:player.stay};}
        private function samePlayer(a:Object,b:Object):Boolean {return a.x===b.x && a.y===b.y && a.dx===b.dx && a.dy===b.dy && a.hp===b.hp && a.stay===b.stay;}
        private function counters():Object {
            var value:Object={};for each(var name:String in COUNTERS)if(name in grafon)value[name]=grafon[name];return value;
        }
        private function snapshot():Object {return {atMs:getTimer(),pause:world.onPause,camera:fields(cam,CAMERA),gg:playerState(),scene:counters(),copies:presenter.copies,allocated:presenter.allocated,memoryBytes:System.totalMemory};}
        private function rememberTiles():void {
            for each(var surface:Object in grafon.sceneSurfaces())for(var i:int=0;i<4;++i) {
                var b:Bitmap=surface.bitmaps[i];
                require(b.bitmapData===surface.nativeBuffers[i],"Presenter was already applied");
                originalTiles.push({bitmap:b,data:b.bitmapData,parent:b.parent,visible:b.visible,smoothing:b.smoothing,pixelSnapping:b.pixelSnapping,scrollRect:b.scrollRect});
            }
        }
        private function checkNativeBindings():void {
            for each(var surface:Object in grafon.sceneSurfaces())for(var i:int=0;i<4;++i) {
                var b:Bitmap=surface.bitmaps[i];var r:Rectangle=b.scrollRect;
                require(b.bitmapData===surface.nativeBuffers[i] && r!=null && r.x==surface.gutter && r.y==surface.gutter && r.width==surface.side && r.height==surface.side,"Native buffer binding/crop not restored");
            }
        }
        private function saveDisplay(d:DisplayObject):void {require(d!=null,"Missing camera display");displays.push({target:d,matrix:d.transform.matrix.clone()});}
        private function fields(target:*,names:Array):Object {var value:Object={};for each(var name:String in names)value[name]=target[name];return value;}
        private function plain(target:Object):Object {var value:Object={};for(var name:String in target)value[name]=target[name];return value;}
        private function assign(target:*,values:Object):void {for(var name:String in values)target[name]=values[name];}
        private function sameFields(target:*,values:Object):Boolean {for(var name:String in values)if(target[name]!==values[name])return false;return true;}
        private function sameMatrix(a:Matrix,b:Matrix):Boolean {return a.a===b.a && a.b===b.b && a.c===b.c && a.d===b.d && a.tx===b.tx && a.ty===b.ty;}
        private function disposeOwned():void {
            while(owned.length) {
                var bitmap:BitmapData=owned.pop();
                try {bitmap.dispose();++report.pixelBitmapsDisposed;}
                catch(error:Error){report.pixelDisposeErrors.push(error.message);}
            }
        }
        private function require(ok:Boolean,message:String):void {if(!ok)throw new Error(message);}
        private function fail(error:Error):void {report.errors.push(error.message);report.passed=false;report.complete=false;clear(world);}
    }
}
