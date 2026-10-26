package tests {
    import flash.desktop.NativeApplication;
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.display.DisplayObject;
    import flash.display.Stage;
    import flash.display.DisplayObjectContainer;
    import flash.display.MovieClip;
    import flash.utils.Dictionary;
    import flash.display.PNGEncoderOptions;
    import flash.filesystem.File;
    import flash.filesystem.FileMode;
    import flash.filesystem.FileStream;
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
        private var snd:Class;
        private var api:*;
        private var saved:Object;
        private var report:Object;
        private var displays:Array=[];
        private var originalTiles:Array=[];
        private var terrain:Array=[];
        private var owned:Array=[];
        private var views:Array=[];
        private var route:Array=[];
        private var prepareRoute:Array=[];
        private var order:Array=[0,1,1,0];
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
            report={version:"camera-far-static-visibility-1",diagnosticOnly:true,performanceEligible:false,
                terminalOnly:true,complete:false,passed:false,pixelsValid:false,errors:[],pixels:[],windows:[],
                framesMs:[],sampleAtMs:[],prepareMs:0,prepareWorkMs:0,pixelMs:0,
                pixelBitmapsCreated:0,pixelBitmapsDisposed:0,pixelDisposeErrors:[],pixelBufferPeakBytes:0,measurementFrames:480,
                intervalMeaning:"Applied camera/crop work, next actual frame presentation, then next step entry. No segment-clock resets.",
                limits:["World.onPause stops simulation; Flash timelines and other frame callbacks remain live.",
                    "120fps diagnostic changes timeline speed; these intervals are not gameplay FPS.",
                    "Scale 1, zero shake, integer world-to-Stage translation only.",
                    "Paused attribution only: Only qualified static direct roots outside the whole route plus 320px are hidden. No wrappers or per-frame full tree scans. End/switch audits do not prove every intermediate callback state. One fixed native warm-up, then three exact natural camera invariants before alpha tests. Cold screenshot behavior remains separately recorded.",
                    "This is not an enemy-free gameplay run: simulation is paused, while timelines and other callbacks can continue.",
                    "Native prewarmed caches/counters remain resident; no simulated objects are moved or removed.",
                    "Final end snapshot and cleanup are outside the last measured interval."]};
            world=w;presenter=p;
            try {
                require(w!=null && p!=null,"Missing world/presenter");
                cam=w.cam;grafon=w.grafon;player=w.gg;location=w.loc;stage=w.main.stage as Stage;
                require(stage!=null && w.swfStage===stage && w.allStat==1 && w.t_exit==0,"Unstable world/stage");
                require(grafon.sceneLarge && cam.moved && grafon.sceneChunkSide==320,"Requires native 320px large scene");
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
                for each(var layer:DisplayObject in [grafon.visObjs[0],grafon.visObjs[1],grafon.visObjs[2],grafon.visObjs[3],grafon.visObjs[4],grafon.visObjs[5]]) {
                    require(layer!=null && layer.parent!=null && isFinite(layer.alpha),"Display parent identity mismatch");
                    terrain.push({target:layer,parent:layer.parent,alpha:layer.alpha,visible:layer.visible});
                }
                report.terrainInitial=layerState();
                saved.ready=true;
                require(/^pfe-modsettings-continuous-motion-[0-9a-f]{32}$/.test(NativeApplication.nativeApplication.applicationID),"Isolated motion application required");
                require(saved.worldVisible===true,"World must start visible");
                require(w.mm!=null && w.mm.active===false,"Main menu must be inactive");
                report.nativeMenuChildren=[];
                for(var menuChild:int=0;menuChild<w.main.numChildren;++menuChild) {
                    var className:String=getQualifiedClassName(w.main.getChildAt(menuChild));
                    report.nativeMenuChildren.push({className:className,visible:w.main.getChildAt(menuChild).visible});
                    require(className!="visMainMenu","Native mainMenuOff must remove main menu display");
                }
                stage.nativeWindow.visible=true;
                require(stage.nativeWindow.visible===true,"Owned private window did not become visible");
                report.originalFrameRate=saved.frameRate;report.testFrameRate=120;
                report.stage={width:stage.stageWidth,height:stage.stageHeight,quality:stage.quality};
                report.initial=snapshot();
                require(Number(cam.scaleV)==1,"Initial camera must already be scale 1");
                require(cam.screenX==stage.stageWidth && cam.screenY==stage.stageHeight,"Stage/camera size mismatch");
                w.onPause=true;
                require(w.onPause===true && w.gg===player && w.loc===location,"Pause was not applied");
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
                require(w===world,"World argument replaced");guard();
                require(getTimer()-beginAt<180000,"Camera raster timeout");
                if(phase==0) {
                    var workAt:int=getTimer();
                    var point:Object=prepareRoute[cursor];
                    applyCamera(point.x,point.y);collectViewport();
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
                            collectRoots();phase=1;pixelAt=getTimer();
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
                    row.workMs.push(pending.workMs);row.worldVisible.push(pending.worldVisible);row.windowVisible.push(pending.windowVisible);
                    require(sameLayers(layerState(),row.condition),"Terrain changed during rendered interval");row.terrain.push(pending.terrain);
                    ++age;
                    if(age==120) {
                        row.endAtMs=now;row.end=snapshot();row.copiesEnd=presenter.copies;row.allocatedEnd=presenter.allocated;
                        ++segment;
                        if(segment==order.length) {
                            report.timingEndAtMs=now;report.timingElapsedMs=now-report.timingStartAtMs;
                            auditRoots();report.timingEnd=row.end;report.timingRasterDelta={};report.zeroRasterWork=true;
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
            try {restoreRoots();cleanup.terrainRestored=sameLayers(layerState(),0);if(rootsReady)auditRoots();}catch(eTerrain:Error){cleanup.errors.push("terrain: "+eTerrain.message);}
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
            cleanup.pendingOwnedBitmaps=owned.length;cleanup.elapsedMs=getTimer()-at;
            if(report.pixelDisposeErrors.length)cleanup.errors.push("Owned pixel bitmap disposal failed");
            cleanup.restored=cleanup.errors.length==0 && owned.length==0;
            report.cleanup=cleanup;report.elapsedMs=getTimer()-beginAt;
            if(!cleanup.restored){report.passed=false;report.errors.push("Cleanup failed");}
            return cleanup;
        }

        private function makeRoute():void {
            var minX:int=Math.ceil(cam.screenX/2)+120;
            var maxX:int=Math.floor(cam.maxsx-cam.screenX/2)-120;
            var minY:int=Math.ceil(cam.screenY/2+100)+120;
            var maxY:int=Math.floor(cam.maxsy-cam.screenY/2+100)-120;
            require(minX<=maxX && minY<=maxY,"Map cannot contain the integer camera route");
            var x:int=Math.max(minX,Math.min(maxX,int(cam.X)));
            var y:int=Math.max(minY,Math.min(maxY,int(cam.Y)));
            views=[{x:x,y:y},{x:x+120,y:y},{x:x,y:y+120},{x:x-120,y:y-120},{x:x+120,y:y+120}];
            for(var leg:int=0;leg<5;++leg) {
                var a:Object=views[leg];var b:Object=views[(leg+1)%5];
                for(var i:int=0;i<24;++i)route.push({x:a.x+(b.x-a.x)*i/24,y:a.y+(b.y-a.y)*i/24});
            }
            report.routeTranslationOnly=true;report.playerMovedByHelper=false;report.prepareCalls=0;
        }

        private function startWindow():void {
            var condition:int=order[segment];age=0;
            row={index:segment,condition:condition,mode:["native-moving","far-static-hidden-moving"][condition],
                hidden:false,moving:true,startAtMs:previous,
                framesMs:[],sampleAtMs:[],vx:[],vy:[],cameraX:[],cameraY:[],gg:[],scene:[],workMs:[],
                worldVisible:[],windowVisible:[],terrain:[],start:snapshot(),copiesStart:presenter.copies,allocatedStart:presenter.allocated};
            report.windows.push(row);
        }

        private function applyFrame():void {
            var at:int=getTimer();
            var point:Object=route[age];
            applyCamera(point.x,point.y);applyLayers(row.condition);
            require(grafon.sceneViewReady(),"Unprepared viewport during timing");
            require(world.visual.visible===true,"World visibility changed");
            checkTransform();guard();
            pending={vx:cam.vx,vy:cam.vy,x:cam.X,y:cam.Y,gg:playerState(),scene:counters(),workMs:getTimer()-at,worldVisible:world.visual.visible,windowVisible:stage.nativeWindow.visible,terrain:layerState()};
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
            var at:int=getTimer(),result:Object={index:index,x:point.x,y:point.y,passed:false,conditions:[]};
            report.pixels.push(result);
            try {
                require(world.visual.visible===true,"World must remain visible");applyCamera(point.x,point.y);
                require(grafon.sceneViewReady(),"Pixel viewport not prepared");applyLayers(0);
                var original:BitmapData=warmNative(point,index);
                for(var mode:int=1;mode<=1;++mode) {
                    applyLayers(mode);var suppressed:BitmapData=capture();
                    applyLayers(0);var restored:BitmapData=capture();
                    var item:Object={condition:mode,changed:compare(original,suppressed),restored:compare(original,restored)};
                    result.conditions.push(item);
                    if(index==0 || !item.restored.equal) {
                        savePixel("original-"+index+"-"+mode,original);
                        savePixel("suppressed-"+index+"-"+mode,suppressed);
                        savePixel("restored-"+index+"-"+mode,restored);
                        item.savedPixelTriplet=true;
                    }
                    require(item.changed.equal && item.restored.equal,"Offscreen root culling changed pixels");
                }
                result.passed=true;
            } finally {applyLayers(0);disposeOwned();result.elapsedMs=getTimer()-at;}
        }

        private function warmNative(point:Object,index:int):BitmapData {
            if(report.nativeWarmups==null)report.nativeWarmups=[];
            var record:Object={view:index,protocol:"one fixed horizontal roundtrip then three exact invariants",checks:[]};
            report.nativeWarmups.push(record);
            var cold:BitmapData=capture();
            applyCamera(point.x+1,point.y);require(grafon.sceneViewReady(),"Warm-up away viewport not prepared");
            var away:BitmapData=capture();
            applyCamera(point.x,point.y);require(grafon.sceneViewReady(),"Warm-up return viewport not prepared");
            var baseline:BitmapData=capture();record.coldVsWarm=compare(cold,baseline);
            if(index==0 || !record.coldVsWarm.equal){savePixel("cold-"+index,cold);savePixel("warm-"+index,baseline);}
            for each(var offset:Object in [{x:1,y:0},{x:0,y:1},{x:120,y:120}]){
                applyCamera(point.x+offset.x,point.y+offset.y);
                require(grafon.sceneViewReady(),"Invariant away viewport not prepared");away=capture();
                applyCamera(point.x,point.y);require(grafon.sceneViewReady(),"Invariant return viewport not prepared");
                var restored:BitmapData=capture(),comparison:Object=compare(baseline,restored);
                record.checks.push({offset:offset,pixels:comparison});
                require(comparison.equal,"Native camera pixel baseline is still unstable after fixed warm-up");
            }
            record.passed=true;return baseline;
        }

        private var routeBounds:Rectangle;
        private var roots:Array=[];
        private var maskTargets:Dictionary=new Dictionary(true);
        private var currentCondition:int=0;
        private var rootsReady:Boolean=false;

        private function collectViewport():void {
            var view:Rectangle=new Rectangle(-cam.vx,-cam.vy,stage.stageWidth,stage.stageHeight);
            routeBounds=routeBounds==null?view:routeBounds.union(view);
        }

        private function collectMasks(node:DisplayObject):void {
            if(node.mask!=null)maskTargets[node.mask]=true;
            var container:DisplayObjectContainer=node as DisplayObjectContainer;
            if(container!=null)for(var i:int=0;i<container.numChildren;++i)collectMasks(container.getChildAt(i));
        }

        private function staticReason(node:DisplayObject):String {
            if(node.mask!=null || maskTargets[node]===true)return "mask";
            if(node.filters.length>0)return "filters";
            if(node.transform.matrix3D!=null || node.transform.matrix==null)return "3d";
            if(node.blendMode!="normal")return "blend";
            var clip:MovieClip=node as MovieClip;
            if(clip!=null && clip.totalFrames>1 && clip.isPlaying)return "playing";
            var container:DisplayObjectContainer=node as DisplayObjectContainer;
            if(container!=null)for(var i:int=0;i<container.numChildren;++i) {
                var reason:String=staticReason(container.getChildAt(i));if(reason!="")return reason;
            }
            return "";
        }

        private function collectRoots():void {
            require(!rootsReady && routeBounds!=null,"Root collection state");
            var at:int=getTimer();routeBounds.inflate(320,320);
            report.rootSelection={scanned:0,selected:0,byLayer:[0,0,0,0,0,0],classes:{},skips:{},
                area:{x:routeBounds.x,y:routeBounds.y,width:routeBounds.width,height:routeBounds.height},
                perFrameFullScans:0,transitionWrites:0,audits:0};
            collectMasks(stage);
            for(var l:int=0;l<terrain.length;++l) {
                var parent:DisplayObjectContainer=terrain[l].target as DisplayObjectContainer;
                require(parent!=null && parent===grafon.visObjs[l],"Object layer missing");
                for(var i:int=0;i<parent.numChildren;++i) {
                    var root:DisplayObject=parent.getChildAt(i),reason:String="";
                    ++report.rootSelection.scanned;
                    try {
                        if(!root.visible)reason="already-hidden";
                        if(reason=="")reason=staticReason(root);
                        var bounds:Rectangle=root.getBounds(world.visual);
                        if(reason=="" && (!isFinite(bounds.x) || !isFinite(bounds.y) || !isFinite(bounds.width) || !isFinite(bounds.height) || bounds.isEmpty()))reason="bounds";
                        if(reason=="" && bounds.intersects(routeBounds))reason="route-visible";
                        if(reason=="") {
                            roots.push({target:root,parent:parent,index:i,alpha:root.alpha,matrix:root.transform.matrix.clone(),visible:root.visible,bounds:bounds});
                            ++report.rootSelection.byLayer[l];
                            var name:String=getQualifiedClassName(root);
                            report.rootSelection.classes[name]=int(report.rootSelection.classes[name])+1;
                        }
                    } catch(error:Error){reason="unreadable";}
                    if(reason!="")report.rootSelection.skips[reason]=int(report.rootSelection.skips[reason])+1;
                }
            }
            rootsReady=true;report.rootSelection.selected=roots.length;
            report.rootSelection.prepareMs=getTimer()-at;
            require(roots.length>0,"No qualified offscreen roots");auditRoots();
        }

        private function auditRoots():void {
            if(!rootsReady)return;
            for each(var item:Object in roots) {
                var root:DisplayObject=item.target;
                require(root.parent===item.parent && item.parent.getChildIndex(root)==item.index,"Root ownership/order changed");
                require(root.visible===(currentCondition==0?item.visible:false),"Root visibility changed externally");
                require(root.alpha===item.alpha && sameMatrix(root.transform.matrix,item.matrix),"Root local pose changed");
                require(staticReason(root)=="","Root acquired an effect or animation");
                var bounds:Rectangle=root.getBounds(world.visual);
                require(bounds.equals(item.bounds) && !bounds.intersects(routeBounds),"Root bounds changed");
            }
            ++report.rootSelection.audits;
        }

        private function restoreRoots():void {
            var errors:Array=[];
            for each(var item:Object in roots) {
                var root:DisplayObject=item.target;
                try {
                    if(item.controlled===true && root.visible===false)root.visible=item.visible;
                    require(root.visible===item.visible,"Could not restore controlled visibility");
                    item.controlled=false;
                } catch(error:Error){errors.push(error.message);}
            }
            currentCondition=0;
            require(errors.length==0,"Root restore: "+errors.join(";"));
        }

        private function applyLayers(condition:int):void {
            require(condition==0 || condition==1,"Invalid root condition");
            for(var i:int=0;i<terrain.length;++i)require(terrain[i].target===grafon.visObjs[i] && terrain[i].target.parent===terrain[i].parent,"Layer identity changed");
            if(condition==currentCondition)return;
            require(rootsReady,"Root selection missing");auditRoots();
            for each(var item:Object in roots) {
                item.target.visible=condition==0?item.visible:false;
                item.controlled=condition==1;
                ++report.rootSelection.transitionWrites;
            }
            currentCondition=condition;
        }

        private function layerState():Array {return [currentCondition,roots.length];}
        private function sameLayers(value:Array,condition:int):Boolean {
            return value.length==2 && value[0]==condition && value[1]==roots.length;
        }


        private function savePixel(name:String,data:BitmapData):void {
            var folder:File=File.applicationStorageDirectory.resolvePath("display-pixels");
            folder.createDirectory();
            var stream:FileStream=new FileStream();
            try {
                stream.open(folder.resolvePath(name+".png"),FileMode.WRITE);
                stream.writeBytes(data.encode(data.rect,new PNGEncoderOptions()));
            } finally {stream.close();}
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
