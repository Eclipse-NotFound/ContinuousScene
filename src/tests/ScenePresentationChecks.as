package tests {
    import flash.display.BitmapData;
    import flash.geom.Rectangle;
    import flash.geom.Point;
    /** End-only isolated check: native decal history must not be saved. */
    public class ScenePresentationChecks {
        public static function run(w:*,present:*,check:Function,tiles:Boolean=true):Object {
            var g:*=w.grafon,c:*=w.cam,gg:*=w.gg;
            var saved:Object={x:gg.X,y:gg.Y,zoom:c.isZoom};
            var result:Object={views:0,dirtyDisplays:0};
            try {
                for(var zoom:int=0;zoom<3;++zoom)for each(var x:Number in [saved.x,Math.min(w.loc.limX-200,saved.x+1550),Math.min(w.loc.limX-200,saved.x+1800)]) {
                    present.clear();c.setZoom(zoom);gg.setLocPos(x,saved.y);c.calc(gg);
                    compare(w,present,check,"presentation-view-"+zoom+"-"+x);++result.views;
                }
                present.clear();c.setZoom(saved.zoom);gg.setLocPos(saved.x,saved.y);c.calc(gg);present.update(w,true);
                g.decal(null,SceneDecalMetalPaint,saved.x+320,saved.y-100,1,0,"normal");
                check("presentation-native-decal-dirties-surfaces",g.sceneLastDirtyCount>0,g.sceneLastDirtyCount);
                present.update(w,true);
                if(tiles)for each(var s:Object in g.sceneSurfaces())for(var layer:int=0;layer<4;++layer){
                    var b:*=s.bitmaps[layer];if(!b.visible)continue;
                    var expected:BitmapData=new BitmapData(s.side,s.side,true,0);
                    expected.copyPixels(s.nativeBuffers[layer],new Rectangle(s.gutter,s.gutter,s.side,s.side),new Point());
                    var diff:*=b.bitmapData.compare(expected);
                    check("presentation-current-native-pixels-"+s.cx+":"+s.cy+":"+layer,diff===0);
                    if(diff is BitmapData)diff.dispose();expected.dispose();++result.dirtyDisplays;
                }
                // Compare the already-updated helper before clearing its cache.
                var updated:BitmapData=new BitmapData(w.main.stage.stageWidth,w.main.stage.stageHeight,false,0);
                updated.draw(w.main.stage);present.clear();
                var nativePixels:BitmapData=updated.clone();nativePixels.draw(w.main.stage);
                var delta:*=updated.compare(nativePixels);check("presentation-dirty-display-current",delta===0);
                if(delta is BitmapData)delta.dispose();updated.dispose();nativePixels.dispose();
                compare(w,present,check,"presentation-after-native-decal");
            } finally {present.clear();c.setZoom(saved.zoom);gg.setLocPos(saved.x,saved.y);c.calc(gg);}
            return result;
        }
        private static function compare(w:*,present:*,check:Function,name:String):void {
            var stage:*=w.main.stage;
            var before:BitmapData=new BitmapData(stage.stageWidth,stage.stageHeight,false,0),after:BitmapData=before.clone();
            try {
                present.clear();before.draw(stage);present.update(w,true);after.draw(stage);
                var diff:*=after.compare(before);check(name,diff===0,{zoom:w.cam.scaleV});
                if(diff is BitmapData)diff.dispose();
            } finally {before.dispose();after.dispose();}
        }
    }
}
