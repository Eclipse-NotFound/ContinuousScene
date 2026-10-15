package {
    import flash.display.Sprite;
    import flash.display.BitmapData;
    import flash.display.BitmapDataChannel;
    import flash.desktop.NativeApplication;
    import flash.geom.Rectangle;
    import flash.geom.Point;

    public class CopyChannelProbe extends Sprite {
        public function CopyChannelProbe() {
            var report:Object={appId:NativeApplication.nativeApplication.applicationID,cases:[],roundTrips:[]};
            try {
                var source:BitmapData=new BitmapData(5,5,true,0);
                for(var y:int=0;y<5;++y) for(var x:int=0;x<5;++x)
                    source.setPixel32(x,y,uint(1+x+y*5)<<24);
                report.sourceAlpha=alphaRows(source);
                var values:Array=[0.25,0.5,0.75,-0.25,-0.5,-0.75,
                    1.25,1.5,1.75,2.25,2.5,2.75,-1.25,-1.5,-1.75,-2.25,-2.5,-2.75];
                for each(var value:Number in values) {
                    for each(var axis:String in ["x","y","xy"]) {
                        var vx:Number=axis=="y"?0:value,vy:Number=axis=="x"?0:value;
                        sample(report,source,"source-"+axis,value,new Rectangle(vx,vy,3,3),new Point(2,2));
                        sample(report,source,"dest-"+axis,value,new Rectangle(1,1,3,3),new Point(axis=="y"?2:value,axis=="x"?2:value));
                        sample(report,source,"both-"+axis,value,new Rectangle(vx,vy,3,3),new Point(vx,vy));
                    }
                }
                for each(value in [4.25,4.5,4.75])
                    sample(report,source,"source-right-bottom",value,new Rectangle(value,value,3,3),new Point(2,2));
                for each(value in [13.25,13.5,13.75,-0.25,-0.5,-0.75])
                    roundTrip(report,value);
                roundTrip(report,13.5,4);
                source.dispose(); report.ok=true;
            } catch(error:Error) {report.ok=false;report.error=error.getStackTrace();}
            trace("COPYCHANNEL_RESULT "+JSON.stringify(report));
            NativeApplication.nativeApplication.exit(report.ok?0:1);
        }
        private static function alphaRows(bitmap:BitmapData):Array {
            var rows:Array=[];
            for(var y:int=0;y<bitmap.height;++y) {
                var row:Array=[];
                for(var x:int=0;x<bitmap.width;++x) row.push(bitmap.getPixel32(x,y)>>>24);
                rows.push(row);
            }
            return rows;
        }
        private static function sample(report:Object,source:BitmapData,kind:String,value:Number,rect:Rectangle,point:Point):void {
            var target:BitmapData=new BitmapData(8,8,true,0);
            target.copyChannel(source,rect,point,BitmapDataChannel.ALPHA,BitmapDataChannel.ALPHA);
            var pixels:Array=[];
            for(var y:int=0;y<8;++y) for(var x:int=0;x<8;++x) {
                var a:uint=target.getPixel32(x,y)>>>24;
                if(a) pixels.push({x:x,y:y,alpha:a,sourceX:(a-1)%5,sourceY:int((a-1)/5)});
            }
            report.cases.push({kind:kind,value:value,sourceRect:[rect.x,rect.y,rect.width,rect.height],
                destPoint:[point.x,point.y],nonzero:pixels});
            target.dispose();
        }
        private static function roundTrip(report:Object,value:Number,width:int=8):void {
            var front:BitmapData=new BitmapData(32,32,true,0);
            for(var y:int=0;y<32;++y) for(var x:int=0;x<32;++x)
                front.setPixel32(x,y,uint(1+(x+y*32)%254)<<24);
            var before:BitmapData=front.clone();
            var color:BitmapData=new BitmapData(width,width,false,0);
            // Native Grafon.decal uses origin + width as sourceRect width,
            // while the small opaque color bitmap clips the destination.
            var sourceRect:Rectangle=new Rectangle(value,value,value+width,value+width);
            color.copyChannel(front,sourceRect,new Point(),BitmapDataChannel.ALPHA,BitmapDataChannel.GREEN);
            var saved:Array=[];
            for(y=0;y<width;++y) {var row:Array=[];for(x=0;x<width;++x) row.push((color.getPixel(x,y)>>8)&255);saved.push(row);}
            front.copyChannel(color,new Rectangle(0,0,width,width),new Point(value,value),BitmapDataChannel.GREEN,BitmapDataChannel.ALPHA);
            var changed:Array=[];
            for(y=0;y<32;++y) for(x=0;x<32;++x) {
                var a:uint=front.getPixel32(x,y)>>>24,b:uint=before.getPixel32(x,y)>>>24;
                if(a!=b) changed.push({x:x,y:y,before:b,after:a});
            }
            report.roundTrips.push({origin:value,width:width,sourceRect:[sourceRect.x,sourceRect.y,sourceRect.width,sourceRect.height],
                savedGreen:saved,alphaChanges:changed});
            front.dispose();before.dispose();color.dispose();
        }
    }
}
