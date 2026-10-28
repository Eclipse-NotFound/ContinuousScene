package {
    import flash.display.DisplayObjectContainer;
    import flash.display.MovieClip;
    import flash.utils.Dictionary;
    import flash.utils.getDefinitionByName;

    /** Sidecar scheduling only: never changes collision flags or unit arrays. */
    public class NativeSceneActivity {
        private static var rooms:Dictionary=new Dictionary(true);
        private static var bulletClass:Class;
        private static var current:Object;
        public static function update(loc:*):Object {
            var nativeState:Object=NativeSceneAdapter.state(loc.land);
            if(!nativeState || nativeState.loc!==loc)return null;
            var w:*=NativeSceneAdapter.host();
            var s:Object=rooms[loc];
            if(!s)rooms[loc]=s={records:new Dictionary(true),sleeping:new Dictionary(true),tick:0,awake:0,asleep:0};
            current=s;++s.tick;s.awake=0;s.asleep=0;
            if(!bulletClass)bulletClass=getDefinitionByName("fe.weapon.Bullet") as Class;
            var c:*=w.cam,scale:Number=c.scaleV;
            var left:Number=-c.vx/scale-600,top:Number=-c.vy/scale-600;
            var right:Number=left+c.screenX/scale+1200,bottom:Number=top+c.screenY/scale+1200;
            var cameraRange:Object=SceneActivityCameraRange.observing() ? SceneActivityCameraRange.plan(w,loc,s.tick,left,top,right,bottom) : null;
            var useCameraRange:Boolean=cameraRange!=null && cameraRange.applied===true;
            if(useCameraRange) {left=cameraRange.planned.left;top=cameraRange.planned.top;right=cameraRange.planned.right;bottom=cameraRange.planned.bottom;}
            var threats:Array=[];
            for(var p:*=loc.firstObj;p;p=p.nobj)if(p is bulletClass && !p.off) {
                var radius:Number=400+Number(p.explRadius);
                threats.push({l:Math.min(p.X,p.X+p.dx*4)-radius,r:Math.max(p.X,p.X+p.dx*4)+radius,
                    t:Math.min(p.Y,p.Y+p.dy*4)-radius,b:Math.max(p.Y,p.Y+p.dy*4)+radius});
            }
            for each(var u:* in loc.units) {
                if(!u)continue;
                var r:Object=s.records[u];
                if(!r)s.records[u]=r={hp:u.hp,engaged:false,until:0,clips:[]};
                if(u.hp<r.hp || u.celUnit!=null || u.cut>0 || u.poison>0)r.engaged=true;
                r.hp=u.hp;
                var active:Boolean=!w.grafon.scenePauseDistant || u===loc.gg || u.player || u.npc || u.boss
                    || u.fraction<=0 || u.fraction>=100 || u.fraction==loc.gg.fraction || u.sost!=1 || r.engaged
                    || u.hp<u.maxhp || u.stun>0 || u.bind!=null || u.levit || u.t_emerg>0 || u.effects.length>0
                    || (u.inter && u.inter.isMove)
                    || (!useCameraRange && (Math.abs(u.X-loc.gg.X)<1900 && Math.abs(u.Y-loc.gg.Y)<1300))
                    || (u.X+u.scX>=left && u.X-u.scX<=right && u.Y>=top && u.Y-u.scY<=bottom);
                if(!active)for each(var threat:Object in threats)
                    if(u.X>=threat.l && u.X<=threat.r && u.Y>=threat.t && u.Y-u.scY<=threat.b){active=true;break;}
                if(active)r.until=s.tick+45;
                active=active || s.tick<r.until;
                if(active) {resume(r);delete s.sleeping[u];++s.awake;}
                else {
                    if(!s.sleeping[u]) {
                        // Activation can snap a grounded unit by one pixel after
                        // the map translation. Finish the native visual sync.
                        u.setVisPos();freeze(u.vis as DisplayObjectContainer,r.clips);
                    }
                    s.sleeping[u]=true;u.onCursor=0;++s.asleep;
                }
            }
            return s.sleeping;
        }
        public static function sleeping(loc:*):Object {
            var s:Object=rooms[loc];return s?s.sleeping:null;
        }
        public static function wake(u:*):void {
            if(!u || !rooms[u.loc])return;
            var s:Object=rooms[u.loc],r:Object=s.records[u];
            if(r){r.engaged=true;resume(r);}
            delete s.sleeping[u];
        }
        public static function activityCameraRangeVersion():String {return SceneActivityCameraRange.version();}
        public static function activityCameraRangeSet(enabled:Boolean):Object {return SceneActivityCameraRange.setEnabled(enabled);}
        public static function activityCameraRangeVerify():Object {
            var w:*=NativeSceneAdapter.host();
            return SceneActivityCameraRange.verify(w,w && w.loc ? sleeping(w.loc) : null);
        }
        public static function activityCameraRangeSnapshot():Object {return SceneActivityCameraRange.snapshot();}
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
        public static function stats():Object {return current?{awake:current.awake,asleep:current.asleep}:null;}
    }
}
