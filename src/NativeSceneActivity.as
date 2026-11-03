package {
    import flash.display.DisplayObjectContainer;
    import flash.display.MovieClip;
    import flash.utils.Dictionary;
    import flash.utils.getDefinitionByName;

    /** Sidecar scheduling only: never changes collision flags or unit arrays. */
    public class NativeSceneActivity {
        /** Anticipatory wakes (proximity/viewport margin only) are smoothed to
         * this many units per frame, nearest to the player first, so a camera
         * pan across a camp cannot resume every clip and AI in a single frame.
         * Combat, damage, on-path projectile danger and status signals always
         * wake immediately and never pass through this budget; the wide alert
         * halo around a flying round only schedules a budgeted wake. */
        public static var wakeBudget:int=1;
        /** Engagement expiry (ticks) for far units without any combat signal.
         * Pursuers inside the leash radius never expire. */
        public static var disengageTicks:int=150;
        private static var rooms:Dictionary=new Dictionary(true);
        private static var bulletClass:Class;
        private static var current:Object;
        public static function update(loc:*):Object {
            var nativeState:Object=NativeSceneAdapter.state(loc.land);
            if(!nativeState || nativeState.loc!==loc)return null;
            var w:*=NativeSceneAdapter.host();
            var s:Object=rooms[loc];
            if(!s)rooms[loc]=s={records:new Dictionary(true),sleeping:new Dictionary(true),tick:0,awake:0,asleep:0,leashed:0};
            current=s;++s.tick;s.awake=0;s.asleep=0;s.leashed=0;
            if(!bulletClass)bulletClass=getDefinitionByName("fe.weapon.Bullet") as Class;
            var c:*=w.cam,scale:Number=c.scaleV;
            var left:Number=-c.vx/scale-600,top:Number=-c.vy/scale-600;
            var right:Number=left+c.screenX/scale+1200,bottom:Number=top+c.screenY/scale+1200;
            var threats:Array=[];
            for(var p:*=loc.firstObj;p;p=p.nobj)if(p is bulletClass && !p.off) {
                // Impact corridor: the four-frame flight path padded by the
                // explosion radius plus a small margin — genuine hit danger.
                // The stored box is the corridor; pad widens it to the old
                // 400px alert halo used only for budgeted scheduling.
                var impact:Number=40+Number(p.explRadius);
                threats.push({l:Math.min(p.X,p.X+p.dx*4)-impact,r:Math.max(p.X,p.X+p.dx*4)+impact,
                    t:Math.min(p.Y,p.Y+p.dy*4)-impact,b:Math.max(p.Y,p.Y+p.dy*4)+impact,
                    pad:360});
            }
            var deferred:Array=[],granted:int=0;
            for each(var u:* in loc.units) {
                if(!u)continue;
                var r:Object=s.records[u];
                if(!r)s.records[u]=r={hp:u.hp,engaged:false,leashed:false,deadline:0,until:0,clips:[]};
                var combatSignal:Boolean=u.hp<r.hp || u.celUnit!=null || u.cut>0 || u.poison>0;
                if(combatSignal){r.engaged=true;r.deadline=s.tick+disengageTicks;r.leashed=false;}
                r.hp=u.hp;
                // Engagement leash: far from the player and silent past the
                // deadline, an enemy may re-sleep (wounded or not). Inside the
                // leash radius pursuit behaviour is untouched.
                var nearLeash:Boolean=Math.abs(u.X-loc.gg.X)<2200 && Math.abs(u.Y-loc.gg.Y)<1600;
                if(nearLeash)r.leashed=false;
                else if(r.engaged && s.tick>=r.deadline){r.engaged=false;r.leashed=true;r.until=0;}
                var proximity:Boolean=Math.abs(u.X-loc.gg.X)<1900 && Math.abs(u.Y-loc.gg.Y)<1300;
                var inView:Boolean=false,threatened:Boolean=false,alerted:Boolean=false;
                if(!proximity) {
                    inView=u.X+u.scX>=left && u.X-u.scX<=right && u.Y>=top && u.Y-u.scY<=bottom;
                    if(!inView)for each(var threat:Object in threats)
                        if(u.X>=threat.l-threat.pad && u.X<=threat.r+threat.pad && u.Y>=threat.t-threat.pad && u.Y-u.scY<=threat.b+threat.pad) {
                            if(u.X>=threat.l && u.X<=threat.r && u.Y>=threat.t && u.Y-u.scY<=threat.b)threatened=true;
                            else alerted=true;
                            break;
                        }
                }
                var active:Boolean=!w.grafon.scenePauseDistant || u===loc.gg || u.player || u.npc || u.boss
                    || u.fraction<=0 || u.fraction>=100 || u.fraction==loc.gg.fraction || u.sost!=1 || r.engaged
                    || (u.hp<u.maxhp && !r.leashed) || u.stun>0 || u.bind!=null || u.levit || u.t_emerg>0 || u.effects.length>0
                    || (u.inter && u.inter.isMove)
                    || proximity || inView || threatened || alerted;
                if(active)r.until=s.tick+45;
                var wakeNow:Boolean=active || s.tick<r.until;
                if(!wakeNow) {
                    if(!s.sleeping[u]) {
                        // Activation can snap a grounded unit by one pixel after
                        // the map translation. Finish the native visual sync.
                        u.setVisPos();freeze(u.vis as DisplayObjectContainer,r.clips);
                    }
                    s.sleeping[u]=true;u.onCursor=0;++s.asleep;
                    if(r.leashed)++s.leashed;
                } else if(!s.sleeping[u])++s.awake;
                else {
                    // Sleeping unit wants to wake. Urgent semantics (combat,
                    // on-path projectile danger, status, non-hostile, feature
                    // off) keep the original immediate resume; anticipatory
                    // proximity/viewport wakes and the wide alert halo are
                    // spread over later frames by the budget.
                    var urgent:Boolean=!w.grafon.scenePauseDistant || combatSignal || threatened || r.engaged
                        || u.sost!=1 || (u.hp<u.maxhp && !r.leashed) || u.stun>0 || u.bind!=null || u.levit || u.t_emerg>0
                        || u.effects.length>0 || (u.inter && u.inter.isMove)
                        || u===loc.gg || u.player || u.npc || u.boss
                        || u.fraction<=0 || u.fraction>=100 || u.fraction==loc.gg.fraction;
                    if(urgent) {resume(r);delete s.sleeping[u];++s.awake;}
                    else {
                        var ddx:Number=u.X-loc.gg.X,ddy:Number=u.Y-loc.gg.Y;
                        deferred.push({u:u,r:r,d:ddx*ddx+ddy*ddy});
                    }
                }
            }
            if(deferred.length) {
                deferred.sortOn("d",Array.NUMERIC);
                while(granted<wakeBudget && deferred.length) {
                    var pick:Object=deferred.shift();
                    resume(pick.r);delete s.sleeping[pick.u];++granted;++s.awake;
                }
                s.asleep+=deferred.length;
            }
            return s.sleeping;
        }
        public static function sleeping(loc:*):Object {
            var s:Object=rooms[loc];return s?s.sleeping:null;
        }
        public static function wake(u:*):void {
            if(!u || !rooms[u.loc])return;
            var s:Object=rooms[u.loc],r:Object=s.records[u];
            if(r){r.engaged=true;r.deadline=s.tick+disengageTicks;resume(r);}
            delete s.sleeping[u];
        }
        private static function freeze(parent:DisplayObjectContainer,clips:Array):void {
            if(!parent)return;
            var mc:MovieClip=parent as MovieClip;
            if(mc && mc.isPlaying){clips.push({clip:mc,frame:mc.currentFrame});mc.stop();}
            for(var i:int=0;i<parent.numChildren;++i)freeze(parent.getChildAt(i) as DisplayObjectContainer,clips);
        }
        private static function resume(r:Object):void {
            if(!r.clips.length)return;
            for each(var item:Object in r.clips)
                if(!item.clip.isPlaying && item.clip.currentFrame==item.frame)item.clip.play();
            r.clips=[];
        }
        public static function stats():Object {
            return current?{awake:current.awake,asleep:current.asleep,leashed:current.leashed,
                budget:wakeBudget,version:"leash-wake-2"}:null;
        }
        /** Live budget access for probes: value<0 only reads the current setting. */
        public static function budget(value:int=-1):int {
            if(value>=0)wakeBudget=value;
            return wakeBudget;
        }
    }
}
