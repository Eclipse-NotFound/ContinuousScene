from pathlib import Path
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'camera-object-cache-v8-20261101'
PIXEL=HERE.parent/'camera-scaled-fill-v9-20261101'
source=(OLD/'ContinuousSceneMotionMod.as').read_text('utf-8')
source=source.replace('import flash.geom.Rectangle;', 'import flash.geom.Rectangle;\n    import flash.display.BitmapData;')
source=source.replace('camera-object-cache-8','camera-terrain-cache-10')
source=source.replace('private static var viewport:ObjectViewportProbe;','private static var cacheNodes:Array=[];')
source=source.replace('            viewport=new ObjectViewportProbe(g);','')
a=source.index('            for each(var draw:String',source.index('private static function makeSchedule'))
b=source.index('            report.schedule=schedule',a)
source=source[:a]+'''            for(var ni:int=0;ni<layers.length;++ni) {
                var node:DisplayObject=layers[ni].getChildByName("ContinuousSceneEventBitmapFill"+ni);
                assertThat("formal-presenter-node-"+ni,node!=null && !node.cacheAsBitmap);
                cacheNodes.push(node);
            }
            pixelCheck();
            for each(var axis:String in ["static","x","y","y","x","static"])
                for each(var draw:String in ["full","terrainCache"])
                    schedule.push({fps:120,axis:axis,mode:draw,frames:180});
'''+source[b:]
source=source.replace('            viewport.apply(mode,cam);','            applyCache(mode=="terrainCache");')
source=source.replace('if(viewport)viewport.restore();','applyCache(false);')
source=source.replace('mark.rows=rows;mark.actualFrameRate','''mark.rows=rows;
                        for(var ni:int=0;ni<cacheNodes.length;++ni)assertThat("cache-owner-"+index+"-"+ni,cacheNodes[ni].parent===layers[ni] && cacheNodes[ni].cacheAsBitmap===(mode=="terrainCache"));
                        mark.actualFrameRate''')
pixel=(PIXEL/'ContinuousSceneMotionMod.as').read_text('utf-8')
a=pixel.index('        private static function captureWorld()')
b=pixel.index('        private static function pixelCheck()',a)
extra=pixel[a:b]+'''        private static function applyCache(enabled:Boolean):void {
            for each(var node:DisplayObject in cacheNodes)if(node.cacheAsBitmap!=enabled)node.cacheAsBitmap=enabled;
        }
        private static function pixelCheck():void {
            var a:BitmapData=captureWorld();applyCache(true);var b:BitmapData=captureWorld();
            applyCache(false);var c:BitmapData=captureWorld();
            report.pixels=compareImages(a,b);report.restoredPixels=compareImages(a,c);
            a.dispose();b.dispose();c.dispose();
            assertThat("cached-terrain-pixels-within-approved-limit",report.pixels.maxRGB<=2 && report.pixels.maxAlpha==0,report.pixels);
            assertThat("cached-terrain-restores-exactly",report.restoredPixels.changed==0,report.restoredPixels);
        }
'''
source=source.replace('        private static function finish(error:String=null):void {',extra+'        private static function finish(error:String=null):void {')
(HERE/'ContinuousSceneMotionMod.as').write_text(source,'utf-8')
(HERE/'work.py').write_text((OLD/'work.py').read_text('utf-8'),'utf-8')
print('Prepared bounded existing terrain-presentation cache experiment.')
