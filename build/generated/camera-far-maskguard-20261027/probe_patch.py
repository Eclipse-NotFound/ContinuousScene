"""Read mask once, guard absent child, identify any remaining incomplete traversal."""
from pathlib import Path
import importlib.util
import shutil
HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-far-singleframe-20261027/probe_patch.py'
spec=importlib.util.spec_from_file_location('far_mask_seed',PATCH_SOURCE)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
ORIGINAL=base.HELPER
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
CHANGED=base.CHANGED
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,HERE/'prepare.py')

def helper_source():
    s=ORIGINAL.read_text('utf-8-sig');assert s==base.helper_source()
    s=s.replace('camera-far-singleframe-1','camera-far-maskguard-1')
    start=s.index('        private function collectMasks(')
    end=s.index('        private function staticReason(',start)
    replacement='''        private function collectMasks(node:DisplayObject,path:String="stage"):void {
            if(node==null){report.maskNullNodes=int(report.maskNullNodes)+1;return;}
            var name:String=getQualifiedClassName(node);
            try {
                var mask:DisplayObject=node.mask;
                if(mask!=null)maskTargets[mask]=true;
                var container:DisplayObjectContainer=node as DisplayObjectContainer;
                if(container!=null)for(var i:int=0;i<container.numChildren;++i)collectMasks(container.getChildAt(i),path+"/"+i);
                report.maskNodes=int(report.maskNodes)+1;
            } catch(error:Error){throw new Error("Mask walk at "+path+" "+name+": "+error.message);}
        }

'''
    return s[:start]+replacement+s[end:]

def transform(source):return base.transform(source)

def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert not destination.exists() and not (source/CHANGED[1]).exists()
    shutil.copytree(source,destination)
    main=destination/CHANGED[0];main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/CHANGED[1])
