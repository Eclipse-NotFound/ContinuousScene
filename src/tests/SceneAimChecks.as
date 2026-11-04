package tests {
    /** Deterministic aim-look checks over a fake world. No stage, no game
     * loop: every frame is a direct SceneAimController.update call with the
     * native camera values re-seeded first, mirroring the real ordering where
     * the native Camera.calc recenters before our ENTER_FRAME(-200) pan.
     *
     * The interactive contract these checks lock down (CS 0.9.9):
     *  - a cursor inside the view never steers; only a short rest against a
     *    screen edge latches a look direction,
     *  - the latched look persists while the cursor aims anywhere inside the
     *    widened view, so the player can shoot without losing the distance,
     *  - the pan follows a critically damped curve: a small first step, no
     *    per-frame jump above the safety cap and no overshoot,
     *  - the panned viewport is re-ensured through the host scene tick,
     *  - the screen->world identity stays exact for both the rendered view and
     *    the value the native calc derives next frame. */
    public class SceneAimChecks {
        public static function run(type:Class):Array {
            var rows:Array=[];
            function check(name:String,ok:Boolean,detail:String=""):void {rows.push({name:name,ok:ok});if(!ok)throw new Error("Aim: "+name+" "+detail);}
            function near(a:Number,b:Number,tol:Number):Boolean {return a>=b-tol&&a<=b+tol;}
            var preVX:Number=0,preVY:Number=0;
            function makeWorld():Object {
                var visual:Object={x:0,y:0};
                var satsVis:Object={x:0,y:0};
                var ticks:Object={n:0};
                return {cam:{moved:true,camRun:false,showOn:false,vx:-500,vy:-400,maxvx:3000,maxvy:2000,
                        scaleV:1,quakeX:0,quakeY:0,screenX:1920,screenY:1000,celX:960,celY:500},
                    visual:visual,sats:{active:false,vis:satsVis},
                    grafon:{sceneLarge:true,visSats:{visible:false},ticks:ticks,
                        sceneTick:function():void {++ticks.n;}},
                    ctr:{keyLook:false},t_exit:0,allStat:1,onPause:false,onConsol:false,celX:0,celY:0};
            }
            // Hold-to-look controller: every geometry scenario below drives the
            // press/release pair, so it opts out of the 0.9.9 toggle default.
            function hold():* {var o:*=new type();o.toggleMode=false;return o;}
            // One simulated frame: native calc re-centers, then the pan runs.
            function frame(c:*,w:Object,mx:Number,my:Number):Boolean {
                w.cam.vx=-500;w.cam.vy=-400;
                preVX=w.cam.vx;preVY=w.cam.vy;
                return c.update(w,mx,my);
            }
            function tickCount(w:Object):int {return int(w.grafon.ticks.n);}
            var CX:Number=960,CY:Number=500;
            // Screen-edge cursor positions (0 is the very edge: depth 1.0).
            var RIGHT:Number=1919,LEFT:Number=0,BOTTOM:Number=999;

            // -- idle, and the decoupling invariant ------------------------------
            var w:Object=makeWorld();
            var c:*=hold();
            check("idle-no-apply",c.update(w,CX,CY)==false&&c.offsetX==0&&c.offsetY==0);
            check("idle-no-viewport-sync",tickCount(w)==0,"ticks "+tickCount(w));
            c.keyDown(18,false,false,false);
            var midApplied:int=0;
            for(var i:int=0;i<60;i++){if(frame(c,w,CX+220,CY))midApplied++;}
            check("cursor-inside-view-never-steers",midApplied==0&&c.offsetX==0&&c.offsetY==0,
                "applied "+midApplied+" off "+c.offsetX+","+c.offsetY);
            check("deadzone-never-steers",frame(c,w,CX+120,CY-100)==false&&c.offsetX==0);
            check("no-latch-recorded",int(c.statsSnapshot().latches)==0,"latches "+c.statsSnapshot().latches);
            // The rest timer survives a cursor that strays back inside the view:
            // only a centred cursor or a different edge re-arms it. This is what
            // lets an isolated probe drive its own cursor while the entry keeps
            // calling update() with the real one.
            c=hold();w=makeWorld();
            c.keyDown(18,false,false,false);
            frame(c,w,RIGHT,CY);
            frame(c,w,CX,CY+300);          // inside the view, not centred
            frame(c,w,RIGHT+0,CY);
            frame(c,w,CX,CY+300);
            frame(c,w,RIGHT,CY);
            check("dwell-survives-inview-pass",c.offsetX>0&&int(c.statsSnapshot().latches)==1,
                "off "+c.offsetX+" latches "+c.statsSnapshot().latches);
            frame(c,w,CX,CY);              // centred cursor re-arms the latch
            check("deadzone-rearms-dwell",c.lookAnchored&&c.offsetX>0,
                "anchored should hold once latched");

            // -- edge latch: delay, direction, per-frame cap ---------------------
            c=hold();w=makeWorld();
            c.keyDown(18,false,false,false);
            var firstApplied:int=-1,firstStep:Number=0,prevX:Number=0;
            var maxStepSeen:Number=0,maxStepAt:int=-1,maxX:Number=0,lastStep:Number=0;
            for(i=1;i<=70;i++) {
                var wasApplied:Boolean=frame(c,w,RIGHT,CY);
                if(wasApplied&&firstApplied<0) {firstApplied=i;firstStep=c.offsetX;}
                var step:Number=c.offsetX-prevX;
                if(step>maxStepSeen){maxStepSeen=step;maxStepAt=i;}
                lastStep=step;
                prevX=c.offsetX;
                if(c.offsetX>maxX)maxX=c.offsetX;
            }
            check("edge-latch-needs-rest",firstApplied>=2&&firstApplied<=5,"frame "+firstApplied);
            check("edge-latch-pans-right",c.offsetX>650&&near(c.offsetY,0,1.5),
                "off "+c.offsetX+","+c.offsetY);
            check("latched-once-per-entry",int(c.statsSnapshot().latches)==1,
                "latches "+c.statsSnapshot().latches);
            // A first-order lerp used to start at 154px (and then stall at the
            // 50px hard cap); the spring must ease in from well under that.
            check("first-step-is-small",firstStep>2&&firstStep<60,"first "+firstStep);
            check("first-step-under-quarter-of-target",firstStep<700*0.25,"first "+firstStep);
            check("spring-accelerates-then-settles",maxStepAt>firstApplied&&lastStep<maxStepSeen*0.5,
                "peak frame "+maxStepAt+" step "+maxStepSeen+" last "+lastStep);
            check("per-frame-cap-respected",maxStepSeen<=90,"maxStep "+maxStepSeen);
            check("no-overshoot",maxX<=700.999,"maxX "+maxX);
            check("viewport-sync-runs-while-panned",tickCount(w)>40,"ticks "+tickCount(w));

            // -- the pan persists while the crosshair works inside the view ------
            var heldX:Number=c.offsetX;
            for(i=0;i<30;i++)frame(c,w,CX,CY);
            check("latch-survives-cursor-to-centre",near(c.offsetX,heldX,1.5)&&c.offsetY==0,
                "off "+c.offsetX+" was "+heldX);
            for(i=0;i<30;i++)frame(c,w,CX+320,CY+120);
            check("crosshair-free-inside-view",near(c.offsetX,heldX,1.5),
                "off "+c.offsetX+" after in-view aim");
            // Aim at a target on the far side of the panned view: still no swing.
            for(i=0;i<30;i++)frame(c,w,CX-420,CY-260);
            check("crosshair-free-across-view",near(c.offsetX,heldX,1.5),
                "off "+c.offsetX+" after opposite in-view aim");
            check("world-map-follows-pan",near(Number(w.celX),Number(w.cam.celX)-preVX,0.01)&&
                near(Number(w.celX),CX-420-Number(w.cam.vx),1.01),
                "wcelX "+w.celX+" cel "+w.cam.celX+" cam "+w.cam.vx+" pre "+preVX);

            // -- re-latch on the opposite edge -----------------------------------
            for(i=0;i<4;i++)frame(c,w,LEFT,CY);
            for(i=0;i<70;i++)frame(c,w,LEFT,CY);
            check("re-latch-opposite-edge",c.offsetX<-650&&int(c.statsSnapshot().latches)==2,
                "off "+c.offsetX+" latches "+c.statsSnapshot().latches);

            // -- release ---------------------------------------------------------
            c.keyUp(18);
            var returningFrames:int=0;
            var lastOff:Number=c.offsetX;
            var monotone:Boolean=true;
            for(i=0;i<90;i++) {
                if(frame(c,w,LEFT,CY))returningFrames++;
                if(c.offsetX<lastOff-0.01)monotone=false;
                lastOff=c.offsetX;
            }
            check("release-returns-to-zero",c.offsetX==0&&c.offsetY==0&&returningFrames>5,
                "frames "+returningFrames+" off "+c.offsetX);
            check("release-is-monotone",monotone);
            check("release-restores-cursor",near(Number(w.cam.celX),LEFT,0.01),
                "celX "+w.cam.celX+" want "+LEFT);

            // -- vertical latch and distance depth -------------------------------
            c=hold();w=makeWorld();
            c.keyDown(18,false,false,false);
            for(i=0;i<70;i++)frame(c,w,CX,BOTTOM);
            check("bottom-edge-latches-down",c.offsetY>350&&near(c.offsetX,0,1.5),
                "off "+c.offsetX+","+c.offsetY);
            c.keyUp(18);
            for(i=0;i<90;i++)frame(c,w,CX,CY);

            c=hold();w=makeWorld();
            c.keyDown(18,false,false,false);
            for(i=0;i<70;i++)frame(c,w,1920-1-80,CY); // just inside the band start
            check("band-depth-scales-distance",c.offsetX>250&&c.offsetX<420,
                "off "+c.offsetX);

            // A second update() in the same frame must not stack the pan: the
            // isolated probe supplies its own cursor on top of the entry's call.
            c=hold();w=makeWorld();
            c.keyDown(18,false,false,false);
            for(i=0;i<70;i++)frame(c,w,RIGHT,CY);
            c.update(w,RIGHT,CY); // same frame, no native recentre in between
            // The base must stay the pre-pan value: a stacked pan would put
            // vx near -500-2*700 instead of -500-offX.
            check("double-update-does-not-stack",
                near(Number(w.cam.vx),-500-c.offsetX,0.01)&&near(Number(w.celX),RIGHT-Number(w.cam.vx),1.01),
                "vx "+w.cam.vx+" off "+c.offsetX+" celX "+w.celX);
            c.keyUp(18);
            for(i=0;i<90;i++)frame(c,w,CX,CY);
            check("double-update-releases",c.offsetX==0&&c.offsetY==0);

            c=hold();w=makeWorld();
            w.cam.maxvx=600;
            c.keyDown(18,false,false,false);
            for(i=0;i<70;i++){w.cam.vx=-5;w.cam.vy=-400;preVX=w.cam.vx;preVY=w.cam.vy;c.update(w,RIGHT,CY);}
            check("right-edge-clamped",w.cam.vx==-600&&near(Number(w.celX),RIGHT+600,1.01),
                "vx "+w.cam.vx+" celX "+w.celX);
            c=hold();w=makeWorld();
            w.cam.maxvx=6000;
            c.keyDown(18,false,false,false);
            for(i=0;i<70;i++){w.cam.vx=-5;w.cam.vy=-400;preVX=w.cam.vx;preVY=w.cam.vy;c.update(w,LEFT,CY);}
            check("left-edge-clamped",w.cam.vx==0&&near(Number(w.celX),LEFT,1.01),
                "vx "+w.cam.vx+" celX "+w.celX);
            c=hold();w=makeWorld();
            w.cam.maxvy=-1; // map shorter than screen at this zoom
            c.keyDown(18,false,false,false);
            for(i=0;i<70;i++)frame(c,w,CX,BOTTOM);
            check("short-map-y-no-pan",w.cam.vy==-400&&w.visual.y==-400,"vy "+w.cam.vy);

            // -- interlocks -------------------------------------------------------
            var suspend:Object=makeWorld();
            var sc:*=hold();
            sc.keyDown(18,false,false,false);
            for(i=0;i<70;i++)frame(sc,suspend,RIGHT,CY);
            check("pre-suspend-applied",sc.offsetX>600,"offX "+sc.offsetX);
            suspend.sats.active=true;
            check("sats-suspends-resets",sc.update(suspend,RIGHT,CY)==false&&sc.offsetX==0);
            suspend.sats.active=false;
            for(i=0;i<70;i++)frame(sc,suspend,RIGHT,CY);
            suspend.grafon.visSats.visible=true;
            check("sats-overlay-suspends",sc.update(suspend,RIGHT,CY)==false&&sc.offsetX==0);
            suspend.grafon.visSats.visible=false;
            for(i=0;i<70;i++)frame(sc,suspend,RIGHT,CY);
            suspend.ctr.keyLook=true;
            check("native-look-suspends",sc.update(suspend,RIGHT,CY)==false&&sc.offsetX==0);
            suspend.ctr.keyLook=false;
            for(i=0;i<70;i++)frame(sc,suspend,RIGHT,CY);
            suspend.allStat=2;
            check("world-inactive-suspends",sc.update(suspend,RIGHT,CY)==false&&sc.offsetX==0);
            suspend.allStat=1;
            for(i=0;i<70;i++)frame(sc,suspend,RIGHT,CY);
            suspend.grafon.sceneLarge=false;
            check("not-scene-suspends",sc.update(suspend,RIGHT,CY)==false&&sc.offsetX==0);
            suspend.grafon.sceneLarge=true;
            for(i=0;i<70;i++)frame(sc,suspend,RIGHT,CY);
            suspend.cam.moved=false;
            check("static-camera-suspends",sc.update(suspend,RIGHT,CY)==false&&sc.offsetX==0);
            suspend.cam.moved=true;
            for(i=0;i<70;i++)frame(sc,suspend,RIGHT,CY);
            suspend.cam.camRun=true;
            check("scripted-camera-suspends",sc.update(suspend,RIGHT,CY)==false&&sc.offsetX==0);
            suspend.cam.camRun=false;
            for(i=0;i<70;i++)frame(sc,suspend,RIGHT,CY);
            sc.enabled=false;
            check("disabled-suspends",sc.update(suspend,RIGHT,CY)==false&&sc.offsetX==0);
            sc.enabled=true;
            for(i=0;i<70;i++)frame(sc,suspend,RIGHT,CY);
            check("resumes-after-gate-clears",sc.offsetX>600,"offX "+sc.offsetX);

            // -- input: toggle default, auto-repeat, custom binding, slots -------
            var tw:Object=makeWorld();
            var tc:*=new type(); // production defaults: toggle mode on
            check("toggle-is-the-default",tc.toggleMode&&tc.statsSnapshot().toggleMode);
            tc.keyDown(18,false,false,false); // toggle ON
            tc.keyDown(18,false,false,false); // auto-repeat must not flip again
            check("toggle-repeat-safe",tc.aimActive()&&tc.statsSnapshot().toggles==1);
            for(i=0;i<70;i++)frame(tc,tw,RIGHT,CY);
            check("toggle-stays-on-release",tc.offsetX>650,"offX "+tc.offsetX);
            tc.keyUp(18); // no effect in toggle mode
            check("toggle-ignores-keyup",tc.aimActive()&&tc.offsetX>650);
            tc.keyDown(18,false,false,false); // toggle OFF
            var fade:int=0;
            for(i=0;i<90;i++){if(frame(tc,tw,CX,CY))fade++;}
            check("toggle-off-returns",tc.offsetX==0&&!tc.aimActive()&&fade>5);
            tc.keyDown(18,false,false,false);
            tc.deactivate();
            check("deactivate-clears-toggle",!tc.aimActive()&&!tc.triggerHeld());

            var kw:Object=makeWorld();
            var kc:*=hold();
            kc.keybind={code:75,ctrl:true,alt:false,shift:false};
            for(i=0;i<60;i++)frame(kc,kw,RIGHT,CY);
            check("bare-key-ignored",kc.offsetX==0);
            kc.keyDown(75,true,false,false);
            for(i=0;i<70;i++)frame(kc,kw,RIGHT,CY);
            check("combo-binding-pans",kc.offsetX>600,"offX "+kc.offsetX);
            kc.keyUp(75);
            for(i=0;i<90;i++)frame(kc,kw,CX,CY);
            check("combo-release-returns",kc.offsetX==0);

            var mw:Object=makeWorld();
            var mc:*=hold();
            mc.triggerModifier=1; // Ctrl slot
            mc.keyDown(18,false,false,false);
            for(i=0;i<40;i++)frame(mc,mw,RIGHT,CY);
            check("alt-ignored-in-ctrl-slot",mc.offsetX==0,"offX "+mc.offsetX);
            mc.keyUp(18);mc.keyDown(17,false,false,false);
            for(i=0;i<70;i++)frame(mc,mw,RIGHT,CY);
            check("ctrl-pans-in-ctrl-slot",mc.offsetX>600,"offX "+mc.offsetX);
            mc.keyUp(17);
            var nc:*=hold();
            nc.triggerModifier=2; // none: modifiers off, custom only
            var nw:Object=makeWorld();
            nc.keyDown(18,false,false,false);nc.keyDown(17,false,false,false);
            for(i=0;i<60;i++)frame(nc,nw,RIGHT,CY);
            check("none-slot-ignores-modifiers",nc.offsetX==0);

            // -- render extras & tuning ------------------------------------------
            var qw:Object=makeWorld();
            var qc:*=hold();
            qc.keyDown(18,false,false,false);
            for(i=0;i<70;i++){qw.cam.vx=-500;qw.cam.vy=-400;qw.cam.quakeX=12;qw.cam.quakeY=-7;qc.update(qw,RIGHT,CY);}
            check("quake-passthrough",qw.visual.x==qw.cam.vx+12&&qw.visual.y==qw.cam.vy-7,
                "vis "+qw.visual.x+","+qw.visual.y+" cam "+qw.cam.vx+","+qw.cam.vy);
            qc.keyUp(18);
            for(i=0;i<90;i++){qw.cam.vx=-500;qw.cam.vy=-400;qc.update(qw,CX,CY);}
            var zw:Object=makeWorld();
            var zc:*=hold();
            zw.cam.scaleV=0.5;
            zc.keyDown(18,false,false,false);
            for(i=0;i<70;i++)frame(zc,zw,RIGHT,CY);
            check("zoom-mouse-mapping",near(Number(zw.celX),(Number(zw.cam.celX)-preVX)/0.5,0.01),
                "wcelX "+zw.celX+" expect "+((Number(zw.cam.celX)-preVX)/0.5));
            zc.keyUp(18);
            var dw:Object=makeWorld();
            var dc:*=hold();
            dc.distanceScale=0.5;
            dc.keyDown(18,false,false,false);
            for(i=0;i<70;i++)frame(dc,dw,RIGHT,CY);
            check("distance-scale-halved",near(dc.offsetX,350,3)&&near(dc.offsetY,0,1.5),
                "off "+dc.offsetX+","+dc.offsetY);
            dc.keyUp(18);
            // Speed: the faster profile reaches the same band sooner.
            var fn:Object=makeWorld();
            var fnormal:*=hold();
            fnormal.keyDown(18,false,false,false);
            var normalFrames:int=0;
            while(fnormal.offsetX<590&&normalFrames<200){frame(fnormal,fn,RIGHT,CY);normalFrames++;}
            var ff:Object=makeWorld();
            var ffast:*=hold();
            ffast.speedIndex=3;
            ffast.keyDown(18,false,false,false);
            var fastFrames:int=0;
            while(ffast.offsetX<590&&fastFrames<200){frame(ffast,ff,RIGHT,CY);fastFrames++;}
            check("fast-converges-sooner",fastFrames<normalFrames,"fast "+fastFrames+" normal "+normalFrames);
            var snap:Object=ffast.statsSnapshot();
            check("stats-snapshot-fields",snap.version is String&&snap.applied>0&&snap.aiming>0&&
                snap.edgeClamped>=0&&snap.viewportSyncs>0&&snap.latches>0&&snap.maxStep>0,
                "applied "+snap.applied+" syncs "+snap.viewportSyncs);
            disableSync(type);

            // -- native int-typed camera (live-verified silent truncation) ----
            var intCam:FakeIntCamera=new FakeIntCamera();
            var iw:Object={cam:intCam,visual:{x:0,y:0},sats:{active:false,vis:{x:0,y:0}},
                grafon:{sceneLarge:true,visSats:{visible:false},sceneTick:function():void {}},
                ctr:{keyLook:false},t_exit:0,allStat:1,onPause:false,onConsol:false,celX:0,celY:0};
            var ic:*=hold();
            ic.distanceScale=0.93; // deliberately produces fractional offsets
            ic.keyDown(18,false,false,false);
            for(i=0;i<80;i++){intCam.vx=-500;intCam.vy=-400;preVX=intCam.vx;preVY=intCam.vy;ic.update(iw,RIGHT,BOTTOM);}
            check("int-camera-panned",intCam.vx!=-500,"vx "+intCam.vx);
            check("int-camera-view-consistent",
                iw.visual.x==Number(intCam.vx)+intCam.quakeX&&iw.visual.y==Number(intCam.vy)+intCam.quakeY,
                "vis "+iw.visual.x+","+iw.visual.y+" cam "+intCam.vx+","+intCam.vy);
            check("int-camera-world-map",
                near(Number(iw.celX),RIGHT-Number(intCam.vx),1.01)&&
                near(Number(iw.celX),(Number(intCam.celX)-preVX)/intCam.scaleV,0.01),
                "wcel "+iw.celX+" render "+(RIGHT-Number(intCam.vx)));
            return rows;
        }

        /** The viewport hook is optional: disabling it must stop the scene
         * calls without changing the pan itself. */
        private static function disableSync(type:Class):void {
            var ticks:Object={n:0};
            var w:Object={cam:{moved:true,camRun:false,showOn:false,vx:-500,vy:-400,maxvx:3000,maxvy:2000,
                    scaleV:1,quakeX:0,quakeY:0,screenX:1920,screenY:1000,celX:960,celY:500},
                visual:{x:0,y:0},sats:{active:false,vis:{x:0,y:0}},celX:0,celY:0,
                ctr:{keyLook:false},t_exit:0,allStat:1,onPause:false,onConsol:false,
                grafon:{sceneLarge:true,visSats:{visible:false},ticks:ticks,
                    sceneTick:function():void {++ticks.n;}}};
            var c:*=new type();
            c.toggleMode=false;
            c.viewportSync=false;
            c.keyDown(18,false,false,false);
            for(var i:int=0;i<70;i++){w.cam.vx=-500;w.cam.vy=-400;c.update(w,1919,500);}
            if(int(ticks.n)!=0)throw new Error("Aim: viewport-sync-can-be-disabled " + ticks.n);
            if(c.offsetX<650)throw new Error("Aim: viewport-sync-can-be-disabled pan " + c.offsetX);
        }
    }
}
