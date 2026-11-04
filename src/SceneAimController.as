package {
    import flash.events.Event;
    import flash.events.KeyboardEvent;

    /** Aim-look camera pan for continuous scenes (v2, CS 0.9.9).
     *
     * The production entry calls update() from ENTER_FRAME priority -200, i.e.
     * after the native Camera.calc has re-centred the view on the player. The
     * pan is a transient per-frame view shift; world state, sound focus and the
     * native camera logic stay intact.
     *
     * What changed against aim-look-1 and why:
     *
     *  1. The pan no longer follows the cursor distance. The player steers it by
     *     holding the cursor against a screen edge; the direction and distance
     *     are latched and persist. aim-look-1 made the offset proportional to
     *     the cursor's distance from the screen centre, so moving the cursor
     *     back into the view to aim at the enemy the pan had just revealed
     *     collapsed the pan and lost the target. Now the cursor is a free
     *     crosshair anywhere inside the widened view while the camera keeps
     *     looking where it was told to.
     *
     *  2. The offset is integrated with a critically damped spring instead of a
     *     first-order lerp plus a 50px hard clamp. The old model reached its
     *     highest speed on the very first frame (700*0.22 = 154px) and then
     *     stalled at a constant 50px/frame, which read as a snap.
     *
     *  3. After the pan is written the controller asks the scene graph to
     *     re-ensure and re-cull with the *panned* viewport. The host's
     *     Camera.calc -> Grafon.sceneTick ran earlier in the frame with the
     *     un-panned player-centred rect, so chunks in the newly exposed band
     *     were either never rendered or already culled to visible=false; the
     *     walls in the distance stayed black however far the camera moved.
     *
     *  4. Camera.celX is pre-shifted by the pan so the native next-frame
     *     assignment w.celX=(celX-vx)/scale still resolves to the world point
     *     actually under the cursor, and w.celX is written from the same
     *     identity in this frame so consumers on either side of the handler
     *     agree to the pixel. aim-look-1 double-counted the shift when writing
     *     w.celX, so the in-frame value was one pan width off.
     */
    public class SceneAimController {
        public static const VERSION:String="aim-look-2";
        /** Cursor radius around the screen centre that never steers. */
        public static const DEADZONE:Number=150;
        /** Cursor distance to the nearest screen edge that steers the look. */
        public static const EDGE_BAND:Number=90;
        /** Frames the cursor must rest in the band before the look latches, so
         * a fast sweep across the screen to shoot does not swing the camera. */
        public static const EDGE_FRAMES:int=3;
        public static const MAX_OFFSET_X:Number=700;
        public static const MAX_OFFSET_Y:Number=380;
        /** Absolute safety cap on one frame's pan delta (the spring peaks at
         * roughly 43px/frame at the fastest setting). */
        public static const MAX_STEP:Number=90;
        /** Fixed integration step: the game loop is 30fps and a fixed step
         * keeps the deterministic checks comparable frame by frame. */
        public static const FRAME_DT:Number=1/30;
        /** Critically damped settle times per speed index (seconds). */
        private static const SMOOTH_IN:Array=[0.40,0.26,0.17];
        private static const SMOOTH_OUT:Array=[0.30,0.20,0.13];
        /** Velocity ceiling per speed index (px/s). */
        private static const MAX_SPEED:Array=[700,1000,1400];

        public var enabled:Boolean=true;
        /** 0=left Alt, 1=left Ctrl, 2=none (custom keybind only). */
        public var triggerModifier:int=0;
        /** Optional normalized binding {code,ctrl,alt,shift}; code 0 = unbound. */
        public var keybind:Object=null;
        /** CS 0.9.9 default: a tap enters the look, another tap leaves it, so
         * the left hand keeps WASD/jump/reload while the look is held. */
        public var toggleMode:Boolean=true;
        /** 0.5 .. 1.5 */
        public var distanceScale:Number=1;
        /** 1=slow 2=normal 3=fast */
        public var speedIndex:int=2;
        /** Re-ensure/re-cull the scene graph for the panned viewport. Only the
         * continuous large scene has anything to do; a fault or an older host
         * simply leaves the flag alone. */
        public var viewportSync:Boolean=true;

        private var stage:*;
        private var altHeld:Boolean=false;
        private var ctrlHeld:Boolean=false;
        private var customHeld:Boolean=false;
        private var triggerLatch:Boolean=false;
        private var toggledOn:Boolean=false;
        private var offX:Number=0;
        private var offY:Number=0;
        private var velX:Number=0;
        private var velY:Number=0;
        /** Latched look direction (unit vector) and distance factor. */
        private var lookX:Number=0;
        private var lookY:Number=0;
        private var lookScale:Number=1;
        private var anchored:Boolean=false;
        private var edgeFrames:int=0;
        private var dwellBand:int=-1;
        private var appliedLast:Boolean=false;
        private var baseVx:Number=0;
        private var baseVy:Number=0;
        private var wroteVx:Number=NaN;
        private var wroteVy:Number=NaN;
        private var mouseNowX:Number=0;
        private var mouseNowY:Number=0;
        private var lastReason:String="idle";
        private var stats:Object={frames:0,aiming:0,applied:0,resets:0,toggles:0,
            edgeClamped:0,latches:0,viewportSyncs:0,maxOffsetSeen:0,maxStep:0};

        public function SceneAimController() {}

        public function install(stageRef:*):void {
            if(stage || !stageRef)return;
            stage=stageRef;
            stage.addEventListener(KeyboardEvent.KEY_DOWN,onKeyDown,false,500,true);
            stage.addEventListener(KeyboardEvent.KEY_UP,onKeyUp,false,500,true);
            stage.addEventListener(Event.DEACTIVATE,onDeactivate,false,500,true);
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
        public function deactivate():void {
            altHeld=false;ctrlHeld=false;customHeld=false;
            triggerLatch=false;toggledOn=false;
        }
        private function afterKeyEvent():void {
            // KEY_DOWN auto-repeat must not flip the toggle again: only a
            // fresh press edge (released since the last down) counts.
            var now:Boolean=triggerHeld();
            if(now && !triggerLatch && toggleMode) {
                toggledOn=!toggledOn;
                ++stats.toggles;
            }
            triggerLatch=now;
        }
        private function onKeyDown(event:KeyboardEvent):void {
            keyDown(event.keyCode,event.ctrlKey,event.altKey,event.shiftKey);
        }
        private function onKeyUp(event:KeyboardEvent):void {keyUp(event.keyCode);}
        private function onDeactivate(event:Event):void {deactivate();}

        public function triggerHeld():Boolean {
            return (triggerModifier==0&&altHeld)||(triggerModifier==1&&ctrlHeld)||customHeld;
        }
        public function aimActive():Boolean {return toggleMode?toggledOn:triggerHeld();}
        public function get offsetX():Number {return offX;}
        public function get offsetY():Number {return offY;}
        public function get reason():String {return lastReason;}
        public function get lookAnchored():Boolean {return anchored;}
        public function get lookDirectionX():Number {return lookX;}
        public function get lookDirectionY():Number {return lookY;}

        public function reset(reason:String):void {
            offX=0;offY=0;velX=0;velY=0;lookX=0;lookY=0;lookScale=1;
            anchored=false;edgeFrames=0;dwellBand=-1;toggledOn=false;lastReason=reason;
            appliedLast=false;
        }
        public function statsSnapshot():Object {
            return {version:VERSION,enabled:enabled,triggerModifier:triggerModifier,
                keybind:keybind?int(keybind.code):0,toggleMode:toggleMode,
                distanceScale:distanceScale,speedIndex:speedIndex,
                viewportSync:viewportSync,anchored:anchored,
                lookX:lookX,lookY:lookY,lookScale:lookScale,
                offsetX:offX,offsetY:offY,reason:lastReason,
                frames:stats.frames,aiming:stats.aiming,applied:stats.applied,
                resets:stats.resets,toggles:stats.toggles,
                latches:stats.latches,viewportSyncs:stats.viewportSyncs,
                edgeClamped:stats.edgeClamped,maxOffsetSeen:stats.maxOffsetSeen,
                maxStep:stats.maxStep};
        }

        /** One frame. mouseX/mouseY are stage coordinates (same space as
         * cam.celX). Returns true when a pan was applied this frame. */
        public function update(w:*,mouseX:Number,mouseY:Number):Boolean {
            ++stats.frames;
            if(!w || !w.cam)return false;
            var cam:*=w.cam;
            mouseNowX=mouseX;mouseNowY=mouseY;
            var gate:String=eligibility(w,cam);
            if(gate!="") {release(gate);return false;}
            var aimOn:Boolean=aimActive();
            if(aimOn) {
                ++stats.aiming;
                steer(cam,mouseX,mouseY);
            } else {
                // Release clears the latch here; the offset then decays to zero
                // through the same spring, so the return is smooth.
                anchored=false;edgeFrames=0;dwellBand=-1;
            }
            var tx:Number=0;
            var ty:Number=0;
            if(anchored) {
                tx=lookX*MAX_OFFSET_X*distanceScale*lookScale;
                ty=lookY*MAX_OFFSET_Y*distanceScale*lookScale;
            }
            var idx:int=speedIndex<1?1:(speedIndex>3?3:int(speedIndex));
            var settle:Number=anchored?Number(SMOOTH_IN[idx-1]):Number(SMOOTH_OUT[idx-1]);
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
                lastReason=aimOn?"aim-near-center":"idle";
                restoreCursor(cam);
                return false;
            }
            apply(w,cam,mouseX,mouseY);
            lastReason=aimOn?"aiming":"returning";
            return true;        }

        /** Edge-anchored steering: the cursor only *chooses* a look direction.
         * Once the cursor has rested against an edge for EDGE_FRAMES the
         * direction and distance are latched and the camera keeps that look
         * while the cursor freely aims anywhere inside the widened view. A
         * later rest against another edge re-latches. */
        private function steer(cam:*,mouseX:Number,mouseY:Number):void {
            var screenW:Number=Number(cam.screenX);
            var screenH:Number=Number(cam.screenY);
            var dx:Number=mouseX-screenW*0.5;
            var dy:Number=mouseY-screenH*0.5;
            var d:Number=Math.sqrt(dx*dx+dy*dy);
            if(d<=DEADZONE) {
                // Centred cursor: idle, and it re-arms the latch.
                edgeFrames=0;dwellBand=-1;
                return;
            }
            var left:Number=mouseX;
            var leftEdge:Number=left;
            var rightEdge:Number=screenW-1-mouseX;
            var topEdge:Number=mouseY;
            var bottomEdge:Number=screenH-1-mouseY;
            var band:int=-1;
            var edge:Number=EDGE_BAND+1;
            if(leftEdge<=EDGE_BAND&&leftEdge<edge) {band=0;edge=leftEdge;}
            if(rightEdge<=EDGE_BAND&&rightEdge<edge) {band=1;edge=rightEdge;}
            if(topEdge<=EDGE_BAND&&topEdge<edge) {band=2;edge=topEdge;}
            if(bottomEdge<=EDGE_BAND&&bottomEdge<edge) {band=3;edge=bottomEdge;}
            if(band<0) {
                // Cursor inside the view: hold everything. The dwell is not
                // cleared here, so a crosshair that strays out of the band for
                // a frame (or a caller that supplies its own cursor position,
                // as the isolated probe does) cannot restart the rest timer.
                return;
            }
            if(band!=dwellBand) {
                dwellBand=band;
                edgeFrames=1;
                return;
            }
            ++edgeFrames;
            if(edgeFrames!=EDGE_FRAMES)return;
            // Depth into the band sets the distance: a light touch at the band
            // start is a short look, pressing into the very edge is full.
            var depth:Number=1-Math.max(0,Math.min(edge/EDGE_BAND,1));
            lookX=dx/d;
            lookY=dy/d;
            lookScale=0.4+0.6*depth;
            anchored=true;
            ++stats.latches;
        }

        private function release(reason:String):void {
            if(offX!=0||offY!=0||velX!=0||velY!=0||anchored||toggledOn) {
                offX=0;offY=0;velX=0;velY=0;anchored=false;toggledOn=false;
                ++stats.resets;
            }
            edgeFrames=0;dwellBand=-1;
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
            // World clamp: never reveal the void past map bounds. An axis
            // whose map is smaller than the screen has no valid pan range.
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
            // fractional value is silently truncated. Re-read the stored
            // values so the rendered view, the cursor mapping and the
            // crosshair all agree to the pixel.
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
    }
}
