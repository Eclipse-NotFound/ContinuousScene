from pathlib import Path
import importlib.util
import ast
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'camera-room-axis-baseline-20261027'
def save(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():assert path.read_text('utf-8-sig')==text,path
    else:path.write_text(text,'utf-8')
spec=importlib.util.spec_from_file_location('room_axes_v2_patch',HERE/'probe_patch.py')
patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)
save(patch.HELPER,patch.helper_source())
runner=(OLD/'run.py').read_text('utf-8-sig').replace('camera-room-axis-baseline-1','camera-room-axis-baseline-2')
before="    assert trial['stage']['width']==1280 and trial['stage']['height']==720"
after=before+"\n    assert trial['testZoom']==1 and trial['initial']['camera']['scaleV']==trial['originalZoom']"
assert runner.count(before)==1;runner=runner.replace(before,after,1)
runner=runner.replace("roomAxis=trial['roomAxis'],world=raw['world'],viewport=raw['viewport'],",
    "roomAxis=trial['roomAxis'],originalZoom=trial['originalZoom'],testZoom=trial['testZoom'],world=raw['world'],viewport=raw['viewport'],",1)
ast.parse(runner);save(HERE/'run.py',runner)
print('Prepared native unit zoom selection, with original camera and display restoration retained.')

