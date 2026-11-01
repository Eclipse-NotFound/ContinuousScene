from pathlib import Path
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'camera-scaled-fill-v9-20261101'
helper=(OLD/'LocalPhaseMaskedBitmapFill.as').read_text('utf-8')
helper=helper.replace('private var layerMask:int;', 'public var phaseOverride:Number=NaN;\n        private var layerMask:int;')
helper=helper.replace('var phase:Number=Math.round((scaledGutter-Math.floor(scaledGutter))/observedMatrixScale);','var phase:Number=isNaN(phaseOverride)?Math.round((scaledGutter-Math.floor(scaledGutter))/observedMatrixScale):phaseOverride;')
(HERE/'LocalPhaseMaskedBitmapFill.as').write_text(helper,'utf-8')
source=(OLD/'ContinuousSceneMotionMod.as').read_text('utf-8')
source=source.replace('camera-scaled-fill-9','camera-phase-search-11')
source=source.replace('main.stage.frameRate=120;phase=10;', 'main.stage.frameRate=30;phase=40;')
source=source.replace('                else if(phase==10) {','''                else if(phase==40) {
                    if(++age==15){phaseSearch();finish();return;}
                }
                else if(phase==10) {''')
extra='''        private static function phaseSearch():void {
            var api:*=main.getChildByName("ContinuousSceneCarrier")["nativeAPI"];
            api.scenePresentationEnabledV1(false);
            report.search=[];var a:BitmapData=captureWorld();
            for each(var phaseValue:Number in [-1,0,0.25,0.45,0.5,0.506,0.55,0.75,1,1.5]) {
                fill.clear();fill.phaseOverride=phaseValue;fill.update(w,true);
                var b:BitmapData=captureWorld(),dif:Object=compareImages(a,b);
                report.search.push({phase:phaseValue,difference:dif,presented:fill.stats().presented});b.dispose();
            }
            fill.clear();var c:BitmapData=captureWorld();report.restoredPixels=compareImages(a,c);
            a.dispose();c.dispose();
            assertThat("phase-search-restores-native",report.restoredPixels.changed==0);
        }
'''
source=source.replace('        private static function finish(error:String=null):void {',extra+'        private static function finish(error:String=null):void {')
(HERE/'ContinuousSceneMotionMod.as').write_text(source,'utf-8')
(HERE/'work.py').write_text((OLD/'work.py').read_text('utf-8'),'utf-8')
print('Prepared actual-scale texture-phase investigation; no performance claim.')
