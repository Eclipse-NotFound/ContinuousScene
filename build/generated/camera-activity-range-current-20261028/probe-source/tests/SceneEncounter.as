package tests {
    import flash.utils.getQualifiedClassName;
    import flash.utils.getDefinitionByName;
    /** Isolated probe only: native armed actors, native targeting and weapons. */
    public class SceneEncounter {
        private var w:*,actors:Array=[];
        public var targetFrames:int=0,shots:int=0,movingFrames:int=0,actualShotFrames:int=0;
        public function SceneEncounter(world:*):void {w=world;}
        private function solid(x:Number,y:Number):Boolean {
            var t:*=w.loc.getAbsTile(x,y);
            return t==null || (t.phis==1 && x>=t.phX1 && x<=t.phX2 && y>=t.phY1 && y<=t.phY2);
        }
        private function floorAt(x:Number,y:Number,height:Number,width:Number):Number {
            var best:Number=NaN,dist:Number=1e9;
            for(var yy:int=Math.max(1,int(y/40)-12);yy<Math.min(w.loc.spaceY-1,int(y/40)+13);++yy){
                var t:*=w.loc.getAbsTile(x,yy*40+20);
                if(!t || t.phis!=1)continue;
                var top:Number=t.phY1-1;
                if(solid(x,top-height) || solid(x-width*.4,top-height*.5) || solid(x+width*.4,top-height*.5) || solid(x,top))continue;
                if(Math.abs(top-y)<dist){dist=Math.abs(top-y);best=top;}
            }
            return best;
        }
        public function prepare(x:Number,y:Number,fixed:Boolean=false,localOnly:Boolean=false,durable:Boolean=false,route:Object=null):Object {
            var details:Array=[],nextX:Number=x+350,removed:int=0;
            if(localOnly){
                if(!fixed)throw new Error("Local population control requires fixed actors");
                // Attribution fixture only. Remove actors without death, loot,
                // quest callbacks or writes to any real game storage.
                for each(var old:* in w.loc.units.concat()){
                    if(!old || old===w.gg || old.player || old.npc || old.fraction<=0 || old.fraction>=100 || old.fraction==w.gg.fraction)continue;
                    old.disabled=true;old.remVisual();w.loc.remObj(old);
                    w.loc.units.splice(w.loc.units.indexOf(old),1);++removed;
                }
            }
            var candidates:Array=w.loc.units;
            if(fixed){
                candidates=[];var Raider:Class=getDefinitionByName("fe.unit.UnitRaider") as Class;
                for(var i:int=0;i<6;++i)candidates.push(new Raider("1",4,null,{weap:"lmg",tr:1}));
            }
            for each(var u:* in candidates){
                var kind:String=getQualifiedClassName(u);
                if(actors.length>=6)break;
                if(u===w.gg || u.sost!=1 || u.npc || u.boss || u.fraction<=0 || u.fraction>=100 || u.fraction==w.gg.fraction)continue;
                if(!u.currentWeapon || u.currentWeapon.tip<3 || !/Unit(Raider|Merc|Ranger|Slaver|Zebra|Encl)$/.test(kind))continue;
                var xx:Number,yy:Number=NaN;
                if(route) {xx=route.enemies[actors.length].x;yy=route.enemies[actors.length].y;}
                else while(nextX<x+1600){xx=nextX;nextX+=80;yy=floorAt(xx,y,u.scY,u.scX);if(!isNaN(yy))break;}
                if(isNaN(yy))continue;
                if(fixed){u.maxhp=u.hp=durable?100000:500;u.putLoc(w.loc,xx,yy);w.loc.addObj(u);w.loc.units.push(u);u.currentWeapon.damage=2;}
                u.setPos(xx,yy);u.dx=u.dy=0;u.setCel(w.gg);u.storona=-1;
                actors.push({unit:u,attack:int(u.currentWeapon.t_attack),gun:u.currentWeapon,bullet:u.currentWeapon.b});
                details.push({type:kind,id:u.id,x:xx,y:yy,weapon:u.currentWeapon.id});
            }
            var playerY:Number=route?route.y:floorAt(x,y,w.gg.scY,w.gg.scX);
            return {units:details,fixed:fixed,localOnly:localOnly,removed:removed,fixedActorHP:fixed?(durable?100000:500):null,playerY:isNaN(playerY)?y:playerY};
        }
        public function actorUnits():Array {
            var out:Array=[];for each(var actor:Object in actors)out.push(actor.unit);return out;
        }
        public function sample():void {
            for each(var r:Object in actors){
                var u:*=r.unit;
                if(u.sost!=1)continue;
                if(u.celUnit===w.gg)++targetFrames;
                if(Math.abs(u.dx)+Math.abs(u.dy)>.1)++movingFrames;
                if(u.currentWeapon){
                    var gun:*=u.currentWeapon,t:int=gun.t_attack;
                    if(t>r.attack)++shots;r.attack=t;
                    if(gun===r.gun && gun.b && gun.b!==r.bullet && gun.b.weap===gun && gun.b.owner===u)++actualShotFrames;
                    r.gun=gun;r.bullet=gun.b;
                }
            }
        }
        public function snapshot():Object {
            var alive:int=0,armed:int=0,targeting:int=0,details:Array=[];
            var asleep:*=w.main.getChildByName("ContinuousSceneCarrier")["nativeAPI"].sleeping(w.loc);
            for each(var r:Object in actors) {
                var u:*=r.unit;
                var gun:*=u.currentWeapon;
                details.push({x:u.X,y:u.Y,dx:u.dx,dy:u.dy,hp:u.hp,maxhp:u.maxhp,target:u.celUnit===w.gg,
                    celX:u.celX,celY:u.celY,climbing:u.isLaz,levit:u.levit,stun:u.stun,shok:u.shok,
                    disabled:u.disabled,sleeping:asleep?Boolean(asleep[u]):false,
                    weapon:gun?{id:gun.id,hold:gun.hold,holder:gun.holder,attack:gun.t_attack,reload:gun.t_reload,hp:gun.hp,jammed:gun.jammed}:null});
                if(u.sost!=1)continue;
                ++alive;if(u.currentWeapon)++armed;if(u.celUnit===w.gg)++targeting;
            }
            return {targetFrames:targetFrames,shots:shots,actualShotFrames:actualShotFrames,movingFrames:movingFrames,alive:alive,armed:armed,targeting:targeting,actors:details};
        }
    }
}
