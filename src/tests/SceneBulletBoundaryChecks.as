package tests {
    import flash.utils.getDefinitionByName;
    import flash.utils.getQualifiedClassName;
    /** End-of-run fixture: native offscreen hit versus an explicit-target control. */
    public class SceneBulletBoundaryChecks {
        public static function run(w:*):Object {
            var root:*=w.visual.root,previous:*,target:*,readError:String=null;
            try {previous=root["sceneCU"];}catch(error:Error){readError=error.message;}
            var candidates:Array=previous as Array;
            var cam:*=w.cam,left:Number=(-cam.vx-cam.quakeX)/cam.scaleV-500;
            var top:Number=(-cam.vy-cam.quakeY)/cam.scaleV-500;
            // Sleeping distant actors are disabled by design. Create a native,
            // active target on the known test corridor, then remove it entirely.
            var Raider:Class=getDefinitionByName("fe.unit.UnitRaider") as Class;
            target=new Raider("1",4,null,{weap:"autor",tr:1});
            var fixtureX:Number=NaN;
            for(var xx:int=6200;xx<8800;xx+=80) {
                var clear:Boolean=w.loc.getAbsTile(xx,2920).phis==0 && w.loc.getAbsTile(xx,2890).phis==0;
                for each(var u:* in w.loc.units)if(u && !u.disabled && !u.trigDis && u.sost!=4
                    && u.X2>=xx-40 && u.X1<=xx+40 && u.Y2>=2880 && u.Y1<=2960)clear=false;
                if(clear){fixtureX=xx;break;}
            }
            if(isNaN(fixtureX))throw new Error("No isolated offscreen test position");
            target.putLoc(w.loc,fixtureX,2959);w.loc.addObj(target);w.loc.units.push(target);
            target.setPos(fixtureX,2959);target.dx=target.dy=0;target.disabled=false;
            var initialFraction:int=target.fraction;
            target.fraction=w.gg.fraction==1?2:1;
            var Bullet:Class=getDefinitionByName("fe.weapon.Bullet") as Class;
            var hp:Number=target.hp,maxhp:Number=target.maxhp,result:Object={x:target.X,y:target.Y,
                className:getQualifiedClassName(target),rootClass:getQualifiedClassName(root),listReadError:readError,
                initialFraction:initialFraction,ownerFraction:w.gg.fraction,targetFraction:target.fraction,
                cameraList:candidates?candidates.length:null,allUnits:w.loc.units.length,
                offscreen:!(target.X>=left && target.X<=left+cam.screenX/cam.scaleV+1000 && target.Y>=top && target.Y<=top+cam.screenY/cam.scaleV+1000),
                targetInCameraList:candidates?candidates.indexOf(target)>=0:false};
            try {
                target.maxhp=target.hp=10000;
                var b:*=new Bullet(w.gg,(target.X1+target.X2)*.5,(target.Y1+target.Y2)*.5,null,false);
                b.damage=500;b.dx=b.dy=0;b.run();result.cameraDamage=10000-target.hp;result.cameraBulletOff=b.off;
                result.cameraVisited=Boolean(b.parr && b.parr.indexOf(target)>=0);
                result.cameraContacts=[];
                if(b.parr)for each(var hit:* in b.parr)result.cameraContacts.push({type:getQualifiedClassName(hit),x:hit.X,y:hit.Y,fraction:hit.fraction});
                target.hp=10000;
                b=new Bullet(w.gg,(target.X1+target.X2)*.5,(target.Y1+target.Y2)*.5,null,false);
                b.damage=500;b.dx=b.dy=0;b.targetObj=target;b.run();result.completeDamage=10000-target.hp;result.completeBulletOff=b.off;
                result.controlValid=result.completeDamage>0;
                result.cameraMissReproduced=result.controlValid && result.cameraDamage==0;
            } finally {
                target.hp=hp;target.maxhp=maxhp;target.remVisual();w.loc.remObj(target);
                var at:int=w.loc.units.indexOf(target);if(at>=0)w.loc.units.splice(at,1);
            }
            return result;
        }
    }
}
