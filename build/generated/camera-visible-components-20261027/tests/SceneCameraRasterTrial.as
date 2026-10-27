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
        private var componentTargets:Array=[];
        private var componentMode:int=0;
        private const COMPONENTS:Array=["native","no-light","no-terrain","no-decor","no-actors","no-backdrop","no-gui","no-world"];
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
        private var order:Array=[0,4,0,8,0,12,0,16,0,20,0,24,0,28,1,5,1,9,1,13,1,17,1,21,1,25,1,29,2,6,2,10,2,14,2,18,2,22,2,26,2,30,3,7,3,11,3,15,3,19,3,23,3,27,3,31,31,3,27,3,23,3,19,3,15,3,11,3,7,3,30,2,26,2,22,2,18,2,14,2,10,2,6,2,29,1,25,1,21,1,17,1,13,1,9,1,5,1,28,0,24,0,20,0,16,0,12,0,8,0,4,0];
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
            report={version:"camera-visible-components-1",diagnosticOnly:true,performanceEligible:false,
                terminalOnly:true,complete:false,passed:false,pixelsValid:false,errors:[],pixels:[],windows:[],
                framesMs:[],sampleAtMs:[],prepareMs:0,prepareWorkMs:0,pixelMs:0,
                pixelBitmapsCreated:0,pixelBitmapsDisposed:0,pixelDisposeErrors:[],pixelBufferPeakBytes:0,measurementFrames:6720,
                intervalMeaning:"Applied camera/crop work, next actual frame presentation, then next step entry. No segment-clock resets.",
                limits:["Native simulation remains active; hostile actors and existing projectiles are removed only in this private fixture.",
                    "120fps diagnostic; native simulation and Flash callbacks continue, not ordinary gameplay FPS.",
                    "The same native camera script replays horizontal/vertical/combined paths in each map mode.",
                    "No player teleport during measurement; this is not a natural jump test.",
                    "Camera/cache restoration is checked; deliberately removed fixture enemies are not restored.",
                    "Visibility omissions are diagnostic controls, not optimizations; all intervals and switch costs retained."]};
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
                initComponents();
                stripHostiles();
                stage.frameRate=120;require(stage.frameRate==120,"120fps setting not accepted");
                cam.camRun=true;cam.quakeX=0;cam.quakeY=0;cam.otryv=0;cam.showOn=false;cam.dblack=0;
                w.ctr.keyLook=false;w.ctr.keyZoom=false;
                makeRoute();
                report.views=views;report.route=route;
                prepareRoute=views.concat(route);prepareAt=getTimer();
                report.prepareStart=snapshot();
                prepareBaseline=counters();report.preparePasses=[];
            } catch(error:Error) {fail(error);}
            return report;
        }

        public function step(w:*):Boolean {
            if(closed)return true;
            try {
                require(w===world,"World argument replaced");guard();++report.simulationTicks;
                require(getTimer()-beginAt<420000,"Camera raster timeout");
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
                    row.workMs.push(pending.workMs);row.worldVisible.push(pending.worldVisible);row.windowVisible.push(pending.windowVisible);
                    ++age;
                    if(age==60) {
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
            return closed;
        }

        public function clear(w:*):Object {
            if(closed)return report!=null?report.cleanup:{restored:true,notStarted:true};
            closed=true;
            var at:int=getTimer();
            var cleanup:Object={restored:true,errors:[],nativeCachesRetained:true,pendingOwnedBitmaps:0};
            try {if(presenter!=null)presenter.clear();} catch(e0:Error){cleanup.errors.push("presenter: "+e0.message);}
            disposeOwned();
            if(stage)stage.removeEventListener(Event.EXIT_FRAME,onComponentExit);
            try {applyComponent(0);checkComponents();cleanup.componentsRestored=true;} catch(componentError:Error){cleanup.componentsRestored=false;cleanup.errors.push("component restore: "+componentError.message);}
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
            cleanup.pendingOwnedBitmaps=owned.length;cleanup.elapsedMs=getTimer()-at;cleanup.fixturePopulationNotRestored=true;
            if(report.pixelDisposeErrors.length)cleanup.errors.push("Owned pixel bitmap disposal failed");
            cleanup.restored=cleanup.errors.length==0 && owned.length==0;
            report.cleanup=cleanup;report.elapsedMs=getTimer()-beginAt;
            if(!cleanup.restored){report.passed=false;report.errors.push("Cleanup failed");}
            return cleanup;
        }

        private function makeRoute():void {
            require(stage.stageWidth==1920 && stage.stageHeight==1080,"Component diagnosis requires 1920x1080 content");
            var offsetX:int=grafon.sceneLarge?3840:0,offsetY:int=grafon.sceneLarge?4000:0;
            require(grafon.sceneLarge?(location.spaceX==240 && location.spaceY==125):
                (location.spaceX==48 && location.spaceY==25),"Unexpected matched room dimensions");
            var x:int=Math.round(player.X),y:int=Math.round(player.Y);
            report.cameraRouteFollowsInitialPlayer=true;
            views=[{x:x,y:y},{x:x+120,y:y},{x:x,y:y+48},{x:x-120,y:y-48},{x:x+120,y:y+48}];
            for(var leg:int=0;leg<5;++leg) {
                var a:Object=views[leg],b:Object=views[(leg+1)%5];
                for(var i:int=0;i<24;++i)route.push({x:a.x+(b.x-a.x)*i/24,y:a.y+(b.y-a.y)*i/24});
            }
            report.roomAxis={continuous:grafon.sceneLarge,offsetX:offsetX,offsetY:offsetY,
                localCenterX:x-offsetX,localCenterY:y-offsetY,roomGridX:2,roomGridY:4,roomWidth:1920,roomHeight:1000};
            report.routeTranslationOnly=true;report.playerMovedByHelper=false;report.prepareCalls=0;
        }

        private function startWindow():void {
            var code:int=order[segment],condition:int=code%4,component:int=int(code/4);age=0;
            row={index:segment,code:code,component:component,condition:condition,mode:COMPONENTS[component]+"-"+["static","horizontal","vertical","combined"][condition],
                exitChecks:0,hidden:component==7,moving:condition!=0,startAtMs:previous,
                framesMs:[],sampleAtMs:[],vx:[],vy:[],cameraX:[],cameraY:[],gg:[],scene:[],workMs:[],
                worldVisible:[],windowVisible:[],start:snapshot(),copiesStart:presenter.copies,allocatedStart:presenter.allocated};
            report.windows.push(row);
        }

        private function applyFrame():void {
            var at:int=getTimer();
            var target:Object=row.moving?route[age*2]:views[0];
            var point:Object={x:row.condition==2?views[0].x:target.x,y:row.condition==1?views[0].y:target.y};
            applyCamera(point.x,point.y);
            require(grafon.sceneViewReady(),"Unprepared viewport during timing");
            applyComponent(row.component);checkComponents();
            checkTransform();guard();
            pending={vx:cam.vx,vy:cam.vy,x:cam.X,y:cam.Y,gg:playerState(),scene:counters(),workMs:getTimer()-at,worldVisible:world.visual.visible,windowVisible:stage.nativeWindow.visible};
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
            var at:int=getTimer(),result:Object={index:index,x:point.x,y:point.y,passed:false,controls:[]};
            report.pixels.push(result);
            try {
                applyComponent(0);applyCamera(point.x,point.y);checkComponents();
                require(grafon.sceneViewReady(),"Pixel viewport not prepared");
                var a:BitmapData=capture(),repeat:BitmapData=capture();
                result.nativeRepeat=compare(a,repeat);releaseSnapshot(repeat);
                require(result.nativeRepeat.equal,"Native repeated image differs");
                result.visibleCoverage=coverage(a);savePNG("components-native-"+index+".png",a);
                require(result.visibleCoverage.fraction>=0.15,"Mostly black camera viewport");
                for(var mode:int=1;mode<COMPONENTS.length;++mode) {
                    applyComponent(mode);checkComponents();var changed:BitmapData=capture();
                    var entry:Object={component:mode,name:COMPONENTS[mode],changed:compare(a,changed)};
                    if(index==0)savePNG("components-"+COMPONENTS[mode]+".png",changed);
                    releaseSnapshot(changed);
                    applyComponent(0);checkComponents();var restored:BitmapData=capture();
                    entry.restore=compare(a,restored);releaseSnapshot(restored);result.controls.push(entry);
                    require(entry.restore.equal,"Component restore differs");
                }
                result.passed=true;
            } finally {applyComponent(0);disposeOwned();result.elapsedMs=getTimer()-at;}
        }
        private function releaseSnapshot(b:BitmapData):void {
            var index:int=owned.indexOf(b);require(index>=0,"Unknown pixel bitmap");
            b.dispose();owned.splice(index,1);++report.pixelBitmapsDisposed;
        }
        private function initComponents():void {
            report.components={targets:[],visibilityWrites:0,applyCalls:0,checks:0,exitChecks:0,mode:0};
            addComponent(world.visual,"world",7);
            addComponent(grafon.visLight,"light",1);
            for each(var name:String in ["visBack","visBack2","visFront","visVoda"])addComponent(grafon[name],name,2);
            for each(var layer:int in [0,1,3])addComponent(grafon.visObjs[layer],"objects-"+layer,3);
            for each(layer in [2,4,5])addComponent(grafon.visObjs[layer],"objects-"+layer,4);
            addComponent(grafon.visFon,"backdrop",5);
            var gui:DisplayObject=null;
            for(var i:int=0;i<world.main.numChildren;++i)if(getQualifiedClassName(world.main.getChildAt(i))=="visualGUI") {
                require(gui==null,"Duplicate native GUI");gui=world.main.getChildAt(i);
            }
            require(gui!=null,"Missing native GUI");addComponent(gui,"native-gui",6);
            require(componentTargets.length==14,"Wrong component target count");
            stage.addEventListener(Event.EXIT_FRAME,onComponentExit,false,int.MIN_VALUE);
        }
        private function addComponent(d:DisplayObject,name:String,mode:int):void {
            require(d!=null && d.parent!=null,"Missing component "+name);
            componentTargets.push({target:d,name:name,mode:mode,parent:d.parent,visible:d.visible});
            report.components.targets.push({name:name,mode:mode,className:getQualifiedClassName(d),visible:d.visible});
        }
        private function applyComponent(mode:int):void {
            if(report.components==null)return;
            require(mode>=0 && mode<COMPONENTS.length,"Unknown component mode");
            for each(var t:Object in componentTargets) {
                require(t.target.parent===t.parent,"Component parent changed");
                var v:Boolean=mode==t.mode?false:t.visible;
                if(t.target.visible!==v){t.target.visible=v;++report.components.visibilityWrites;}
            }
            componentMode=mode;report.components.mode=mode;++report.components.applyCalls;
        }
        private function checkComponents():void {
            for each(var t:Object in componentTargets) {
                require(t.target.parent===t.parent && t.target.visible===(componentMode==t.mode?false:t.visible),"Component visibility/parent changed: "+t.name);
            }
            if(report.components)++report.components.checks;
        }
        private function onComponentExit(e:Event):void {
            if(closed || phase!=3)return;
            try {checkComponents();++report.components.exitChecks;++row.exitChecks;}
            catch(error:Error){fail(error);}
        }

        private function coverage(b:BitmapData):Object {
            var rect:Rectangle=new Rectangle(96,80,stage.stageWidth-192,stage.stageHeight-160);
            var pixels:Vector.<uint>=b.getVector(rect),count:int=0;
            for(var i:int=0;i<pixels.length;++i) {
                var p:uint=pixels[i];if(Math.max(p>>>16&255,p>>>8&255,p&255)>20)++count;
            }
            return {colored:count,pixels:pixels.length,fraction:count/pixels.length};
        }
        private function savePNG(name:String,b:BitmapData):void {
            var f:FileStream=new FileStream();
            try {f.open(File.applicationStorageDirectory.resolvePath(name),FileMode.WRITE);f.writeBytes(b.encode(b.rect,new PNGEncoderOptions()));}
            finally {f.close();}
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
