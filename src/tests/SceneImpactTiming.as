package tests {
    import flash.utils.getTimer;
    /** Terminal isolated benchmark: the caller exits without saving mark history. */
    public class SceneImpactTiming {
        public static function run(g:*):Array {
            var rows:Array=[];
            if(!("sceneCompactImpacts" in g))return rows;
            for(var pass:int=0;pass<4;++pass) {
                g.sceneCompactImpacts=(pass%2)==1;
                var start:int=getTimer();
                for(var i:int=0;i<100;++i)
                    g.decal(null,SceneDecalMetalPaint,2560+(i%4)*0.25,640+(i%3)*0.25,1,0,"normal");
                rows.push({compact:g.sceneCompactImpacts,calls:100,ms:getTimer()-start});
            }
            g.sceneCompactImpacts=true;
            return rows;
        }
    }
}
