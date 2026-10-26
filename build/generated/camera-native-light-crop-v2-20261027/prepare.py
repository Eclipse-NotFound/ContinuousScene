"""Use public display-list identity: Grafon's lightBitmap member is internal."""
from pathlib import Path
import ast
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'camera-native-light-crop-20261027'
def save(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():assert path.read_text('utf-8-sig')==text,path
    else:path.write_text(text,'utf-8')
presenter=(OLD/'SceneTilePresentation.as').read_text('utf-8-sig')
before='                target=w.grafon.lightBitmap as Bitmap;parent=w.grafon.visLight;'
after='''                parent=w.grafon.visLight;target=null;
                for(var childIndex:int=0;childIndex<parent.numChildren;++childIndex) {
                    var child:Bitmap=parent.getChildAt(childIndex) as Bitmap;
                    if(child!=null && child.bitmapData===w.grafon.lightBmp) {
                        require(target==null,"Ambiguous native lighting bitmap");target=child;
                    }
                }
                initial={parentVisible:parent.visible,children:parent.numChildren,
                    matched:target!=null,targetVisible:target!=null?target.visible:false};'''
assert presenter.count(before)==1;presenter=presenter.replace(before,after,1)
before='w.grafon.lightBitmap===target'
assert presenter.count(before)==1;presenter=presenter.replace(before,'w.grafon.visLight===parent',1)
save(HERE/'SceneTilePresentation.as',presenter)
patch=(OLD/'probe_patch.py').read_text('utf-8-sig').replace('camera-native-light-crop-1','camera-native-light-crop-2')
before="PRESENTER,HERE/'prepare.py')"
after="PRESENTER,HERE/'prepare.py',HERE.parent/'camera-native-light-crop-20261027/SceneTilePresentation.as',HERE.parent/'camera-native-light-crop-20261027/probe_patch.py',HERE.parent/'camera-native-light-crop-20261027/run.py')"
assert patch.count(before)==1;patch=patch.replace(before,after,1)
ast.parse(patch);save(HERE/'probe_patch.py',patch)
import importlib.util
spec=importlib.util.spec_from_file_location('native_light_public_patch',HERE/'probe_patch.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
save(module.HELPER,module.helper_source())
runner=(OLD/'run.py').read_text('utf-8-sig').replace('camera-native-light-crop-1','camera-native-light-crop-2')
ast.parse(runner);save(HERE/'run.py',runner)
print('Prepared public child/BitmapData identity lookup; crop, restoration and acceptance unchanged.')

