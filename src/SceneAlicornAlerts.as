package {
    import flash.utils.Dictionary;

    /** One relay decision per recipient's native alert episode, shared by both broadcasts. */
    public class SceneAlicornAlerts {
        private static var location:*;
        private static var episodes:Dictionary=new Dictionary(true);

        private static function sync(unit:*):void {
            if(location!==unit.loc) {
                location=unit.loc;
                episodes=new Dictionary(true);
            }
        }
        public static function allow(unit:*):Boolean {
            sync(unit);
            var episode:Object=episodes[unit];
            if(!episode) {
                // No received alert: this is an independent native alarm source.
                episodes[unit]={allow:true};
                return true;
            }
            return episode.allow;
        }
        public static function receive(unit:*):void {
            sync(unit);
            if(episodes[unit]) return; // Neither repeated messages nor cycles reroll.
            var chance:int=ContinuousSceneMod.alicornRelayPercent;
            episodes[unit]={allow:chance>=100 || (chance>0 && Math.random()*100<chance)};
        }
        public static function clear(unit:*):void {
            delete episodes[unit];
        }
    }
}
