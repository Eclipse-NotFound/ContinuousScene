package tests {
    import flash.display.Sprite;
    import flash.events.KeyboardEvent;

    /** Deterministic aim-look checks over a fake world. No stage, no game
     * loop: every frame is a direct SceneAimController.update call with the
     * native camera values re-seeded first, mirroring the real ordering where
     * the native Camera.calc recenters before our ENTER_FRAME(-200) pan.
     *
     * The interactive contract these checks lock down (CS 0.9.10):
     *  - the trigger key is cancelled before the runtime can hand it to the OS
     *    (a bare Alt that is not cancelled activates the Win32 window menu and
     *    the app loses the mouse until the player clicks inside it),
     *  - the extension is a continuous, monotone function of how far the cursor
     *    is pushed out, reaching exactly full extension at any screen edge,
     *  - once the player has pushed and held, aiming anywhere inside the view
     *    does not move or shrink the view, while pushing back out to the rim
     *    re-aims the direction,
     *  - a one-frame sweep to the rim does not park the camera there,
     *  - the trigger comes down through hold, toggle and tap/hold modes,
     *  - the pan follows a critically damped curve: a small first step, no
     *    per-frame jump above the safety cap and no overshoot,
     *  - the panned viewport is re-ensured through the host scene tick,
     *  - the screen->world identity stays exact for both the rendered view and
     *    the value the native calc derives next frame. */
    public class SceneAimChecks {
        private static const CX:Number=960;
        private static const CY:Number=500;
        private static const RIGHT:Number=1919;
        private static const LEFT:Number=0;
        private static const BOTTOM:Number=999;
        private static const TOP:Number=1;
        /** sqrt(960^2+500^2): half-diagonal of the 1920x1000 fixture screen. */
        private static const MAXD:Number=1082.404;
        private static const DEAD:Number=MAXD*SceneAimController.DEADZONE_FRAC;
        /** Analytic extension for a cursor offset of d pixels along an axis
         * whose screen-rectangle radius is rectR. */
        private static function ext(d:Number,rectR:Number):Number {
            var span:Number=rectR-DEAD;
            var u:Number=span>1?((d-DEAD)/span):1;
            if(u<0)u=0; else if(u>1)u=1;
            return Math.pow(u,SceneAimController.DEPTH_EXP);
        }

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
            // Hold-to-look controller: most scenarios drive the press/release
            // pair, so they opt out of the mode plumbing explicitly.
            function hold():* {var o:*=new type();o.aimMode=SceneAimController.MODE_HOLD;return o;}
            // One simulated frame: native calc re-centers, then the pan runs.
            function frame(c:*,w:Object,mx:Number,my:Number):Boolean {
                w.cam.vx=-500;w.cam.vy=-400;
                preVX=w.cam.vx;preVY=w.cam.vy;
                return c.update(w,mx,my);
            }
            function tickCount(w:Object):int {return int(w.grafon.ticks.n);}
            /** Fresh controller, press Alt, run n frames at a fixed cursor. */
            function push(dx:Number,dy:Number,n:int,speed:int=2):* {
                var w:Object=makeWorld();
                var c:*=hold();
                c.speedIndex=speed;
                c.keyDown(18,false,false,false);
                for(var i:int=0;i<n;i++)frame(c,w,CX+dx,CY+dy);
                return {c:c,w:w};
            }
            var i:int;

            // -- idle, and the decoupling invariant ------------------------------
            var w:Object=makeWorld();
            var c:*=hold();
            check("idle-no-apply",c.update(w,CX,CY)==false&&c.offsetX==0&&c.offsetY==0);
            check("idle-no-viewport-sync",tickCount(w)==0,"ticks "+tickCount(w));
            c.keyDown(18,false,false,false);
            for(i=0;i<40;i++)frame(c,w,CX+60,CY);
            check("deadzone-never-steers",c.offsetX==0&&c.offsetY==0&&c.reason=="aim-near-center",
                "off "+c.offsetX+","+c.offsetY+" reason "+c.reason);
            check("no-look-recorded",int(c.statsSnapshot().pushes)==0,"pushes "+c.statsSnapshot().pushes);
            c.keyUp(18);

            // -- continuous distance lever --------------------------------------
            // The whole point of V3: pushing the cursor further out must extend
            // the view further, smoothly and predictably, everywhere between the
            // centre and the rim - not only inside a 90px band at the edge.
            var samples:Array=[150,250,350,450,550,650,750,850,959];
            var previous:Number=-1;
            var monotone:Boolean=true;
            var worstError:Number=0;
            for each(var d:int in samples) {
                var probe:*=push(d,0,90);
                var got:Number=probe.c.offsetX;
                var want:Number=700*ext(d,960);
                if(got<previous)monotone=false;
                previous=got;
                var err:Number=Math.abs(got-want);
                if(err>worstError)worstError=err;
                probe.c.keyUp(18);
            }
            check("distance-lever-is-monotone",monotone,"last "+previous);
            check("distance-lever-matches-curve",worstError<3,"worst error "+worstError.toFixed(2));
            check("edge-is-full-extension",near(previous,699.3,3),"edge "+previous.toFixed(2));
            var mid:*=push(400,0,90);
            check("mid-push-is-proportional",near(mid.c.offsetX,189.3,3),
                "off "+mid.c.offsetX.toFixed(2)+" want "+189.3);
            mid.c.keyUp(18);
            // Any edge, not just the horizontal one: 100% at the bottom edge.
            var low:*=push(0,499,90);
            check("vertical-edge-is-full",near(low.c.offsetY,378.8,3)&&near(low.c.offsetX,0,1.5),
                "off "+low.c.offsetX.toFixed(2)+","+low.c.offsetY.toFixed(2));
            low.c.keyUp(18);
            // Direction is a unit vector: the pan keeps the 700:380 axis ratio.
            var corner:*=push(959,499,90);
            check("diagonal-keeps-axis-ratio",near(corner.c.offsetX,620.2,4)&&near(corner.c.offsetY,175.2,4),
                "off "+corner.c.offsetX.toFixed(2)+","+corner.c.offsetY.toFixed(2));
            corner.c.keyUp(18);

            // -- spring curve ----------------------------------------------------
            var cap:*=push(959,0,70);
            var cc:*=cap.c;
            check("edge-deposit",cc.offsetX>650,"off "+cc.offsetX);
            cc.keyUp(18);
            var run2:*=makeWorld();
            var spring:*=hold();
            spring.keyDown(18,false,false,false);
            var firstStep:Number=-1,maxStepSeen:Number=0,maxStepAt:int=-1,maxX:Number=0;
            var prevX:Number=0,steps:Array=[];
            for(i=1;i<=70;i++) {
                frame(spring,run2,RIGHT,CY);
                var step:Number=spring.offsetX-prevX;
                if(i==1)firstStep=spring.offsetX;
                if(step>maxStepSeen) {maxStepSeen=step;maxStepAt=i;}
                steps.push(step);
                prevX=spring.offsetX;
                if(spring.offsetX>maxX)maxX=spring.offsetX;
            }
            check("first-step-is-small",firstStep>2&&firstStep<20,"first "+firstStep.toFixed(2));
            check("spring-accelerates",Number(steps[2])>Number(steps[0])&&Number(steps[4])>Number(steps[2]),
                "steps "+steps[0]+" "+steps[2]+" "+steps[4]);
            check("per-frame-cap-respected",maxStepSeen<=90,"maxStep "+maxStepSeen.toFixed(2));
            check("peak-then-settle",maxStepAt>2&&maxStepSeen<60,"peak frame "+maxStepAt+" step "+maxStepSeen.toFixed(2));
            check("no-overshoot",maxX<=700.001,"maxX "+maxX);
            check("viewport-sync-runs-while-panned",tickCount(run2)>40,"ticks "+tickCount(run2));

            // -- aim stability: the whole reason the extension is sticky -------
            var heldX:Number=spring.offsetX;
            var aimW:*=run2;
            for(i=0;i<40;i++)frame(spring,aimW,CX,CY);
            check("aim-at-centre-keeps-view",near(spring.offsetX,heldX,1.5)&&spring.offsetY==0,
                "off "+spring.offsetX+" was "+heldX);
            for(i=0;i<40;i++)frame(spring,aimW,CX+320,CY+120);
            check("aim-inside-view-keeps-view",near(spring.offsetX,heldX,1.5),
                "off "+spring.offsetX+" after in-view aim");
            // Aiming across to the far side of the view: the camera must not
            // swing around just because the crosshair crossed the centre.
            for(i=0;i<40;i++)frame(spring,aimW,CX-420,CY-260);
            check("aim-across-view-keeps-view",near(spring.offsetX,heldX,1.5)&&near(spring.offsetY,0,1.5),
                "off "+spring.offsetX+","+spring.offsetY+" after opposite in-view aim");
            check("world-map-follows-pan",near(Number(aimW.celX),Number(aimW.cam.celX)-preVX,0.01)&&
                near(Number(aimW.celX),CX-420-Number(aimW.cam.vx),1.01),
                "wcelX "+aimW.celX+" cel "+aimW.cam.celX+" cam "+aimW.cam.vx+" pre "+preVX);

            // -- re-steer by pushing to another rim ------------------------------
            var lastAngle:Number=Math.atan2(spring.lookDirectionY,spring.lookDirectionX);
            var maxTurn:Number=0;
            for(i=0;i<90;i++) {
                frame(spring,aimW,CX,TOP);
                var angle:Number=Math.atan2(spring.lookDirectionY,spring.lookDirectionX);
                var turn:Number=Math.abs(angle-lastAngle);
                while(turn>Math.PI)turn=Math.PI*2-turn;
                if(turn>maxTurn)maxTurn=turn;
                lastAngle=angle;
            }
            check("rim-push-resteers-up",near(spring.offsetY,-379,5)&&near(spring.offsetX,0,5),
                "off "+spring.offsetX.toFixed(2)+","+spring.offsetY.toFixed(2));
            check("resteer-is-slewed",maxTurn<=SceneAimController.SLEW_DEG*Math.PI/180+0.002,
                "max turn "+maxTurn+" deg "+maxTurn*180/Math.PI);

            // -- a one-frame sweep must not park the camera ----------------------
            var flickW:Object=makeWorld();
            var flick:*=hold();
            flick.keyDown(18,false,false,false);
            frame(flick,flickW,RIGHT,CY);            // single frame at the rim
            for(i=0;i<90;i++)frame(flick,flickW,CX+300,CY);
            check("flick-does-not-park",near(flick.offsetX,700*ext(300,960),3),
                "off "+flick.offsetX.toFixed(2)+" want "+(700*ext(300,960)).toFixed(2));
            flick.keyUp(18);
            for(i=0;i<90;i++)frame(flick,flickW,CX+300,CY);
            // A deliberate push does park, and only the trigger brings it down.
            var held:*=push(959,0,30);
            for(i=0;i<120;i++)frame(held.c,held.w,CX+300,CY);
            check("deliberate-push-parks",held.c.offsetX>650,
                "off "+held.c.offsetX.toFixed(2));
            // Depth never ratchets down inside one look, but a re-push further
            // out still extends it.
            for(i=0;i<90;i++)frame(held.c,held.w,CX+959,CY);
            check("re-push-keeps-full",held.c.offsetX>698,"off "+held.c.offsetX.toFixed(2));

            // -- release ---------------------------------------------------------
            held.c.keyUp(18);
            var returningFrames:int=0;
            var lastOff:Number=held.c.offsetX;
            var back:Boolean=true;
            for(i=0;i<120;i++) {
                if(frame(held.c,held.w,CX+959,CY))returningFrames++;
                if(held.c.offsetX>lastOff+0.01)back=false;
                lastOff=held.c.offsetX;
            }
            check("release-returns-to-zero",held.c.offsetX==0&&held.c.offsetY==0&&returningFrames>5,
                "frames "+returningFrames+" off "+held.c.offsetX);
            check("release-is-monotone",back);
            check("release-restores-cursor",near(Number(held.w.cam.celX),CX+959,0.01),
                "celX "+held.w.cam.celX);

            // A second update() in the same frame must not stack the pan.
            var twice:*=push(959,0,70);
            twice.c.update(twice.w,CX+959,CY);
            check("double-update-does-not-stack",
                near(Number(twice.w.cam.vx),-500-twice.c.offsetX,0.01)&&
                near(Number(twice.w.celX),CX+959-Number(twice.w.cam.vx),1.01),
                "vx "+twice.w.cam.vx+" off "+twice.c.offsetX+" celX "+twice.w.celX);
            twice.c.keyUp(18);

            // -- world clamps ----------------------------------------------------
            var cw:Object=makeWorld();
            cw.cam.maxvx=600;
            var clampC:*=hold();
            clampC.keyDown(18,false,false,false);
            for(i=0;i<70;i++) {cw.cam.vx=-5;cw.cam.vy=-400;preVX=cw.cam.vx;preVY=cw.cam.vy;clampC.update(cw,RIGHT,CY);}
            check("right-edge-clamped",cw.cam.vx==-600&&near(Number(cw.celX),RIGHT+600,1.01),
                "vx "+cw.cam.vx+" celX "+cw.celX);
            var lw:Object=makeWorld();
            lw.cam.maxvx=6000;
            var lc:*=hold();
            lc.keyDown(18,false,false,false);
            for(i=0;i<70;i++) {lw.cam.vx=-5;lw.cam.vy=-400;preVX=lw.cam.vx;preVY=lw.cam.vy;lc.update(lw,LEFT,CY);}
            check("left-edge-clamped",lw.cam.vx==0&&near(Number(lw.celX),LEFT,1.01),
                "vx "+lw.cam.vx+" celX "+lw.celX);
            var sw:Object=makeWorld();
            sw.cam.maxvy=-1; // map shorter than screen at this zoom
            var shc:*=hold();
            shc.keyDown(18,false,false,false);
            for(i=0;i<70;i++)frame(shc,sw,CX,BOTTOM);
            check("short-map-y-no-pan",sw.cam.vy==-400&&sw.visual.y==-400,"vy "+sw.cam.vy);

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

            // -- trigger modes ----------------------------------------------------
            var mw:Object=makeWorld();
            var hc:*=new type();
            check("hold-is-the-default",hc.aimMode==SceneAimController.MODE_HOLD&&!hc.toggleMode&&
                hc.statsSnapshot().aimMode==0);
            hc.keyDown(18,false,false,false);
            for(i=0;i<70;i++)frame(hc,mw,RIGHT,CY);
            check("hold-pans-while-held",hc.offsetX>650,"offX "+hc.offsetX);
            hc.keyUp(18);
            var gone:int=0;
            for(i=0;i<120;i++){if(frame(hc,mw,RIGHT,CY))gone++;}
            check("hold-release-returns",hc.offsetX==0&&gone>5&&!hc.aimActive(),"frames "+gone);

            var tw:Object=makeWorld();
            var tc:*=new type();
            tc.aimMode=SceneAimController.MODE_TOGGLE;
            tc.keyDown(18,false,false,false); // toggle ON
            tc.keyDown(18,false,false,false); // auto-repeat must not flip again
            check("toggle-repeat-safe",tc.aimActive()&&tc.statsSnapshot().toggles==1);
            for(i=0;i<70;i++)frame(tc,tw,RIGHT,CY);
            check("toggle-stays-on-release",tc.offsetX>650,"offX "+tc.offsetX);
            tc.keyUp(18); // no effect in toggle mode
            check("toggle-ignores-keyup",tc.aimActive()&&tc.offsetX>650);
            tc.keyDown(18,false,false,false); // toggle OFF
            var fade:int=0;
            tc.keyUp(18);
            for(i=0;i<120;i++){if(frame(tc,tw,CX,CY))fade++;}
            check("toggle-off-returns",tc.offsetX==0&&!tc.aimActive()&&fade>5,"frames "+fade);
            tc.keyDown(18,false,false,false);
            tc.deactivate();
            check("deactivate-clears-toggle",!tc.aimActive()&&!tc.triggerHeld());
            tc.deactivate();

            // Smart mode: a tap latches, holding stays temporary.
            var sw2:Object=makeWorld();
            var sm:*=new type();
            sm.aimMode=SceneAimController.MODE_SMART;
            var now:Number=1000;
            sm.clock=function():Number {return now;};
            sm.keyDown(18,false,false,false);
            check("smart-hold-is-active",sm.aimActive());
            now=1100;
            sm.keyUp(18);
            check("smart-tap-latches",sm.aimActive()&&sm.statsSnapshot().toggles==1);
            for(i=0;i<70;i++)frame(sm,sw2,RIGHT,CY);
            check("smart-latch-pans",sm.offsetX>650,"offX "+sm.offsetX);
            now=3000;
            sm.keyDown(18,false,false,false);
            now=3700; // a long press is temporary, not another toggle
            sm.keyUp(18);
            check("smart-long-press-is-temporary",sm.aimActive()&&sm.statsSnapshot().toggles==1);
            now=5000;
            sm.keyDown(18,false,false,false);
            now=5100;
            sm.keyUp(18);
            check("smart-tap-unlatches",!sm.aimActive());

            // -- custom binding and modifier slots --------------------------------
            var kw:Object=makeWorld();
            var kc:*=hold();
            kc.keybind={code:75,ctrl:true,alt:false,shift:false};
            for(i=0;i<60;i++)frame(kc,kw,RIGHT,CY);
            check("bare-key-ignored",kc.offsetX==0);
            kc.keyDown(75,true,false,false);
            for(i=0;i<70;i++)frame(kc,kw,RIGHT,CY);
            check("combo-binding-pans",kc.offsetX>600,"offX "+kc.offsetX);
            kc.keyUp(75);
            for(i=0;i<120;i++)frame(kc,kw,CX,CY);
            check("combo-release-returns",kc.offsetX==0);

            var ctrlW:Object=makeWorld();
            var mc:*=hold();
            mc.triggerModifier=1; // Ctrl slot
            mc.keyDown(18,false,false,false);
            for(i=0;i<40;i++)frame(mc,ctrlW,RIGHT,CY);
            check("alt-ignored-in-ctrl-slot",mc.offsetX==0,"offX "+mc.offsetX);
            mc.keyUp(18);mc.keyDown(17,false,false,false);
            for(i=0;i<70;i++)frame(mc,ctrlW,RIGHT,CY);
            check("ctrl-pans-in-ctrl-slot",mc.offsetX>600,"offX "+mc.offsetX);
            mc.keyUp(17);
            var nc:*=hold();
            nc.triggerModifier=2; // none: modifiers off, custom only
            var nw:Object=makeWorld();
            nc.keyDown(18,false,false,false);nc.keyDown(17,false,false,false);
            for(i=0;i<60;i++)frame(nc,nw,RIGHT,CY);
            check("none-slot-ignores-modifiers",nc.offsetX==0);

            // -- OS-level key cancellation ---------------------------------------
            // The Alt-pulls-the-mouse-out bug: an uncancelled bare Alt reaches
            // the Win32 window menu. These two checks are the regression test.
            var dispatcher:Sprite=new Sprite();
            var keyC:*=hold();
            keyC.install(dispatcher);
            var altDown:KeyboardEvent=new KeyboardEvent(KeyboardEvent.KEY_DOWN,true,true,0,18);
            dispatcher.dispatchEvent(altDown);
            check("alt-keydown-cancelled",altDown.isDefaultPrevented());
            check("alt-still-reaches-controller",keyC.triggerHeld());
            var altUp:KeyboardEvent=new KeyboardEvent(KeyboardEvent.KEY_UP,true,true,0,18);
            dispatcher.dispatchEvent(altUp);
            check("alt-keyup-cancelled",altUp.isDefaultPrevented());
            check("alt-release-reaches-controller",!keyC.triggerHeld());
            var otherKey:KeyboardEvent=new KeyboardEvent(KeyboardEvent.KEY_DOWN,true,true,0,75);
            dispatcher.dispatchEvent(otherKey);
            check("unbound-key-not-cancelled",!otherKey.isDefaultPrevented());
            keyC.keyUp(18);
            var ctrlOnly:*=hold();
            ctrlOnly.triggerModifier=1;
            var ctrlDispatcher:Sprite=new Sprite();
            ctrlOnly.install(ctrlDispatcher);
            var ctrlDown:KeyboardEvent=new KeyboardEvent(KeyboardEvent.KEY_DOWN,true,true,0,18);
            ctrlDispatcher.dispatchEvent(ctrlDown);
            check("alt-not-cancelled-in-ctrl-slot",!ctrlDown.isDefaultPrevented());
            var ctrlSelf:KeyboardEvent=new KeyboardEvent(KeyboardEvent.KEY_DOWN,true,true,0,17);
            ctrlDispatcher.dispatchEvent(ctrlSelf);
            check("ctrl-cancelled-in-ctrl-slot",ctrlSelf.isDefaultPrevented());
            ctrlOnly.deactivate();
            // A disabled controller must not swallow the player's keys.
            var offC:*=hold();
            offC.enabled=false;
            var offDispatcher:Sprite=new Sprite();
            offC.install(offDispatcher);
            var quiet:KeyboardEvent=new KeyboardEvent(KeyboardEvent.KEY_DOWN,true,true,0,18);
            offDispatcher.dispatchEvent(quiet);
            check("disabled-does-not-cancel",!quiet.isDefaultPrevented());
            offC.deactivate();

            // -- cursor override seam (used by the isolated live probe) ----------
            // While the seam is set the entry's own update() call steers with the
            // driver's cursor, so the probe can drive the real game from a hidden
            // desktop whose pointer never moves. Releasing it must hand the real
            // cursor back to the native aim identity in one frame.
            var ow:Object=makeWorld();
            var oc:*=hold();
            oc.keyDown(18,false,false,false);
            oc.cursorOverride={x:RIGHT,y:CY};
            for(i=0;i<70;i++)frame(oc,ow,CX,CY);
            check("override-steers",oc.offsetX>650,"off "+oc.offsetX);
            check("override-is-applied",near(Number(ow.celX),(RIGHT-Number(ow.cam.vx)),1.01),
                "wcelX "+ow.celX+" render "+(RIGHT-Number(ow.cam.vx)));
            oc.keyUp(18);
            for(i=0;i<120;i++)frame(oc,ow,CX,CY);
            check("override-release-returns",oc.offsetX==0,"off "+oc.offsetX);
            oc.cursorOverride=null;
            frame(oc,ow,CX,CY);
            check("override-handover-restores-cursor",near(Number(ow.cam.celX),CX,0.01),
                "celX "+ow.cam.celX+" want "+CX);

            // -- render extras & tuning ------------------------------------------
            var qw:Object=makeWorld();
            var qc:*=hold();
            qc.keyDown(18,false,false,false);
            for(i=0;i<70;i++){qw.cam.vx=-500;qw.cam.vy=-400;qw.cam.quakeX=12;qw.cam.quakeY=-7;qc.update(qw,RIGHT,CY);}
            check("quake-passthrough",qw.visual.x==qw.cam.vx+12&&qw.visual.y==qw.cam.vy-7,
                "vis "+qw.visual.x+","+qw.visual.y+" cam "+qw.cam.vx+","+qw.cam.vy);
            qc.keyUp(18);
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
            for(i=0;i<90;i++)frame(dc,dw,RIGHT,CY);
            check("distance-scale-halved",near(dc.offsetX,350,3)&&near(dc.offsetY,0,1.5),
                "off "+dc.offsetX+","+dc.offsetY);
            dc.keyUp(18);
            // Speed: the faster profile reaches the same extension sooner.
            var fn:Object=makeWorld();
            var fnormal:*=hold();
            fnormal.keyDown(18,false,false,false);
            var normalFrames:int=0;
            while(fnormal.offsetX<590&&normalFrames<300){frame(fnormal,fn,RIGHT,CY);normalFrames++;}
            var ff:Object=makeWorld();
            var ffast:*=hold();
            ffast.speedIndex=3;
            ffast.keyDown(18,false,false,false);
            var fastFrames:int=0;
            while(ffast.offsetX<590&&fastFrames<300){frame(ffast,ff,RIGHT,CY);fastFrames++;}
            check("fast-converges-sooner",fastFrames<normalFrames,"fast "+fastFrames+" normal "+normalFrames);
            var snap:Object=ffast.statsSnapshot();
            check("stats-snapshot-fields",snap.version is String&&snap.applied>0&&snap.aiming>0&&
                snap.edgeClamped>=0&&snap.viewportSyncs>0&&snap.pushes>0&&snap.maxStep>0&&
                snap.maxDepth>0&&snap.focusLosses>=0,
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
            c.aimMode=SceneAimController.MODE_HOLD;
            c.viewportSync=false;
            c.keyDown(18,false,false,false);
            for(var i:int=0;i<70;i++){w.cam.vx=-500;w.cam.vy=-400;c.update(w,1919,500);}
            if(int(ticks.n)!=0)throw new Error("Aim: viewport-sync-can-be-disabled " + ticks.n);
            if(c.offsetX<650)throw new Error("Aim: viewport-sync-can-be-disabled pan " + c.offsetX);
        }
    }
}
