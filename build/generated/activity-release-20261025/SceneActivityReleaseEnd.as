package {
    import flash.utils.getDefinitionByName;
    import flash.utils.getQualifiedClassName;
    import flash.utils.getTimer;

    /** Read only, after the final timing sample. Not a lifecycle acceptance test. */
    public class SceneActivityReleaseEnd {
        public static function read(w:*):Object {
            var started:int=getTimer();
            var api:*=w.main.getChildByName("ContinuousSceneCarrier")["nativeAPI"];
            var Idle:Class=api.idleAccess as Class;
            var WeaponIdle:Class=api.weaponIdleAccess as Class;
            if(!Idle || !WeaponIdle)throw new Error("Sibling-domain observation API missing");
            var names:Array=["fe.unit.Unit","fe.unit.UnitRaider","fe.unit.UnitMerc","fe.unit.UnitSlaver",
                "fe.weapon.Weapon","fe.weapon.WThrow"];
            var actual:Array=Idle["nativeClasses"](), identities:Array=[];
            if(actual.length!=names.length)throw new Error("Native class identity list changed");
            for(var i:int=0;i<names.length;++i) {
                var same:Boolean=actual[i]===getDefinitionByName(names[i]);
                identities.push({name:names[i],same:same});
                if(!same)throw new Error("Native extern identity mismatch: "+names[i]);
            }
            if(api.activityLeaseVersion()!=="activity-lease-1")throw new Error("Activity candidate API missing");
            if(Idle["mayRest"](null)!==false || Idle["mayRest"]({})!==false)
                throw new Error("Unknown objects incorrectly qualify for rest");
            var sleeping:Object=api.sleeping(w.loc), units:Array=[], positive:int=0, awakePositive:int=0;
            var released:int=0,releasedSleeping:int=0;
            for each(var u:* in w.loc.units) {
                if(!u)continue;
                var canRest:Boolean=Idle["mayRest"](u)===true;
                var record:Object=api.activityProbe(u);
                if(record && record.released){++released;if(record.sleeping)++releasedSleeping;}
                if(canRest) {++positive;if(!sleeping || !sleeping[u])++awakePositive;}
                var gun:*=u.currentWeapon;
                units.push({kind:getQualifiedClassName(u),id:u.id,x:u.X,y:u.Y,hp:u.hp,maxhp:u.maxhp,
                    target:u.celUnit!=null,priorTarget:u.priorUnit!=null,mayRest:canRest,
                    sleeping:sleeping?Boolean(sleeping[u]):false,record:record,
                    weapon:gun?{kind:getQualifiedClassName(gun),id:gun.id,rapid:gun.rapid,
                        t_attack:gun.t_attack,t_prep:gun.t_prep,t_reload:gun.t_reload,
                        mayRest:WeaponIdle["mayRest"](gun,u)===true}:null});
                if(canRest && (u.celUnit!=null || u.priorUnit!=null))
                    throw new Error("Targeted unit qualified for rest");
            }
            return {version:"activity-release-end-1",diagnosticOnly:true,performanceEligible:false,
                nativeIdentityVerified:true,identities:identities,unknownObjectsRejected:true,
                positive:positive,awakePositive:awakePositive,released:released,releasedSleeping:releasedSleeping,
                units:units,activity:api.activityStats(),
                startedAtMs:started,endedAtMs:getTimer(),lifecycleVerified:false};
        }
    }
}
