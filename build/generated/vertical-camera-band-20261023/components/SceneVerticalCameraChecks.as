package tests {
    import flash.desktop.NativeApplication;
    import flash.display.Sprite;
    import flash.system.ApplicationDomain;
    import flash.utils.getQualifiedClassName;
    import flash.utils.getTimer;

    /** Terminal, synchronous Camera.calc geometry checks. Never a physics or FPS test. */
    public class SceneVerticalCameraChecks {
        private static const KEY:String="verticalCameraState";
        private static const VERSION:String="vertical-camera-band-1";
        private static const CAM_FIELDS:String="moved,screenX,screenY,X,Y,vx,vy,ovy,maxsx,maxsy,maxvx,maxvy,celX,celY,camRun,otryv,quakeX,quakeY,isZoom,scaleV,scaleS,dblack,showOn,showX,showY";
        private static const PLAYER_FIELDS:String="X,Y,X1,X2,Y1,Y2,scY";
        private static const DISPLAY_FIELDS:String="x,y,scaleX,scaleY,visible,alpha";

        public static function run(w:*, check:Function=null, expectCandidate:Boolean=true):Object {
            var started:int=getTimer();
            var out:Object={version:"vertical-camera-components-1",diagnosticOnly:true,
                performanceEligible:false,terminalOnly:true,expectCandidate:expectCandidate,
                passed:false,cases:[],restore:{passed:false},limitations:[
                    "Synchronous logical camera geometry, not native movement, jumping, streaming, visual pixels, or performance.",
                    "Grafon.loc is temporarily null: the real calc still calls sceneTick, whose native null-location guard returns before terrain preparation/culling.",
                    "Camera screenX/screenY are logical fixtures. The real Stage dimensions and World.swfStage reference are never changed; setLoc is not called.",
                    "scY is the full collision height. Bounds checks cover the collision body, not hair, weapon artwork, wings, filters, or HUD occlusion.",
                    "The real zoom key creates an expected GUI notification with private timers. It is not restored; terminate this isolated process without saving or performance sampling.",
                    "The real quake case consumes native Math.random values; the inaccessible RNG state cannot be restored. No extra random draws are introduced by this helper.",
                    "Location identity checks use an existing native Location with physics paused; they are not a real travel/load lifecycle acceptance test.",
                    "For a viewport too short for the native +100 foot anchor, fallback equality is tested; universal player visibility is not claimed."
                ]};
            var cam:*=null, player:*=null, loc:*=null, grafon:*=null, carrier:*=null, api:*=null;
            var wc:Class=null, snd:Class=null, ad:ApplicationDomain=null;
            var saves:Array=[], displaySaves:Array=[];
            var originalState:*=null, hadState:Boolean=false, apiSaved:Boolean=false;
            var originalAPI:*=null, originalCamera:*=null, originalLoc:*=null;
            var stageRef:*=null, stageWidth:int=0, stageHeight:int=0;
            var ctx:Object=null;
            try {
                var app:String=NativeApplication.nativeApplication.applicationID;
                if(app.indexOf("pfe-modsettings-continuous-motion-")!=0)
                    throw new Error("An isolated continuous-motion application is required");
                if(!w || !w.main || !w.gg || !w.cam || !w.loc || !w.grafon || !w.ctr)
                    throw new Error("The native world, camera and player must already be initialized");
                ad=w.main.loaderInfo.applicationDomain;
                wc=ad.getDefinition("fe.World") as Class;
                snd=ad.getDefinition("fe.Snd") as Class;
                if(readPublic(wc,"w")!==w)throw new Error("The supplied world is not the actual host-domain World.w");
                var nativeCameraClass:Class=ad.getDefinition("fe.inter.Camera") as Class;
                if(Object(w.cam).constructor!==nativeCameraClass)
                    throw new Error("The camera does not belong to the native host domain");
                cam=w.cam;player=w.gg;loc=w.loc;grafon=w.grafon;
                if(!grafon.sceneLarge || grafon.loc!==loc || !(loc.limX>=4000 && loc.limY>=2400))
                    throw new Error("A real initialized continuous scene with an interior test area is required");
                carrier=w.main.getChildByName("ContinuousSceneCarrier");
                if(!carrier || !("nativeAPI" in carrier) || carrier["nativeAPI"]==null
                    || carrier["nativeAPI"].constructor!==Object)
                    throw new Error("The existing native API must be a plain Object");
                api=carrier["nativeAPI"];originalAPI=api;apiSaved=true;
                hadState=api.hasOwnProperty(KEY);originalState=api[KEY];
                originalCamera=cam;originalLoc=loc;
                stageRef=w.swfStage;stageWidth=stageRef.stageWidth;stageHeight=stageRef.stageHeight;
                save(saves,w,"onPause,cam,loc,celX,celY,log");
                save(saves,cam,CAM_FIELDS);save(saves,player,PLAYER_FIELDS);
                save(saves,w.ctr,"keyLook,keyZoom");save(saves,loc,"sky");
                save(saves,grafon,"loc,sceneLarge");save(saves,snd,"centrX,centrY");
                save(saves,wc,"w");
                for each(var display:* in [w.visual,w.sats.vis,w.vscene,w.vblack,
                    grafon.ramT,grafon.ramB,grafon.ramL,grafon.ramR]) {
                    if(!display)throw new Error("A native camera display dependency is absent");
                    save(displaySaves,display,DISPLAY_FIELDS);
                }
                // Delete before the first calc, so the original state object itself is never mutated.
                delete api[KEY];
                w.onPause=true;
                grafon.loc=null;
                ctx={w:w,cam:cam,player:player,loc:loc,grafon:grafon,api:api,
                    out:out,candidate:expectCandidate,calls:0,
                    x:Math.floor(loc.limX/2),y:Math.floor(loc.limY/2),height:Number(player.scY)};
                if(!isFinite(ctx.height) || ctx.height<=0 || ctx.height>=300)
                    throw new Error("The native collision height is outside this component fixture");
                out.applicationID=app;
                out.nativeIdentity={world:readPublic(wc,"w")===w,cameraClass:getQualifiedClassName(cam),
                    playerClass:getQualifiedClassName(player),locationClass:getQualifiedClassName(loc),
                    initialCollisionHeight:ctx.height,stageWidth:stageWidth,stageHeight:stageHeight};

                base(ctx);
                cam.Y=cam.ovy=ctx.y+25;
                step(ctx,"first-context-hard-reset",ctx.y,{state:true});
                var b:Number=band(cam,player);
                position(player,ctx.x,ctx.y-50);
                step(ctx,"rise-inside-band",ctx.y,{bodyVisible:true});
                position(player,ctx.x,ctx.y+50);
                step(ctx,"fall-inside-band",ctx.y,{bodyVisible:true});
                position(player,ctx.x,ctx.y-b-40);
                step(ctx,"rise-past-band",ctx.y-40,{bodyVisible:true});
                position(player,ctx.x,ctx.y+b+40);
                step(ctx,"fall-past-band",ctx.y+40,{bodyVisible:true});
                for(var repeat:int=0;repeat<3;++repeat)
                    step(ctx,"stationary-repeat-"+repeat,ctx.y+40,{bodyVisible:true});

                base(ctx);prime(ctx);
                position(player,ctx.x,ctx.y+cam.screenY*0.45);
                step(ctx,"fast-fall-hard-bound",player.Y-band(cam,player),{bodyVisible:true});
                position(player,ctx.x,ctx.y-cam.screenY);
                step(ctx,"far-vertical-teleport",player.Y,{bodyVisible:true});
                position(player,ctx.x+cam.screenX,player.Y+25);
                step(ctx,"far-horizontal-teleport-resets-y",player.Y,{bodyVisible:true});

                base(ctx);prime(ctx);
                cam.setZoom(2);
                step(ctx,"external-setZoom-2",player.Y*cam.scaleV,{state:true,bodyVisible:true});
                cam.setZoom(1);
                step(ctx,"external-setZoom-1",player.Y*cam.scaleV,{state:true,bodyVisible:true});
                cam.setZoom(0);
                step(ctx,"external-setZoom-0",player.Y,{state:true,bodyVisible:true});
                cam.ovy=int(player.Y*expectedZoom(cam,loc,1,wc)+25);
                w.ctr.keyZoom=true;
                step(ctx,"real-zoom-key",player.Y*expectedZoom(cam,loc,1,wc),
                    {state:true,bodyVisible:true,zoomConsumed:true});
                out.guiZoomNotificationProduced=true;

                base(ctx);prime(ctx);
                cam.Y=cam.ovy=int(player.Y+25);
                cam.screenX=1024;cam.screenY=720;cam.setZoom(0);
                step(ctx,"logical-viewport-resize",player.Y,{state:true,bodyVisible:true});
                base(ctx);prime(ctx);
                cam.screenY=300;cam.setZoom(0);
                step(ctx,"short-valid-viewport-reset",player.Y,{state:true,bodyVisible:true});
                position(player,ctx.x,ctx.y+75);
                step(ctx,"short-viewport-band-shrinks",player.Y-band(cam,player),{bodyVisible:true});
                cam.screenY=180;cam.setZoom(0);
                step(ctx,"too-short-viewport-native-fallback",NaN,{stateCleared:true});
                base(ctx);prime(ctx);
                player.scY=750;position(player,ctx.x,ctx.y-25);
                step(ctx,"collision-body-too-high-fallback",NaN,{stateCleared:true});

                base(ctx);prime(ctx);
                grafon.sceneLarge=false;position(player,ctx.x,ctx.y-25);
                step(ctx,"ordinary-scene-fallback",NaN,{stateCleared:true});
                grafon.sceneLarge=true;position(player,ctx.x,ctx.y-30);
                step(ctx,"return-to-large-scene-reset",player.Y,{state:true});
                loc.sky=true;
                step(ctx,"sky-native-fallback",NaN,{stateCleared:true});
                loc.sky=false;step(ctx,"leave-sky-reset",player.Y,{state:true});
                carrier["nativeAPI"]=null;position(player,ctx.x,player.Y-25);
                step(ctx,"missing-api-native-fallback",NaN,{});
                carrier["nativeAPI"]=api;delete api[KEY];
                step(ctx,"restored-api-fresh-context",player.Y,{state:true});

                base(ctx);prime(ctx);
                w.ctr.keyLook=true;cam.celY=cam.screenY-20;
                step(ctx,"native-keyLook",NaN,{look:true});
                w.ctr.keyLook=false;cam.otryv=0.4;
                step(ctx,"look-return-blend",NaN,{look:true});
                step(ctx,"look-reaches-zero-native-frame",NaN,{look:true});
                step(ctx,"first-frame-after-look-reset",player.Y,{state:true,look:false});
                cam.showOn=true;cam.showX=900;cam.showY=700;
                step(ctx,"native-script-show",NaN,{look:true});
                cam.showOn=false;cam.otryv=0;
                step(ctx,"script-show-exit-reset",player.Y,{state:true,look:false});
                cam.camRun=true;cam.Y=ctx.y+80;
                step(ctx,"native-camRun-preserved",NaN,{look:true});
                cam.camRun=false;
                step(ctx,"camRun-exit-reset",player.Y,{state:true,look:false});

                base(ctx);prime(ctx);
                position(player,ctx.x,player.scY+1);
                step(ctx,"top-map-edge",player.Y,{bodyVisible:true});
                position(player,ctx.x,loc.limY-1);
                step(ctx,"bottom-map-edge",player.Y,{bodyVisible:true});
                base(ctx);prime(ctx);
                cam.maxsy=cam.screenY/2;cam.maxvy=cam.maxsy-cam.screenY;
                step(ctx,"map-shorter-than-viewport",NaN,{stateCleared:true});
                base(ctx);prime(ctx);
                cam.moved=false;
                step(ctx,"nonmoving-camera-fallback",NaN,{stateCleared:true});

                base(ctx);prime(ctx);
                var alternate:*=null;
                var nativeState:*=api["state"] is Function ? api["state"](w.land) : null;
                if(nativeState && nativeState.regions is Array) {
                    for each(var region:Object in nativeState.regions) {
                        if(region && region.source!==loc && region.source!=null
                            && getQualifiedClassName(region.source)=="fe.loc::Location" && !region.source.sky) {
                            alternate=region.source;
                            out.alternateLocationSource="nativeAPI.state(land).regions[].source";
                            break;
                        }
                    }
                }
                if(!alternate) {
                    alternate=otherLocation(w.land ? w.land.locs : null,loc,0);
                    out.alternateLocationSource="existing land.locs";
                }
                if(alternate) {
                    cam.Y=cam.ovy=int(player.Y*cam.scaleV+25);
                    w.loc=alternate;
                    step(ctx,"existing-native-location-identity-change",player.Y,{state:true});
                    w.loc=loc;
                    step(ctx,"original-location-identity-restored",player.Y,{state:true});
                } else {
                    out.cases.push({name:"existing-native-location-identity-change",passed:false,
                        inconclusive:true,reason:"No second existing non-sky native Location; no location was fabricated"});
                }
                var cameraClass:Class=ad.getDefinition("fe.inter.Camera") as Class;
                var temporaryCamera:*=new cameraClass(w);
                w.cam=temporaryCamera;ctx.cam=temporaryCamera;
                configure(ctx,false);
                temporaryCamera.Y=temporaryCamera.ovy=int(player.Y+25);
                step(ctx,"native-camera-identity-change",player.Y,{state:true});
                w.cam=cam;ctx.cam=cam;
                cam.Y=cam.ovy=int(player.Y*cam.scaleV+25);
                step(ctx,"original-camera-identity-restored",player.Y,{state:true});

                base(ctx);prime(ctx);
                cam.screenY=300;cam.setZoom(0);
                step(ctx,"quake-fixture-viewport-reset",player.Y,{state:true});
                cam.quakeY=20;position(player,ctx.x,ctx.y+40);
                var quakeExpected:Number=Math.max(player.Y-band(cam,player),
                    Math.min(cam.ovy,player.Y+band(cam,player)));
                step(ctx,"native-quake-reserved-margin",quakeExpected,{bodyVisible:true,quakeBound:20});
                out.nativeRNGAdvanced=true;
                out.actualCalcCalls=ctx.calls;
            } catch(error:*) {
                out.error=String(error);
                if(error is Error)out.errorStack=(error as Error).getStackTrace();
            } finally {
                var failures:Array=[];
                restore(displaySaves,failures);
                restore(saves,failures);
                if(apiSaved) {
                    try {
                        carrier["nativeAPI"]=originalAPI;
                        if(hadState)originalAPI[KEY]=originalState;
                        else delete originalAPI[KEY];
                        if(carrier["nativeAPI"]!==originalAPI
                            || originalAPI.hasOwnProperty(KEY)!==hadState
                            || (hadState && originalAPI[KEY]!==originalState))
                            failures.push("nativeAPI/state identity restoration failed");
                    } catch(apiError:*) {failures.push("nativeAPI: "+String(apiError));}
                }
                if(stageRef) {
                    if(w.swfStage!==stageRef || stageRef.stageWidth!=stageWidth || stageRef.stageHeight!=stageHeight)
                        failures.push("The real stage identity/dimensions changed");
                }
                out.restore={passed:failures.length==0,errors:failures,
                    nativeAPIIdentity:apiSaved && carrier["nativeAPI"]===originalAPI,
                    playerIdentity:player!=null && w.gg===player,
                    cameraIdentity:originalCamera!=null && w.cam===originalCamera,
                    locationIdentity:originalLoc!=null && w.loc===originalLoc,
                    hostWorldIdentity:wc!=null && readPublic(wc,"w")===w,
                    excluded:["Expected native zoom GUI notification/private timer","Native quake RNG consumption"]};
            }
            out.elapsedMs=getTimer()-started;
            out.passed=out.error==null && out.cases.length>0 && out.restore.passed;
            for each(var row:Object in out.cases)if(!row.passed)out.passed=false;
            if(check!=null) {
                for each(row in out.cases)check("vertical-camera-"+row.name,Boolean(row.passed),row);
                check("vertical-camera-components-restored",Boolean(out.restore.passed),out.restore);
            }
            return out;
        }

        private static function base(ctx:Object):void {
            ctx.w.cam=ctx.cam;ctx.w.loc=ctx.loc;ctx.grafon.sceneLarge=true;ctx.loc.sky=false;
            ctx.player.scY=ctx.height;position(ctx.player,ctx.x,ctx.y);
            configure(ctx,true);
        }

        private static function configure(ctx:Object,clearState:Boolean):void {
            var c:*=ctx.cam;
            c.moved=true;c.screenX=1280;c.screenY=800;
            c.maxsx=ctx.loc.limX;c.maxsy=ctx.loc.limY;
            c.maxvx=c.maxsx-c.screenX;c.maxvy=c.maxsy-c.screenY;
            c.scaleV=1;c.scaleS=Math.min(c.screenX/1920,c.screenY/1000);c.isZoom=0;
            c.X=int(ctx.player.X);c.Y=c.ovy=int(ctx.player.Y);
            c.vx=int(-c.X+c.screenX/2);c.vy=int(-c.Y+c.screenY/2+100);
            c.celX=640;c.celY=400;c.camRun=false;c.otryv=0;c.quakeX=c.quakeY=0;
            c.showOn=false;c.showX=-1;c.showY=0;c.dblack=0;
            ctx.w.ctr.keyLook=false;ctx.w.ctr.keyZoom=false;
            ctx.w.visual.scaleX=ctx.w.visual.scaleY=ctx.w.sats.vis.scaleX=ctx.w.sats.vis.scaleY=1;
            if(clearState)delete ctx.api[KEY];
        }

        private static function prime(ctx:Object):void {
            step(ctx,"prime-"+ctx.calls,ctx.player.Y*ctx.cam.scaleV,{state:true});
        }

        private static function position(p:*,x:Number,y:Number):void {
            p.X=x;p.Y=y;p.X1=x-p.scX/2;p.X2=x+p.scX/2;p.Y1=y-p.scY;p.Y2=y;
        }

        private static function band(c:*,p:*):Number {
            var f:Number=c.screenY/2+100,m:Number=2+Math.abs(c.quakeY);
            return Math.max(0,Math.min(160,c.screenY*.18,f-p.scY*c.scaleV-m,c.screenY-m-f));
        }

        private static function expectedZoom(c:*,loc:*,zoom:int,wc:Class):Number {
            var large:Boolean=loc!=null && (loc.spaceX>readPublic(wc,"cellsX") || loc.spaceY>readPublic(wc,"cellsY"));
            var s:Number=1;
            if(zoom==1)s=Math.max(c.screenX/(large?1920:c.maxsx),c.screenY/(large?1000:c.maxsy));
            else if(zoom==2)s=Math.min(c.screenX/(large?1920:c.maxsx),c.screenY/(large?1000:c.maxsy));
            return s>.98?1:s;
        }

        // Native expression oracle: candidate fixtures provide their separate expected Y.
        private static function nativeExpected(ctx:Object):Object {
            var c:*=ctx.cam,p:*=ctx.player,w:*=ctx.w;
            var s:Number=Number(c.scaleV),maxvx:Number=c.maxvx,maxvy:Number=c.maxvy;
            if(w.ctr.keyZoom) {
                var zoom:int=w.loc && w.loc.sky ? 2 : (c.isZoom+1>2?0:c.isZoom+1);
                var wc:Class=w.main.loaderInfo.applicationDomain.getDefinition("fe.World") as Class;
                s=expectedZoom(c,w.loc,zoom,wc);
                maxvx=int(c.maxsx*s-c.screenX);maxvy=int(c.maxsy*s-c.screenY);
            }
            var x:int=c.X,y:int=c.Y,ovy:int=c.ovy,vx:int=c.vx,vy:int=c.vy;
            var look:Number=c.otryv,showX:Number=c.showX;
            if(c.moved) {
                if((w.ctr.keyLook || c.showOn) && look<1)look+=c.showOn?.2:.05;
                if(!w.ctr.keyLook && !c.showOn && look>0)look=Math.max(0,look-.2);
                if(w.ctr.keyLook)showX=-1;
                if(!c.camRun) {
                    if(look>0) {
                        x=int(p.X*s+look*((showX>=0?showX:c.celX)-c.screenX/2)*(showX>=0?1.3:1));
                        y=int(p.Y*s+look*((showX>=0?c.showY:c.celY)-c.screenY/2)*(showX>=0?1.3:1));
                    } else {
                        x=int(p.X*s);
                        var delta:Number=c.ovy-p.Y*s;
                        y=int(delta>5 && delta<50 ? c.ovy-delta/4 : p.Y*s);
                    }
                }
                ovy=y;
                vx=maxvx<0?int(-maxvx/2):int(Math.max(-maxvx,Math.min(0,-x+c.screenX/2)));
                vy=maxvy<0?int(-maxvy/2):int(Math.max(-maxvy,Math.min(0,-y+c.screenY/2+100)));
            }
            return {X:x,Y:y,ovy:ovy,vx:vx,vy:vy,otryv:look,showX:showX,scale:s,maxvy:maxvy};
        }

        private static function step(ctx:Object,name:String,candidateY:Number,requirements:Object):void {
            var c:*=ctx.cam,p:*=ctx.player,w:*=ctx.w;
            var expected:Object=nativeExpected(ctx),beforeBand:Number=band(c,p);
            var selected:Boolean=ctx.candidate && isFinite(candidateY);
            if(selected) {
                expected.Y=int(candidateY);expected.ovy=expected.Y;
                expected.vy=expected.maxvy<0?int(-expected.maxvy/2)
                    :int(Math.max(-expected.maxvy,Math.min(0,-expected.Y+c.screenY/2+100)));
            }
            var originalPlayer:Object=values(p,PLAYER_FIELDS);
            var before:Object={Y:c.Y,ovy:c.ovy,vy:c.vy,playerY:p.Y,scY:p.scY,
                scale:c.scaleV,screenY:c.screenY,band:beforeBand,quakeY:c.quakeY};
            c.calc(p);++ctx.calls;
            var failed:Array=[];
            for each(var field:String in ["X","Y","ovy","vx","vy","showX"])
                if(c[field]!==expected[field])failed.push(field+": "+c[field]+" != "+expected[field]);
            if(Math.abs(c.otryv-expected.otryv)>1e-10)failed.push("native look interpolation changed");
            if(!sameValues(p,originalPlayer))failed.push("Camera.calc changed the player collision geometry");
            // DisplayObject setters may quantize fractional local coordinates.
            // Use the real independent setter/getter, never a relaxed tolerance.
            var rawTranslation:Object={x:c.vx+c.quakeX,y:c.vy+c.quakeY};
            var translationOracle:Sprite=new Sprite();
            translationOracle.x=rawTranslation.x;translationOracle.y=rawTranslation.y;
            if(w.visual.x!==translationOracle.x || w.visual.y!==translationOracle.y
                || w.sats.vis.x!==w.visual.x || w.sats.vis.y!==w.visual.y)
                failed.push("World/SATS presentation translation is not synchronized");
            if(Math.abs(w.celX-(c.celX-c.vx)/c.scaleV)>1e-8
                || Math.abs(w.celY-(c.celY-c.vy)/c.scaleV)>1e-8)
                failed.push("Native screen-to-world aim conversion changed");
            var snd:Class=w.main.loaderInfo.applicationDomain.getDefinition("fe.Snd") as Class;
            if(readPublic(snd,"centrX")!==c.X || readPublic(snd,"centrY")!==c.Y)failed.push("Native audio center changed");
            var state:*=ctx.api[KEY];
            if(ctx.candidate && requirements.state) {
                if(!state || state.version!==VERSION || state.camera!==c || state.loc!==w.loc
                    || state.scale!==Number(c.scaleV) || state.screenX!==c.screenX || state.screenY!==c.screenY
                    || state.lastPlayerX!==p.X || state.lastPlayerY!==p.Y)
                    failed.push("Candidate context does not match the live camera/location/player");
            }
            if(ctx.candidate && requirements.stateCleared && state!=null)
                failed.push("Candidate context was retained outside its eligibility");
            if(ctx.candidate && requirements.hasOwnProperty("look")
                && (!state || Boolean(state.lookActive)!==Boolean(requirements.look)))
                failed.push("Candidate observation/camRun history was not recorded");
            var top:Number=(p.Y-p.scY)*c.scaleV+c.vy+c.quakeY;
            var bottom:Number=p.Y*c.scaleV+c.vy+c.quakeY;
            if(requirements.bodyVisible && (top<0 || bottom>c.screenY))failed.push("Collision body is outside the logical viewport");
            if(requirements.zoomConsumed && (w.ctr.keyZoom || c.isZoom!=1))failed.push("Real zoom key was not consumed/cycled");
            if(requirements.zoomConsumed && (w.visual.scaleX!==c.scaleV || w.visual.scaleY!==c.scaleV
                || w.sats.vis.scaleX!==c.scaleV || w.sats.vis.scaleY!==c.scaleV))
                failed.push("Native zoom display scale is not synchronized");
            if(requirements.hasOwnProperty("quakeBound") && Math.abs(c.quakeY)>requirements.quakeBound)
                failed.push("Native quake unexpectedly increased in magnitude");
            if(ctx.grafon.loc!==null)failed.push("Terrain streaming was not isolated");
            ctx.out.cases.push({name:name,passed:failed.length==0,errors:failed,before:before,
                expectedY:expected.Y,expectedVy:expected.vy,candidateExpectation:selected,
                after:{X:c.X,Y:c.Y,ovy:c.ovy,vx:c.vx,vy:c.vy,scale:c.scaleV,
                    screenY:c.screenY,quakeY:c.quakeY,collisionTop:top,collisionBottom:bottom,
                    rawTranslation:rawTranslation,
                    setterTranslation:{x:translationOracle.x,y:translationOracle.y},
                    visualTranslation:{x:w.visual.x,y:w.visual.y},
                    satsTranslation:{x:w.sats.vis.x,y:w.sats.vis.y},
                    look:c.otryv,statePresent:state!=null,stateLook:state?state.lookActive:null}});
        }

        private static function otherLocation(value:*,current:*,depth:int):* {
            if(value==null || depth>3)return null;
            if(value!==current && getQualifiedClassName(value)=="fe.loc::Location" && !value.sky)return value;
            if(value is Array)for each(var child:* in value) {
                var found:*=otherLocation(child,current,depth+1);
                if(found!=null)return found;
            }
            return null;
        }

        private static function values(target:*,fields:String):Object {
            var result:Object={};
            for each(var field:String in fields.split(","))result[field]=readPublic(target,field);
            return result;
        }

        private static function save(list:Array,target:*,fields:String):void {
            list.push({target:target,values:values(target,fields)});
        }

        private static function sameValues(target:*,expected:Object):Boolean {
            for(var field:String in expected) {
                var a:*=readPublic(target,field),b:*=expected[field];
                if(a!==b && !(a is Number && b is Number && isNaN(a) && isNaN(b)))return false;
            }
            return true;
        }

        private static function restore(list:Array,errors:Array):void {
            for(var index:int=list.length-1;index>=0;--index) {
                var entry:Object=list[index];
                for(var field:String in entry.values) {
                    try {writePublic(entry.target,field,entry.values[field]);}
                    catch(error:*) {errors.push(field+": "+String(error));}
                }
                try {if(!sameValues(entry.target,entry.values))errors.push("Restored property comparison failed");}
                catch(compareError:*) {errors.push("Restore comparison: "+String(compareError));}
            }
        }

        // Host fields in this helper are public. A QName prevents the probe's
        // package namespace (tests::) from binding an unresolved Class member.
        private static function readPublic(target:*,field:String):* {
            return target[new QName("",field)];
        }

        private static function writePublic(target:*,field:String,value:*):void {
            target[new QName("",field)]=value;
        }
    }
}
