"""Select native zoom 0 only after saving all camera/display state; restore on exit."""
from pathlib import Path
import importlib.util
import shutil
HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-room-axis-baseline-20261027/probe_patch.py'
spec=importlib.util.spec_from_file_location('room_axes_v1_patch',PATCH_SOURCE)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
ORIGINAL=base.HELPER
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
CHANGED=base.CHANGED
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,HERE/'prepare.py')
def helper_source():
    source=ORIGINAL.read_text('utf-8-sig');assert source==base.helper_source()
    edits=[
      ('version:"camera-room-axis-baseline-1"','version:"camera-room-axis-baseline-2"'),
      ('                require(Number(cam.scaleV)==1,"Initial camera must already be scale 1");',
       '''                report.originalZoom=cam.scaleV;
                cam.setZoom(0);
                require(Number(cam.scaleV)==1,"Native unit zoom selection failed");
                report.testZoom=cam.scaleV;''')
    ]
    for old,new in edits:
        assert source.count(old)==1,(old,source.count(old));source=source.replace(old,new,1)
    return source
def transform(source):return base.transform(source)
def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert not destination.exists() and not (source/'tests/SceneCameraRasterTrial.as').exists()
    shutil.copytree(source,destination)
    main=destination/'ContinuousSceneMotionProbe.as'
    main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/'tests/SceneCameraRasterTrial.as')

