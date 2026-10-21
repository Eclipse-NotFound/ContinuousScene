package tests {
    import flash.display.BitmapData;
    import flash.geom.Rectangle;
    import flash.geom.Point;
    import flash.utils.Dictionary;
    /** Probe only. No production registration. Verification and timing separate. */
    public class SceneBlitReuse {
        private var records:Dictionary=new Dictionary(true);
        private var enabled:Boolean=false,verify:Boolean=false;
        private var calls:int=0,repeats:int=0,skipped:int=0,verified:int=0,mismatches:int=0;
        public function reset(on:Boolean,checkPixels:Boolean):void {
            records=new Dictionary(true);enabled=on;verify=checkPixels;
            calls=repeats=skipped=verified=mismatches=0;
        }
        public function gate(unit:*,source:BitmapData,target:BitmapData,rect:Rectangle,point:Point):Boolean {
            ++calls;
            var old:Object=records[unit];
            var same:Boolean=old!=null && old.source===source && old.target===target
                && old.x==rect.x && old.y==rect.y && old.w==rect.width && old.h==rect.height
                && old.px==point.x && old.py==point.y;
            if(!same) {
                // The original int parameters and blitX/Y have already produced
                // this exact rectangle. Cache the actual copy arguments.
                records[unit]={source:source,target:target,x:rect.x,y:rect.y,w:rect.width,h:rect.height,
                    px:point.x,py:point.y};
                return false;
            }
            ++repeats;
            if(verify) {
                var expected:BitmapData=target.clone();
                var difference:*;
                try {
                    expected.copyPixels(source,rect,point);
                    difference=expected.compare(target);++verified;
                    if(difference!==0){++mismatches;return false;}
                } finally {if(difference is BitmapData)difference.dispose();expected.dispose();}
            }
            if(enabled)++skipped;
            return enabled;
        }
        public function snapshot():Object {
            return {enabled:enabled,verify:verify,calls:calls,repeats:repeats,skipped:skipped,verified:verified,mismatches:mismatches};
        }
    }
}
