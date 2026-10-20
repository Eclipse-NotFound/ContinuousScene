package tests {
    import flash.utils.getDefinitionByName;
    import flash.utils.getTimer;
    /** Native detached bullet fixtures; no firing, damage or AI mutation. */
    public class SceneThreatChecks {
        public static function run(w:*,check:Function):Object {
            var api:Class=w.main.getChildByName("ContinuousSceneTdfcThreat")["api"] as Class;
            var Bullet:Class=getDefinitionByName("fe.weapon.Bullet") as Class;
            var Smart:Class=getDefinitionByName("fe.weapon.SmartBullet") as Class;
            var Pt:Class=getDefinitionByName("fe.Pt") as Class;
            var owner:*=null;for each(var u:* in w.loc.units)if(u && u!==w.gg && u.loc===w.loc){owner=u;break;}
            if(owner==null)throw new Error("Missing native threat owner fixture");
            var ordinary:*=new Bullet(w.gg,120,180,null,false);
            // SmartBullet's native constructor ignores param5. Remove its
            // temporary registration immediately, before another world step.
            var smart:*=new Smart(w.gg,120,180,null,false);w.loc.remObj(smart);
            var targets:Array=[],noise:Array=[];
            for(var i:int=0;i<260;++i)noise.push(new Pt());
            var sample:Object={unit:w.gg,x:100,y:200,cy:180,dx:0,dy:0};
            var result:Object={version:api["sceneThreatVersion"],comparisons:0,timing:[]};
            var oldFlag:*=api["sceneThreatFast"];
            try {
                for each(var bullet:* in [ordinary,smart])for each(var slot:int in [0,1,255,256])
                  for each(var velocity:Number in [0,1,10,59,60,100]) {
                    for(i=0;i<noise.length;++i)noise[i].nobj=i+1<noise.length?noise[i+1]:null;
                    bullet.owner=owner;bullet.vel=velocity;bullet.rot=Math.PI;bullet.ddy=0;bullet.liv=30;bullet.explRadius=0;
                    bullet.X=120;bullet.Y=180;bullet.nobj=noise[slot];
                    var head:*=slot==0?bullet:noise[0];if(slot>0)noise[slot-1].nobj=bullet;
                    var loc:Object={firstObj:head};
                    api["sceneThreatFast"]=true;
                    var actual:Object=api["threat"](sample,loc),expected:Object=api["sceneThreatReference"](sample,loc);
                    var equal:Boolean=JSON.stringify(actual)===JSON.stringify(expected);
                    check("threat-exact-"+result.comparisons,equal);
                    check("threat-range-and-scan-boundary-"+result.comparisons,(actual!=null)==(slot<256 && velocity>0 && velocity<60));
                    bullet.owner=w.gg;check("threat-own-shot-"+result.comparisons,api["threat"](sample,loc)==null);
                    bullet.owner=owner;bullet.liv=0;check("threat-expired-shot-"+result.comparisons,api["threat"](sample,loc)==null);
                    ++result.comparisons;
                  }
                // Full 256-node traversal with the same native objects in ABBA.
                for(i=0;i<noise.length;++i)noise[i].nobj=i+1<noise.length?noise[i+1]:null;
                loc={firstObj:noise[0]};
                for(var round:int=0;round<4;++round){
                    api["sceneThreatFast"]=round==1 || round==2;
                    var begin:int=getTimer();
                    for(i=0;i<1000;++i)api["threat"](sample,loc);
                    result.timing.push({fast:api["sceneThreatFast"],calls:1000,ms:getTimer()-begin});
                }
            } finally {api["sceneThreatFast"]=oldFlag;ordinary.nobj=smart.nobj=null;}
            return result;
        }
    }
}
