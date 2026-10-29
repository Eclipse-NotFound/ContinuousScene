package tests {
    import flash.desktop.NativeApplication;
    import flash.utils.getDefinitionByName;
    import flash.utils.getQualifiedClassName;

    /** Terminal component check, NOT a player-weapon range or AI-response test.
     * Creates short-path native Bullet objects beside existing enemies; never
     * moves/creates enemies, edits HP, sets visibility, or disables collision.
     * The caller owns a unique test app/storage and must exit without saving.
     * activity() advances private scheduler history; real damage is retained.
     * No loc.step(), world frame, compilation, or test launcher lives here.
     */
    public class SceneOffscreenHitChecks {
        /** Choose an already hidden, sleeping target without moving any actor. */
        public static function hiddenFocus(main:*,w:*):Object {
            var api:*=main.getChildByName("ContinuousSceneCarrier")["nativeAPI"];
            var sleeping:Object=api.sleeping(w.loc);
            for each(var u:* in w.loc.units)if(eligible(u,w,w.loc,sleeping,"rv-hidden") && findFixture(w.loc,u))
                return {x:Number(u.X),y:(Number(u.Y1)+Number(u.Y2))/2,id:String(u.id)};
            throw new Error("No hidden natural target for onscreen camera test");
        }
        public static function run(main:*, w:*, check:Function, options:Object):Object {
            var appID:String=NativeApplication.nativeApplication.applicationID;
            need(check,"offscreen-hit-isolated-app",options && options.expectedApplicationID===appID
                && /^pfe-modsettings-continuous-motion-[0-9a-f]{32}$/.test(appID),appID);
            var mode:String=options.mode ? String(options.mode) : "offscreen";
            need(check,"offscreen-hit-known-mode",mode=="offscreen" || mode=="rv-hidden" || mode=="rv-onscreen",mode);
            var carrier:*=main ? main.getChildByName("ContinuousSceneCarrier") : null;
            var api:*=carrier ? carrier["nativeAPI"] : null;
            need(check,"offscreen-hit-contract",w && w.loc && w.gg && w.cam && w.grafon
                && w.grafon.sceneLarge && w.grafon.scenePauseDistant && w.t_exit==0
                && api && api.activity is Function && api.sleeping is Function && api.state is Function);
            var loc:*=w.loc, state:*=api.state(loc.land);
            need(check,"offscreen-hit-native-location",state && state.loc===loc && w.gg.loc===loc);
            var rv:*=main.getChildByName("RVExplorationAPI");
            var rvAPI:*=rv ? rv["api"] : null;
            var rvActive:Boolean=rvAPI && rvAPI.active is Function && Boolean(rvAPI.active(loc));
            if(mode!="offscreen")need(check,"offscreen-hit-rv-active",rvActive);
            var result:Object={version:"native-offscreen-hit-1",terminalOnly:true,mode:mode,
                applicationID:appID,rvActive:rvActive,activityCalls:0,bulletSteps:0,worldSteps:0,
                scope:"Native short-path Bullet collision/damage plus scheduler eligibility. "
                    +"Not original weapon range, native AI response, explosion, beam, or performance. "
                    +"rv-hidden requires an off-screen sleeping invisible enemy; rv-onscreen requires an on-screen invisible enemy. "
                    +"Only initially sleeping targets demonstrate wake eligibility after damage.",
                cases:[],qualifyingTargets:0};
            // Natural sleepers may still have their ordinary activation grace.
            // No fake damage/target assignment is used to change eligibility.
            var sleeping:Object=api.activity(loc);++result.activityCalls;
            for(var settle:int=0;settle<50;++settle) {
                sleeping=api.activity(loc);++result.activityCalls;
            }
            var fixture:Object=null;
            for each(var candidate:* in loc.units) {
                if(!eligible(candidate,w,loc,sleeping,mode))continue;
                ++result.qualifyingTargets;
                fixture=findFixture(loc,candidate);
                if(fixture)break;
            }
            need(check,"offscreen-hit-qualified-natural-target",fixture!=null,
                {mode:mode,qualifyingTargets:result.qualifyingTargets,activity:api.activityStats()});
            var target:*=fixture.target;
            var initialSleep:Boolean=Boolean(sleeping[target]);
            var before:Object=unitState(target,w,sleeping);
            result.target=before;result.geometry=fixture.geometry;
            var units:Array=[],initialSleeping:Array=[];
            for each(var u:* in loc.units)if(u) {
                units.push({unit:u,hp:u.hp,disabled:u.disabled,trigDis:u.trigDis,loc:u.loc});
                if(u!==target && sleeping[u])initialSleeping.push(u);
            }
            need(check,"offscreen-hit-unrelated-sleepers-exist",initialSleeping.length>0,initialSleeping.length);
            var Bullet:Class=getDefinitionByName("fe.weapon.Bullet") as Class;
            var bullets:Array=[];
            var hp:Number=Number(target.hp),memberCount:int=loc.units.length;
            result.memberCountBefore=memberCount;
            try {
                // The solid wall lies between this origin and the target.
                // The first endpoint is inside its native physical rectangle.
                var wall:Object=fixture.wall;
                var blocked:*=makeBullet(Bullet,w.gg,wall.startX,fixture.y,wall.dx,2,12);
                bullets.push(blocked);
                stepBullet(blocked,result);
                var wallFirst:Object=bulletState(blocked);
                need(check,"offscreen-hit-real-wall-stops-bullet",blocked.tilehit && blocked.babah
                    && Number(target.hp)==hp && unchangedHP(units),wallFirst);
                var stoppedX:Number=blocked.X,stoppedY:Number=blocked.Y;
                for(var i:int=0;i<6 && blocked.in_chain;++i)stepBullet(blocked,result);
                need(check,"offscreen-hit-wall-remains-blocking",blocked.X==stoppedX && blocked.Y==stoppedY
                    && !blocked.in_chain && Number(target.hp)==hp && unchangedHP(units)
                    && wall.tile.phis==wall.phis && wall.tile.phX1==wall.x1 && wall.tile.phX2==wall.x2
                    && wall.tile.phY1==wall.y1 && wall.tile.phY2==wall.y2,
                    {first:wallFirst,final:bulletState(blocked),targetHP:target.hp});
                result.cases.push({name:"solid-wall",ok:true,first:wallFirst,final:bulletState(blocked),
                    hpBefore:hp,hpAfter:target.hp,allUnitHPUnchanged:unchangedHP(units),
                    physicalBefore:{phis:wall.phis,x1:wall.x1,x2:wall.x2,y1:wall.y1,y2:wall.y2},
                    physicalAfter:{phis:wall.tile.phis,x1:wall.tile.phX1,x2:wall.tile.phX2,y1:wall.tile.phY1,y2:wall.tile.phY2}});

                // liv==1 still performs its last native movement before expiry.
                // Its endpoint stays outside the target; never step it again
                // after native removal, which would bypass the world chain.
                var expired:*=makeBullet(Bullet,w.gg,fixture.expireX,fixture.y,fixture.dir*2,2,1);
                bullets.push(expired);stepBullet(expired,result);
                need(check,"offscreen-hit-expiry-before-contact",expired.liv<=0 && !expired.in_chain
                    && !expired.babah && !expired.tilehit && Number(target.hp)==hp && unchangedHP(units),bulletState(expired));
                result.cases.push({name:"native-expiry-before-contact",ok:true,final:bulletState(expired),
                    hpBefore:hp,hpAfter:target.hp,allUnitHPUnchanged:unchangedHP(units)});

                sleeping=api.sleeping(loc);
                need(check,"offscreen-hit-before-shot-state",eligible(target,w,loc,sleeping,mode)
                    && Boolean(sleeping[target])==initialSleep && Number(target.hp)==hp,unitState(target,w,sleeping));
                var shot:*=makeBullet(Bullet,w.gg,fixture.startX,fixture.y,fixture.dx,2,12);
                bullets.push(shot);
                result.firstShotBefore=bulletState(shot);
                // No activity() between insertion and contact: this explicitly
                // covers an enemy that was still asleep at the hit, rather than
                // merely proving projectile threat prediction can wake it.
                result.sleepImmediatelyBeforeShot=Boolean(api.sleeping(loc)[target]);
                stepBullet(shot,result);
                result.firstShotAfter=bulletState(shot);
                result.afterHitBeforeActivity=unitState(target,w,api.sleeping(loc));
                need(check,"offscreen-hit-first-real-bullet-damages",shot.babah && !shot.tilehit
                    && Number(target.hp)<hp && Number(target.hp)>0 && target.sost==1,
                    {beforeHP:hp,after:result.afterHitBeforeActivity,bullet:result.firstShotAfter});
                // Remove only our spent projectile BEFORE activity so the
                // following wake cannot pass solely because of its threat box.
                if(shot.in_chain)shot.setNull();
                result.testBulletsDetachedBeforeWake=allDetached(bullets);
                need(check,"offscreen-hit-no-test-threat-before-wake",result.testBulletsDetachedBeforeWake);
                sleeping=api.activity(loc);++result.activityCalls;
                result.afterActivity=unitState(target,w,sleeping);
                need(check,"offscreen-hit-next-activity-awake",!sleeping[target],result.afterActivity);
                need(check,"offscreen-hit-collision-membership-preserved",loc.units.length==memberCount
                    && loc.units.indexOf(target)>=0 && target.loc===loc
                    && target.disabled===before.disabled && target.trigDis===before.trigDis);
                result.memberCountAfter=loc.units.length;
                result.targetStillMember=loc.units.indexOf(target)>=0 && target.loc===loc;
                var stillSleeping:int=0,otherWoken:int=0;
                for each(u in initialSleeping) {
                    if(sleeping[u])++stillSleeping;else ++otherWoken;
                }
                result.unrelatedSleepers={before:initialSleeping.length,after:stillSleeping,woken:otherWoken};
                // A real native alarm may wake nearby allies. Do not require
                // zero local responses, but a hit must not wake the whole map.
                need(check,"offscreen-hit-does-not-wake-all-sleepers",stillSleeping>0,result.unrelatedSleepers);
                result.cases.push({name:"short-path-hit-and-next-activity",ok:true,hpBefore:hp,hpAfter:target.hp,
                    sleptAtContact:result.sleepImmediatelyBeforeShot});
            } finally {
                for each(var b:* in bullets)if(b && b.in_chain)b.setNull();
            }
            return result;
        }

        private static function eligible(u:*,w:*,loc:*,sleep:Object,mode:String):Boolean {
            if(!u || u===w.gg || u.loc!==loc || u.player || u.npc || u.boss || u.sost!=1
                || u.disabled || u.trigDis || u.invulner || u.dopTestOn || u.invis || u.retDamage
                || u.fraction<=0 || u.fraction>=100 || u.fraction==w.gg.fraction
                || getQualifiedClassName(u)=="fe.unit::UnitTrigger" || Number(u.hp)<20
                || Number(u.hp)!=Number(u.maxhp) || Number(u.shithp)>0
                || Number(u.skin)>0 || Number(u.armor)>0 || Number(u.marmor)>0
                || !u.vulner || Number(u.vulner[0])<=0 || Number(u.allVulnerMult)<=0)return false;
            var p:Object=projection(u,w);
            if(!p.valid)return false;
            if(mode=="offscreen")return Boolean(sleep[u]) && p.outside;
            if(mode=="rv-onscreen")return !p.outside && u.vis!=null && u.vis.visible===false;
            return Boolean(sleep[u]) && p.outside && u.vis!=null && u.vis.visible===false;
        }

        private static function findFixture(loc:*,u:*):Object {
            var y:Number=(Number(u.Y1)+Number(u.Y2))/2;
            if(!isFinite(y) || y<1 || y>=Number(loc.limY)-1)return null;
            for each(var dir:int in [1,-1]) {
                var edge:Number=dir==1?Number(u.X1):Number(u.X2);
                var start:Number=edge-dir*4, end:Number=edge+dir*2, expire:Number=start-dir*10;
                if(!clearSegment(loc,expire,end,y,u))continue;
                var wall:Object=findWall(loc,u,y,dir);
                if(wall)return {target:u,y:y,dir:dir,startX:start,dx:end-start,expireX:expire,wall:wall,
                    geometry:{targetX1:u.X1,targetX2:u.X2,targetY1:u.Y1,targetY2:u.Y2,
                        y:y,startX:start,endX:end,expireX:expire,wallStartX:wall.startX,wallEndX:wall.startX+wall.dx,
                        wallRect:{x1:wall.x1,x2:wall.x2,y1:wall.y1,y2:wall.y2}}};
            }
            return null;
        }

        private static function findWall(loc:*,u:*,y:Number,dir:int):Object {
            var edge:Number=dir==1?Number(u.X1):Number(u.X2);
            for(var distance:int=24;distance<=960;distance+=4) {
                var x:Number=edge-dir*distance;
                if(x<4 || x>=Number(loc.limX)-4)break;
                var t:*=loc.getAbsTile(x,y);
                // phis==2 is a one-way platform with Bullet's explicit tile
                // targeting rule, not an arbitrary solid horizontal wall.
                if(!t || t.phis!=1 || x<t.phX1 || x>t.phX2 || y<t.phY1 || y>t.phY2)continue;
                var outside:Number=dir==1?Number(t.phX1)-2:Number(t.phX2)+2;
                var inside:Number=dir==1?Number(t.phX1)+2:Number(t.phX2)-2;
                if(inside<Number(t.phX1) || inside>Number(t.phX2)
                    || !clearSegment(loc,outside,outside,y,null) || overlapsAny(loc,inside,y,null))continue;
                if(dir*(Number(u.X)-inside)<=0)continue;
                return {tile:t,phis:t.phis,x1:t.phX1,x2:t.phX2,y1:t.phY1,y2:t.phY2,startX:outside,dx:inside-outside};
            }
            return null;
        }

        private static function clearSegment(loc:*,a:Number,b:Number,y:Number,allowed:*):Boolean {
            if(!isFinite(a) || !isFinite(b) || a<1 || b<1 || a>=Number(loc.limX)-1 || b>=Number(loc.limX)-1)return false;
            var n:int=Math.ceil(Math.abs(b-a));
            for(var i:int=0;i<=n;++i) {
                var x:Number=n==0?a:a+(b-a)*i/n;
                var t:*=loc.getAbsTile(x,y);
                if(!t || Number(t.water)>0 || (t.phis==1 && x>=t.phX1 && x<=t.phX2 && y>=t.phY1 && y<=t.phY2)
                    || overlapsAny(loc,x,y,allowed))return false;
            }
            return true;
        }
        private static function overlapsAny(loc:*,x:Number,y:Number,allowed:*):Boolean {
            for each(var u:* in loc.units)if(u && u!==allowed && u.sost!=4 && !u.disabled && !u.trigDis
                && u.loc===loc && x>=u.X1 && x<=u.X2 && y>=u.Y1 && y<=u.Y2)return true;
            return false;
        }
        private static function makeBullet(B:Class,owner:*,x:Number,y:Number,dx:Number,damage:Number,life:int):* {
            var b:*=new B(owner,x,y,null,true);
            b.dx=dx;b.dy=0;b.vel=Math.abs(dx);b.rot=dx<0?Math.PI:0;
            b.damage=damage;b.liv=life;b.precision=0;b.damageExpl=0;b.destroy=0;b.explRadius=0;b.tipDecal=0;
            return b;
        }
        private static function stepBullet(b:*,result:Object):void { b.step();++result.bulletSteps; }
        private static function allDetached(bullets:Array):Boolean {
            for each(var b:* in bullets)if(b.in_chain)return false;return true;
        }
        private static function unchangedHP(units:Array):Boolean {
            for each(var s:Object in units)if(s.unit.hp!==s.hp)return false;return true;
        }
        private static function projection(u:*,w:*):Object {
            var c:*=w.cam,s:Number=Number(c.scaleV);
            var x1:Number=Number(u.X1)*s+Number(c.vx),x2:Number=Number(u.X2)*s+Number(c.vx);
            var y1:Number=Number(u.Y1)*s+Number(c.vy),y2:Number=Number(u.Y2)*s+Number(c.vy);
            var valid:Boolean=isFinite(s) && s>0 && isFinite(x1) && isFinite(x2) && isFinite(y1) && isFinite(y2)
                && x2>x1 && y2>y1 && Number(c.screenX)>0 && Number(c.screenY)>0;
            return {valid:valid,outside:valid && (x2<0 || y2<0 || x1>Number(c.screenX) || y1>Number(c.screenY)),
                x1:x1,y1:y1,x2:x2,y2:y2,screenX:c.screenX,screenY:c.screenY,scale:s,vx:c.vx,vy:c.vy};
        }
        private static function unitState(u:*,w:*,sleep:Object):Object {
            return {type:getQualifiedClassName(u),id:u.id,x:u.X,y:u.Y,hp:u.hp,maxhp:u.maxhp,sost:u.sost,
                asleep:Boolean(sleep[u]),disabled:u.disabled,trigDis:u.trigDis,isVis:u.isVis,
                visualVisible:u.vis?u.vis.visible:null,visualMask:u.vis?u.vis.mask!=null:null,
                priorUnitIsPlayer:u.priorUnit===w.gg,celUnitIsPlayer:u.celUnit===w.gg,
                projection:projection(u,w)};
        }
        private static function bulletState(b:*):Object {
            return {x:b.X,y:b.Y,dx:b.dx,dy:b.dy,vel:b.vel,life:b.liv,dist:b.dist,damage:b.damage,
                babah:b.babah,tilehit:b.tilehit,off:b.off,inChain:b.in_chain,hasTarget:b.targetObj!=null};
        }
        private static function need(check:Function,name:String,ok:Boolean,detail:*=null):void {
            check(name,ok,detail);if(!ok)throw new Error(name+": "+String(detail));
        }
    }
}
