package tests {
    import flash.display.BitmapData;
    import flash.display.Bitmap;
    import flash.display.DisplayObjectContainer;
    import flash.display.DisplayObject;
    import flash.geom.Point;
    import flash.geom.Rectangle;
    import flash.utils.getTimer;
    /** Component attribution only; never a replacement for live frame timing. */
    public class SceneRasterTiming {
        public static function run(w:*,fogPresentation:*):Object {
            var g:*=w.grafon,stage:*=w.main.stage;
            var groups:Object={world:[w.visual],fog:[g.visLight],objects:g.visObjs,
                raster:[g.visBack,g.visBack2,g.visFront,g.visVoda]};
            var result:Object={rows:[],width:stage.stageWidth,height:stage.stageHeight,
                quality:stage.quality,worldFilters:w.visual.filters.length,worldCached:w.visual.cacheAsBitmap};
            var bitmap:BitmapData=new BitmapData(stage.stageWidth,stage.stageHeight,false,0);
            var reference:BitmapData=bitmap.clone();reference.draw(stage);
            try {
                for each(var mode:String in ["baseline","fogpixels","tilecrop","composite","fogclip","objectclip","fog","objects","raster","world","world","raster","objects","fog","objectclip","fogclip","composite","tilecrop","fogpixels","baseline"]) {
                    var saved:Array=[],clips:Array=[],created:Array=[],nodes:Array=groups[mode] as Array;
                    if(nodes)for each(var d:DisplayObject in nodes){saved.push([d,d.visible]);d.visible=false;}
                    var view:Rectangle=g.sceneViewport();view.inflate(160,160);
                    view=new Rectangle(Math.floor(view.x),Math.floor(view.y),Math.ceil(view.right)-Math.floor(view.x),Math.ceil(view.bottom)-Math.floor(view.y));
                    var prepareAt:int=getTimer();
                    if(mode=="fogpixels")fogPresentation.update(w,true);
                    if(mode=="tilecrop")for each(var cropLayer:DisplayObjectContainer in groups.raster){
                        var originals:Array=[];
                        for(var ci:int=0;ci<cropLayer.numChildren;++ci)originals.push(cropLayer.getChildAt(ci));
                        for each(var source:Bitmap in originals){
                            if(!source || !source.visible || !source.bitmapData || !source.scrollRect)continue;
                            var sourceRect:Rectangle=source.scrollRect;
                            var cut:BitmapData=new BitmapData(sourceRect.width,sourceRect.height,true,0);
                            cut.copyPixels(source.bitmapData,sourceRect,new Point());
                            var copy:Bitmap=new Bitmap(cut);copy.x=source.x;copy.y=source.y;cropLayer.addChild(copy);created.push(copy);
                            saved.push([source,source.visible]);source.visible=false;
                        }
                    }
                    if(mode=="composite")for each(var layer:DisplayObjectContainer in groups.raster){
                        var merged:BitmapData=new BitmapData(view.width,view.height,true,0);
                        for(var childIndex:int=0;childIndex<layer.numChildren;++childIndex){
                            var child:Bitmap=layer.getChildAt(childIndex) as Bitmap;
                            if(!child || !child.visible || !child.bitmapData)continue;
                            var area:Rectangle=child.scrollRect?child.scrollRect:child.bitmapData.rect;
                            merged.copyPixels(child.bitmapData,area,new Point(child.x-view.x,child.y-view.y),null,null,true);
                            saved.push([child,child.visible]);child.visible=false;
                        }
                        var batched:Bitmap=new Bitmap(merged);batched.x=view.x;batched.y=view.y;layer.addChild(batched);created.push(batched);
                    }
                    var prepareMs:int=getTimer()-prepareAt;
                    if(mode=="fogclip"){
                        d=g.visLight.getChildAt(0);clips.push([d,d.scrollRect,d.x,d.y]);
                        var r:Rectangle=new Rectangle(Math.floor((view.x+20)/40),Math.floor((view.y+60)/40),Math.ceil(view.width/40)+2,Math.ceil(view.height/40)+2);
                        d.scrollRect=r;d.x=r.x;d.y=r.y;
                    }
                    if(mode=="objectclip")for each(d in g.visObjs){clips.push([d,d.scrollRect,d.x,d.y]);d.scrollRect=view;d.x=view.x;d.y=view.y;}
                    try {
                        bitmap.draw(stage); // Warm the current display state.
                        var begin:int=getTimer();
                        for(var i:int=0;i<8;++i){bitmap.fillRect(bitmap.rect,0);bitmap.draw(stage);}
                        var row:Object={mode:mode,draws:8,ms:getTimer()-begin,prepareMs:prepareMs};
                        if(mode=="fogclip" || mode=="objectclip" || mode=="composite" || mode=="tilecrop" || mode=="fogpixels"){
                            var diff:*=bitmap.compare(reference);row.pixelsEqual=diff===0;
                            if(diff is BitmapData){row.changedBounds=diff.getColorBoundsRect(0xffffffff,0,false).toString();diff.dispose();}
                        }
                        result.rows.push(row);
                    } finally {
                        for each(var pair:Array in saved)pair[0].visible=pair[1];
                        for each(pair in clips){pair[0].scrollRect=pair[1];pair[0].x=pair[2];pair[0].y=pair[3];}
                        for each(batched in created){batched.parent.removeChild(batched);batched.bitmapData.dispose();}
                        if(mode=="fogpixels")fogPresentation.clear();
                    }
                }
            } finally {bitmap.dispose();reference.dispose();}
            return result;
        }
    }
}
