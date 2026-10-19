package {
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.geom.Point;
    import flash.geom.Rectangle;
    import flash.events.DataEvent;
    import flash.utils.getTimer;
    public class ContinuousSceneWallTrimChecks {
        private static function capture(g:*):Object {
            var result:Object={};
            for each(var parent:* in [g.visFront,g.visBack])for(var i:int=0;i<parent.numChildren;++i) {
                var b:Bitmap=parent.getChildAt(i) as Bitmap;
                if(!b || !b.bitmapData || b.name.indexOf("WallBlendScene")!=0)continue;
                var clip:Rectangle=b.scrollRect;
                var data:BitmapData=new BitmapData(clip.width,clip.height,true,0);
                data.copyPixels(b.bitmapData,clip,new Point());
                result[b.name+":"+b.x+":"+b.y]=data;
            }
            return result;
        }
        public static function run(w:*,check:Function):Array {
            var rows:Array=[];
            var reference:Object;
            try {
                for(var mode:int=0;mode<2;++mode) {
                  setCurrentMode(w,mode==0);
                  for(var pass:int=0;pass<4;++pass) {
                    var request:DataEvent=new DataEvent("continuousSceneTrimPadding",false,false,(pass%2)==1?"1":"0");
                    var start:int=getTimer();w.main.dispatchEvent(request);
                    rows.push({mode:mode==0?"current":"second",trim:(pass%2)==1,ms:getTimer()-start});
                    check("wall-padding-switch-acknowledged-"+mode+"-"+pass,request.data=="done");
                    var images:Object=capture(w.grafon),count:int=0,bad:int=0;
                    if(reference) {
                        for(var key:String in reference) {
                            ++count;
                            if(!images[key]){++bad;continue;}
                            var diff:*=reference[key].compare(images[key]);
                            if(diff!==0)++bad;if(diff is BitmapData)diff.dispose();
                        }
                        check("wall-padding-visible-pixels-"+mode+"-"+pass,count>0 && bad==0,{images:count,different:bad});
                        for each(var old:BitmapData in reference)old.dispose();
                    }
                    reference=images;
                  }
                  for each(var last:BitmapData in reference)last.dispose();reference=null;
                }
            } finally {if(reference)for each(var image:BitmapData in reference)image.dispose();setCurrentMode(w,true);}
            return rows;
        }
        private static function setCurrentMode(w:*,value:Boolean):void {
            var api:*=w.main.getChildByName("ModSettingsCarrier")["modAPI"];
            for each(var page:Object in api.getPages())if(page.modId=="wallblend")
                for each(var item:Object in page.items)if(item.key=="currentMode") {item["set"](value);return;}
            throw new Error("WallBlend mode setting unavailable");
        }
    }
}
