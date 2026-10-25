package fe.weapon {
    import fe.Obj;
    import fe.unit.Unit;

    /** Compiler-only native names/types; never package this class. */
    public class Weapon extends Obj {
        public var owner:Unit;
        internal var is_attack:Boolean;
        internal var is_pattack:Boolean;
        public var t_attack:int;
        public var t_prep:int;
        public var t_reload:int;
        public var t_rel:int;
        public var t_shoot:int;
        public var t_auto:int;
        internal var t_ret:int;
        internal var rotUp:Number;
        public var hold:int;
        public var holder:int;
        public var recharg:int;
        public var reloadMult:Number;
    }
}
