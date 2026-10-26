"""Retain the failed alpha control and capture the exact restoration mismatch."""
from pathlib import Path
import importlib.util
import shutil
HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-display-contribution-20261026/probe_patch.py'
spec=importlib.util.spec_from_file_location('display_pixel_seed',PATCH_SOURCE)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
ORIGINAL=base.HELPER
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
CHANGED=base.CHANGED
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,HERE/'prepare.py')

def helper_source():
    source=ORIGINAL.read_text('utf-8-sig');assert source==base.helper_source()
    edits=[
      ('version:"camera-display-contribution-1"','version:"camera-display-pixels-1"'),
      ('    import flash.display.Stage;','''    import flash.display.Stage;
    import flash.display.PNGEncoderOptions;
    import flash.filesystem.File;
    import flash.filesystem.FileMode;
    import flash.filesystem.FileStream;'''),
      ('require(saved.worldVisible===true,"World must start visible");','''require(saved.worldVisible===true,"World must start visible");
                require(w.mm!=null && w.mm.active===false,"Main menu must be inactive");
                report.nativeMenuChildren=[];
                for(var menuChild:int=0;menuChild<w.main.numChildren;++menuChild) {
                    var className:String=getQualifiedClassName(w.main.getChildAt(menuChild));
                    report.nativeMenuChildren.push({className:className,visible:w.main.getChildAt(menuChild).visible});
                    require(className!="visMainMenu","Native mainMenuOff must remove main menu display");
                }'''),
      ('require(item.restored.equal,"Terrain visibility did not restore exact pixels");','''if(index==0 || !item.restored.equal) {
                        savePixel("original-"+index+"-"+mode,original);
                        savePixel("suppressed-"+index+"-"+mode,suppressed);
                        savePixel("restored-"+index+"-"+mode,restored);
                        item.savedPixelTriplet=true;
                    }
                    require(item.restored.equal,"Terrain visibility did not restore exact pixels");'''),
      ('        private function capture():BitmapData {','''        private function savePixel(name:String,data:BitmapData):void {
            var folder:File=File.applicationStorageDirectory.resolvePath("display-pixels");
            folder.createDirectory();
            var stream:FileStream=new FileStream();
            try {
                stream.open(folder.resolvePath(name+".png"),FileMode.WRITE);
                stream.writeBytes(data.encode(data.rect,new PNGEncoderOptions()));
            } finally {stream.close();}
        }
        private function capture():BitmapData {''')
    ]
    for old,new in edits:
        assert source.count(old)==1;source=source.replace(old,new,1)
    return source

def transform(source):
    source=base.transform(source)
    old='w.mm.active=false;w.newGame(-1,"Scene Motion",{propusk:true});phase=1;'
    new='w.mm.mainMenuOff();if(w.mm.active)throw new Error("Native menu shutdown failed");w.newGame(-1,"Scene Motion",{propusk:true});phase=1;'
    assert source.count(old)==1
    return source.replace(old,new,1)

def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert not destination.exists() and not (source/'tests/SceneCameraRasterTrial.as').exists()
    shutil.copytree(source,destination)
    main=destination/'ContinuousSceneMotionProbe.as'
    main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/'tests/SceneCameraRasterTrial.as')

