package tests {
    import flash.display.BitmapData;
    import flash.display.PNGEncoderOptions;
    import flash.filesystem.File;
    import flash.filesystem.FileMode;
    import flash.filesystem.FileStream;
    import flash.utils.getTimer;

    /** Synchronous terminal view, after all performance timestamps. */
    public class SceneCombatAtlasPixels {
        public static function run(w:*,presenter:*):Object {
            var result:Object={startedAtMs:getTimer(),passed:false,error:null,created:0,disposed:0,stateRestored:false};
            var images:Array=[],original:Object=state(w),location:*=w.loc,player:*=w.gg,grafon:*=w.grafon;
            try {
                presenter.beginFrame();
                var nativeImage:BitmapData=capture(w,images,result);
                presenter.update(w,true,true);result.presented=presenter.presented;result.presentation=presenter.snapshot();
                var atlasImage:BitmapData=capture(w,images,result);result.atlas=compare(nativeImage,atlasImage);
                presenter.beginFrame();var restored:BitmapData=capture(w,images,result);result.restore=compare(nativeImage,restored);
                result.stateRestored=w.loc===location && w.gg===player && w.grafon===grafon && same(original,state(w));
                result.passed=result.presented && result.atlas.maxRGB<=2 && result.atlas.maxAlpha==0 && result.restore.equal && result.stateRestored;
                if(!result.passed) {
                    result.nativePNG=png("combat-native",nativeImage);result.atlasPNG=png("combat-atlas",atlasImage);result.restoredPNG=png("combat-restored",restored);
                }
            } catch(error:Error) {result.error=error.message;result.passed=false;}
            finally {
                presenter.beginFrame();
                for each(var data:BitmapData in images){data.dispose();++result.disposed;}
                images=[];result.endedAtMs=getTimer();
            }
            return result;
        }
        private static function capture(w:*,owned:Array,result:Object):BitmapData {
            var data:BitmapData=new BitmapData(w.main.stage.stageWidth,w.main.stage.stageHeight,true,0);
            owned.push(data);++result.created;data.draw(w.main.stage);return data;
        }
        private static function compare(a:BitmapData,b:BitmapData):Object {
            var av:Vector.<uint>=a.getVector(a.rect),bv:Vector.<uint>=b.getVector(b.rect);
            var changed:int=0,alpha:int=0,rgb:int=0;
            for(var i:int=0;i<av.length;++i)if(av[i]!=bv[i]) {
                ++changed;var x:uint=av[i],y:uint=bv[i];
                alpha=Math.max(alpha,Math.abs(int(x>>>24)-int(y>>>24)));
                rgb=Math.max(rgb,Math.abs(int(x>>>16&255)-int(y>>>16&255)),Math.abs(int(x>>>8&255)-int(y>>>8&255)),Math.abs(int(x&255)-int(y&255)));
            }
            return {equal:changed==0,differentPixels:changed,maxAlpha:alpha,maxRGB:rgb,pixels:av.length};
        }
        private static function state(w:*):Object {
            return {pause:w.onPause,x:w.gg.X,y:w.gg.Y,dx:w.gg.dx,dy:w.gg.dy,hp:w.gg.hp,
                vx:w.cam.vx,vy:w.cam.vy,scale:w.cam.scaleV,quakeX:w.cam.quakeX,quakeY:w.cam.quakeY,
                sats:w.sats.active,satsVisible:w.grafon.visSats.visible,large:w.grafon.sceneLarge,
                worldX:w.visual.x,worldY:w.visual.y,worldScaleX:w.visual.scaleX,worldScaleY:w.visual.scaleY};
        }
        private static function same(a:Object,b:Object):Boolean {for(var key:String in a)if(a[key]!==b[key])return false;return true;}
        private static function png(name:String,data:BitmapData):String {
            var dir:File=File.applicationStorageDirectory.resolvePath("combat-atlas-diagnostics");dir.createDirectory();
            var file:File=dir.resolvePath(name+".png"),stream:FileStream=new FileStream();
            try {stream.open(file,FileMode.WRITE);stream.writeBytes(data.encode(data.rect,new PNGEncoderOptions()));}
            finally {stream.close();}return file.nativePath;
        }
    }
}

