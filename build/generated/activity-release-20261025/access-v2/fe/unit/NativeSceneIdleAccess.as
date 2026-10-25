package fe.unit {
    import fe.weapon.NativeSceneWeaponIdleAccess;
    import fe.weapon.Weapon;
    import fe.weapon.WThrow;

    /** Candidate only. External declarations must never be linked into the mod. */
    public class NativeSceneIdleAccess {
        private static const CONSTRUCTOR:QName = new QName("", "constructor");

        /** Compare each Class with the actual host domain before scheduling. */
        public static function nativeClasses():Array {
            return [Unit, UnitRaider, UnitMerc, UnitSlaver, Weapon, WThrow];
        }

        /** Necessary idle evidence only; caller retains every existing protection. */
        public static function mayRest(value:*):Boolean {
            var result:Boolean = false;
            try {
                result = inspect(value);
            } catch (error:*) {
                // Failure cannot authorize sleeping. No native operation is caught.
                result = false;
            }
            return result;
        }

        private static function inspect(value:*):Boolean {
            var u:Unit = value as Unit;
            if (u == null) return false;
            var kind:Class = Object(u)[CONSTRUCTOR] as Class;
            if (kind !== UnitRaider && kind !== UnitMerc && kind !== UnitSlaver) return false;
            var raider:UnitRaider = u as UnitRaider;
            if (raider == null || (u.aiState != 0 && u.aiState != 1) || u.aiSpok != 0
                || u.celUnit != null || u.priorUnit != null
                || raider.aiAttack != 0 || raider.t_chCel != 0) return false;
            if (u.currentWeapon != null && !NativeSceneWeaponIdleAccess.mayRest(u.currentWeapon, u)) return false;
            var children:Array = u.childObjs;
            if (children == null) return false;
            for (var key:String in children) {
                var child:* = children[key];
                if (child != null && !NativeSceneWeaponIdleAccess.mayRest(child, u)) return false;
            }
            return true;
        }
    }
}
