"""Read-only display metadata around the unchanged alpha restoration check."""
from pathlib import Path
import importlib.util
import shutil

HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-display-pixels-20261027/probe_patch.py'
spec=importlib.util.spec_from_file_location('display_state_seed',PATCH_SOURCE)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
ORIGINAL=base.HELPER
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
CHANGED=base.CHANGED
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,HERE/'prepare.py',HERE/'display-state.as.inc')

def helper_source():
    source=ORIGINAL.read_text('utf-8-sig');assert source==base.helper_source()
    edits=[
      ('version:"camera-display-pixels-1"','version:"camera-display-state-1"'),
      ('measurementFrames:960','measurementFrames:0'),
      ('    import flash.display.Stage;','    import flash.display.Stage;\n    import flash.display.DisplayObjectContainer;\n    import flash.display.MovieClip;\n    import flash.text.TextField;\n    import flash.utils.Dictionary;'),
      ('        private var closed:Boolean=false;','        private var closed:Boolean=false;\n        private var nodeIds:Dictionary=new Dictionary(true);\n        private var nodeSequence:int=0;'),
      ('                var original:BitmapData=capture();','''                report.nodeSnapshots=[];
                inspectNodes("before-native");
                var original:BitmapData=capture();
                inspectNodes("after-native");
                var repeated:BitmapData=capture();
                report.nativeRepeat=compare(original,repeated);
                inspectNodes("after-native-repeat");
                savePixel("native-repeat-"+index,repeated);
                savePixel("native-original-"+index,original);
                require(report.nativeRepeat.equal,"Unchanged native capture is not stable");'''),
      ('                    applyLayers(mode);var suppressed:BitmapData=capture();','''                    applyLayers(mode);inspectNodes("suppressed-before-"+mode);
                    var suppressed:BitmapData=capture();inspectNodes("suppressed-after-"+mode);'''),
      ('                    applyLayers(0);var restored:BitmapData=capture();','''                    applyLayers(0);inspectNodes("restored-before-"+mode);
                    var restored:BitmapData=capture();inspectNodes("restored-after-"+mode);'''),
      ('''                    pixelCase(views[cursor],cursor);++cursor;
                    if(cursor==views.length) {
                        report.pixelMs=getTimer()-pixelAt;
                        report.pixelsValid=true;
                        presenter.clear();applyCamera(views[0].x,views[0].y);
                        phase=2;settle=0;
                    }''','''                    pixelCase(views[0],0);
                    report.pixelMs=getTimer()-pixelAt;report.pixelsValid=true;
                    report.complete=true;report.passed=true;clear(w);'''),
      ('        private function savePixel(name:String,data:BitmapData):void {',
       (HERE/'display-state.as.inc').read_text('utf-8-sig')+'\n        private function savePixel(name:String,data:BitmapData):void {')]
    for old,new in edits:
        assert source.count(old)==1,old;source=source.replace(old,new,1)
    return source

def transform(source):return base.transform(source)

def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert not destination.exists() and not (source/CHANGED[1]).exists()
    shutil.copytree(source,destination)
    main=destination/CHANGED[0];main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/CHANGED[1])
