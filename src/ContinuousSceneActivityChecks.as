package {
    import flash.utils.getDefinitionByName;
    public class ContinuousSceneActivityChecks {
        public static function run(main:*,w:*,check:Function):Object {
            var api:*=main.getChildByName("ContinuousSceneCarrier")["nativeAPI"];
            var sleep:Object=api.activity(w.loc),far:Array=[];
            for each(var u:* in w.loc.units)if(u && sleep[u])far.push(u);
            check("distant-unengaged-enemies-pause",far.length>=4,{stats:api.activityStats(),count:far.length});
            if(far.length<4)throw new Error("Not enough sleeping native enemies for coverage");
            var a:*=far[0],b:*=far[1],c:*=far[2],d:*=far[3];
            var count:int=w.loc.units.length,disabled:Boolean=a.disabled,x:Number=a.X,y:Number=a.Y;
            w.loc.step();
            check("sleep-keeps-position-and-collision-membership",a.X==x && a.Y==y && a.disabled==disabled && w.loc.units.length==count && w.loc.units.indexOf(a)>=0);
            var gx:Number=w.gg.X,gy:Number=w.gg.Y;
            w.gg.X=a.X;w.gg.Y=a.Y;api.activity(w.loc);
            check("approach-wakes-before-contact",!sleep[a]);
            w.gg.X=gx;w.gg.Y=gy;
            b.celUnit=w.gg;api.activity(w.loc);b.celUnit=null;
            for(var i:int=0;i<50;++i)api.activity(w.loc);
            check("pursuit-stays-awake-after-losing-target",!sleep[b]);
            c.hp-=1;api.activity(w.loc);
            check("damage-wakes-distant-enemy",!sleep[c]);
            var Bullet:Class=getDefinitionByName("fe.weapon.Bullet") as Class;
            var bullet:*=new Bullet(w.gg,d.X-800,d.Y-20,null,true);bullet.dx=200;bullet.dy=0;
            api.activity(w.loc);
            check("projectile-path-wakes-distant-enemy",!sleep[d]);
            var liv:int=bullet.liv;
            w.loc.step();
            check("projectile-step-never-paused",bullet.liv<liv || !bullet.in_chain);
            if(bullet.in_chain)bullet.setNull();
            w.grafon.scenePauseDistant=false;api.activity(w.loc);
            var asleep:int=0;for each(u in w.loc.units)if(u && sleep[u])++asleep;
            check("scheduler-disabled-restores-all-units",asleep==0);
            w.grafon.scenePauseDistant=true;api.activity(w.loc);
            return {initialSleeping:far.length,units:w.loc.units.length};
        }
    }
}
