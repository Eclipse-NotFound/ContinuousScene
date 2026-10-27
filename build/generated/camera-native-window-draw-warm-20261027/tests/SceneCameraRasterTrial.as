package tests {
    import flash.desktop.NativeApplication;
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.display.DisplayObject;
    import flash.display.Stage;
    import flash.display.PNGEncoderOptions;
    import flash.filesystem.File;
    import flash.filesystem.FileMode;
    import flash.filesystem.FileStream;
    import flash.display.NativeWindow;
    import flash.display.NativeWindowInitOptions;
    import flash.display.NativeWindowSystemChrome;
    import flash.geom.Matrix;
    import flash.geom.Rectangle;
    import flash.system.System;
    import flash.utils.getQualifiedClassName;
    import flash.utils.getTimer;

    /** Terminal, paused-world attribution. Not a combat or gameplay acceptance test. */
    public class SceneCameraRasterTrial {
        private var world:*;
        private var cam:*;
        private var grafon:*;
        private var player:*;
        private var location:*;
        private var presenter:*;
        private var stage:Stage;
        private var originalStage:Stage;
        private var stages:Array=[];
        private var stageRoots:Array=[];
        private var extraWindows:Array=[];
        private var nativeMode:int=0;
        private var closeWait:int=0;
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
        private var order:Array=[0,1,2,3,4,5,5,4,3,2,1,0];
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
        private const CAMERA:Array=["moved","screenX","screenY","X","Y","vx","vy","ovy","maxsx","maxsy","maxvx","maxvy","celX","celY","camRun","otryv","quakeX","quakeY","isZoom","scaleV","scaleS","dblack","showOn","showX","showY"];
        private const COUNTERS:Array=["sceneRedraws","sceneDrawMs","sceneMaxDrawMs","sceneResident","sceneEvictions","sceneMisses","sceneWarmCount","sceneWarmSlices","sceneWarmForced","sceneLastDirtyCount"];

        public function begin(w:*,p:*):Object {
            if(report!=null)throw new Error("Camera raster trial is single-use");
            beginAt=getTimer();
            report={version:"camera-native-window-draw-warm-1",diagnosticOnly:true,performanceEligible:false,
                terminalOnly:true,complete:false,passed:false,pixelsValid:false,errors:[],pixels:[],windows:[],
                framesMs:[],sampleAtMs:[],prepareMs:0,prepareWorkMs:0,pixelMs:0,
                pixelBitmapsCreated:0,pixelBitmapsDisposed:0,pixelDisposeErrors:[],pixelBufferPeakBytes:0,measurementFrames:1440,
                intervalMeaning:"Applied camera/crop work, next actual frame presentation, then next step entry. No segment-clock resets.",
                limits:["World.onPause stops simulation; Flash timelines and other frame callbacks remain live.",
                    "120fps diagnostic changes timeline speed; these intervals are not gameplay FPS.",
                    "Scale 1, zero shake, integer world-to-Stage translation only.",
                    "Same world and animation tree is reparented between native windows; transfers can invoke stage lifecycle callbacks.",
                    "This is not an enemy-free gameplay run: simulation is paused, while timelines and other callbacks can continue.",
                    "Native prewarmed caches/counters remain resident; no simulated objects are moved or removed.",
                    "Final end snapshot and cleanup are outside the last measured interval."]};
            world=w;presenter=p;report.nativeWindows=[];report.stageSwitches=[];report.windowPixelsNotCaptured=true;
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
                require(w.mm!=null && w.mm.active===false,"Main menu must be inactive");
                report.nativeMenuChildren=[];
                for(var menuChild:int=0;menuChild<w.main.numChildren;++menuChild) {
                    var menuClass:String=getQualifiedClassName(w.main.getChildAt(menuChild));
                    report.nativeMenuChildren.push({className:menuClass,visible:w.main.getChildAt(menuChild).visible});
                    require(menuClass!="visMainMenu","Actual native menu shutdown required");
                }
                report.airRenderMode=stage.nativeWindow.renderMode;
                report.windowPixelsNotCaptured=true;
                originalStage=stage;
                stages=[stage];
                for(var rootIndex:int=0;rootIndex<stage.numChildren;++rootIndex)stageRoots.push(stage.getChildAt(rootIndex));
                require(stageRoots.length>0,"No Stage roots");
                report.originalRootClasses=[];
                for each(var root:DisplayObject in stageRoots)report.originalRootClasses.push(getQualifiedClassName(root));
                stage.nativeWindow.visible=true;
                require(stage.nativeWindow.visible===true,"Owned private window did not become visible");
                report.originalFrameRate=saved.frameRate;report.testFrameRate=120;
                report.stage={width:stage.stageWidth,height:stage.stageHeight,quality:stage.quality};
                report.initial=snapshot();
                report.originalZoom=cam.scaleV;
                cam.setZoom(0);
                require(Number(cam.scaleV)==1,"Native unit zoom selection failed");
                report.testZoom=cam.scaleV;
                require(cam.screenX==stage.stageWidth && cam.screenY==stage.stageHeight,"Stage/camera size mismatch");
                w.onPause=true;
                require(w.onPause===true && w.gg===player && w.loc===location,"Pause was not applied");
                stage.frameRate=120;require(stage.frameRate==120,"120fps setting not accepted");
                cam.camRun=true;cam.quakeX=0;cam.quakeY=0;cam.otryv=0;cam.showOn=false;cam.dblack=0;
                w.ctr.keyLook=false;w.ctr.keyZoom=false;
                makeNativeWindows();makeRoute();
                report.views=views;report.route=route;
                prepareRoute=views.concat(route);prepareAt=getTimer();
                report.prepareStart=snapshot();
                prepareBaseline=counters();report.preparePasses=[];
            } catch(error:Error) {fail(error);}
            return report;
        }

        public function step(w:*):Boolean {
            if(closed)return finishOwnedClose();
            try {
                require(w===world,"World argument replaced");guard();
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
                    switchNativeWindow(0);pixelCase(views[cursor],cursor);++cursor;
                    if(cursor==views.length) {
                        report.pixelMs=getTimer()-pixelAt;
                        report.pixelsValid=true;
                        presenter.clear();applyCamera(views[0].x,views[0].y);
                        phase=2;settle=0;
                    }
                } else if(phase==2) {
                    applyCamera(views[0].x,views[0].y);
                    require(grafon.sceneViewReady(),"Prepared view became incomplete");
                    if(++settle==12) {
                        report.stabilizationFrames=settle;report.timingStart=snapshot();
                        phase=3;previous=getTimer();report.timingStartAtMs=previous;
                        startWindow();applyFrame();
                    }
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
                    row.nativeMode.push(pending.nativeMode);row.renderer.push(pending.renderer);row.workMs.push(pending.workMs);row.worldVisible.push(pending.worldVisible);row.windowVisible.push(pending.windowVisible);
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
                            report.complete=true;report.passed=true;clear(w);
                        } else {startWindow();applyFrame();}
                    } else applyFrame();
                }
            } catch(error:Error) {fail(error);}
            return closed && finishOwnedClose();
        }

        public function clear(w:*):Object {
            if(closed)return report!=null?report.cleanup:{restored:true,notStarted:true};
            closed=true;
            var at:int=getTimer();
            var cleanup:Object={restored:true,errors:[],nativeCachesRetained:true,pendingOwnedBitmaps:0};
            try {if(presenter!=null)presenter.clear();} catch(e0:Error){cleanup.errors.push("presenter: "+e0.message);}
            disposeOwned();
            if(saved!=null && saved.ready) {
                try {switchNativeWindow(0);}
                catch(stageRestore:Error){cleanup.errors.push("Stage restore: "+stageRestore.message);}
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
                    require(samePlayer(playerState(),saved.gg),"Player simulation changed while paused");
                    require(world.visual.visible===saved.worldVisible && stage.nativeWindow.visible===saved.nativeWindowVisible,"World/window visibility restore mismatch");
                    for each(display in displays)require(sameMatrix(display.target.transform.matrix,display.matrix),"Display transform restore mismatch");
                    require(world.celX===saved.celX && world.celY===saved.celY && world.ctr.keyLook===saved.look && world.ctr.keyZoom===saved.zoom,"Controller/aim restore mismatch");
                    require(world.vblack.visible===saved.blackVisible && world.vblack.alpha===saved.blackAlpha,"Black overlay restore mismatch");
                    require(snd[new QName("","centrX")]===saved.sndX && snd[new QName("","centrY")]===saved.sndY,"Sound center restore mismatch");
                    require(api.hasOwnProperty("verticalCameraState")===saved.hasState && (!saved.hasState || api["verticalCameraState"]===saved.state),"Camera API identity restore mismatch");
                    if(saved.stateFields!=null)require(sameFields(saved.state,saved.stateFields),"Camera API fields restore mismatch");
                } catch(e8:Error){cleanup.errors.push("verify: "+e8.message);}
            }
            cleanup.ownedWindowsCreated=extraWindows.length;cleanup.ownedWindowsClosed=0;
            for each(var extra:NativeWindow in extraWindows)try {
                require(extra.stage.numChildren==0,"Owned window still contains native roots");
                extra.close();if(extra.closed)++cleanup.ownedWindowsClosed;
            }catch(windowClose:Error){cleanup.errors.push("Window close: "+windowClose.message);}
            if(originalStage!=null)try {
                require(stage===originalStage && world.swfStage===originalStage && world.main.stage===originalStage,"Original Stage not restored");
                require(originalStage.numChildren==stageRoots.length,"Original Stage root count mismatch");
                for(var restoreRoot:int=0;restoreRoot<stageRoots.length;++restoreRoot)
                    require(originalStage.getChildAt(restoreRoot)===stageRoots[restoreRoot],"Original Stage root order mismatch");
            }catch(rootRestore:Error){cleanup.errors.push("Stage roots: "+rootRestore.message);}
            cleanup.pendingOwnedBitmaps=owned.length;cleanup.elapsedMs=getTimer()-at;
            if(report.pixelDisposeErrors.length)cleanup.errors.push("Owned pixel bitmap disposal failed");
            cleanup.restored=cleanup.errors.length==0 && owned.length==0;
            report.cleanup=cleanup;report.elapsedMs=getTimer()-beginAt;
            if(!cleanup.restored){report.passed=false;report.errors.push("Cleanup failed");}
            return cleanup;
        }

        private function finishOwnedClose():Boolean {
            if(report==null || report.cleanup==null)return true;
            var total:int=0;
            for each(var window:NativeWindow in extraWindows)if(window.closed)++total;
            report.cleanup.ownedWindowsClosed=total;
            if(total==extraWindows.length)return true;
            if(++closeWait<60)return false;
            report.cleanup.errors.push("Owned windows did not close after 60 frame callbacks");
            report.cleanup.restored=false;report.passed=false;report.complete=false;
            report.errors.push("Deferred close failed");return true;
        }

        private function savePNG(b:BitmapData,name:String):void {
            var path:File=File.applicationStorageDirectory.resolvePath(name);
            var stream:FileStream=new FileStream();
            try {stream.open(path,FileMode.WRITE);stream.writeBytes(b.encode(b.rect,new PNGEncoderOptions()));}
            finally {stream.close();}
        }

        private function makeNativeWindows():void {
            report.nativeWindows.push({index:0,renderer:stage.nativeWindow.renderMode,width:stage.stageWidth,height:stage.stageHeight,quality:stage.quality});
            require(stage.nativeWindow.renderMode=="direct","Original window must be direct");
            for each(var renderer:String in ["direct","auto"]) {
                var options:NativeWindowInitOptions=new NativeWindowInitOptions();
                options.renderMode=renderer;options.systemChrome=NativeWindowSystemChrome.NONE;
                options.transparent=false;options.resizable=false;options.minimizable=false;options.maximizable=false;
                var window:NativeWindow=new NativeWindow(options);
                extraWindows.push(window);
                window.title=NativeApplication.nativeApplication.applicationID+"-native-"+renderer;
                window.width=originalStage.stageWidth;window.height=originalStage.stageHeight;
                window.x=originalStage.nativeWindow.x;window.y=originalStage.nativeWindow.y;
                var target:Stage=window.stage;stages.push(target);
                target.scaleMode=originalStage.scaleMode;target.align=originalStage.align;
                target.quality=originalStage.quality;target.color=originalStage.color;target.frameRate=120;
                require(target.stageWidth==originalStage.stageWidth && target.stageHeight==originalStage.stageHeight,"New Stage size differs");
                require(window.renderMode==renderer,"Requested native renderer not accepted");
                report.nativeWindows.push({index:stages.length-1,renderer:window.renderMode,width:target.stageWidth,height:target.stageHeight,quality:target.quality});
            }
        }

        private function switchNativeWindow(index:int):void {
            if(originalStage==null)return;
            require(index>=0 && index<stages.length,"Invalid native window index");
            var target:Stage=stages[index];if(stage===target)return;
            var source:Stage=stage,at:int=getTimer(),count:int=stageRoots.length;
            require(source.numChildren==count && target.numChildren==0,"Unexpected Stage children before transfer");
            var matrices:Array=[],frames:Array=[];
            for(var i:int=0;i<count;++i) {
                var root:DisplayObject=stageRoots[i];
                require(source.getChildAt(i)===root,"Stage root order changed");
                matrices.push(root.transform.matrix.clone());
            }
            for(i=0;i<count;++i)target.addChild(stageRoots[i]);
            world.swfStage=target;stage=target;nativeMode=index;
            source.nativeWindow.visible=false;target.nativeWindow.visible=true;
            require(source.numChildren==0 && target.numChildren==count && world.main.stage===target,"Stage transfer failed");
            require(stage.stageWidth==2032 && stage.stageHeight==1084 && stage.quality===report.stage.quality,"Stage properties changed");
            for(i=0;i<count;++i)require(target.getChildAt(i)===stageRoots[i] && sameMatrix(stageRoots[i].transform.matrix,matrices[i]),"Root matrix/order changed");
            report.stageSwitches.push({index:index,atMs:at,workMs:getTimer()-at,renderer:stage.nativeWindow.renderMode,rootCount:count});
        }

        private function makeRoute():void {
            require(stage.stageWidth==2032 && stage.stageHeight==1084,"Native window comparison requires 2032x1084 content");
            var offsetX:int=grafon.sceneLarge?3840:0,offsetY:int=grafon.sceneLarge?4000:0;
            require(grafon.sceneLarge?(location.spaceX==240 && location.spaceY==125):
                (location.spaceX==48 && location.spaceY==25),"Unexpected matched room dimensions");
            var x:int=offsetX+960,y:int=offsetY+400;
            views=[{x:x,y:y},{x:x+120,y:y},{x:x,y:y+48},{x:x-120,y:y-48},{x:x+120,y:y+48}];
            for(var leg:int=0;leg<5;++leg) {
                var a:Object=views[leg],b:Object=views[(leg+1)%5];
                for(var i:int=0;i<24;++i)route.push({x:a.x+(b.x-a.x)*i/24,y:a.y+(b.y-a.y)*i/24});
            }
            report.roomAxis={continuous:grafon.sceneLarge,offsetX:offsetX,offsetY:offsetY,
                localCenterX:960,localCenterY:400,roomGridX:2,roomGridY:4,roomWidth:1920,roomHeight:1000};
            report.routeTranslationOnly=true;report.playerMovedByHelper=false;report.prepareCalls=0;
        }

        private function startWindow():void {
            var condition:int=order[segment];age=0;switchNativeWindow(int(condition/2));
            row={index:segment,condition:condition,mode:["original-static","original-moving","direct-static","direct-moving","auto-static","auto-moving"][condition],
                hidden:false,moving:condition%2==1,startAtMs:previous,
                framesMs:[],sampleAtMs:[],vx:[],vy:[],cameraX:[],cameraY:[],gg:[],scene:[],workMs:[],
                worldVisible:[],windowVisible:[],nativeMode:[],renderer:[],start:snapshot(),copiesStart:presenter.copies,allocatedStart:presenter.allocated};
            report.windows.push(row);
        }

        private function applyFrame():void {
            var at:int=getTimer();
            var target:Object=row.moving?route[age]:views[0];
            var point:Object=target;
            applyCamera(point.x,point.y);
            require(grafon.sceneViewReady(),"Unprepared viewport during timing");
            require(world.visual.visible===true,"World visibility changed");
            checkTransform();guard();
            pending={nativeMode:nativeMode,renderer:stage.nativeWindow.renderMode,vx:cam.vx,vy:cam.vy,x:cam.X,y:cam.Y,gg:playerState(),scene:counters(),workMs:getTimer()-at,worldVisible:world.visual.visible,windowVisible:stage.nativeWindow.visible};
        }

        private function applyCamera(x:Number,y:Number):void {
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
                // One fixed warm roundtrip per camera position. Do not retry until passing.
                var warmInitial:BitmapData=capture();result.fixedWarmDraws=[];
                for each(var warmMode:int in [1,2,0]) {
                    switchNativeWindow(warmMode);
                    var warmImage:BitmapData=capture();result.fixedWarmDraws.push({mode:warmMode,change:compare(warmInitial,warmImage)});
                }
                disposeOwned();
                result.roundtrips=[];
                for(var pass:int=0;pass<3;++pass) {
                    var a:BitmapData=capture(),b:BitmapData=capture();
                    var trip:Object={index:pass,nativeRepeat:compare(a,b)};result.roundtrips.push(trip);
                    switchNativeWindow(1);var d:BitmapData=capture();trip.newDirect=compare(a,d);
                    switchNativeWindow(2);var c:BitmapData=capture();trip.newAuto=compare(a,c);
                    switchNativeWindow(0);var back:BitmapData=capture();trip.restored=compare(a,back);
                    if(index==0 && pass==0) {
                        savePNG(a,"window-original.png");savePNG(d,"window-direct.png");
                        savePNG(c,"window-auto.png");savePNG(back,"window-restored.png");
                    }
                    trip.passed=trip.nativeRepeat.equal && trip.newDirect.equal && trip.newAuto.equal && trip.restored.equal;
                    result.nativeRepeat=trip.nativeRepeat;result.newDirect=trip.newDirect;
                    result.newAuto=trip.newAuto;result.restored=trip.restored;
                    disposeOwned();
                    require(trip.passed,"Warm same-world Stage transfer changed software pixels");
                }
                result.passed=true;
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
            require(world.cam===cam && world.grafon===grafon && world.gg===player && world.loc===location && world.main.stage===stage && world.swfStage===stage,"World identities changed");
            require(world.onPause===true && world.allStat==1 && world.t_exit==0 && stage.frameRate==120,"Pause/runtime state changed");
            require(stage.nativeWindow.visible===true,"Owned window visibility changed during diagnosis");
            require(samePlayer(playerState(),saved.gg),"Player position/velocity/HP changed during paused attribution");
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
