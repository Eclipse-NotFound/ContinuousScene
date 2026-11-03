package tests {
    /** Mirrors the native fe.inter.Camera field types exactly: vx/vy/celX/celY
     * are declared int there, so fractional writes truncate silently. The
     * deterministic checks use this fixture to cover that path; the live probe
     * covers it inside the real game. */
    public class FakeIntCamera {
        public var moved:Boolean=true;
        public var camRun:Boolean=false;
        public var showOn:Boolean=false;
        public var vx:int=-500;
        public var vy:int=-400;
        public var maxvx:int=3000;
        public var maxvy:int=2000;
        public var scaleV:Number=1;
        public var quakeX:Number=0;
        public var quakeY:Number=0;
        public var screenX:int=1920;
        public var screenY:int=1000;
        public var celX:int=960;
        public var celY:int=500;
    }
}
