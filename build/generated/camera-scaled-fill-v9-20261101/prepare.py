from pathlib import Path
import shutil
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'camera-object-cache-v8-20261101'
TERRAIN=HERE.parent/'camera-local-phase-mask7-platform-camera-20261029'
shutil.copy2(TERRAIN/'LocalPhaseMaskedBitmapFill.as',HERE/'LocalPhaseMaskedBitmapFill.as')
source=(OLD/'ContinuousSceneMotionMod.as').read_text('utf-8')
source=source.replace('import flash.geom.Rectangle;', 'import flash.geom.Rectangle;\n    import flash.display.BitmapData;\n    import flash.geom.Matrix;')
source=source.replace('camera-object-cache-8','camera-scaled-fill-9')
source=source.replace('private static var viewport:ObjectViewportProbe;', 'private static var fill:LocalPhaseMaskedBitmapFill=new LocalPhaseMaskedBitmapFill(7);\n        private static var drawing:String="full";')
source=source.replace('            viewport=new ObjectViewportProbe(g);','')
a=source.index('            for each(var draw:String',source.index('private static function makeSchedule'))
b=source.index('            report.schedule=schedule',a)
source=source[:a]+'''            pixelCheck();
            for each(var axis:String in ["static","x","y","y","x","static"])
                for each(var draw:String in ["full","fill"])
                    schedule.push({fps:120,axis:axis,mode:draw,frames:180});
'''+source[b:]
source=source.replace('            viewport.apply(mode,cam);','''            var api:*=main.getChildByName("ContinuousSceneCarrier")["nativeAPI"];
            if(mode=="fill") {
                if(drawing!="fill")api.scenePresentationEnabledV1(false);
                fill.update(w,true);
            } else if(drawing!="full") {
                fill.clear();api.scenePresentationEnabledV1(true);
            }
            drawing=mode;''')
source=source.replace('if(viewport)viewport.restore();', 'fill.clear();')
source=source.replace('mark.rows=rows;mark.actualFrameRate', '''mark.rows=rows;mark.fill=fill.stats();
                        if(mode=="fill")assertThat("fill-active-"+index,mark.fill.presented && mark.fill.internalErrors==0 && mark.fill.cleanupErrors==0,mark.fill.lastFallback);
                        mark.actualFrameRate''')
needle='        private static function finish(error:String=null):void {'
extras='''        private static function captureWorld():BitmapData {
            var result:BitmapData=new BitmapData(main.stage.stageWidth,main.stage.stageHeight,true,0);
            result.draw(w.visual,w.visual.transform.concatenatedMatrix,null,null,null,true);
            return result;
        }
        private static function compareImages(a:BitmapData,b:BitmapData):Object {
            var changes:*=a.compare(b),record:Object={changed:0,maxRGB:0,maxAlpha:0};
            if(changes is BitmapData) {
                BitmapData(changes).dispose();
                var av:Vector.<uint>=a.getVector(a.rect),bv:Vector.<uint>=b.getVector(b.rect);
                for(var i:int=0;i<av.length;++i)if(av[i]!=bv[i]) {
                    ++record.changed;
                    record.maxRGB=Math.max(record.maxRGB,Math.abs(int(av[i]&255)-int(bv[i]&255)),Math.abs(int((av[i]>>>8)&255)-int((bv[i]>>>8)&255)),Math.abs(int((av[i]>>>16)&255)-int((bv[i]>>>16)&255)));
                    record.maxAlpha=Math.max(record.maxAlpha,Math.abs(int(av[i]>>>24)-int(bv[i]>>>24)));
                }
            }else assertThat("compare-result",changes===0);
            return record;
        }
        private static function pixelCheck():void {
            var api:*=main.getChildByName("ContinuousSceneCarrier")["nativeAPI"];
            api.scenePresentationEnabledV1(false);
            var a:BitmapData=captureWorld();fill.update(w,true);var b:BitmapData=captureWorld();
            report.pixelStatus=fill.stats();fill.clear();var c:BitmapData=captureWorld();
            report.pixels=compareImages(a,b);report.restoredPixels=compareImages(a,c);
            a.dispose();b.dispose();c.dispose();api.scenePresentationEnabledV1(true);
            assertThat("fill-pixels-within-approved-limit",report.pixels.maxRGB<=2 && report.pixels.maxAlpha==0,report.pixels);
            assertThat("fill-restores-exactly",report.restoredPixels.changed==0,report.restoredPixels);
        }
'''
source=source.replace(needle,extras+needle)
(HERE/'ContinuousSceneMotionMod.as').write_text(source,'utf-8')
work=(OLD/'work.py').read_text('utf-8')
(HERE/'work.py').write_text(work,'utf-8')
print('Prepared scaled three-layer presentation test.')
