"""Test whether an actually presented native pose repairs the stale baseline."""
from pathlib import Path
import importlib.util
import shutil
HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-display-state-20261027/probe_patch.py'
spec=importlib.util.spec_from_file_location('display_settled_seed',PATCH_SOURCE)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
ORIGINAL=base.HELPER
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
CHANGED=base.CHANGED
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,HERE/'prepare.py')

def helper_source():
    source=ORIGINAL.read_text('utf-8-sig');assert source==base.helper_source()
    source=source.replace('version:"camera-display-state-1"','version:"camera-display-settled-1"',1)
    old='''                } else if(phase==1) {
                    pixelCase(views[0],0);'''
    new='''                } else if(phase==1) {
                    // Move to this pose before three actual native frame presentations.
                    // Do not relax the existing exact restoration gate.
                    if(settle<3) {
                        applyCamera(views[0].x,views[0].y);++settle;
                        require(grafon.sceneViewReady(),"Settled pixel view is incomplete");
                        return false;
                    }
                    report.pixelViewSettleFrames=settle;
                    pixelCase(views[0],0);'''
    assert source.count(old)==1;return source.replace(old,new,1)

def transform(source):return base.transform(source)

def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert not destination.exists() and not (source/CHANGED[1]).exists()
    shutil.copytree(source,destination)
    main=destination/CHANGED[0];main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/CHANGED[1])
