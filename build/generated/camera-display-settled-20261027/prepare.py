from pathlib import Path
import importlib.util
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('display_settled_patch',HERE/'probe_patch.py')
patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)
content=patch.helper_source();patch.HELPER.parent.mkdir(parents=True,exist_ok=True)
if patch.HELPER.exists():assert patch.HELPER.read_text('utf-8-sig')==content
else:patch.HELPER.write_text(content,'utf-8')
source=(HERE.parent/'camera-display-state-20261027/run.py').read_text('utf-8-sig')
source=source.replace("VERSION = 'camera-display-state-1'","VERSION = 'camera-display-settled-1'")
needle="    assert trial['nativeRepeat']['equal'] and trial['pixelsValid'] and len(trial['pixels'])==1"
assert source.count(needle)==1;source=source.replace(needle,needle+"\n    assert trial['pixelViewSettleFrames']==3")
target=HERE/'run.py'
if target.exists():assert target.read_text('utf-8-sig')==source
else:target.write_text(source,'utf-8')
print('Prepared three actual frame presentations before unchanged pixel restoration gate')
