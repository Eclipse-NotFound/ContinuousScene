package fe.unit {
    import fe.Obj;
    import fe.weapon.Weapon;

    /** External names/types only. Slot order is not a runtime contract. */
    public class Unit extends Obj {
        internal var aiState:int;
        internal var aiSpok:int;
        public var celUnit:Unit;
        public var priorUnit:Unit;
        public var childObjs:Array;
        public var currentWeapon:Weapon;
    }
}
