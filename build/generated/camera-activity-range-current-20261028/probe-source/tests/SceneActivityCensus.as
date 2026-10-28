package tests {
    import flash.display.DisplayObjectContainer;
    import flash.display.MovieClip;
    import flash.utils.getQualifiedClassName;
    /** Read-only end-of-phase census; excluded from frame timing samples. */
    public class SceneActivityCensus {
        public static function read(w:*):Object {
            var asleep:Object=w.main.getChildByName("ContinuousSceneCarrier")["nativeAPI"].sleeping(w.loc);
            var classes:Object={},reasons:Object={},far:Array=[];
            var c:*=w.cam,s:Number=c.scaleV;
            var l:Number=-c.vx/s-600,t:Number=-c.vy/s-600,r:Number=l+c.screenX/s+1200,b:Number=t+c.screenY/s+1200;
            for each(var u:* in w.loc.units){
                if(!u || (asleep && asleep[u]))continue;
                var cls:String=getQualifiedClassName(u).split("::").pop();
                classes[cls]=int(classes[cls])+1;
                var near:Boolean=(Math.abs(u.X-w.gg.X)<1900 && Math.abs(u.Y-w.gg.Y)<1300)
                    || (u.X+u.scX>=l && u.X-u.scX<=r && u.Y>=t && u.Y-u.scY<=b);
                var reason:String=near?"visible-or-near":u===w.gg || u.player?"player":u.npc?"npc":u.boss?"boss":
                    u.fraction<=0 || u.fraction>=100 || u.fraction==w.gg.fraction?"nonhostile":u.sost!=1?"not-alive":
                    u.celUnit!=null?"target":u.hp<u.maxhp?"damaged":u.effects.length>0?"effect":
                    u.stun>0 || u.bind!=null || u.levit || u.t_emerg>0?"status":
                    u.inter && u.inter.isMove?"interaction":"sticky-or-grace-or-projectile";
                reasons[reason]=int(reasons[reason])+1;
                if(!near)far.push({cls:cls,id:u.id,reason:reason,x:u.X,y:u.Y,hp:u.hp,maxhp:u.maxhp,target:!!u.celUnit});
            }
            var objects:Object={};
            for(var obj:*=w.loc.firstObj;obj;obj=obj.nobj){
                cls=getQualifiedClassName(obj).split("::").pop();objects[cls]=int(objects[cls])+1;
            }
            var display:Object={nodes:0,clips:0,playing:0,playingClasses:{}};
            walk(w.visual,display);
            return {classes:classes,reasons:reasons,far:far,objects:objects,display:display};
        }
        private static function walk(parent:DisplayObjectContainer,out:Object):void {
            if(!parent)return;++out.nodes;
            var mc:MovieClip=parent as MovieClip;
            if(mc){++out.clips;if(mc.isPlaying){++out.playing;var cls:String=getQualifiedClassName(mc);out.playingClasses[cls]=int(out.playingClasses[cls])+1;}}
            for(var i:int=0;i<parent.numChildren;++i)walk(parent.getChildAt(i) as DisplayObjectContainer,out);
        }
    }
}
