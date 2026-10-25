package fe.weapon {
    import fe.unit.Unit;

    /** Exact known weapon classes only; reads the native fe.weapon internal QName. */
    public class NativeSceneWeaponIdleAccess {
        private static const CONSTRUCTOR:QName = new QName("", "constructor");

        public static function mayRest(value:*, owner:Unit):Boolean {
            var result:Boolean = false;
            try {
                result = inspect(value, owner);
            } catch (error:*) {
                result = false;
            }
            return result;
        }

        private static function inspect(value:*, owner:Unit):Boolean {
            var weapon:Weapon = value as Weapon;
            if (weapon == null || owner == null || weapon.owner !== owner) return false;
            var kind:Class = Object(weapon)[CONSTRUCTOR] as Class;
            if (kind !== Weapon && kind !== WThrow) return false;
            if (weapon.rapid <= 0) return false;
            if (weapon.t_attack != 0 || weapon.t_prep != 0 || weapon.t_reload != 0
                || weapon.t_rel != 0 || weapon.t_shoot != 0 || weapon.t_auto != 0) return false;
            if (weapon.is_attack || weapon.is_pattack || weapon.t_ret != 0
                || !isFinite(weapon.rotUp) || weapon.rotUp != 0) return false;
            if (weapon.recharg < 0 || weapon.hold < 0 || weapon.holder < 0) return false;
            if (weapon.recharg != 0 && weapon.hold < weapon.holder) return false;
            if (!isFinite(weapon.reloadMult) || Math.round(10 * weapon.reloadMult) <= 0) return false;
            return true;
        }
    }
}
