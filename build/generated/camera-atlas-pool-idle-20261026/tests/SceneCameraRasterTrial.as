package tests {
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.display.DisplayObject;
    import flash.display.Stage;
    import flash.geom.Matrix;
    import flash.geom.Rectangle;
    import flash.system.System;
    import flash.utils.getDefinitionByName;
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
        private var owned:Array=[];
        private var views:Array=[];
        private var route:Array=[];
        private var prepareRoute:Array=[];
        private var order:Array=[0,1,2,3,3,2,1,0];
        private var phase:int=0;
        private var cursor:int=0;
        private var retries:int=0;
        private var settle:int=0;
        private var segment:int=0;
        private var age:int=0;
        private var previous:int=0;
        private var beginAt:int=0;
        private var prepareAt:int=0;
        private var pixelAt:int=0;
        private var preparePass:int=0;
        private var prepareBaseline:Object;
        private var pending:Object;
        private var row:Object;
        private var closed:Boolean=false;
        private const CAMERA:Array=["moved","screenX","screenY","X","Y","vx","vy","ovy","maxsx","maxsy","maxvx","maxvy","celX","celY","camRun","otryv","quakeX","quakeY","isZoom","scaleV","scaleS","dblack","showOn","showX","showY"];
        private const COUNTERS:Array=["sceneRedraws","sceneDrawMs","sceneMaxDrawMs","sceneResident","sceneEvictions","sceneMisses","sceneWarmCount","sceneWarmSlices","sceneWarmForced","sceneLastDirtyCount"];

        public function begin(w:*,p:*):Object {
            if(report!=null)throw new Error("Camera raster trial is single-use");
            beginAt=getTimer();
            report={version:"camera-atlas-pool-idle-1",poolPreparation:[],diagnosticOnly:true,performanceEligible:false,
                terminalOnly:true,complete:false,passed:false,pixelsValid:false,errors:[],pixels:[],fallbackPixels:[],windows:[],
                pixelTolerance:{maxRGB:2,maxAlpha:0,restoreExact:true},
                framesMs:[],sampleAtMs:[],prepareMs:0,prepareWorkMs:0,pixelMs:0,
                pixelBitmapsCreated:0,pixelBitmapsDisposed:0,pixelDisposeErrors:[],pixelBufferPeakBytes:0,measurementFrames:960,
                intervalMeaning:"Applied camera/atlas work, next actual frame presentation, then next step entry. No segment-clock resets.",
                limits:["World.onPause stops simulation; Flash timelines and other frame callbacks remain live.",
                    "120fps diagnostic changes timeline speed; these intervals are not gameplay FPS.",
                    "Scale 1, zero shake, integer world-to-Stage translation only.",
                    "Atlas permits at most 2/255 difference per RGB channel and exact alpha; restoration remains fully exact.",
                    "Native prewarmed caches/counters remain resident; no simulated objects are moved or removed.",
                    "Final end snapshot and cleanup are outside the last measured interval."]};
            world=w;presenter=p;
            try {
                require(w!=null && p!=null,"Missing world/presenter");
                cam=w.cam;grafon=w.grafon;player=w.gg;location=w.loc;stage=w.main.stage as Stage;
                require(stage!=null && w.swfStage===stage && w.allStat==1 && w.t_exit==0,"Unstable world/stage");
                require(grafon.sceneLarge && cam.moved && grafon.sceneChunkSide==320,"Requires native 320px large scene");
                require(getQualifiedClassName(p)=="SceneRasterPresentation","Wrong presentation helper");
                require(w.sats!=null && w.sats.vis!=null && w.visual!=null,"Missing camera targets");
                snd=w.main.loaderInfo.applicationDomain.getDefinition("fe.Snd") as Class;
                var carrier:*=w.main.getChildByName("ContinuousSceneCarrier");
                api=carrier!=null && "nativeAPI" in carrier?carrier["nativeAPI"]:null;
                require(api!=null && api.constructor===Object,"Missing native camera state API");
                saved={pause:w.onPause,camera:fields(cam,CAMERA),gg:playerState(),celX:w.celX,celY:w.celY,
                    look:w.ctr.keyLook,zoom:w.ctr.keyZoom,frameRate:stage.frameRate,
                    sndX:snd[new QName("","centrX")],sndY:snd[new QName("","centrY")],
                    blackVisible:w.vblack.visible,blackAlpha:w.vblack.alpha,
                    hasState:api.hasOwnProperty("verticalCameraState"),state:api["verticalCameraState"]};
                saved.stateFields=saved.state!=null && saved.state.constructor===Object?plain(saved.state):null;
                saveDisplay(w.visual);saveDisplay(w.sats.vis);saveDisplay(w.vscene);
                saveDisplay(grafon.ramT);saveDisplay(grafon.ramB);saveDisplay(grafon.ramL);saveDisplay(grafon.ramR);
                rememberTiles();
                saved.ready=true;
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
                    applyCamera(point.x,point.y);
                    ++report.prepareCalls;
                    if(grafon.sceneViewReady()) {++cursor;retries=0;} else if(++retries>300)throw new Error("Native viewport did not finish preparing");
                    report.prepareWorkMs+=getTimer()-workAt;
                    if(cursor==prepareRoute.length) {
                        var preparationEnd:Object=counters(),quiet:Boolean=true,changes:Object={};
                        for each(var preparationKey:String in ["sceneRedraws","sceneDrawMs","sceneResident","sceneEvictions","sceneMisses","sceneWarmCount","sceneWarmSlices","sceneWarmForced"]) {
                            if(preparationKey in preparationEnd && preparationKey in prepareBaseline) {
                                changes[preparationKey]=Number(preparationEnd[preparationKey])-Number(prepareBaseline[preparationKey]);
                                if(changes[preparationKey]!=0)quiet=false;
                            }
                        }
                        ++preparePass;report.preparePasses.push({pass:preparePass,quiet:quiet,delta:changes});
                        cursor=0;
                        if(quiet) {
                            report.prepareMs=getTimer()-prepareAt;report.prepareEnd=snapshot();preparePool("before-pixels");
                            phase=1;pixelAt=getTimer();
                        } else {
                            require(preparePass<12,"Native route did not settle within 12 complete preparation passes");
                            prepareBaseline=preparationEnd;
                        }
                    }
                } else if(phase==1) {
                    pixelCase(views[cursor],cursor);++cursor;
                    if(cursor==views.length) {
                        fallbackCase("fractional",false);fallbackCase("scaled",true);
                        report.pixelMs=getTimer()-pixelAt;
                        report.pixelsValid=true;
                        presenter.clear();applyCamera(views[0].x,views[0].y);preparePool("before-timing");
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
                    var now:int=getTimer();
                    var interval:int=now-previous;previous=now;
                    require(interval>=0,"Non-monotonic timer");
                    report.framesMs.push(interval);report.sampleAtMs.push(now);
                    row.framesMs.push(interval);row.sampleAtMs.push(now);
                    row.vx.push(pending.vx);row.vy.push(pending.vy);
                    row.cameraX.push(pending.x);row.cameraY.push(pending.y);
                    row.gg.push(pending.gg);row.scene.push(pending.scene);
                    row.workMs.push(pending.workMs);row.presented.push(pending.presented);
                    row.atlasStates.push(pending.atlas);row.cameraMs.push(pending.cameraMs);row.presenterMs.push(pending.presenterMs);row.guardMs.push(pending.guardMs);row.snapshotMs.push(pending.snapshotMs);
                    ++age;
                    if(age==120) {
                        row.endAtMs=now;row.end=snapshot();row.copiesEnd=presenter.copies;row.rebuildsEnd=presenter.rebuilds;
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
                            report.stationaryRefresh=[];stationaryRefresh(false);stationaryRefresh(true);
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
            try {if(presenter!=null){cleanup.atlasBefore=presenter.snapshot();presenter.clear();cleanup.atlasAfter=presenter.snapshot();}} catch(e0:Error){cleanup.errors.push("presenter: "+e0.message);}
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
                // These restoration operations must still run if an earlier check failed.
                try {stage.frameRate=saved.frameRate;}catch(e6:Error){cleanup.errors.push("frameRate: "+e6.message);}
                try {world.onPause=saved.pause;}catch(e7:Error){cleanup.errors.push("pause: "+e7.message);}
                try {
                    require(sameFields(cam,saved.camera) && world.onPause===saved.pause && stage.frameRate==saved.frameRate,"Camera/pause/frameRate restore mismatch");
                    require(samePlayer(playerState(),saved.gg),"Player simulation changed while paused");
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
            var minX:int=Math.ceil(cam.screenX/2)+960;
            var maxX:int=Math.floor(cam.maxsx-cam.screenX/2)-960;
            var minY:int=Math.ceil(cam.screenY/2+100)+960;
            var maxY:int=Math.floor(cam.maxsy-cam.screenY/2+100)-960;
            require(minX<=maxX && minY<=maxY,"Map cannot contain the integer camera route");
            var x:int=Math.max(minX,Math.min(maxX,int(cam.X)));
            var y:int=Math.max(minY,Math.min(maxY,int(cam.Y)));
            // World-aligned pages are 1280px. These legs cross both page axes,
            // visit more than the 8-page cap, and finally revisit the origin.
            views=[{x:x,y:y},{x:x+960,y:y+960},{x:x-960,y:y+960},{x:x-960,y:y-960},{x:x,y:y}];
            for(var leg:int=0;leg<4;++leg) {
                var a:Object=views[leg];var b:Object=views[leg+1];
                for(var i:int=0;i<30;++i)route.push({x:a.x+(b.x-a.x)*i/30,y:a.y+(b.y-a.y)*i/30});
            }
            report.routeTranslationOnly=true;report.playerMovedByHelper=false;report.prepareCalls=0;
        }

        private function startWindow():void {
            var condition:int=order[segment];age=0;
            row={index:segment,condition:condition,mode:["native-static","native-moving","atlas-static","atlas-moving"][condition],
                atlas:condition>=2,moving:condition%2==1,startAtMs:previous,
                framesMs:[],sampleAtMs:[],vx:[],vy:[],cameraX:[],cameraY:[],gg:[],scene:[],workMs:[],presented:[],atlasStates:[],cameraMs:[],presenterMs:[],guardMs:[],snapshotMs:[],
                start:snapshot(),copiesStart:presenter.copies,rebuildsStart:presenter.rebuilds};
            report.windows.push(row);
        }

        private function preparePool(label:String):void {
            var item:Object={label:label,startedAtMs:getTimer(),before:presenter.snapshot(),memoryBefore:System.totalMemory};
            presenter.preallocate(world);
            item.endedAtMs=getTimer();item.after=presenter.snapshot();item.memoryAfter=System.totalMemory;
            report.poolPreparation.push(item);
        }

        private function applyFrame():void {
            var at:int=getTimer();
            var point:Object=row.moving?route[age]:views[0];
            applyCamera(point.x,point.y);
            require(grafon.sceneViewReady(),"Unprepared viewport during timing");
            var cameraEnd:int=getTimer();
            if(row.atlas)presenter.update(world,true);else presenter.useNativeForTest();
            var presenterEnd:int=getTimer();
            checkTransform();guard();var guardEnd:int=getTimer();
            pending={vx:cam.vx,vy:cam.vy,x:cam.X,y:cam.Y,gg:playerState(),scene:counters(),presented:presenter.presented,atlas:presenter.snapshot(),workMs:getTimer()-at};
            var end:int=getTimer();pending.workMs=end-at;
            pending.cameraMs=cameraEnd-at;pending.presenterMs=presenterEnd-cameraEnd;
            pending.guardMs=guardEnd-presenterEnd;pending.snapshotMs=end-guardEnd;
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
            var at:int=getTimer();
            var a:BitmapData;var b:BitmapData;var c:BitmapData;
            var result:Object={index:index,x:point.x,y:point.y,equal:false,exactEqual:false,withinTolerance:false,restored:false,passed:false};
            report.pixels.push(result);
            try {
                presenter.beginFrame();applyCamera(point.x,point.y);require(grafon.sceneViewReady(),"Pixel viewport not prepared");
                a=capture();presenter.update(world,true,true);result.forcedPresentation=presenter.presented;require(result.forcedPresentation===true,"Pixel check must present the atlas");b=capture();
                result.presentation=presenter.snapshot();
                result.atlas=compare(a,b);presenter.beginFrame();c=capture();result.restore=compare(a,c);
                result.equal=result.atlas.equal;result.exactEqual=result.atlas.equal;
                result.withinTolerance=result.atlas.maxRGB<=2 && result.atlas.maxAlpha==0;
                result.restored=result.restore.equal;
                result.passed=result.withinTolerance && result.restored;
                result.camera={vx:cam.vx,vy:cam.vy,scale:cam.scaleV};
                require(result.passed,"RGB2/alpha0 atlas tolerance or exact restoration failed at view "+index);
            } finally {
                presenter.beginFrame();disposeOwned();result.elapsedMs=getTimer()-at;
            }
        }

        private function fallbackCase(label:String,scale:Boolean):void {
            var original:Matrix=world.visual.transform.matrix.clone();
            var oldScale:Number=cam.scaleV,oldQuake:Number=cam.quakeX;
            var result:Object={name:label,passed:false};report.fallbackPixels.push(result);
            try {
                presenter.beginFrame();
                var altered:Matrix=original.clone();
                if(scale){altered.a=.8;altered.d=.8;cam.scaleV=.8;}
                else {altered.tx+=.25;cam.quakeX=.25;}
                world.visual.transform.matrix=altered;
                var a:BitmapData=capture();presenter.update(world,true,true);
                result.presented=presenter.presented;result.state=presenter.snapshot();
                var b:BitmapData=capture();result.compare=compare(a,b);
                result.passed=!result.presented && result.compare.equal;
                require(result.passed,"Geometry fallback must remain exactly native: "+label);
            } finally {
                presenter.beginFrame();world.visual.transform.matrix=original;
                cam.scaleV=oldScale;cam.quakeX=oldQuake;disposeOwned();
            }
        }

        private function stationaryFixture(breakWall:Boolean):Object {
            var view:Rectangle=grafon.sceneViewport();
            var left:int=Math.max(1,Math.ceil((view.left+80)/40)),right:int=Math.min(location.spaceX-2,Math.floor((view.right-80)/40));
            var top:int=Math.max(1,Math.ceil((view.top+80)/40)),bottom:int=Math.min(location.spaceY-2,Math.floor((view.bottom-80)/40));
            for(var y:int=bottom;y>=top;--y)for(var x:int=left;x<=right;++x) {
                var t:*=location.getTile(x,y),px:Number=x*40+20,py:Number=y*40+20;
                if(!t || t.phis!=1 || t.fake || t.trap || t.door || t.front=="" || t.water>0 || t.mat<1 || t.mat>6 || t.mat==5 || !(t.hp>0) ||
                    px<t.phX1 || px>t.phX2 || py<t.phY1 || py>t.phY2)continue;
                if(breakWall && (t.indestruct || !isFinite(t.hp) || !isFinite(t.thre) || (!location.destroyOn && t.hp>500)))continue;
                return {x:px,y:py,tileX:x,tileY:y,material:t.mat,hp:t.hp,threshold:t.thre};
            }
            return null;
        }

        private function stationaryRefresh(breakWall:Boolean):void {
            var item:Object={breakWall:breakWall,passed:false,startedAtMs:getTimer()};
            report.stationaryRefresh.push(item);
            try {
                presenter.beginFrame();applyCamera(views[0].x,views[0].y);
                require(grafon.sceneViewReady(),"Mutation viewport must already be resident");
                // Populate a genuinely current cache before changing native pixels.
                presenter.update(world,true,true);require(presenter.presented,"Mutation cache not populated");
                presenter.beginFrame();
                var fixture:Object=stationaryFixture(breakWall);item.fixture=fixture;
                require(fixture!=null,"No visible native wall fixture; do not silently skip mutation coverage");
                var revisions:Array=[];
                for each(var surface:Object in grafon.sceneSurfaces())revisions.push({surface:surface,revision:surface.revision});
                var beforeImage:BitmapData=capture();item.before=presenter.snapshot();
                if(breakWall) {
                    var tile:*=location.getTile(fixture.tileX,fixture.tileY);
                    var damage:Number=Math.max(Number(tile.hp),Number(tile.thre))+1;
                    location.hitTile(tile,damage,fixture.x,fixture.y,1);
                    item.nativeAction={phis:tile.phis,hp:tile.hp,damage:damage};
                    require(tile.phis==0,"Native wall did not break");
                } else {
                    var Bullet:Class=getDefinitionByName("fe.weapon.Bullet") as Class;
                    var bullet:*=new Bullet(player,fixture.x-1,fixture.y,null,false);
                    bullet.dx=1;bullet.dy=0;bullet.vel=1;bullet.damage=0;bullet.destroy=0;
                    bullet.damageExpl=0;bullet.explRadius=0;bullet.tipDecal=1;bullet.partEmit=false;bullet.off=true;
                    bullet.run();
                    item.nativeAction={tilehit:bullet.tilehit,babah:bullet.babah,detached:true,unitCollisionSkipped:true};
                    require(bullet.tilehit && bullet.babah,"Native bullet did not hit the wall");
                }
                var changed:BitmapData=capture();item.nativeChanged=compare(beforeImage,changed);
                item.changedSurfaceRevisions=0;
                for each(var previousSurface:Object in revisions)if(previousSurface.surface.revision!==previousSurface.revision)++item.changedSurfaceRevisions;
                require(item.nativeChanged.differentPixels>0 && item.changedSurfaceRevisions>0,"Native mutation produced no visible pixel/revision change");
                // No frame advance or sceneTick between mutation and static readback.
                presenter.update(world,true);item.skipped=presenter.snapshot();
                require(!presenter.presented && item.skipped.stationarySkips==item.before.stationarySkips+1,"Stationary shortcut not used");
                require(item.skipped.copies==item.before.copies && item.skipped.rebuilds==item.before.rebuilds,"Stationary shortcut copied pixels");
                var staticImage:BitmapData=capture();item.staticExact=compare(changed,staticImage);
                require(item.staticExact.equal,"Static path concealed a native mutation");
                applyCamera(views[0].x+4,views[0].y);require(grafon.sceneViewReady(),"Resume view not ready");
                var movedNative:BitmapData=capture();presenter.update(world,true);item.moving=presenter.snapshot();
                require(presenter.presented && item.moving.copies>item.skipped.copies,"Moving resume did not synchronize changed pixels");
                var movedAtlas:BitmapData=capture();item.movingPixels=compare(movedNative,movedAtlas);
                require(item.movingPixels.maxAlpha==0 && item.movingPixels.maxRGB<=2,"Moving resume contains stale or invalid pixels");
                presenter.beginFrame();var restored:BitmapData=capture();item.restoreExact=compare(movedNative,restored);
                require(item.restoreExact.equal,"Moving resume did not restore native pixels exactly");
                guard();item.passed=true;
            } finally {presenter.beginFrame();disposeOwned();item.endedAtMs=getTimer();}
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
            require(samePlayer(playerState(),saved.gg),"Player position/velocity/HP changed during paused attribution");
        }
        private function playerState():Object {return {x:player.X,y:player.Y,dx:player.dx,dy:player.dy,hp:player.hp,stay:player.stay};}
        private function samePlayer(a:Object,b:Object):Boolean {return a.x===b.x && a.y===b.y && a.dx===b.dx && a.dy===b.dy && a.hp===b.hp && a.stay===b.stay;}
        private function counters():Object {
            var value:Object={};for each(var name:String in COUNTERS)if(name in grafon)value[name]=grafon[name];return value;
        }
        private function snapshot():Object {return {atMs:getTimer(),pause:world.onPause,camera:fields(cam,CAMERA),gg:playerState(),scene:counters(),copies:presenter.copies,rebuilds:presenter.rebuilds,atlas:presenter.snapshot(),memoryBytes:System.totalMemory};}
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
