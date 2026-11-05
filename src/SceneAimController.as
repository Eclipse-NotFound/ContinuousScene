package {
    import flash.desktop.NativeApplication;
    import flash.events.Event;
    import flash.events.KeyboardEvent;
    import flash.utils.getTimer;

    /** Aim-look camera pan for continuous scenes (v3, CS 0.9.10).
     *
     * The production entry calls update() from ENTER_FRAME priority -200, i.e.
     * after the native Camera.calc has re-centred the view on the player, and
     * again from this class's own post-apply viewport sync. The pan is a
     * transient per-frame view shift; world state, sound focus and the native
     * camera logic stay intact.
     *
     * What changed against aim-look-2 (0.9.9) and why:
     *
     *  1. The trigger no longer reaches the operating system. A bare Alt press
     *     is the Win32 "activate the window menu" gesture (WM_SYSCOMMAND /
     *     SC_KEYMENU): the window drops its mouse capture and the app stops
     *     seeing the mouse until the player clicks inside it, which is exactly
     *     the "the mouse leaves the game until I click" report. Key events are
     *     now cancelled with preventDefault() (plus stopImmediatePropagation
     *     for the bare modifier, which the game itself never binds) before the
     *     runtime hands them to the OS.
     *
     *  2. The pan is a continuous function of how far the cursor is pushed out,
     *     not a three-frame latch that jumps from nothing to full extension.
     *     depth = ((d - deadzone) / (edge radius - deadzone)) ^ 1.25, where the
     *     edge radius is the screen rectangle boundary in the cursor's own
     *     direction: reaching the edge *anywhere* is exactly 100% extension, so
     *     "the closer to the edge, the further I look" holds everywhere between
     *     the centre and the rim instead of only inside a 90px band.
     *
     *  3. Extension is sticky exactly while the player is aiming, and not
     *     before. The aim gesture is exactly "pull the crosshair in", so a
     *     naive distance mapping would collapse the view the moment the player
     *     aims at what it revealed (the 0.9.8 runaway: cursor in -> camera
     *     back -> target leaves the screen -> cursor follows -> ...). The depth
     *     therefore only follows the cursor inwards for the first ARM_FRAMES
     *     after the cursor stopped pushing out. A stray one-frame sweep to the
     *     rim therefore unwinds by itself; a deliberate push parks the look.
     *     There is deliberately NO "cursor at the screen centre" release: with
     *     the view extended, the middle of the screen is the middle of the
     *     newly exposed ground, so aiming there would drop the view exactly
     *     like 0.9.8 did. The look comes down only through the trigger
     *     (release in hold mode, tap again in toggle/smart mode) or through the
     *     optional holdDecay creep.
     *
     *  4. The screen edge latch, the "depth into the band", the per-frame edge
     *     dwell and the toggle default are gone. Hold (0.9.8 behaviour) is the
     *     default again; toggle and a tap/hold hybrid are selectable and behave
     *     as peers.
     *
     *  5. Unchanged and still required: after the pan is written the controller
     *     asks the scene graph to re-ensure and re-cull with the *panned*
     *     viewport (the host ran Camera.calc -> Grafon.sceneTick with the
     *     un-panned player rect earlier in the frame), Camera.celX is pre-shifted
     *     so the native next-frame assignment still resolves the world point
     *     under the cursor, and w.celX is written from that same identity.
     */
    public class SceneAimController {
        public static const VERSION:String="aim-look-3";
        /** 0=hold the trigger (0.9.8 feel, default), 1=tap to latch,
         *  2=tap latches / holding stays temporary. */
        public static const MODE_HOLD:int=0;
        public static const MODE_TOGGLE:int=1;
        public static const MODE_SMART:int=2;
        /** Cursor radius, as a fraction of the screen half-diagonal, that never
         * steers. Small enough that a near target is still aimable. */
        public static const DEADZONE_FRAC:Number=0.09;
        /** Cursor radius fraction above which the look direction may follow the
         * cursor. Inside it the direction is frozen so micro-aim cannot swing
         * an extended view. */
        public static const STEER_FRAC:Number=0.42;
        /** Extension gap (in depth units) below the current extension within
         * which the cursor is treated as pointing rather than aiming, so the
         * direction may follow it. Pushing to the rim in another direction
         * re-aims the look; aiming at anything inside the view does not. */
        public static const RESTEER_GAP:Number=0.18;
        /** Exponent of the screen-radius -> extension curve: slightly convex so
         * the first part of the push is gentle and the last part is decisive. */
        public static const DEPTH_EXP:Number=1.25;
        /** Frames after the last outward push during which pulling the cursor
         * back in still retracts. Distinguishes a stray flick from a look. */
        public static const ARM_FRAMES:int=3;
        /** Longest direction change per frame, degrees. */
        public static const SLEW_DEG:Number=6;
        /** A press shorter than this latches in smart mode (ms). */
        public static const SMART_TAP_MS:Number=250;
        public static const MAX_OFFSET_X:Number=700;
        public static const MAX_OFFSET_Y:Number=380;
        /** Absolute safety cap on one frame's pan delta (the spring peaks at
         * roughly 45px/frame at the default speed). */
        public static const MAX_STEP:Number=90;
        /** Fixed integration step: the game loop is 30fps and a fixed step keeps
         * the deterministic checks comparable frame by frame. */
        public static const FRAME_DT:Number=1/30;
        /** Critically damped settle times per speed index (seconds): extended
         * look, and return. */
        private static const SMOOTH_IN:Array=[0.60,0.42,0.30];
        private static const SMOOTH_OUT:Array=[0.36,0.24,0.16];
        /** Velocity ceiling per speed index (px/s). */
        private static const MAX_SPEED:Array=[1200,1700,2300];

        public var enabled:Boolean=true;
        /** 0=left Alt, 1=left Ctrl, 2=none (custom keybind only). */
        public var triggerModifier:int=0;
        /** Optional normalized binding {code,ctrl,alt,shift}; code 0 = unbound. */
        public var keybind:Object=null;
        /** MODE_HOLD (default) / MODE_TOGGLE / MODE_SMART. */
        public var aimMode:int=MODE_HOLD;
        /** 0.5 .. 1.5 */
        public var distanceScale:Number=1;
        /** 1=slow 2=normal 3=fast */
        public var speedIndex:int=2;
        /** Re-ensure/re-cull the scene graph for the panned viewport. */
        public var viewportSync:Boolean=true;
        /** Extra depth lost per second once the cursor stops pushing out. Zero
         * keeps the view exactly where the player put it; the explicit gestures
         * (cursor home, trigger release, toggle off) are the fast way down. */
        public var holdDecay:Number=0;
        /** Try to take the window back after the OS stole it, instead of making
         * the player click inside the game to continue. */
        public var recoverFocus:Boolean=true;
        /** Test seam: when set ({x,y}) update() ignores its cursor arguments so
         * an out-of-process driver can steer deterministically while the entry
         * keeps calling update() with the real cursor. */
        public var cursorOverride:Object=null;
        /** Test seam: replaces getTimer() so smart-mode taps are deterministic. */
        public var clock:Function=null;

        private var stage:*;
        private var altHeld:Boolean=false;
        private var ctrlHeld:Boolean=false;
        private var customHeld:Boolean=false;
        private var triggerLatch:Boolean=false;
        private var latched:Boolean=false;
        private var pressAt:Number=0;
        private var lastPressAt:Number=-1e9;
        private var focusLostAt:Number=-1e9;
        /** Look direction (unit vector) and its current extension 0..1. */
        private var holdX:Number=0;
        private var holdY:Number=0;
        private var holdDir:Boolean=false;
        private var depth:Number=0;
        private var offX:Number=0;
        private var offY:Number=0;
        private var velX:Number=0;
        private var velY:Number=0;
        private var pushRun:int=0;
        private var appliedLast:Boolean=false;        private var baseVx:Number=0;
        private var baseVy:Number=0;
        private var wroteVx:Number=NaN;
        private var wroteVy:Number=NaN;
        private var mouseNowX:Number=0;
        private var mouseNowY:Number=0;
        private var overrideUsed:Boolean=false;
        private var lastReason:String="idle";
        private var stats:Object={frames:0,aiming:0,applied:0,resets:0,presses:0,
            toggles:0,pushes:0,releases:0,edgeClamped:0,viewportSyncs:0,
            focusLosses:0,maxOffsetSeen:0,maxStep:0,maxDepth:0};

        public function SceneAimController() {}

        public function install(stageRef:*):void {
            if(stage || !stageRef)return;
            stage=stageRef;
            // Priority 500: run before the game's own handlers so the trigger
            // key is cancelled before anything can forward it to the OS.
            stage.addEventListener(KeyboardEvent.KEY_DOWN,onKeyDown,false,500,true);
            stage.addEventListener(KeyboardEvent.KEY_UP,onKeyUp,false,500,true);
            stage.addEventListener(Event.DEACTIVATE,onDeactivate,false,500,true);
            try {
                NativeApplication.nativeApplication.addEventListener(Event.DEACTIVATE,onDeactivate,false,500,true);
            } catch(desktopError:Error) {}
        }

        // Input entry points. Public and synthetic-event free so checks can
        // drive them deterministically; the stage listeners only delegate.
        public function keyDown(keyCode:int,ctrlKey:Boolean,altKey:Boolean,shiftKey:Boolean):void {
            if(keyCode==18)altHeld=true;
            if(keyCode==17)ctrlHeld=true;
            if(bindingMatches(keyCode,ctrlKey,altKey,shiftKey))customHeld=true;
            afterKeyEvent();
        }
        public function keyUp(keyCode:int):void {
            if(keyCode==18)altHeld=false;
            if(keyCode==17)ctrlHeld=false;
            if(keybind && int(keybind.code)==keyCode)customHeld=false;
            afterKeyEvent();
        }
        /** Window/app deactivation. The look is dropped rather than left armed:
         * a missed KEY_UP would otherwise hold the view (and, in hold mode, the
         * trigger) for as long as the player is away. */
        public function deactivate():void {
            altHeld=false;ctrlHeld=false;customHeld=false;
            triggerLatch=false;latched=false;
            if(nowMs()-lastPressAt<400) {
                focusLostAt=nowMs();
                ++stats.focusLosses;
            }
        }
        private function afterKeyEvent():void {
            var now:Boolean=triggerHeld();
            if(now&&!triggerLatch) {
                // KEY_DOWN auto-repeat must not count as another press edge.
                pressAt=nowMs();lastPressAt=pressAt;++stats.presses;
                if(aimMode==MODE_TOGGLE) {
                    latched=!latched;
                    ++stats.toggles;
                }
            } else if(!now&&triggerLatch) {
                ++stats.releases;
                if(aimMode==MODE_SMART && nowMs()-pressAt<SMART_TAP_MS) {
                    latched=!latched;
                    ++stats.toggles;
                }
            }
            triggerLatch=now;
        }
        private function onKeyDown(event:KeyboardEvent):void {
            // Cancelling the event is what keeps a bare Alt from reaching the
            // Win32 window menu. Only the trigger itself is consumed, so game
            // combos (and Alt+F4) are untouched.
            if(isTriggerEvent(event)) {
                event.preventDefault();
                if(event.keyCode==18||event.keyCode==17) event.stopImmediatePropagation();
            }
            keyDown(event.keyCode,event.ctrlKey,event.altKey,event.shiftKey);
        }
        private function onKeyUp(event:KeyboardEvent):void {
            if(isTriggerEvent(event)) {
                event.preventDefault();
                if(event.keyCode==18||event.keyCode==17) event.stopImmediatePropagation();
            }
            keyUp(event.keyCode);
        }
        private function onDeactivate(event:Event):void {deactivate();}
        /** True for the events whose default action must not happen: the bare
         * built-in modifier this controller listens to, or the custom binding. */
        public function isTriggerEvent(event:KeyboardEvent):Boolean {
            if(!enabled)return false;
            if(triggerModifier==0&&event.keyCode==18)return true;
            if(triggerModifier==1&&event.keyCode==17)return true;
            return bindingMatches(event.keyCode,event.ctrlKey,event.altKey,event.shiftKey);
        }
        /** One-shot: the window was probably stolen by the menu gesture rather
         * than by a real app switch. The entry re-activates it when this is
         * true, then calls focusRecovered(). */
        public function needsFocusRecovery():Boolean {
            return recoverFocus&&focusLostAt>-1e8&&nowMs()-focusLostAt<250;
        }
        public function focusRecovered():void {focusLostAt=-1e9;}

        public function triggerHeld():Boolean {
            return (triggerModifier==0&&altHeld)||(triggerModifier==1&&ctrlHeld)||customHeld;
        }
        public function aimActive():Boolean {
            if(aimMode==MODE_TOGGLE)return latched;
            if(aimMode==MODE_SMART)return latched||triggerHeld();
            return triggerHeld();
        }
        /** Backwards compatible view of the mode (0.9.9 stored a boolean). */
        public function get toggleMode():Boolean {return aimMode!=MODE_HOLD;}
        public function set toggleMode(value:Boolean):void {aimMode=value?MODE_TOGGLE:MODE_HOLD;}
        public function get offsetX():Number {return offX;}
        public function get offsetY():Number {return offY;}
        public function get reason():String {return lastReason;}
        public function get lookAnchored():Boolean {return holdDir;}
        public function get lookDirectionX():Number {return holdX;}
        public function get lookDirectionY():Number {return holdY;}
        public function get lookDepth():Number {return depth;}

        public function reset(reason:String):void {
            offX=0;offY=0;velX=0;velY=0;
            clearLook();latched=false;
            lastReason=reason;appliedLast=false;
        }
        public function statsSnapshot():Object {
            return {version:VERSION,enabled:enabled,triggerModifier:triggerModifier,
                keybind:keybind?int(keybind.code):0,aimMode:aimMode,toggleMode:aimMode!=MODE_HOLD,
                distanceScale:distanceScale,speedIndex:speedIndex,
                viewportSync:viewportSync,holdDecay:holdDecay,
                anchored:holdDir,lookX:holdX,lookY:holdY,depth:depth,
                offsetX:offX,offsetY:offY,reason:lastReason,
                frames:stats.frames,aiming:stats.aiming,applied:stats.applied,
                resets:stats.resets,presses:stats.presses,toggles:stats.toggles,
                pushes:stats.pushes,latches:stats.pushes,releases:stats.releases,
                viewportSyncs:stats.viewportSyncs,edgeClamped:stats.edgeClamped,
                focusLosses:stats.focusLosses,maxOffsetSeen:stats.maxOffsetSeen,
                maxStep:stats.maxStep,maxDepth:stats.maxDepth};
        }

        /** One frame. mouseX/mouseY are stage coordinates (same space as
         * cam.celX). Returns true when a pan was applied this frame. */
        public function update(w:*,mouseX:Number,mouseY:Number):Boolean {
            ++stats.frames;
            if(!w || !w.cam)return false;
            var cam:*=w.cam;
            var over:Object=cursorOverride;
            if(over!=null) {
                mouseX=Number(over.x);mouseY=Number(over.y);
                overrideUsed=true;
            } else if(overrideUsed) {
                // The test seam just let go of the cursor: hand the real one
                // back so the native aim identity is exact again even if the
                // pointer never moved (a hidden desktop pins it).
                overrideUsed=false;
                cam.celX=mouseX;cam.celY=mouseY;
                appliedLast=false;wroteVx=NaN;wroteVy=NaN;
            }
            mouseNowX=mouseX;mouseNowY=mouseY;
            var gate:String=eligibility(w,cam);
            if(gate!="") {release(gate);return false;}
            var aimOn:Boolean=aimActive();
            if(aimOn) {
                ++stats.aiming;
                steer(cam,mouseX,mouseY);
                lastReason=holdDir?"aiming":"aim-near-center";
            } else {
                clearLook();
            }
            var tx:Number=0;
            var ty:Number=0;
            if(holdDir) {
                tx=holdX*MAX_OFFSET_X*distanceScale*depth;
                ty=holdY*MAX_OFFSET_Y*distanceScale*depth;
            }
            var idx:int=speedIndex<1?1:(speedIndex>3?3:int(speedIndex));
            var settle:Number=aimOn?Number(SMOOTH_IN[idx-1]):Number(SMOOTH_OUT[idx-1]);
            var ceiling:Number=Number(MAX_SPEED[idx-1]);
            var sx:Object=spring(offX,tx,velX,settle,ceiling);
            offX=stepClamp(Number(sx.pos),offX);
            velX=Number(sx.vel);
            var sy:Object=spring(offY,ty,velY,settle,ceiling);
            offY=stepClamp(Number(sy.pos),offY);
            velY=Number(sy.vel);
            if(tx==0&&ty==0&&Math.abs(offX)<0.75&&Math.abs(offY)<0.75
                &&Math.abs(velX)<6&&Math.abs(velY)<6) {
                offX=0;offY=0;velX=0;velY=0;
            }
            var mag:Number=Math.sqrt(offX*offX+offY*offY);
            if(mag>Number(stats.maxOffsetSeen))stats.maxOffsetSeen=mag;
            if(offX==0&&offY==0) {
                if(!aimOn)lastReason="idle";
                restoreCursor(cam);
                return false;
            }
            apply(w,cam,mouseX,mouseY);
            if(!aimOn)lastReason="returning";
            return true;
        }

        /** Continuous steering: the cursor's distance from the screen centre is
         * the extension lever, its direction is the look direction, and the
         * extension only sticks once the player has actually held the push (see
         * the class comment). */
        private function steer(cam:*,mouseX:Number,mouseY:Number):void {
            var cx:Number=Number(cam.screenX)*0.5;
            var cy:Number=Number(cam.screenY)*0.5;
            var maxD:Number=Math.sqrt(cx*cx+cy*cy);
            if(!(maxD>1))maxD=1;
            var dead:Number=maxD*DEADZONE_FRAC;
            var dx:Number=mouseX-cx;
            var dy:Number=mouseY-cy;
            var d:Number=Math.sqrt(dx*dx+dy*dy);
            if(d<=dead) {
                // Cursor parked in the middle: nothing to steer with, and the
                // look keeps whatever extension it has. Releasing is the
                // trigger's job - a cursor-home release would drop the view the
                // moment the player aimed at the middle of it, which is the
                // 0.9.8 runaway this feature exists to avoid.
                return;
            }
            var ux:Number=dx/d;
            var uy:Number=dy/d;
            // Screen-rectangle boundary radius in the cursor's own direction:
            // touching the edge anywhere is exactly full extension, so the lever
            // reads the same on a wide and on a tall push.
            var rectR:Number=maxD;
            var ax:Number=Math.abs(ux);
            var ay:Number=Math.abs(uy);
            if(ax>0.0001) {
                var rx:Number=cx/ax;
                if(rx<rectR)rectR=rx;
            }
            if(ay>0.0001) {
                var ry:Number=cy/ay;
                if(ry<rectR)rectR=ry;
            }
            var span:Number=rectR-dead;
            var u:Number=span>1?((d-dead)/span):1;
            if(u<0)u=0; else if(u>1)u=1;
            var want:Number=Math.pow(u,DEPTH_EXP);
            if(!holdDir) {
                if(want<=0.0005)return;
                holdX=ux;holdY=uy;holdDir=true;depth=want;pushRun=0;
                ++stats.pushes;
                trackDepth();
                return;
            }
            // Aiming is a positional gesture, so the direction follows the
            // cursor only while the cursor sits at (or beyond) the rim implied
            // by the current extension. Anywhere deeper inside the view the
            // cursor is aiming at a target and the view must not move.
            var pointing:Boolean=want>=depth-RESTEER_GAP;
            if(pointing&&d>=maxD*STEER_FRAC)slew(ux,uy);
            if(want>=depth) {
                depth=want;
                ++pushRun;
                trackDepth();
            } else if(pushRun<ARM_FRAMES) {
                // The cursor already turned back: follow it, so a one-frame
                // sweep to the rim cannot park the camera there.
                depth=want;pushRun=0;
            } else {
                applyDecay();
            }
        }

        private function trackDepth():void {
            if(depth>Number(stats.maxDepth))stats.maxDepth=depth;
        }

        /** Rotate the look direction toward the cursor, at most SLEW_DEG per
         * frame, so a flick cannot whip an extended view around. */
        private function slew(ux:Number,uy:Number):void {
            var current:Number=Math.atan2(holdY,holdX);
            var next:Number=Math.atan2(uy,ux);
            var delta:Number=next-current;
            while(delta>Math.PI)delta-=Math.PI*2;
            while(delta<-Math.PI)delta+=Math.PI*2;
            var limit:Number=SLEW_DEG*Math.PI/180;
            if(delta>limit)delta=limit;
            else if(delta<-limit)delta=-limit;
            var angle:Number=current+delta;
            holdX=Math.cos(angle);
            holdY=Math.sin(angle);
        }

        private function applyDecay():void {
            if(holdDecay<=0)return;
            depth-=holdDecay*FRAME_DT;
            if(depth<=0)clearLook();
        }

        private function clearLook():void {
            holdDir=false;depth=0;holdX=0;holdY=0;pushRun=0;
        }

        private function release(reason:String):void {
            if(offX!=0||offY!=0||velX!=0||velY!=0||holdDir||latched) {
                offX=0;offY=0;velX=0;velY=0;
                clearLook();latched=false;
                ++stats.resets;
            }
            lastReason=reason;
            restoreCursor(null);
        }

        /** Put the raw cursor coordinate back so the native calc keeps mapping
         * the screen centre to the player once the pan is gone. */
        private function restoreCursor(cam:*):void {
            wroteVx=NaN;wroteVy=NaN;
            if(!appliedLast)return;
            appliedLast=false;
            if(!cam)return;
            cam.celX=mouseNowX;
            cam.celY=mouseNowY;
        }

        private function apply(w:*,cam:*,mouseX:Number,mouseY:Number):void {
            var nativeVx:Number=cam.vx;
            var nativeVy:Number=cam.vy;
            // A second update() in the same frame (the isolated probe supplies
            // its own cursor on top of the entry's call) would otherwise pan
            // from the already panned view and double the offset. Recognising
            // our own last write keeps the base exact for both callers; when
            // the player did not move this also equals the native value, so the
            // guard cannot introduce error.
            if(!isNaN(wroteVx)&&nativeVx==wroteVx&&nativeVy==wroteVy) {
                nativeVx=baseVx;nativeVy=baseVy;
            }
            var vx:Number=nativeVx-offX;
            var vy:Number=nativeVy-offY;
            var clamped:Boolean=false;
            // World clamp: never reveal the void past map bounds. An axis whose
            // map is smaller than the screen has no valid pan range.
            if(cam.maxvx>=0) {
                if(vx>0){vx=0;clamped=true;}
                else if(vx<-cam.maxvx){vx=-cam.maxvx;clamped=true;}
            } else {vx=nativeVx;}
            if(cam.maxvy>=0) {
                if(vy>0){vy=0;clamped=true;}
                else if(vy<-cam.maxvy){vy=-cam.maxvy;clamped=true;}
            } else {vy=nativeVy;}
            if(clamped)++stats.edgeClamped;
            cam.vx=vx;cam.vy=vy;
            // The native Camera declares vx/vy/celX/celY as int: writing a
            // fractional value is silently truncated. Re-read the stored values
            // so the rendered view, the cursor mapping and the crosshair all
            // agree to the pixel.
            var ax:Number=cam.vx;
            var ay:Number=cam.vy;
            w.visual.x=ax+cam.quakeX;
            w.visual.y=ay+cam.quakeY;
            if(w.sats && w.sats.vis) {
                w.sats.vis.x=w.visual.x;w.sats.vis.y=w.visual.y;
            }
            var scale:Number=cam.scaleV>0?cam.scaleV:1;
            var effX:Number=nativeVx-ax;
            var effY:Number=nativeVy-ay;
            // Pre-shift celX so the next native calc, which runs before this
            // handler and recomputes vx from the player, still resolves the
            // cursor to the world point it is actually drawn over.
            cam.celX=mouseX+effX;
            cam.celY=mouseY+effY;
            // Write this frame's value from the same identity the native calc
            // will use next frame (celX - unpanned vx), not from the panned vx:
            // using the panned one double-counts the pan by exactly its width.
            w.celX=(cam.celX-nativeVx)/scale;
            w.celY=(cam.celY-nativeVy)/scale;
            appliedLast=true;
            baseVx=nativeVx;baseVy=nativeVy;wroteVx=ax;wroteVy=ay;
            ++stats.applied;
            syncViewport(w,cam,ax,ay,scale);
        }

        /** Re-run the host's chunk ensure/cull for the panned viewport. The
         * host already ran it this frame with the player-centred rect, so
         * without this call the exposed band is missing or culled away. */
        private function syncViewport(w:*,cam:*,ax:Number,ay:Number,scale:Number):void {
            if(!viewportSync)return;
            var g:*=w.grafon;
            if(!g)return;
            var tick:Function=g.sceneTick as Function;
            if(tick==null)return;
            try {
                tick();
                ++stats.viewportSyncs;
            } catch(syncError:Error) {viewportSync=false;}
        }

        /** Critically damped spring (SmoothDamp form, no distance clamp so the
         * whole pan keeps one continuous speed profile). Returns {pos,vel}. */
        private function spring(current:Number,target:Number,velocity:Number,
                                settle:Number,ceiling:Number):Object {
            var smooth:Number=settle>0.0001?settle:0.0001;
            var omega:Number=2/smooth;
            var x:Number=omega*FRAME_DT;
            var decay:Number=1/(1+x+0.48*x*x+0.235*x*x*x);
            var change:Number=current-target;
            var temp:Number=(velocity+omega*change)*FRAME_DT;
            var nextVel:Number=(velocity-omega*temp)*decay;
            var out:Number=target+(change+temp)*decay;
            if(nextVel>ceiling)nextVel=ceiling;
            else if(nextVel<-ceiling)nextVel=-ceiling;
            return {pos:out,vel:nextVel};
        }

        private function eligibility(w:*,cam:*):String {
            if(!enabled)return "disabled";
            if(!w.grafon || !w.grafon.sceneLarge)return "not-scene";
            if(!cam.moved)return "static-camera";
            if(cam.camRun)return "camera-scripted";
            if(cam.showOn)return "camera-show";
            if(w.ctr && w.ctr.keyLook)return "native-look";
            if(w.t_exit!=0 || w.allStat!=1 || w.onPause)return "world-inactive";
            if(w.onConsol)return "console";
            if(w.sats && w.sats.active)return "sats";
            if(w.grafon.visSats && w.grafon.visSats.visible)return "sats-overlay";
            return "";
        }

        private function stepClamp(next:Number,current:Number):Number {
            var d:Number=next-current;
            var limit:Number=Math.abs(d);
            if(limit>Number(stats.maxStep))stats.maxStep=limit;
            if(d>MAX_STEP)return current+MAX_STEP;
            if(d<-MAX_STEP)return current-MAX_STEP;
            return next;
        }

        private function bindingMatches(keyCode:int,ctrlKey:Boolean,altKey:Boolean,shiftKey:Boolean):Boolean {
            if(!keybind)return false;
            var code:int=int(keybind.code);
            if(code<=0)return false;
            return keyCode==code && Boolean(keybind.ctrl)==ctrlKey &&
                Boolean(keybind.alt)==altKey && Boolean(keybind.shift)==shiftKey;
        }

        private function nowMs():Number {
            return clock!=null?Number(clock()):Number(getTimer());
        }
    }
}
