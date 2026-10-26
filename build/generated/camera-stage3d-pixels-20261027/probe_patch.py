"""Preserve Stage3D rendering; export raw GPU and three comparison images on first/failing view."""
from pathlib import Path
import importlib.util
import shutil
HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-stage3d-background-20261027/probe_patch.py'
spec=importlib.util.spec_from_file_location('stage3d_pixel_seed',PATCH_SOURCE)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
ORIGINAL=base.HELPER
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
PRESENTER=HERE/'SceneTilePresentation.as'
CHANGED=base.CHANGED
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,PRESENTER,HERE/'prepare.py')

IMPORTS="""    import flash.display.PNGEncoderOptions;
    import flash.filesystem.File;
    import flash.filesystem.FileMode;
    import flash.filesystem.FileStream;"""

SAVE="""        private function savePixel(name:String,data:BitmapData):void {
            var folder:File=File.applicationStorageDirectory.resolvePath("stage3d-pixels");
            folder.createDirectory();
            var stream:FileStream=new FileStream();
            try {
                stream.open(folder.resolvePath(name+".png"),FileMode.WRITE);
                stream.writeBytes(data.encode(data.rect,new PNGEncoderOptions()));
            } finally {stream.close();}
        }
"""

def renderer_source():
    source=base.PRESENTER.read_text('utf-8-sig')
    edits=[
      ('    import flash.display.Stage;', '    import flash.display.Stage;\n'+IMPORTS),
      ('            destination.draw(stage);','''            if(captures<=13)savePixel("gpu-raw-"+captures,destination);
            destination.draw(stage);'''),
      ('        public function clear():void {',SAVE+'        public function clear():void {')
    ]
    for old,new in edits:
        assert source.count(old)==1;source=source.replace(old,new,1)
    return source

def helper_source():
    source=ORIGINAL.read_text('utf-8-sig');assert source==base.helper_source()
    edits=[
      ('version:"camera-stage3d-background-1"','version:"camera-stage3d-pixels-1"'),
      ('    import flash.display.Stage;', '    import flash.display.Stage;\n'+IMPORTS),
      ('require(result.passed,"GPU background pixels failed");','''if(!result.passed || index==0) {
                    savePixel("native-"+index,a);savePixel("candidate-"+index,b);savePixel("restored-"+index,c);
                    result.savedPixelTriplet=true;
                }
                require(result.passed,"GPU background pixels failed");'''),
      ('        private function capture():BitmapData {',SAVE+'        private function capture():BitmapData {')
    ]
    for old,new in edits:
        assert source.count(old)==1;source=source.replace(old,new,1)
    return source

def transform(source):return base.transform(source)

def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert PRESENTER.read_text('utf-8-sig')==renderer_source()
    assert not destination.exists() and not (source/'tests/SceneCameraRasterTrial.as').exists()
    shutil.copytree(source,destination)
    main=destination/'ContinuousSceneMotionProbe.as'
    main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/'tests/SceneCameraRasterTrial.as')
    shutil.copy2(PRESENTER,destination/'SceneTilePresentation.as')

