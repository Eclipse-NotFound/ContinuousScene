package tests {
    import flash.desktop.NativeApplication;
    import flash.display.DisplayObjectContainer;
    import flash.display.MovieClip;
    import flash.utils.Dictionary;
    import flash.utils.getDefinitionByName;
    import flash.utils.getQualifiedClassName;

    /** TERMINAL isolated check: the caller must prevent deactivation saves and
     * exit afterwards. activity() advances private scheduler ticks/grace, not
     * world frames. That private history cannot be restored through the API.
     * This tests scheduling semantics, not performance or the first prediction
     * of a newly fired, still-moving bullet. No real enemy step/damage is run.
     */
    public class SceneStoppedThreatChecks {
        private static const VERSION:String="stationary-threats-1";
        private static const FIELDS:Array=["X","Y","dx","dy","hp","maxhp","sost","disabled",
            "trigDis","celUnit","fraction","loc","stun","bind","levit","t_emerg"];

        public static function run(main:*,w:*,check:Function):Object {
            var id:String=NativeApplication.nativeApplication.applicationID;
            var prefix:String="pfe-modsettings-continuous-motion-";
            require(check,"isolated-unique-id",id.indexOf(prefix)==0 && id.length>prefix.length+7,id);
            var carrier:*=main ? main.getChildByName("ContinuousSceneCarrier") : null;
            var api:*=carrier ? carrier["nativeAPI"] : null;
            var ready:Boolean=w && w.loc && w.gg && w.grafon && w.grafon.sceneLarge
                && w.grafon.scenePauseDistant && api && ("stationaryThreatsEnabled" in api)
                && (api.activity is Function) && (api.activityStats is Function);
            require(check,"host-contract",ready);
            var loc:*=w.loc,oldFlag:*=api.stationaryThreatsEnabled;
            var nativeState:*=api.state(loc.land);
            require(check,"native-large-location",nativeState && nativeState.loc===loc);
            var chain:Array=readChain(loc),units:Array=[],clips:Array=[];
            var next:*=loc.nextObj,seen:Dictionary=new Dictionary(true);
            for each(var u:* in loc.units)if(u) {
                var saved:Object={unit:u,onCursor:u.onCursor,values:[],vis:u.vis};
                for each(var key:String in FIELDS)saved.values.push(u[key]);
                if(u.vis) {
                    saved.x=u.vis.x;saved.y=u.vis.y;saved.scaleX=u.vis.scaleX;
                    captureClips(u.vis as DisplayObjectContainer,clips,seen);
                }
                units.push(saved);
            }
            var result:Object={terminalOnly:true,applicationID:id,version:VERSION,schedulerCalls:0,
                worldSteps:0,bulletSteps:0,cases:[],graceDrainCalls:50,
                limitation:"Private activity ticks/grace remain changed. Exit without saving or travel. "
                    +"Does not measure frame time, initial moving-shot overprediction, SATS or network ordering."};
            var bullet:*=null,target:*=null;
            try {
                var sleep:Object=update(api,loc,result);
                require(check,"candidate-version",api.activityStats().version===VERSION,api.activityStats());
                // Existing native projectiles are not changed or removed. Only
                // choose a unit which still sleeps with those threats present.
                for(var i:int=0;i<50;++i)sleep=update(api,loc,result);
                var startX:Number=NaN,startY:Number=NaN,travel:Number=NaN;
                for each(u in loc.units)if(u && sleep[u] && isFinite(Number(u.X)) && isFinite(Number(u.Y))) {
                    var x:Number=Number(u.X),y:Number=Number(u.Y)-Number(u.scY)/2;
                    var candidate:Number=x>=1040 ? x-1000 : x+1000;
                    if(candidate>=40 && candidate<Number(loc.limX)-40 && y>=0 && y<Number(loc.limY)) {
                        target=u;startX=candidate;startY=y;travel=x-candidate;break;
                    }
                }
                require(check,"uncontaminated-native-sleeper",target!=null,api.activityStats());
                result.target={type:getQualifiedClassName(target),id:target.id,x:target.X,y:target.Y,
                    bulletX:startX,bulletY:startY,distance:Math.abs(travel)};
                var Bullet:Class=getDefinitionByName("fe.weapon.Bullet") as Class;
                bullet=new Bullet(w.gg,startX,startY,null,false);
                bullet.dx=travel/4;bullet.dy=0;bullet.vel=Math.abs(bullet.dx);
                bullet.liv=100;bullet.damage=bullet.damageExpl=bullet.destroy=0;
                bullet.explRadius=0;bullet.off=true;
                // Exercise the actual native stop operation, without material,
                // decal, visual, damage, blast or particle effects.
                bullet.popadalo(0);
                require(check,"native-stopped-fixture",bullet.babah && bullet.liv==4
                    && bullet.dx==travel/4 && bullet.dy==0);
                loc.addObj(bullet);

                api.stationaryThreatsEnabled=false;
                settle(api,loc,bullet,target,result,check,"old-stopped");
                bullet.off=false;sleep=update(api,loc,result);
                record(result,check,"old-stopped-velocity-wakes",!sleep[target],api.activityStats());

                api.stationaryThreatsEnabled=true;
                settle(api,loc,bullet,target,result,check,"new-stopped");
                bullet.off=false;
                for(i=0;i<3;++i)sleep=update(api,loc,result);
                record(result,check,"new-stopped-velocity-does-not-wake",Boolean(sleep[target]),api.activityStats());

                settle(api,loc,bullet,target,result,check,"moving");
                bullet.babah=false;bullet.liv=100;bullet.off=false;
                sleep=update(api,loc,result);
                record(result,check,"moving-velocity-still-wakes",!sleep[target],api.activityStats());

                settle(api,loc,bullet,target,result,check,"stopped-blast");
                bullet.babah=true;bullet.liv=4;bullet.explRadius=Math.abs(travel)+64;bullet.off=false;
                require(check,"blast-outside-base-radius",Math.abs(target.X-bullet.X)>400
                    && Math.abs(target.X-bullet.X)<bullet.explRadius);
                sleep=update(api,loc,result);
                record(result,check,"stopped-current-blast-radius-wakes",!sleep[target],api.activityStats());

                // Never step a moving fixture or a live blast: that would run
                // collision/damage and invalidate this no-world-step check.
                bullet.off=true;bullet.explRadius=0;bullet.babah=true;bullet.liv=4;
                var bx:Number=bullet.X,by:Number=bullet.Y,life:int=bullet.liv;
                bullet.step();++result.bulletSteps;
                record(result,check,"native-stopped-step-ages-without-motion",
                    bullet.X===bx && bullet.Y===by && bullet.liv==life-1 && bullet.in_chain,
                    {x:bullet.X,y:bullet.Y,lifeBefore:life,lifeAfter:bullet.liv});
            } finally {
                // No source enemy fields were intentionally changed. Restore
                // activity's cursor/visual synchronization and playback toggles;
                // do not attempt to rewrite its private engagement/history map.
                if(bullet && bullet.in_chain)loc.remObj(bullet);
                api.stationaryThreatsEnabled=oldFlag;
                var logicOK:Boolean=true,visualOK:Boolean=true;
                for each(saved in units) {
                    u=saved.unit;
                    for(i=0;i<FIELDS.length;++i)if(!same(u[FIELDS[i]],saved.values[i]))logicOK=false;
                    u.onCursor=saved.onCursor;
                    if(u.vis!==saved.vis)visualOK=false;
                    if(saved.vis) {
                        saved.vis.x=saved.x;saved.vis.y=saved.y;saved.vis.scaleX=saved.scaleX;
                    }
                }
                for each(var clip:Object in clips) {
                    if(clip.mc.currentFrame!=clip.frame) {visualOK=false;continue;}
                    if(clip.playing && !clip.mc.isPlaying)clip.mc.play();
                    else if(!clip.playing && clip.mc.isPlaying)clip.mc.stop();
                }
                require(check,"logical-unit-state-unchanged",logicOK);
                require(check,"visual-state-restored",visualOK);
                require(check,"fixture-and-chain-restored",sameChain(chain,readChain(loc))
                    && loc.nextObj===next && (!bullet || !bullet.in_chain));
                require(check,"switch-restored",api.stationaryThreatsEnabled===oldFlag);
            }
            return result;
        }

        private static function update(api:*,loc:*,out:Object):Object {
            ++out.schedulerCalls;
            var sleep:Object=api.activity(loc);
            if(!sleep)throw new Error("Stopped threat checks require an active native scheduler");
            return sleep;
        }
        private static function settle(api:*,loc:*,bullet:*,target:*,out:Object,check:Function,name:String):void {
            bullet.off=true;
            var sleep:Object;
            for(var i:int=0;i<50;++i)sleep=update(api,loc,out);
            require(check,name+"-grace-drained",Boolean(sleep[target]),api.activityStats());
        }
        private static function record(out:Object,check:Function,name:String,ok:Boolean,detail:*=null):void {
            out.cases.push({name:name,ok:ok,detail:detail});require(check,name,ok,detail);
        }
        private static function require(check:Function,name:String,ok:Boolean,detail:*=null):void {
            check("stopped-threat-"+name,ok,detail);
            if(!ok)throw new Error("Stopped threat check failed: "+name);
        }
        private static function same(a:*,b:*):Boolean {
            return a===b || (typeof a=="number" && typeof b=="number" && isNaN(a) && isNaN(b));
        }
        private static function readChain(loc:*):Array {
            var out:Array=[],seen:Dictionary=new Dictionary(true),previous:*=null;
            for(var p:*=loc.firstObj;p;p=p.nobj) {
                if(seen[p] || out.length>=20000 || p.pobj!==previous)
                    throw new Error("Invalid native object chain for stopped threat checks");
                seen[p]=true;out.push(p);previous=p;
            }
            if(loc.lastObj!==previous)throw new Error("Native object chain tail mismatch");
            return out;
        }
        private static function sameChain(a:Array,b:Array):Boolean {
            if(a.length!=b.length)return false;
            for(var i:int=0;i<a.length;++i)if(a[i]!==b[i])return false;
            return true;
        }
        private static function captureClips(parent:DisplayObjectContainer,out:Array,seen:Dictionary):void {
            if(!parent || seen[parent])return;seen[parent]=true;
            var mc:MovieClip=parent as MovieClip;
            if(mc)out.push({mc:mc,frame:mc.currentFrame,playing:mc.isPlaying});
            for(var i:int=0;i<parent.numChildren;++i)
                captureClips(parent.getChildAt(i) as DisplayObjectContainer,out,seen);
        }
    }
}
