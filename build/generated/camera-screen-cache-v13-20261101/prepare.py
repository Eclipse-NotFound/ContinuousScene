from pathlib import Path
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'camera-screen-cache-v12-20261101'
helper=(OLD/'ScreenTerrainCache.as').read_text('utf-8')
helper=helper.replace(')*64)-128;',')*64)-256;').replace(')*64)+256;',')*64)+512;')
helper=helper.replace('                var dirty:Boolean=false;','''                if(active && -matrix.tx>=left+32 && -matrix.tx+w.cam.screenX<=left+width-32)nextLeft=left;
                if(active && -matrix.ty>=top+32 && -matrix.ty+w.cam.screenY<=top+height-32)nextTop=top;
                var dirty:Boolean=false;''')
helper=helper.replace('                for each(var item:Object in entries) {\n                    if(item.source.alpha', '''                var exposed:Array=[];
                if(dirty || dx || dy)for each(var surface:Object in surfaces) {
                    var bounds:Rectangle=new Rectangle(surface.cx*320*scale,surface.cy*320*scale,320*scale,320*scale);
                    if(!bounds.intersects(new Rectangle(left,top,width,height)))continue;
                    for(var li:int=0;li<4;++li)if(mask & (1<<li)) {
                        var native:Bitmap=surface.bitmaps[li];
                        if(!native.visible){native.visible=true;exposed.push(native);}
                    }
                }
                try {
                for each(var item:Object in entries) {
                    if(item.source.alpha''')
helper=helper.replace('                if(dx || dy)++shifts;','''                } finally {for each(var restored:Bitmap in exposed)restored.visible=false;}
                if(dx || dy)++shifts;''')
helper=helper.replace('        public function clear():void {','''        public function nativeView(enabled:Boolean):void {
            for each(var item:Object in entries){item.source.alpha=enabled?item.alpha:0;item.bitmap.visible=!enabled;}
        }
        public function clear():void {''')
(HERE/'ScreenTerrainCache.as').write_text(helper,'utf-8')
source=(OLD/'ContinuousSceneMotionMod.as').read_text('utf-8')
source=source.replace('camera-screen-cache-12','camera-screen-cache-13')
source=source.replace('private static var drawing:String="full";', 'private static var drawing:String="full",visualChecked:Boolean=false;')
source=source.replace('            pixelCheck();', '''            if(!visualChecked) {
                pixelCheck();visualChecked=true;phase=10;age=0;warmPass=0;warmCount=g.sceneWarmCount;previousAt=getTimer();return;
            }''')
a=source.index('        private static function pixelCheck():void {')
b=source.index('        private static function finish(',a)
source=source[:a]+'''        private static function pixelCheck():void {
            var api:*=main.getChildByName("ContinuousSceneCarrier")["nativeAPI"];
            api.scenePresentationEnabledV1(false);report.pixels=[];
            var savedX:Number=cam.X,savedY:Number=cam.Y;
            for each(var offset:Array in [[0,0],[120,0],[-160,0],[0,96],[0,-96],[340,0],[-340,0],[0,280],[0,-280],[0,0]]) {
                fill.nativeView(true);
                cam.X=centerX+offset[0];cam.Y=centerY+offset[1];cam.calc(player);g.sceneTick();
                var a:BitmapData=captureWorld();fill.nativeView(false);fill.update(w,true);
                var b:BitmapData=captureWorld(),status:Object=fill.stats(),diff:Object=compareImages(a,b);
                report.pixels.push({offset:offset,difference:diff,stats:status});
                a.dispose();b.dispose();
                assertThat("screen-cache-pixels-"+report.pixels.length,status.presented && diff.maxRGB<=2 && diff.maxAlpha==0,diff);
            }
            fill.nativeView(true);a=captureWorld();fill.nativeView(false);fill.clear();b=captureWorld();
            report.restoredPixels=compareImages(a,b);a.dispose();b.dispose();
            assertThat("screen-cache-restores-exactly",report.restoredPixels.changed==0);
            cam.X=savedX;cam.Y=savedY;cam.calc(player);g.sceneTick();api.scenePresentationEnabledV1(true);
        }
'''+source[b:]
(HERE/'ContinuousSceneMotionMod.as').write_text(source,'utf-8')
(HERE/'work.py').write_text((OLD/'work.py').read_text('utf-8'),'utf-8')
print('Prepared hysteresis and expanded-source coverage revision with ten-view pixel gate.')
