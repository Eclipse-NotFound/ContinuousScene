package tests {
    import flash.desktop.NativeApplication;
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.display.DisplayObject;
    import flash.display.Stage;
    import flash.display.DisplayObjectContainer;
    import flash.display.MovieClip;
    import flash.text.TextField;
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
        private var nodeIds:Dictionary=new Dictionary(true);
        private var nodeSequence:int=0;
        private const CAMERA:Array=["moved","screenX","screenY","X","Y","vx","vy","ovy","maxsx","maxsy","maxvx","maxvy","celX","celY","camRun","otryv","quakeX","quakeY","isZoom","scaleV","scaleS","dblack","showOn","showX","showY"];
        private const COUNTERS:Array=["sceneRedraws","sceneDrawMs","sceneMaxDrawMs","sceneResident","sceneEvictions","sceneMisses","sceneWarmCount","sceneWarmSlices","sceneWarmForced","sceneLastDirtyCount"];

        public function begin(w:*,p:*):Object {
            if(report!=null)throw new Error("Camera raster trial is single-use");
            beginAt=getTimer();
            report={version:"camera-display-state-1",diagnosticOnly:true,performanceEligible:false,
                terminalOnly:true,complete:false,passed:false,pixelsValid:false,errors:[],pixels:[],windows:[],
                framesMs:[],sampleAtMs:[],prepareMs:0,prepareWorkMs:0,pixelMs:0,
                pixelBitmapsCreated:0,pixelBitmapsDisposed:0,pixelDisposeErrors:[],pixelBufferPeakBytes:0,measurementFrames:0,
                intervalMeaning:"Applied camera/crop work, next actual frame presentation, then next step entry. No segment-clock resets.",
                limits:["World.onPause stops simulation; Flash timelines and other frame callbacks remain live.",
                    "120fps diagnostic changes timeline speed; these intervals are not gameplay FPS.",
                    "Scale 1, zero shake, integer world-to-Stage translation only.",
                    "Paused attribution only: native scenery backdrop and six object-layer parents use temporary alpha zero; all camera windows moving.",
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
                for each(var layer:DisplayObject in [grafon.visFon,grafon.visObjs[0],grafon.visObjs[1],grafon.visObjs[2],grafon.visObjs[3],grafon.visObjs[4],grafon.visObjs[5]]) {
                    require(layer!=null && layer.parent!=null && isFinite(layer.alpha),"Display parent identity mismatch");
                    terrain.push({target:layer,parent:layer.parent,alpha:layer.alpha});
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
                    pixelCase(views[0],0);
                    report.pixelMs=getTimer()-pixelAt;report.pixelsValid=true;
                    report.complete=true;report.passed=true;clear(w);
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
            try {if(terrain.length==7){applyLayers(0);cleanup.terrainRestored=sameLayers(layerState(),0);}}catch(eTerrain:Error){cleanup.errors.push("terrain: "+eTerrain.message);}
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
            row={index:segment,condition:condition,mode:["native-moving","backdrop-zero-moving","objects-zero-moving","backdrop-objects-zero-moving"][condition],
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
                report.nodeSnapshots=[];
                inspectNodes("before-native");
                var original:BitmapData=capture();
                inspectNodes("after-native");
                var repeated:BitmapData=capture();
                report.nativeRepeat=compare(original,repeated);
                inspectNodes("after-native-repeat");
                savePixel("native-repeat-"+index,repeated);
                savePixel("native-original-"+index,original);
                require(report.nativeRepeat.equal,"Unchanged native capture is not stable");
                for(var mode:int=1;mode<=3;++mode) {
                    applyLayers(mode);inspectNodes("suppressed-before-"+mode);
                    var suppressed:BitmapData=capture();inspectNodes("suppressed-after-"+mode);
                    applyLayers(0);inspectNodes("restored-before-"+mode);
                    var restored:BitmapData=capture();inspectNodes("restored-after-"+mode);
                    var item:Object={condition:mode,changed:compare(original,suppressed),restored:compare(original,restored)};
                    result.conditions.push(item);
                    if(index==0 || !item.restored.equal) {
                        savePixel("original-"+index+"-"+mode,original);
                        savePixel("suppressed-"+index+"-"+mode,suppressed);
                        savePixel("restored-"+index+"-"+mode,restored);
                        item.savedPixelTriplet=true;
                    }
                    require(item.restored.equal,"Terrain visibility did not restore exact pixels");
                }
                result.passed=true;
            } finally {applyLayers(0);disposeOwned();result.elapsedMs=getTimer()-at;}
        }

        private function applyLayers(condition:int):void {
            require(condition>=0 && condition<=3,"Invalid terrain condition");
            for(var i:int=0;i<terrain.length;++i) {
                var item:Object=terrain[i];
                require(item.target.parent===item.parent,"Display parent changed during attribution");
                item.target.alpha=(i==0?(condition&1):(condition&2))?0:item.alpha;
            }
            require(sameLayers(layerState(),condition),"Terrain visibility did not apply");
        }
        private function layerState():Array {
            var value:Array=[];for each(var item:Object in terrain)value.push(item.target.alpha);return value;
        }
        private function sameLayers(value:Array,condition:int):Boolean {
            if(value.length!=7)return false;
            for(var i:int=0;i<7;++i)if(value[i]!==Number((i==0?(condition&1):(condition&2))?0:terrain[i].alpha))return false;
            return true;
        }

        private function nodeId(value:*):int {
            if(value==null)return 0;
            if(!nodeIds[value])nodeIds[value]=++nodeSequence;
            return nodeIds[value];
        }
        private function inspectNodes(label:String):void {
            var at:int=getTimer();
            var result:Object={label:label,nodes:[],roots:[],errors:[],hashPixels:0,skippedRoots:0};
            report.nodeSnapshots.push(result);
            var screen:Rectangle=new Rectangle(-64,-64,stage.stageWidth+128,stage.stageHeight+128);
            for(var layerIndex:int=0;layerIndex<6;++layerIndex) {
                var layer:DisplayObjectContainer=grafon.visObjs[layerIndex] as DisplayObjectContainer;
                require(layer!=null,"Object layer missing for metadata");
                for(var i:int=0;i<layer.numChildren;++i) {
                    var root:DisplayObject=layer.getChildAt(i),b:Rectangle=root.getBounds(stage);
                    result.roots.push({id:nodeId(root),layer:layerIndex,index:i,className:getQualifiedClassName(root),bounds:rectState(b)});
                    if(b.isEmpty() || !b.intersects(screen)){++result.skippedRoots;continue;}
                    inspectNode(root,result,layerIndex+":"+i,0);
                }
            }
            result.elapsedMs=getTimer()-at;
            require(result.errors.length==0,"Display metadata incomplete");
        }
        private function inspectNode(node:DisplayObject,result:Object,path:String,depth:int):void {
            if(depth>70 || result.nodes.length>=12000){result.errors.push("Node budget exceeded");return;}
            try {
                var m:Matrix=node.transform.matrix,cm:Matrix=node.transform.concatenatedMatrix;
                var ct:*=node.transform.colorTransform,cct:*=node.transform.concatenatedColorTransform;
                var record:Object={id:nodeId(node),parent:nodeId(node.parent),path:path,name:node.name,
                    className:getQualifiedClassName(node),bounds:rectState(node.getBounds(stage)),
                    visible:node.visible,alpha:node.alpha,blend:node.blendMode,cache:node.cacheAsBitmap,
                    mask:nodeId(node.mask),scroll:rectState(node.scrollRect),
                    matrix:fields(m,["a","b","c","d","tx","ty"]),
                    concatMatrix:fields(cm,["a","b","c","d","tx","ty"]),
                    color:fields(ct,["redMultiplier","greenMultiplier","blueMultiplier","alphaMultiplier","redOffset","greenOffset","blueOffset","alphaOffset"]),
                    concatColor:fields(cct,["redMultiplier","greenMultiplier","blueMultiplier","alphaMultiplier","redOffset","greenOffset","blueOffset","alphaOffset"]),filters:[]};
                for each(var filter:* in node.filters) {
                    var f:Object={className:getQualifiedClassName(filter)};
                    for each(var field:String in ["alpha","angle","blurX","blurY","color","distance","hideObject","inner","knockout","quality","strength","matrix"])
                        if(field in filter)f[field]=filter[field];
                    record.filters.push(f);
                }
                var bitmap:Bitmap=node as Bitmap;
                if(bitmap) {
                    var data:BitmapData=bitmap.bitmapData;
                    record.bitmap={id:nodeId(data),smoothing:bitmap.smoothing,snapping:bitmap.pixelSnapping};
                    if(data) {
                        record.bitmap.width=data.width;record.bitmap.height=data.height;record.bitmap.transparent=data.transparent;
                        var pixels:int=data.width*data.height;
                        if(pixels+result.hashPixels<=4000000) {
                            var values:Vector.<uint>=data.getVector(data.rect),hash:uint=5381;
                            for(var k:int=0;k<values.length;++k)hash=uint(Number(hash)*33)^values[k];
                            record.bitmap.hash=hash;result.hashPixels+=pixels;
                        } else result.errors.push("Bitmap hash budget exceeded");
                    }
                }
                var clip:MovieClip=node as MovieClip;
                if(clip)record.clip={frame:clip.currentFrame,total:clip.totalFrames,playing:clip.isPlaying};
                var textField:TextField=node as TextField;
                if(textField)record.text={text:textField.text,embed:textField.embedFonts,aa:textField.antiAliasType,
                    grid:textField.gridFitType,sharpness:textField.sharpness,thickness:textField.thickness};
                result.nodes.push(record);
                var parent:DisplayObjectContainer=node as DisplayObjectContainer;
                if(parent)for(var i:int=0;i<parent.numChildren;++i)inspectNode(parent.getChildAt(i),result,path+"/"+i,depth+1);
            } catch(error:Error){result.errors.push(path+": "+error.message);}
        }
        private function rectState(value:Rectangle):Object {
            return value==null?null:{x:value.x,y:value.y,width:value.width,height:value.height};
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
