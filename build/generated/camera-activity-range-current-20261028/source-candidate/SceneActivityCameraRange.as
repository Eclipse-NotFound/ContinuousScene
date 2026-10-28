package {
    import flash.desktop.NativeApplication;
    import flash.display.DisplayObject;
    import flash.display.Stage;
    import flash.geom.Matrix;
    import flash.utils.getTimer;

    /** Isolated diagnostic only. No camera simulation, RNG or game-field writes. */
    public class SceneActivityCameraRange {
        public static const VERSION:String="activity-camera-range-1";
        private static var configured:Boolean=false, enabled:Boolean=false, requested:Boolean=false, failed:Boolean=false;
        private static var epoch:int=0, plans:int=0, appliedPlans:int=0, fallbackPlans:int=0, verifiedPlans:int=0;
        private static var last:Object, checked:Object, firstFailure:Object, signature:Object;
        private static var planWorld:*, planLoc:*, planCamera:*, planVisual:*;
        private static var reasons:Object={};

        public static function version():String {return VERSION;}
        public static function observing():Boolean {return configured;}
        private static function copy(value:Object):Object {return value==null ? null : JSON.parse(JSON.stringify(value));}
        private static function fail(reason:String,detail:Object=null):void {
            if(!failed)firstFailure={reason:reason,detail:copy(detail),tick:last ? last.tick : null,epoch:epoch};
            failed=true;enabled=false;
        }
        public static function setEnabled(value:Boolean):Object {
            if(!/^pfe-modsettings-continuous-motion-[0-9a-f]{32}$/.test(NativeApplication.nativeApplication.applicationID))
                throw new Error("Camera range switch requires an isolated motion AIR application");
            if(!configured || value!==requested) {
                if(last && last.applied && !last.verified)fail("mode-changed-before-post-check",last);
                ++epoch;signature=null;
            }
            configured=true;requested=value;enabled=value && !failed;
            return snapshot();
        }
        private static function number(value:*,name:String):Number {
            if(typeof value!="number" || !isFinite(value))throw new Error("non-finite-or-unknown:"+name);
            return Number(value);
        }
        private static function integer(value:*,name:String):Number {
            var n:Number=number(value,name);
            if(n<-2147483646 || n>2147483646 || n!=int(n))throw new Error("unsafe-int:"+name);
            return n;
        }
        private static function safeInt(value:Number,name:String):int {
            if(!isFinite(value) || value<-2147483646 || value>2147483646)throw new Error("int-overflow:"+name);
            return int(value);
        }
        private static function rectangle(left:Number,top:Number,right:Number,bottom:Number):Object {
            if(!isFinite(left) || !isFinite(top) || !isFinite(right) || !isFinite(bottom) || right<left || bottom<top)
                throw new Error("invalid-range");
            return {left:left,top:top,right:right,bottom:bottom};
        }
        private static function actualViewport(w:*,c:*):Object {
            var visual:DisplayObject=w.visual as DisplayObject, stage:Stage=visual ? visual.stage : null;
            if(!visual || !stage || stage!==w.swfStage || stage.scaleMode!="noScale" || stage.align!="TL")
                throw new Error("unknown-stage-transform");
            var width:Number=integer(c.screenX,"screenX"),height:Number=integer(c.screenY,"screenY");
            var scale:Number=number(c.scaleV,"scaleV");
            if(width<=0 || height<=0 || scale<=0 || stage.stageWidth!=width || stage.stageHeight!=height)
                throw new Error("stage-camera-size-mismatch");
            var m:Matrix=visual.transform.concatenatedMatrix;
            if(m.a!==scale || m.d!==scale || m.b!==0 || m.c!==0 || !isFinite(m.tx) || !isFinite(m.ty))
                throw new Error("unknown-visual-transform");
            return rectangle(-m.tx/scale,-m.ty/scale,(width-m.tx)/scale,(height-m.ty)/scale);
        }
        private static function ordinary(w:*,loc:*,c:*):String {
            if(w.loc!==loc || w.gg!==loc.gg || !w.gg || w.gg.loc!==loc)return "player-location-mismatch";
            if(w.grafon.sceneLarge!==true || loc.sky!==false || c.moved!==true)return "not-ordinary-large-follow";
            if(w.ctr.keyZoom!==false)return "zoom-input";
            if(w.ctr.keyLook!==false || c.showOn!==false || number(c.otryv,"otryv")!=0 || c.camRun!==false)
                return "look-show-or-camRun";
            if(w.ctr.keySats!==false || w.sats.active!==false || w.grafon.visSats.visible!==false)
                return "sats-or-unknown-sats";
            var parent:DisplayObject=w.visual.parent as DisplayObject;
            if(!parent)return "unknown-visual-parent";
            var p:Matrix=parent.transform.concatenatedMatrix;
            if(p.a!==1 || p.d!==1 || p.b!==0 || p.c!==0 || p.tx!==0 || p.ty!==0)
                return "nonidentity-visual-parent";
            return null;
        }
        // Exact Camera int assignment followed by its native clamps. No Camera.calc call.
        private static function offset(center:int,screen:Number,maximum:Number,vertical:Boolean):int {
            if(maximum<0)return safeInt(-maximum/2,"centered-offset");
            var result:int=safeInt(-Number(center)+screen/2+(vertical ? 100 : 0),"follow-offset");
            if(result>0)result=0;
            if(result<-maximum)result=safeInt(-maximum,"clamped-offset");
            return result;
        }
        private static function fallback(reason:String):Object {
            last.reason=reason;last.applied=false;++fallbackPlans;
            reasons[reason]=reasons[reason]===undefined ? 1 : int(reasons[reason])+1;
            last.planned=last.oldNear;
            return last;
        }
        public static function plan(w:*,loc:*,tick:int,left:Number,top:Number,right:Number,bottom:Number):Object {
            var start:int=getTimer();
            if(last && last.applied && !last.verified)fail("post-check-missing",last);
            checked=null;++plans;
            planWorld=w;planLoc=loc;planCamera=w.cam;planVisual=w.visual;
            last={version:VERSION,epoch:epoch,tick:tick,enabledAtPlan:enabled,applied:false,verified:false,
                reason:null,oldNear:{left:left,top:top,right:right,bottom:bottom},planned:null,
                actualAtPlan:null,predicted:null,marginWorld:320,quakePaddingStage:2,planMs:0};
            try {
                if(!enabled)return fallback(failed ? "disabled-after-failure" : "mode-disabled");
                var c:*=w.cam,scale:Number=number(c.scaleV,"scaleV"),width:Number=integer(c.screenX,"screenX"),height:Number=integer(c.screenY,"screenY");
                var current:Object=actualViewport(w,c);last.actualAtPlan=current;
                var previous:Object=signature;
                signature={world:w,loc:loc,camera:c,visual:w.visual,scale:scale,width:width,height:height};
                if(!previous)return fallback("first-frame");
                if(previous.world!==w || previous.loc!==loc || previous.camera!==c || previous.visual!==w.visual ||
                    previous.scale!==scale || previous.width!==width || previous.height!==height)
                    return fallback("context-scale-or-size-changed");
                var reason:String=ordinary(w,loc,c);
                if(reason)return fallback(reason);
                var x:Number=number(w.gg.X,"playerX")*scale,y:Number=number(w.gg.Y,"playerY")*scale;
                var oldY:Number=integer(c.ovy,"ovy"),maxX:Number=integer(c.maxvx,"maxvx"),maxY:Number=integer(c.maxvy,"maxvy");
                var qx:Number=Math.abs(number(c.quakeX,"quakeX"))+2,qy:Number=Math.abs(number(c.quakeY,"quakeY"))+2;
                // Quake may keep its value, reverse with smaller magnitude, or become zero.
                // A later object step can add new quake/player writes: only the post-check can detect those.
                var vx:int=offset(safeInt(x,"nextX"),width,maxX,false);
                var vyA:int=offset(safeInt(Math.min(oldY,y),"nextY-low"),height,maxY,true);
                var vyB:int=offset(safeInt(Math.max(oldY,y),"nextY-high"),height,maxY,true);
                var lowVY:Number=Math.min(vyA,vyB),highVY:Number=Math.max(vyA,vyB);
                var predicted:Object=rectangle((-vx-qx)/scale,(-highVY-qy)/scale,
                    (width-vx+qx)/scale,(height-lowVY+qy)/scale);
                var planned:Object=rectangle(Math.min(current.left,predicted.left)-320,Math.min(current.top,predicted.top)-320,
                    Math.max(current.right,predicted.right)+320,Math.max(current.bottom,predicted.bottom)+320);
                last.inputs={scale:scale,screenX:width,screenY:height,playerXScaled:x,playerYScaled:y,ovy:oldY,
                    maxvx:maxX,maxvy:maxY,quakeX:Number(c.quakeX),quakeY:Number(c.quakeY),nextVX:vx,nextVYLow:lowVY,nextVYHigh:highVY};
                last.predicted=predicted;last.planned=planned;last.applied=true;last.reason="ordinary-follow-envelope";
                ++appliedPlans;return last;
            } catch(error:*) {return fallback("guard:"+String(error));}
            finally {last.planMs=getTimer()-start;}
            return last; // Explicit for this compiler's try/finally return analysis.
        }
        private static function contains(outer:Object,inner:Object):Boolean {
            return inner.left>=outer.left && inner.top>=outer.top && inner.right<=outer.right && inner.bottom<=outer.bottom;
        }
        public static function verify(w:*,sleeping:Object):Object {
            if(!configured || !last || last.epoch!=epoch)
                return {version:VERSION,ok:!failed,failed:failed,enabled:enabled,applied:false,pending:true,tick:null,epoch:epoch,
                    reason:configured ? "await-next-activity" : "not-configured",planned:null,actual:null,viewportContained:null,
                    visibleSleeping:0,visibleSleepingExamples:[],oldNearOnlySleeping:0,oldNearOnlySleepingExamples:[],
                    unitsExamined:0,errors:[],checkComplete:false};
            if(checked)return copy(checked);
            var start:int=getTimer(),out:Object={version:VERSION,ok:true,failed:failed,enabled:enabled,applied:last.applied,
                pending:false,tick:last.tick,epoch:last.epoch,reason:last.reason,planned:copy(last.planned),actual:null,
                viewportContained:null,visibleSleeping:0,visibleSleepingExamples:[],oldNearOnlySleeping:0,
                oldNearOnlySleepingExamples:[],unitsExamined:0,errors:[],checkComplete:false};
            try {
                if(w!==planWorld || w.loc!==planLoc || w.cam!==planCamera || w.visual!==planVisual)
                    throw new Error("post-check-context-mismatch");
                if(last.applied && (ordinary(w,w.loc,w.cam)!=null || Number(w.cam.scaleV)!==last.inputs.scale ||
                    w.cam.screenX!==last.inputs.screenX || w.cam.screenY!==last.inputs.screenY))
                    throw new Error("post-check-follow-scale-or-size-changed");
                out.actual=actualViewport(w,w.cam);out.viewportContained=contains(last.planned,out.actual);
                if(last.applied && !out.viewportContained)throw new Error("actual-viewport-outside-planned-range");
                if(sleeping==null)throw new Error("post-check-sleeping-set-missing");
                for each(var u:* in w.loc.units) {
                    if(!u)continue;
                    ++out.unitsExamined;if(!sleeping[u])continue;
                    var x:Number=number(u.X,"unit.X"),y:Number=number(u.Y,"unit.Y");
                    var sx:Number=number(u.scX,"unit.scX"),sy:Number=number(u.scY,"unit.scY");
                    if(sx<0 || sy<0)throw new Error("unknown-unit-bounds");
                    if(last.applied) {
                        var inNew:Boolean=x+sx>=last.planned.left && x-sx<=last.planned.right && y>=last.planned.top && y-sy<=last.planned.bottom;
                        var inOld:Boolean=x+sx>=last.oldNear.left && x-sx<=last.oldNear.right && y>=last.oldNear.top && y-sy<=last.oldNear.bottom;
                        var oldPlayerNear:Boolean=Math.abs(x-last.inputs.playerXScaled/last.inputs.scale)<1900 &&
                            Math.abs(y-last.inputs.playerYScaled/last.inputs.scale)<1300;
                        if(!inNew && (inOld || oldPlayerNear)) {
                            ++out.oldNearOnlySleeping;
                            if(out.oldNearOnlySleepingExamples.length<8)
                                out.oldNearOnlySleepingExamples.push({x:x,y:y,scX:sx,scY:sy});
                        }
                    }
                    if(x+sx>=out.actual.left && x-sx<=out.actual.right && y>=out.actual.top && y-sy<=out.actual.bottom) {
                        ++out.visibleSleeping;
                        if(out.visibleSleepingExamples.length<8)out.visibleSleepingExamples.push({id:String(u.id),x:x,y:y,scX:sx,scY:sy});
                    }
                }
                out.checkComplete=true;
                if(out.visibleSleeping>0)throw new Error("visible-entity-sleeping");
            } catch(error:*) {
                out.errors.push(String(error));
                // Unknown geometry in an old-range fallback is explicitly unqualified, not silently accepted as checked.
                if(last.applied || out.actual!=null)fail("post-check-failed",out);
            }
            last.verified=true;++verifiedPlans;out.failed=failed;out.enabled=enabled;out.ok=!failed;
            out.verifyMs=getTimer()-start;checked=out;return copy(out);
        }
        public static function snapshot():Object {
            return {version:VERSION,diagnosticOnly:true,performanceEligible:false,enabled:enabled,requestedEnabled:requested,
                configured:configured,failed:failed,configurationEpoch:epoch,plans:plans,appliedPlans:appliedPlans,
                fallbackPlans:fallbackPlans,verifiedPlans:verifiedPlans,reasons:copy(reasons),firstFailure:copy(firstFailure),
                lastPlan:copy(last),lastVerification:copy(checked)};
        }
    }
}
