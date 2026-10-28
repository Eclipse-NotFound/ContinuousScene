package tests {
    import flash.display.BitmapData;
    import flash.geom.Rectangle;
    import flash.geom.Point;

    /** Compare the initial viewport with the established full-map renderer.
     * Diagnostic only: keep one small core per visible layer, not two worlds. */
    public final class SceneUpcomingChecks {
        public static function pixels(w:*):Object {
            var g:*=w.grafon,loc:*=w.loc;
            var originals:Array=[];
            var result:Object={passed:true,surfaces:0,layers:[]};
            for(var n:int=0;n<4;++n) result.layers.push({layer:n,pixels:0,changed:0,significant:0,alpha:0,max:0});
            try {
                for each(var s:Object in g.sceneSurfaces()) {
                    var row:Object={cx:s.cx,cy:s.cy,layers:[]};
                    for(n=0;n<4;++n) {
                        var data:BitmapData=new BitmapData(s.side,s.side,true,0);
                        data.copyPixels(s.nativeBuffers[n],new Rectangle(s.gutter,s.gutter,s.side,s.side),new Point());
                        row.layers.push(data);
                    }
                    originals.push(row);
                }
                g.scenePreload=true;g.drawLoc(loc);
                var byKey:Object={};
                for each(s in g.sceneSurfaces())byKey[s.cx+":"+s.cy]=s;
                for each(row in originals) {
                    s=byKey[row.cx+":"+row.cy];
                    if(!s)throw new Error("Full renderer omitted a visible surface");
                    ++result.surfaces;
                    for(n=0;n<4;++n) {
                        var expected:Vector.<uint>=s.nativeBuffers[n].getVector(new Rectangle(s.gutter,s.gutter,s.side,s.side));
                        data=row.layers[n];
                        var actual:Vector.<uint>=data.getVector(data.rect);
                        var stats:Object=result.layers[n];
                        for(var i:int=0;i<actual.length;++i) {
                            ++stats.pixels;
                            if(actual[i]==expected[i])continue;
                            ++stats.changed;
                            var error:int=0;
                            for(var shift:int=0;shift<=24;shift+=8)
                                error=Math.max(error,Math.abs(int((actual[i]>>>shift)&255)-int((expected[i]>>>shift)&255)));
                            stats.max=Math.max(stats.max,error);
                            if(error>8)++stats.significant;
                            if(Math.abs(int(actual[i]>>>24)-int(expected[i]>>>24))>8)++stats.alpha;
                        }
                    }
                }
                for each(stats in result.layers)
                    if(stats.significant>64 || stats.alpha>32)result.passed=false;
            } finally {
                for each(row in originals)for each(data in row.layers)data.dispose();
                g.scenePreload=false;g.drawLoc(loc);w.cam.calc(w.gg);
            }
            return result;
        }
    }
}
