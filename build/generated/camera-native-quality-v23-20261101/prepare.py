from pathlib import Path
import shutil
here=Path(__file__).resolve().parent
old=here.parent/'camera-soft-present-v22-20261101'
shutil.copy2(old/'ScreenPresenter.as',here/'ScreenPresenter.as')
shutil.copytree(old/'tests',here/'tests',dirs_exist_ok=True)
src=(old/'ContinuousSceneMotionMod.as').read_text('utf-8').replace('camera-soft-present-22','camera-native-quality-23')
src=src.replace('fill.restore();\n            if(done || !cam)return;', '''fill.restore();
            if(done || !cam)return;
            if(phase==20 && mode=="late")main.stage.quality="high";''')
src=src.replace('["full","half","edge","edge","half","full"]','["full","medium","low","late","late","low","medium","full"]')
src=src.replace('fill.update(w,mode);drawing=mode;', '''var wanted:String=mode=="full"?"high":(mode=="late"?"medium":mode);
            if(String(main.stage.quality).toLowerCase()!=wanted)main.stage.quality=wanted;
            drawing=mode;''')
src=src.replace('if(mode!="full")assertThat("candidate-active-"+index,mark.fill.hidden && mark.fill.overlayVisible,mark.fill);', '''mark.quality=main.stage.quality;
                        assertThat("quality-active-"+index,String(mark.quality).toLowerCase()==(mode=="full"?"high":(mode=="late"?"medium":mode)),mark.quality);''')
start=src.index('        private static function pixelCheck():void {')
end=src.index('        private static function finish(',start)
src=src[:start]+'''        private static function pixelCheck():void {
            report.qualityCapability=[];var original:String=main.stage.quality;
            var a:BitmapData=captureWorld();savePNG("native-high",a);report.pixels=[];
            try {
                for each(var quality:String in ["high","medium","low","best","high"]){
                    main.stage.quality=quality;
                    report.qualityCapability.push({requested:quality,readback:main.stage.quality});
                    assertThat("native-quality-supported-"+quality,String(main.stage.quality).toLowerCase()==quality,main.stage.quality);
                    var b:BitmapData=captureWorld();savePNG("native-"+quality,b);
                    report.pixels.push({mode:quality,difference:compareImages(a,b)});b.dispose();
                }
            }finally{main.stage.quality=original;}
            report.qualityRestored=main.stage.quality;trace("QUALITY "+JSON.stringify(report.qualityCapability));
            a.dispose();
        }
''' +src[end:]
src=src.replace('if(done)return;done=true;\n            fill.clear();','if(done)return;done=true;\n            main.stage.quality="high";fill.clear();')
(here/'ContinuousSceneMotionMod.as').write_text(src,'utf-8')
work=(old/'work.py').read_text('utf-8')
work=work.replace("shutil.copy2(candidate,runtime/'pfe.swf')", """shutil.copy2(candidate,runtime/'pfe.swf')
        descriptor=runtime/'application.xml'
        original_descriptor=descriptor.read_text('utf-8-sig')
        assert '<allowLowQuality>' not in original_descriptor
        revised_descriptor=original_descriptor.replace('http://ns.adobe.com/air/application/30.0','http://ns.adobe.com/air/application/51.1')
        assert revised_descriptor!=original_descriptor
        revised_descriptor=revised_descriptor.replace('</initialWindow>','<allowLowQuality>true</allowLowQuality></initialWindow>')
        descriptor.write_text(revised_descriptor,'utf-8')""")
(here/'work.py').write_text(work,'utf-8')
print('Prepared native quality probe and private descriptor only')
