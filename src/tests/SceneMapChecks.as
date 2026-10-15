package tests {
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.display.DisplayObject;
    import flash.display.DisplayObjectContainer;
    import flash.geom.Point;
    import flash.geom.Rectangle;
    import flash.utils.getDefinitionByName;
    import flash.utils.getQualifiedClassName;

    /** Isolated-driver helper. Open w.pip.onoff(3,1) and settle before run().
     *  No frame advances, saves, file writes, exits, or uncaught test exceptions.
     *  Temporary exploration pixels and UI transforms are restored synchronously.
     */
    public class SceneMapChecks {
        public static function run(w:*):Array {
            var results:Array=[];
            var savedTiles:Array=[];
            var oldDrawAll:Boolean=false, haveDrawAll:Boolean=false;
            var page:*, map:Bitmap, parent:DisplayObjectContainer;
            var oldScale:Number, oldX:Number, oldY:Number, haveUI:Boolean=false;
            try {
                if(!w || !w.land || !w.loc || !w.gg) {
                    add(results,"map-context-ready",false); return results;
                }
                var WorldClass:*=getDefinitionByName("fe.World");
                var loc:*=w.loc, land:*=w.land;
                var cellX:int=WorldClass.cellsX,cellY:int=WorldClass.cellsY;
                var large:Boolean=loc.spaceX>cellX || loc.spaceY>cellY;
                var raster:BitmapData=land.drawMap();
                if(large) {
                    // The continuous fixture is one native Location at grid (0,0).
                    add(results,"map-large-single-location",land.maxLocX-land.minLocX==1 && land.maxLocY-land.minLocY==1);
                    add(results,"map-full-scene-dimensions",raster.width==loc.spaceX && raster.height==loc.spaceY,
                        {actual:[raster.width,raster.height],expected:[loc.spaceX,loc.spaceY]});
                    oldDrawAll=w.drawAllMap;haveDrawAll=true;
                    w.drawAllMap=true; raster=land.drawMap();
                    var farX:int=loc.spaceX-3,farY:int=loc.spaceY-3;
                    add(results,"map-far-terrain-can-be-revealed",(raster.getPixel32(farX,farY)>>>24)==255,
                        {x:farX,y:farY,alpha:raster.getPixel32(farX,farY)>>>24});
                    // Native map alpha takes the maximum of this 2x2 tile group.
                    // drawMapObj changes RGB only, so native object markers cannot
                    // accidentally make these alpha assertions pass.
                    for(var x:int=farX;x<=farX+1;++x) for(var y:int=farY;y<=farY+1;++y) {
                        var tile:*=loc.space[x][y];savedTiles.push({tile:tile,visi:tile.visi});tile.visi=0;
                    }
                    w.drawAllMap=false;raster=land.drawMap();
                    add(results,"map-unexplored-far-terrain-stays-hidden",(raster.getPixel32(farX,farY)>>>24)==0);
                    loc.space[farX+1][farY+1].visi=0.75;raster=land.drawMap();
                    add(results,"map-far-exploration-alpha",(raster.getPixel32(farX,farY)>>>24)==191,
                        {alpha:raster.getPixel32(farX,farY)>>>24});
                    restoreTiles(savedTiles);savedTiles=[];w.drawAllMap=oldDrawAll;haveDrawAll=false;
                    raster=land.drawMap();
                } else {
                    add(results,"map-native-grid-dimensions-unchanged",
                        raster.width==cellX*(land.maxLocX-land.minLocX) && raster.height==cellY*(land.maxLocY-land.minLocY),
                        {actual:[raster.width,raster.height],grid:[land.maxLocX-land.minLocX,land.maxLocY-land.minLocY]});
                }
                var info:Boolean=w.pip && w.pip.active && getQualifiedClassName(w.pip.currentPage)=="fe.inter::PipPageInfo";
                add(results,"map-ui-info-page-open",info);
                if(!info) return results;
                page=w.pip.currentPage;map=page.map as Bitmap;
                add(results,"map-ui-uses-native-land-raster",map && map.bitmapData===land.map);
                if(!map || !map.parent) return results;
                parent=map.parent;
                var marker:DisplayObject=parent.getChildByName("plTag");
                add(results,"map-ui-visible-and-clipped",visible(map) && parent.mask!=null);
                if(large && parent.mask) {
                    var mapBounds:Rectangle=map.getBounds(map.stage);
                    var clipBounds:Rectangle=parent.mask.getBounds(map.stage);
                    clipBounds.inflate(.1,.1);
                    add(results,"map-ui-initial-fitting-axes-visible",
                        (mapBounds.width>clipBounds.width || (mapBounds.left>=clipBounds.left && mapBounds.right<=clipBounds.right)) &&
                        (mapBounds.height>clipBounds.height || (mapBounds.top>=clipBounds.top && mapBounds.bottom<=clipBounds.bottom)),
                        {map:mapBounds.toString(),clip:clipBounds.toString()});
                }
                add(results,"map-ui-player-marker-exists",marker!=null);
                if(!marker) return results;
                var tilePoint:Point=new Point((loc.landX-land.minLocX)*cellX+w.gg.X/WorldClass.tileX,
                    (loc.landY-land.minLocY)*cellY+(w.gg.Y-w.gg.scY/2)/WorldClass.tileY);
                add(results,"map-ui-player-within-raster",tilePoint.x>=0 && tilePoint.y>=0 && tilePoint.x<raster.width && tilePoint.y<raster.height,
                    {tileX:tilePoint.x,tileY:tilePoint.y});
                oldScale=map.scaleX;oldX=parent.x;oldY=parent.y;haveUI=true;
                var grow:Boolean=oldScale<6;
                // drawMap() above refreshed land.ggX/Y. The open UI marker may
                // still represent the preceding gameplay frame. Native zoom
                // recalculates it; use a reversible native pair before comparing.
                if(grow) page.funZoomP(null); else page.funZoomM(null);
                if(grow) page.funZoomM(null); else page.funZoomP(null);
                add(results,"map-ui-player-aligned",aligned(map,marker,tilePoint),alignmentDetail(map,marker,tilePoint));
                if(grow) page.funZoomP(null); else page.funZoomM(null);
                add(results,"map-ui-native-zoom",map.scaleX==oldScale+(grow?1:-1) && map.scaleY==map.scaleX && aligned(map,marker,tilePoint),
                    {before:oldScale,after:map.scaleX,alignment:alignmentDetail(map,marker,tilePoint)});
                if(grow) page.funZoomM(null);else page.funZoomP(null);
                page.funCenter(null);
                var background:DisplayObject=parent.parent ? parent.parent.getChildByName("fon") : null;
                add(results,"map-ui-native-center",background && Math.abs(parent.x+marker.x-background.width/2)<0.1 && Math.abs(parent.y+marker.y-background.height/2)<0.1);
                parent.x+=23;parent.y-=17;
                add(results,"map-ui-pan-transform-keeps-player-aligned",aligned(map,marker,tilePoint),alignmentDetail(map,marker,tilePoint));
            } catch(error:Error) {
                add(results,"map-check-exception",false,error.message);
            } finally {
                try {
                    restoreTiles(savedTiles);
                    if(haveDrawAll) w.drawAllMap=oldDrawAll;
                    if(savedTiles.length || haveDrawAll) w.land.drawMap();
                    if(haveUI) {
                        for(var i:int=0;i<6 && map.scaleX!=oldScale;++i) {
                            if(map.scaleX<oldScale) page.funZoomP(null);else page.funZoomM(null);
                        }
                        parent.x=oldX;parent.y=oldY;
                        add(results,"map-check-restores-ui",map.scaleX==oldScale && parent.x==oldX && parent.y==oldY);
                    }
                } catch(restoreError:Error) { add(results,"map-check-restore-exception",false,restoreError.message); }
            }
            return results;
        }
        private static function add(result:Array,name:String,ok:Boolean,detail:*=null):void {
            result.push({name:name,ok:ok,detail:detail});
        }
        private static function restoreTiles(saved:Array):void {
            for each(var entry:Object in saved) entry.tile.visi=entry.visi;
        }
        private static function aligned(map:Bitmap,marker:DisplayObject,tilePoint:Point):Boolean {
            var a:Point=map.localToGlobal(tilePoint),b:Point=marker.localToGlobal(new Point());
            // Display-object translations are quantized more coarsely than the
            // logical player coordinates. One tenth of a screen pixel avoids
            // reporting native subpixel registration as a displaced map marker.
            return Math.abs(a.x-b.x)<=0.100001 && Math.abs(a.y-b.y)<=0.100001;
        }
        private static function alignmentDetail(map:Bitmap,marker:DisplayObject,tilePoint:Point):Object {
            var expected:Point=map.localToGlobal(tilePoint),actual:Point=marker.localToGlobal(new Point());
            return {expected:[expected.x,expected.y],actual:[actual.x,actual.y],
                delta:[actual.x-expected.x,actual.y-expected.y],tile:[tilePoint.x,tilePoint.y],
                markerLocal:[marker.x,marker.y],mapScale:[map.scaleX,map.scaleY],tolerance:0.100001};
        }
        private static function visible(value:DisplayObject):Boolean {
            if(!value.stage) return false;
            while(value) { if(!value.visible || value.alpha<=0) return false;value=value.parent; }
            return true;
        }
    }
}
