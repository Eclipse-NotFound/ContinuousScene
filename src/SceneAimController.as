package {
    import flash.events.Event;
    import flash.events.KeyboardEvent;

    /** Aim-look camera pan for continuous scenes. The production entry drives
     * update() at ENTER_FRAME priority -200, after the native Camera.calc has
     * re-centered the view on the player: the pan is a transient per-frame
     * view shift toward the mouse while the trigger is held, easing back on
     * release. World state, sound focus and native camera logic stay intact;
     * cam.celX is pre-shifted by the actually applied pan so the next native
     * calc still derives a pixel-exact screen->world mouse mapping. */
    public class SceneAimController {
        public static const VERSION:String="aim-look-1";
        public static const DEADZONE:Number=150;
        public static const MAX_OFFSET_X:Number=700;
        public static const MAX_OFFSET_Y:Number=380;
        public static const CURVE_EXPONENT:Number=1.4;
        public static const MAX_STEP:Number=50;
        private static const SPEED_IN:Array=[0.12,0.22,0.32];
        private static const SPEED_OUT:Array=[0.85,0.75,0.62];

        public var enabled:Boolean=true;
        /** 0=left Alt, 1=left Ctrl, 2=none (custom keybind only). */
        public var triggerModifier:int=0;
        /** Optional normalized binding {code,ctrl,alt,shift}; code 0 = unbound. */
        public var keybind:Object=null;
        public var toggleMode:Boolean=false;
        /** 0.5 .. 1.5 */
        public var distanceScale:Number=1;
        /** 1=slow 2=normal 3=fast */
        public var speedIndex:int=2;

        private var stage:*;
        private var altHeld:Boolean=false;
        private var ctrlHeld:Boolean=false;
        private var customHeld:Boolean=false;
        private var triggerLatch:Boolean=false;
        private var toggledOn:Boolean=false;
        private var offX:Number=0;
        private var offY:Number=0;
        private var lastReason:String="idle";
        private var stats:Object={frames:0,aiming:0,applied:0,resets:0,toggles:0,edgeClamped:0,maxOffsetSeen:0};

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

        public function reset(reason:String):void {
            offX=0;offY=0;toggledOn=false;lastReason=reason;
        }
        public function statsSnapshot():Object {
            return {version:VERSION,enabled:enabled,triggerModifier:triggerModifier,
                keybind:keybind?int(keybind.code):0,toggleMode:toggleMode,
                distanceScale:distanceScale,speedIndex:speedIndex,
                offsetX:offX,offsetY:offY,reason:lastReason,
                frames:stats.frames,aiming:stats.aiming,applied:stats.applied,
                resets:stats.resets,toggles:stats.toggles,
                edgeClamped:stats.edgeClamped,maxOffsetSeen:stats.maxOffsetSeen};
        }

        /** One frame. mouseX/mouseY are stage coordinates (same space as
         * cam.celX). Returns true when a pan was applied this frame. */
        public function update(w:*,mouseX:Number,mouseY:Number):Boolean {
            ++stats.frames;
            if(!w || !w.cam)return false;
            var cam:*=w.cam;
            var gate:String=eligibility(w,cam);
            if(gate!="") {
                if(offX!=0||offY!=0||toggledOn) {
                    offX=0;offY=0;toggledOn=false;++stats.resets;
                }
                lastReason=gate;
                return false;
            }
            var aimOn:Boolean=aimActive();
            var tx:Number=0;
            var ty:Number=0;
            if(aimOn) {
                ++stats.aiming;
                var halfW:Number=cam.screenX*0.5;
                var halfH:Number=cam.screenY*0.5;
                var dx:Number=mouseX-halfW;
                var dy:Number=mouseY-halfH;
                var d:Number=Math.sqrt(dx*dx+dy*dy);
                if(d>DEADZONE) {
                    var span:Number=Math.min(halfW,halfH)-DEADZONE;
                    if(span>1) {
                        var t:Number=(d-DEADZONE)/span;
                        if(t>1)t=1;
                        t=Math.pow(t,CURVE_EXPONENT);
                        tx=dx/d*t*MAX_OFFSET_X*distanceScale;
                        ty=dy/d*t*MAX_OFFSET_Y*distanceScale;
                    }
                }
            }
            var idx:int=speedIndex<1?1:(speedIndex>3?3:int(speedIndex));
            var k:Number=(tx!=0||ty!=0)?Number(SPEED_IN[idx-1]):Number(SPEED_OUT[idx-1]);
            var nx:Number=stepClamp(offX+(tx-offX)*k,offX);
            var ny:Number=stepClamp(offY+(ty-offY)*k,offY);
            if(tx==0&&nx>-0.5&&nx<0.5)nx=0;
            if(ty==0&&ny>-0.5&&ny<0.5)ny=0;
            offX=nx;offY=ny;
            var mag:Number=Math.sqrt(offX*offX+offY*offY);
            if(mag>Number(stats.maxOffsetSeen))stats.maxOffsetSeen=mag;
            if(offX==0&&offY==0) {
                lastReason=aimOn?"aim-near-center":"idle";
                return false;
            }
            apply(w,cam,mouseX,mouseY);
            lastReason=aimOn?"aiming":"returning";
            return true;
        }

        private function apply(w:*,cam:*,mouseX:Number,mouseY:Number):void {
            var nativeVx:Number=cam.vx;
            var nativeVy:Number=cam.vy;
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
            w.visual.x=w.sats.vis.x=ax+cam.quakeX;
            w.visual.y=w.sats.vis.y=ay+cam.quakeY;
            // Keep aiming pixel-exact under the shifted view. Next frame the
            // native calc computes w.celX from (cam.celX-nativeVx)/scale, so
            // pre-shift cam.celX by the actually applied (typed) pan; also
            // refresh w.celX now in case consumers run before that calc.
            var effX:Number=nativeVx-ax;
            var effY:Number=nativeVy-ay;
            cam.celX=mouseX+effX;
            cam.celY=mouseY+effY;
            var acx:Number=cam.celX;
            var acy:Number=cam.celY;
            var scale:Number=cam.scaleV>0?cam.scaleV:1;
            w.celX=(acx-ax)/scale;
            w.celY=(acy-ay)/scale;
            ++stats.applied;
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
