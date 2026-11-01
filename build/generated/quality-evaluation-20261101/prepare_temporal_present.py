"""Diagnostic temporal reprojection, with all simulation steps retained."""
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
source = BASE / 'combat-cost-visible-v27-20261101'
target = BASE / 'camera-temporal-present-v28-20261101'
target.mkdir()
shutil.copy2(source/'work.py', target/'work.py')
shutil.copytree(source/'tests', target/'tests')
shutil.copy2(HERE/'TemporalScreenPresenter.as', target/'ScreenPresenter.as')
code = (source/'ContinuousSceneMotionMod.as').read_text('utf-8')
def replace(old,new):
    global code
    assert code.count(old)==1, old
    code=code.replace(old,new)
replace('version:"combat-cost-visible-27"','version:"camera-temporal-present-28"')
replace('FrameCostProbe.prepare();report.allocationDiagnostic=true;', 'report.temporalPresentationDiagnostic=true;')
replace('FrameCostProbe.observe({sequence:sampleSequence++,mode:route,condition:mode,layerCondition:"real-six-enemy-fire",stageBandMs:now-preAt});','')
replace('report.frameCost=FrameCostProbe.finish();','')
begin=code.index('        private static function makeSchedule():void {')
end=code.index('        private static function enterBlock():void {',begin)
code=code[:begin]+'''        private static function makeSchedule():void {
            if(!visualChecked){pixelCheck();visualChecked=true;phase=10;age=0;warmPass=0;warmCount=g.sceneWarmCount;previousAt=getTimer();return;}
            for each(var axis:String in ["static","x","y"])
                for each(var draw:String in ["full","half2","half3","half3","half2","full"])
                    schedule.push({fps:120,axis:axis,mode:draw,frames:180});
            report.schedule=schedule;index=0;enterBlock();
        }
'''+code[end:]
begin=code.index('        private static function drawPolicy():void {')
end=code.index('        private static function after(e:Event):void {',begin)
code=code[:begin]+'''        private static function drawPolicy():void {
            fill.update(w,mode);drawing=mode;
        }
'''+code[end:]
replace('assertThat("quality-active-"+index,String(mark.quality).toLowerCase()==(mode=="full"?"high":(mode=="late"?"medium":mode)),mark.quality);',
'''assertThat("presentation-active-"+index,mode=="full"?!mark.fill.hidden:mark.fill.hidden && mark.fill.overlayVisible,mark.fill);
                        if(mode!="full")assertThat("bounded-image-age-"+index,mark.fill.maximumAge<=2,mark.fill);''')
begin=code.index('        private static function pixelCheck():void {')
end=code.index('        private static function finish(error:String=null):void {',begin)
code=code[:begin]+'''        private static function pixelCheck():void {
            var a:BitmapData=captureWorld();savePNG("native-high",a);report.pixels=[];
            for each(var wanted:String in ["half2","half3"]){
                fill.update(w,wanted);
                var b:BitmapData=fill.capturePresented();savePNG(wanted,b);b.dispose();
                fill.restore();
                var c:BitmapData=captureWorld();savePNG("restored-"+wanted,c);
                var difference:Object=compareImages(a,c);c.dispose();
                report.pixels.push({mode:wanted,restore:difference,presenter:fill.stats()});
                assertThat("source-restored-"+wanted,w.visual.visible && !fill.stats().overlayVisible,fill.stats());
            }
            fill.clear();a.dispose();
        }
'''+code[end:]
(target/'ContinuousSceneMotionMod.as').write_text(code,'utf-8')
print(target)
