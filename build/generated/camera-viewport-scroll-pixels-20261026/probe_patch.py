"""Retain the failed renderer exactly; save the pixel triplet for diagnosis."""
from pathlib import Path
import importlib.util
import shutil
HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-viewport-scroll-20261026/probe_patch.py'
spec=importlib.util.spec_from_file_location('viewport_scroll_pixels_seed',PATCH_SOURCE)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
ORIGINAL=base.HELPER
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
PRESENTER=HERE/'SceneTilePresentation.as'
CHANGED=base.CHANGED
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,HERE/'prepare.py',PRESENTER)
def helper_source():
    source=ORIGINAL.read_text('utf-8-sig');assert source==base.helper_source()
    edits=[
      ('version:"camera-viewport-scroll-1"','version:"camera-viewport-scroll-pixels-1"'),
      ('    import flash.display.Stage;','''    import flash.display.Stage;
    import flash.display.PNGEncoderOptions;
    import flash.filesystem.File;
    import flash.filesystem.FileMode;
    import flash.filesystem.FileStream;'''),
      ('require(result.passed,"Viewport scroll pixels failed");','''if(!result.passed || index==0) {
                    savePixel("native-"+index,a);savePixel("candidate-"+index,b);savePixel("restored-"+index,c);
                    result.savedPixelTriplet=true;
                }
                require(result.passed,"Viewport scroll pixels failed");'''),
      ('        private function capture():BitmapData {','''        private function savePixel(name:String,data:BitmapData):void {
            var folder:File=File.applicationStorageDirectory.resolvePath("scroll-pixels");
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
        assert source.count(old)==1,(old,source.count(old));source=source.replace(old,new,1)
    return source
def transform(source):return base.transform(source)
def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert PRESENTER.read_bytes()==base.PRESENTER.read_bytes()
    assert not destination.exists() and not (source/'tests/SceneCameraRasterTrial.as').exists()
    shutil.copytree(source,destination)
    main=destination/'ContinuousSceneMotionProbe.as'
    main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/'tests/SceneCameraRasterTrial.as')
    shutil.copy2(PRESENTER,destination/'SceneTilePresentation.as')

