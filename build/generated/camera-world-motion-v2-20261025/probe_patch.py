"""Preserve v1 failure; add repeated native draw controls and saved pixel evidence."""
from pathlib import Path
import hashlib
import importlib.util
import shutil

HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-world-motion-20261025/probe_patch.py'
ORIGINAL=HERE.parent/'camera-world-motion-20261025/tests/SceneCameraRasterTrial.as'
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
CHANGED=['ContinuousSceneMotionProbe.as','tests/SceneCameraRasterTrial.as']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
assert sha(PATCH_SOURCE)=='1B725CA2993C9F59DCFAA1F8FC5133081B79FB3FF420B8E4A898650B9755A110'
assert sha(ORIGINAL)=='D53D246E272B9FB9AE3065C679A398F5DD82028486D43CBC99F6F1A5BB8D540B'
s=importlib.util.spec_from_file_location('world_motion_v1_patch',PATCH_SOURCE)
base=importlib.util.module_from_spec(s);s.loader.exec_module(base)
EXTRA_INPUTS=(base.ORIGINAL,base.PATCH_SOURCE)

PIXELS='''        private function pixelCase(point:Object,index:int):void {
            var at:int=getTimer(),result:Object={index:index,x:point.x,y:point.y,passed:false};
            report.pixels.push(result);
            try {
                world.visual.visible=true;applyCamera(point.x,point.y);
                require(grafon.sceneViewReady(),"Pixel viewport not prepared");
                var a:BitmapData=capture(),b:BitmapData=capture(),c:BitmapData=capture();
                result.nativeFirst=compare(a,b);result.nativeStable=compare(b,c);
                world.visual.visible=false;var hidden:BitmapData=capture();
                require(world.visual.visible===false,"World hide did not apply");
                result.hidden=compare(c,hidden);
                world.visual.visible=true;var d:BitmapData=capture(),e:BitmapData=capture();
                result.restoreFirst=compare(c,d);result.restore=compare(c,e);
                result.restoreStable=compare(d,e);
                if(index==0) {
                    savePixel(a,"native-first");savePixel(b,"native-second");savePixel(c,"native-third");
                    savePixel(hidden,"hidden");savePixel(d,"restore-first");savePixel(e,"restore-second");
                    result.savedImages=6;
                }
                result.passed=result.nativeStable.equal && result.hidden.differentPixels>100 && result.restore.equal && result.restoreStable.equal;
                require(result.passed,"Repeated native draw or restored draw is not stable");
            } finally {
                world.visual.visible=true;disposeOwned();result.elapsedMs=getTimer()-at;
            }
        }

        private function savePixel(data:BitmapData,name:String):void {
            var stream:FileStream=new FileStream();
            try {
                stream.open(File.applicationStorageDirectory.resolvePath("camera-world-"+name+".png"),FileMode.WRITE);
                stream.writeBytes(data.encode(data.rect,new PNGEncoderOptions()));
            } finally {stream.close();}
        }

'''

def helper_source():
    source=ORIGINAL.read_text('utf-8-sig')
    assert source==base.helper_source()
    start=source.index('        private function pixelCase(')
    end=source.index('        private function capture():BitmapData',start)
    edits=[('version:"camera-world-motion-1"','version:"camera-world-motion-2"'),
           ('    import flash.display.Bitmap;', '    import flash.display.PNGEncoderOptions;\n    import flash.filesystem.File;\n    import flash.filesystem.FileMode;\n    import flash.filesystem.FileStream;\n    import flash.display.Bitmap;'),
           (source[start:end],PIXELS)]
    out=source
    for old,new in edits:
        assert out.count(old)==1;out=out.replace(old,new,1)
    rev=out
    for old,new in reversed(edits):
        assert rev.count(new)==1;rev=rev.replace(new,old,1)
    assert rev==source
    return out

def transform(source):return base.transform(source)

def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert not destination.exists() and not (source/'tests/SceneCameraRasterTrial.as').exists()
    shutil.copytree(source,destination)
    main=destination/'ContinuousSceneMotionProbe.as'
    main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/'tests/SceneCameraRasterTrial.as')

if __name__=='__main__':
    output=helper_source()
    if HELPER.exists():assert HELPER.read_text('utf-8-sig')==output
    else:
        HELPER.parent.mkdir(parents=True,exist_ok=True);HELPER.write_text(output,'utf-8')
    runner=HERE.parent/'camera-world-motion-20261025/run.py'
    assert sha(runner)=='9547615A4EB78576526A0DC5286BE9ACADB86756CF8C5EE91BCAA5DE47CDCACC'
    original=runner.read_text('utf-8-sig')
    edits=[("VERSION = 'camera-world-motion-1'","VERSION = 'camera-world-motion-2'"),
           ('patch.HELPER, patch.ORIGINAL, patch.PATCH_SOURCE)})','patch.HELPER, patch.ORIGINAL, patch.PATCH_SOURCE, *patch.EXTRA_INPUTS)})'),
           ("trial['pixelBitmapsDisposed'] == 15","trial['pixelBitmapsDisposed'] == 30"),
           ("        assert row['passed'] and row['hidden']['differentPixels'] > 100", "        assert row['passed'] and row['hidden']['differentPixels'] > 100\n        assert row['nativeStable']['equal'] and row['restoreStable']['equal']")]
    candidate=original
    for old,new in edits:
        assert candidate.count(old) in (1,2),(old,candidate.count(old));candidate=candidate.replace(old,new)
    out=HERE/'run.py'
    if out.exists():assert out.read_text('utf-8-sig')==candidate
    else:out.write_text(candidate,'utf-8')
    print({'helper':sha(HELPER),'runner':sha(out)})
