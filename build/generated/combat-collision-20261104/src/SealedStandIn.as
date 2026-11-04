package
{
    /** Sealed class (no `dynamic` keyword) used to reproduce, offline, the
     *  `Error #1069` that `World.w.visual.root["sceneCU"]` throws on fe.MainFE. */
    public class SealedStandIn
    {
        public var frame:int;

        public function SealedStandIn()
        {
            frame = 0;
        }
    }
}
