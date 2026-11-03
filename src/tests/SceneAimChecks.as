package tests {
    /** Deterministic aim-look checks over a fake world. No stage, no game
     * loop: every frame is a direct SceneAimController.update call with the
     * native camera values re-seeded first, mirroring the real ordering where
     * the native Camera.calc recenters before our ENTER_FRAME(-200) pan. */
    public class SceneAimChecks {
        public static function run(type:Class):Array {
            var rows:Array=[];
            function check(name:String,ok:Boolean,detail:String=""):void {rows.push({name:name,ok:ok});if(!ok)throw new Error("Aim: "+name+" "+detail);}
            function near(a:Number,b:Number,tol:Number):Boolean {return a>=b-tol&&a<=b+tol;}
            function makeWorld():Object {
                var visual:Object={x:0,y:0};
                var satsVis:Object={x:0,y:0};
                return {cam:{moved:true,camRun:false,showOn:false,vx:-500,vy:-400,maxvx:3000,maxvy:2000,
                        scaleV:1,quakeX:0,quakeY:0,screenX:1920,screenY:1000,celX:960,celY:500},
                    visual:visual,sats:{active:false,vis:satsVis},
                    grafon:{sceneLarge:true,visSats:{visible:false}},
                    ctr:{keyLook:false},t_exit:0,allStat:1,onPause:false,onConsol:false,celX:0,celY:0};
            }
            // One simulated frame: native calc re-centers, then the pan runs.
            function frame(c:*,w:Object,mx:Number,my:Number):Boolean {
                w.cam.vx=-500;w.cam.vy=-400;
                return c.update(w,mx,my);
            }
            var CX:Number=960,CY:Number=500;
            var c:*=new type();

            // -- idle & deadzone -------------------------------------------------
            var w:Object=makeWorld();
            check("idle-no-apply",c.update(w,CX,CY)==false&&c.offsetX==0&&c.offsetY==0);
            c.keyDown(18,false,false,false); // hold Alt
            var held:int=0;
            for(var i:int=0;i<30;i++){if(frame(c,w,CX+100,CY-100))held++;}
            check("deadzone-hold-zero",held==0&&c.offsetX==0&&c.offsetY==0,"offsets "+c.offsetX+","+c.offsetY);
            var started:int=0;
            for(i=0;i<120;i++){if(frame(c,w,CX+200,CY))started++;}
            check("beyond-deadzone-pans",started>0&&c.offsetX>0,"offX "+c.offsetX);
            // 200px mouse: t=(50/350)^1.4 — verifies the power curve itself.
            var midExpect:Number=700*Math.pow(50/350,1.4);
            check("small-push-power-curve",near(c.offsetX,midExpect,1.5)&&c.offsetY==0,
                "offX "+c.offsetX+" want "+midExpect);
            c.keyUp(18);
            var back:int=0;
            for(i=0;i<60;i++){if(frame(c,w,CX,CY))back++;}
            check("release-returns-to-zero",c.offsetX==0&&c.offsetY==0&&back>0);

            // -- full push: direction, magnitude, first-frame clamp -------------
            c=new type();w=makeWorld();
            c.keyDown(18,false,false,false);
            var appliedFirst:Boolean=frame(c,w,CX+800,CY+400);
            check("first-frame-applies",appliedFirst);
            check("first-frame-step-clamp",c.offsetX==50&&near(c.offsetY,37.4,1.5),
                "off "+c.offsetX+","+c.offsetY);
            for(i=0;i<140;i++)frame(c,w,CX+800,CY+400);
            var ux:Number=800/Math.sqrt(800*800+400*400);
            var uy:Number=400/Math.sqrt(800*800+400*400);
            check("corner-target-converges",near(c.offsetX,700*ux,6)&&near(c.offsetY,380*uy,6),
                "off "+c.offsetX+","+c.offsetY+" want "+(700*ux)+","+(380*uy));
            check("apply-consistency",w.cam.vx==-500-c.offsetX&&w.cam.vy==-400-c.offsetY&&
                w.visual.x==w.cam.vx&&w.visual.y==w.cam.vy&&w.sats.vis.x==w.cam.vx,
                "vx "+w.cam.vx+" offX "+c.offsetX);
            check("mouse-mapping-shifted",w.cam.celX==CX+800+(-500-w.cam.vx)&&
                w.celX==(w.cam.celX-w.cam.vx)/1,
                "celX "+w.cam.celX+" wcelX "+w.celX);
            c.keyUp(18);
            for(i=0;i<60;i++)frame(c,w,CX,CY);
            check("corner-release-zero",c.offsetX==0&&c.offsetY==0);

            c=new type();w=makeWorld();
            c.keyDown(18,false,false,false);
            for(i=0;i<140;i++)frame(c,w,CX-800,CY-400);
            check("direction-flips",c.offsetX<0&&c.offsetY<0,"off "+c.offsetX+","+c.offsetY);

            // -- world clamp ------------------------------------------------------
            c=new type();w=makeWorld();
            w.cam.maxvx=600;
            c.keyDown(18,false,false,false);
            for(i=0;i<140;i++){w.cam.vx=-5;w.cam.vy=-400;c.update(w,CX+800,CY);}
            check("right-edge-clamped",w.cam.vx==-600&&near(w.cam.celX,CX+800+595,0.01),
                "vx "+w.cam.vx+" celX "+w.cam.celX);
            c=new type();w=makeWorld();
            w.cam.maxvx=6000;
            c.keyDown(18,false,false,false);
            for(i=0;i<140;i++){w.cam.vx=-5;w.cam.vy=-400;c.update(w,CX-800,CY);}
            check("left-edge-clamped",w.cam.vx==0&&near(w.cam.celX,CX-800-5,0.01),
                "vx "+w.cam.vx+" celX "+w.cam.celX);
            c=new type();w=makeWorld();
            w.cam.maxvy=-1; // map shorter than screen at this zoom
            c.keyDown(18,false,false,false);
            for(i=0;i<140;i++)frame(c,w,CX,CY+400);
            check("short-map-y-no-pan",w.cam.vy==-400&&w.visual.y==-400,"vy "+w.cam.vy);
            c.keyUp(18);

            // -- interlocks -------------------------------------------------------
            var suspend:Object=makeWorld();
            var sc:*=new type();
            sc.keyDown(18,false,false,false);
            for(i=0;i<140;i++)frame(sc,suspend,CX+800,CY);
            check("pre-suspend-applied",sc.offsetX>500,"offX "+sc.offsetX);
            suspend.sats.active=true;
            check("sats-suspends-resets",sc.update(suspend,CX+800,CY)==false&&sc.offsetX==0);
            suspend.sats.active=false;
            for(i=0;i<140;i++)frame(sc,suspend,CX+800,CY);
            suspend.grafon.visSats.visible=true;
            check("sats-overlay-suspends",sc.update(suspend,CX+800,CY)==false&&sc.offsetX==0);
            suspend.grafon.visSats.visible=false;
            for(i=0;i<140;i++)frame(sc,suspend,CX+800,CY);
            suspend.ctr.keyLook=true;
            check("native-look-suspends",sc.update(suspend,CX+800,CY)==false&&sc.offsetX==0);
            suspend.ctr.keyLook=false;
            for(i=0;i<140;i++)frame(sc,suspend,CX+800,CY);
            suspend.allStat=2;
            check("world-inactive-suspends",sc.update(suspend,CX+800,CY)==false&&sc.offsetX==0);
            suspend.allStat=1;
            for(i=0;i<140;i++)frame(sc,suspend,CX+800,CY);
            suspend.grafon.sceneLarge=false;
            check("not-scene-suspends",sc.update(suspend,CX+800,CY)==false&&sc.offsetX==0);
            suspend.grafon.sceneLarge=true;
            for(i=0;i<140;i++)frame(sc,suspend,CX+800,CY);
            suspend.cam.moved=false;
            check("static-camera-suspends",sc.update(suspend,CX+800,CY)==false&&sc.offsetX==0);
            suspend.cam.moved=true;
            for(i=0;i<140;i++)frame(sc,suspend,CX+800,CY);
            suspend.cam.camRun=true;
            check("scripted-camera-suspends",sc.update(suspend,CX+800,CY)==false&&sc.offsetX==0);
            suspend.cam.camRun=false;
            for(i=0;i<140;i++)frame(sc,suspend,CX+800,CY);
            sc.enabled=false;
            check("disabled-suspends",sc.update(suspend,CX+800,CY)==false&&sc.offsetX==0);
            sc.enabled=true;
            for(i=0;i<140;i++)frame(sc,suspend,CX+800,CY);
            check("resumes-after-gate-clears",sc.offsetX>500,"offX "+sc.offsetX);

            // -- input: toggle, auto-repeat, custom binding, modifier slots -----
            var tw:Object=makeWorld();
            var tc:*=new type();
            tc.toggleMode=true;
            tc.keyDown(18,false,false,false); // toggle ON
            tc.keyDown(18,false,false,false); // auto-repeat must not flip again
            check("toggle-repeat-safe",tc.aimActive()&&tc.statsSnapshot().toggles==1);
            for(i=0;i<140;i++)frame(tc,tw,CX+800,CY);
            check("toggle-stays-on-release",tc.offsetX>500,"offX "+tc.offsetX);
            tc.keyUp(18); // no effect in toggle mode
            check("toggle-ignores-keyup",tc.aimActive());
            tc.keyDown(18,false,false,false); // toggle OFF
            var fade:int=0;
            for(i=0;i<60;i++){if(frame(tc,tw,CX,CY))fade++;}
            check("toggle-off-returns",tc.offsetX==0&&!tc.aimActive()&&fade>0);
            tc.keyDown(18,false,false,false);
            tc.deactivate();
            check("deactivate-clears-toggle",!tc.aimActive()&&!tc.triggerHeld());

            var kw:Object=makeWorld();
            var kc:*=new type();
            kc.keybind={code:75,ctrl:true,alt:false,shift:false};
            for(i=0;i<60;i++)frame(kc,kw,CX+800,CY);
            check("bare-key-ignored",kc.offsetX==0);
            kc.keyDown(75,true,false,false);
            for(i=0;i<140;i++)frame(kc,kw,CX+800,CY);
            check("combo-binding-pans",kc.offsetX>500,"offX "+kc.offsetX);
            kc.keyUp(75);
            for(i=0;i<60;i++)frame(kc,kw,CX+800,CY);
            check("combo-release-returns",kc.offsetX==0);

            var mw:Object=makeWorld();
            var mc:*=new type();
            mc.triggerModifier=1; // Ctrl slot
            mc.keyDown(18,false,false,false);
            for(i=0;i<90;i++)frame(mc,mw,CX+800,CY);
            check("alt-ignored-in-ctrl-slot",mc.offsetX==0,"offX "+mc.offsetX);
            mc.keyUp(18);mc.keyDown(17,false,false,false);
            for(i=0;i<90;i++)frame(mc,mw,CX+800,CY);
            check("ctrl-pans-in-ctrl-slot",mc.offsetX>500,"offX "+mc.offsetX);
            mc.keyUp(17);
            var nc:*=new type();
            nc.triggerModifier=2; // none: modifiers off, custom only
            var nw:Object=makeWorld();
            nc.keyDown(18,false,false,false);nc.keyDown(17,false,false,false);
            for(i=0;i<90;i++)frame(nc,nw,CX+800,CY);
            check("none-slot-ignores-modifiers",nc.offsetX==0);

            // -- render extras & tuning ------------------------------------------
            var qw:Object=makeWorld();
            var qc:*=new type();
            qc.keyDown(18,false,false,false);
            qw.cam.quakeX=12;qw.cam.quakeY=-7;
            for(i=0;i<140;i++)frame(qc,qw,CX+800,CY);
            check("quake-passthrough",qw.visual.x==qw.cam.vx+12&&qw.visual.y==qw.cam.vy-7,
                "vis "+qw.visual.x+","+qw.visual.y+" cam "+qw.cam.vx+","+qw.cam.vy);
            qc.keyUp(18);
            for(i=0;i<60;i++)frame(qc,qw,CX,CY);
            var zw:Object=makeWorld();
            var zc:*=new type();
            zw.cam.scaleV=0.5;
            zc.keyDown(18,false,false,false);
            for(i=0;i<140;i++)frame(zc,zw,CX+800,CY);
            check("zoom-mouse-mapping",zw.celX==(zw.cam.celX-zw.cam.vx)/0.5,
                "wcelX "+zw.celX+" expect "+((zw.cam.celX-zw.cam.vx)/0.5));
            zc.keyUp(18);
            var dw:Object=makeWorld();
            var dc:*=new type();
            dc.distanceScale=0.5;
            dc.keyDown(18,false,false,false);
            for(i=0;i<140;i++)frame(dc,dw,CX+800,CY);
            check("distance-scale-halved",near(dc.offsetX,350,6)&&dc.offsetY==0,
                "off "+dc.offsetX+","+dc.offsetY);
            dc.keyUp(18);
            // Speed: fast must reach the same band in strictly fewer frames.
            var fn:Object=makeWorld();
            var fnormal:*=new type();
            fnormal.keyDown(18,false,false,false);
            var normalFrames:int=0;
            while(fnormal.offsetX<590&&normalFrames<200){frame(fnormal,fn,CX+800,CY);normalFrames++;}
            var ff:Object=makeWorld();
            var ffast:*=new type();
            ffast.speedIndex=3;
            ffast.keyDown(18,false,false,false);
            var fastFrames:int=0;
            while(ffast.offsetX<590&&fastFrames<200){frame(ffast,ff,CX+800,CY);fastFrames++;}
            check("fast-converges-sooner",fastFrames<normalFrames,"fast "+fastFrames+" normal "+normalFrames);
            var snap:Object=ffast.statsSnapshot();
            check("stats-snapshot-fields",snap.version is String&&snap.applied>0&&snap.aiming>0&&snap.edgeClamped>=0);

            // -- native int-typed camera (live-verified silent truncation) ----
            var intCam:FakeIntCamera=new FakeIntCamera();
            var iw:Object={cam:intCam,visual:{x:0,y:0},sats:{active:false,vis:{x:0,y:0}},
                grafon:{sceneLarge:true,visSats:{visible:false}},ctr:{keyLook:false},
                t_exit:0,allStat:1,onPause:false,onConsol:false,celX:0,celY:0};
            var ic:*=new type();
            ic.distanceScale=0.93; // deliberately produces fractional offsets
            ic.keyDown(18,false,false,false);
            for(i=0;i<180;i++){intCam.vx=-500;intCam.vy=-400;ic.update(iw,CX+800,CY+400);}
            check("int-camera-panned",intCam.vx!=-500,"vx "+intCam.vx);
            check("int-camera-view-consistent",
                iw.visual.x==Number(intCam.vx)+intCam.quakeX&&iw.visual.y==Number(intCam.vy)+intCam.quakeY,
                "vis "+iw.visual.x+","+iw.visual.y+" cam "+intCam.vx+","+intCam.vy);
            check("int-camera-mouse-consistent",
                iw.celX==(Number(intCam.celX)-Number(intCam.vx))/intCam.scaleV&&
                iw.celY==(Number(intCam.celY)-Number(intCam.vy))/intCam.scaleV,
                "wcel "+iw.celX+","+iw.celY+" cel "+intCam.celX+","+intCam.celY);
            return rows;
        }
    }
}
