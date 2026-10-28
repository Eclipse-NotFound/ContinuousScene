package fe.unit {
    /** Test-only access using the native package-internal namespace. Never linked by production. */
    public class AlicornAlertAccess {
        public static function state(u:*):Object {return {state:u.aiState,spok:u.aiSpok};}
        public static function calm(u:*):void {
            u.setNull(true);u.setCel(null,u.X,u.Y);u.priorUnit=null;
            u.aiState=0;u.aiSpok=0;u.aiTCh=0;u.stun=0;u.shok=0;
            u.t_gotov=-10000;u.stroll=false;u.moving=false;u.disabled=true;
        }
        public static function calmDecision(u:*):void {
            u.setCel(null,u.X,u.Y);u.priorUnit=null;u.aiState=0;u.aiSpok=0;u.aiTCh=0;
            u.control();
        }
        public static function decide(u:*):void {u.aiTCh=0;u.control();}
    }
}
