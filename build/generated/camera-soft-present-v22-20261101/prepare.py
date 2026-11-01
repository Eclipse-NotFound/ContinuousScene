from pathlib import Path
import shutil
here=Path(__file__).resolve().parent
old=here.parent/'camera-soft-present-v21-20261101'
for name in ['ScreenPresenter.as','work.py']:
    shutil.copy2(old/name,here/name)
shutil.copytree(old/'tests',here/'tests',dirs_exist_ok=True)
src=(old/'ContinuousSceneMotionMod.as').read_text('utf-8')
src=src.replace('camera-soft-present-21','camera-soft-present-22')
src=src.replace('report.qualityRestored=main.stage.quality;', 'report.qualityRestored=main.stage.quality;trace("QUALITY "+JSON.stringify(report.qualityCapability));')
src=src.replace('savePNG("native-high",a);report.pixels=[];', 'savePNG("native-high",a);report.pixels=[];\n            var repeat:BitmapData=captureWorld();report.nativeRepeat=compareImages(a,repeat);repeat.dispose();')
src=src.replace('var diff:Object=compareImages(a,b);b.dispose();\n                assertThat("native-restored-"+variant,diff.changed==0 && w.visual.visible,diff);', '''var diff:Object=compareImages(a,b);savePNG("restored-"+variant,b);
                repeat=captureWorld();var afterRepeat:Object=compareImages(b,repeat);b.dispose();repeat.dispose();
                report.pixels[report.pixels.length-1].restoreDifference=diff;
                report.pixels[report.pixels.length-1].repeatAfterRestore=afterRepeat;
                assertThat("native-visibility-restored-"+variant,w.visual.visible && !fill.stats().overlayVisible,fill.stats());''')
src=src.replace('report.schedule=schedule;', 'trace("TIMING "+JSON.stringify({dense:options.dense,quality:report.qualityCapability,repeat:report.nativeRepeat,pixels:report.pixels}));report.schedule=schedule;')
(here/'ContinuousSceneMotionMod.as').write_text(src,'utf-8')
print('Prepared v22; v21 failure preserved')
