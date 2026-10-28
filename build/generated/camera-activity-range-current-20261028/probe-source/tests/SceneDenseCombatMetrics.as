package tests {
    import flash.utils.Dictionary;
    import flash.utils.getDefinitionByName;
    import flash.utils.getTimer;

    /** Isolated read-only workload census. Scan cost stays inside wall time. */
    public class SceneDenseCombatMetrics {
        private var bulletClass:Class;
        private var actors:Dictionary=new Dictionary(true);
        private var seen:Dictionary=new Dictionary(true);
        private var initialized:Boolean=false;
        private var boundLoc:*,boundPlayer:*;
        public function bind(w:*,units:Array):void {
            boundLoc=w.loc;boundPlayer=w.gg;
            bulletClass=getDefinitionByName("fe.weapon.Bullet") as Class;
            if(!bulletClass || units.length!=6)throw new Error("Dense fixture requires six native shooters");
            for each(var unit:* in units)actors[unit]=true;
        }
        public function bucket():Object {
            return {version:"dense-workload-1",samples:0,
                x:[],y:[],dx:[],dy:[],stay:[],floorContact:[],walk:[],isRun:[],
                left:[],right:[],runKey:[],jumpKey:[],attackKey:[],
                walkSpeed:[],runSpeed:[],maxSpeed:[],stamina:[],
                liveBullets:[],fixtureBullets:[],playerBullets:[],otherBullets:[],
                visibleBullets:[],chainBullets:[],observedNewBullets:[],
                objectsScanned:[],scanMs:[]};
        }
        public function sample(w:*,out:Object,state:Object):void {
            if(w.loc!==boundLoc || w.gg!==boundPlayer)throw new Error("Dense census world changed");
            var begin:int=getTimer(),live:int=0,fixture:int=0,player:int=0,other:int=0;
            var visible:int=0,chain:int=0,fresh:int=0,scanned:int=0;
            for(var obj:*=w.loc.firstObj;obj;obj=obj.nobj) {
                if(++scanned>100000)throw new Error("Object chain did not terminate");
                if(!(obj is bulletClass) || obj.in_chain!==true)continue;
                ++chain;
                if(!seen[obj]){seen[obj]=true;if(initialized)++fresh;}
                if(obj.vis && obj.vis.visible && obj.vis.alpha>0 && obj.vis.stage)++visible;
                // Bullet.vse is protected. Native step removes ended bullets
                // from this chain; off is the public stopped-flight flag.
                if(obj.off)continue;
                ++live;
                if(obj.owner===boundPlayer)++player;
                else if(actors[obj.owner])++fixture;
                else ++other;
            }
            initialized=true;
            out.scanMs.push(getTimer()-begin);out.objectsScanned.push(scanned);
            out.liveBullets.push(live);out.fixtureBullets.push(fixture);out.playerBullets.push(player);
            out.otherBullets.push(other);out.visibleBullets.push(visible);out.chainBullets.push(chain);
            // The first sample seeds identities without counting pre-existing projectiles.
            // Later observed births are a lower bound: a projectile can end between samples.
            out.observedNewBullets.push(fresh);
            out.x.push(state.X);out.y.push(state.Y);out.dx.push(state.dx);out.dy.push(state.dy);
            out.stay.push(state.stay);out.floorContact.push(state.floorContact);out.walk.push(state.walk);
            out.left.push(state.keys.left);out.right.push(state.keys.right);out.runKey.push(state.keys.run);
            out.jumpKey.push(state.keys.jump);out.attackKey.push(state.keys.attack);
            out.isRun.push(Boolean(w.gg.isRun));out.walkSpeed.push(Number(w.gg.walkSpeed));
            out.runSpeed.push(Number(w.gg.runSpeed));out.maxSpeed.push(Number(w.gg.maxSpeed));
            out.stamina.push(Number(w.gg.stam));++out.samples;
        }
    }
}
