from pathlib import Path
import importlib.util
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('lower_objects_patch',HERE/'probe_patch.py')
patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)
content=patch.helper_source();patch.HELPER.parent.mkdir(parents=True,exist_ok=True)
if patch.HELPER.exists():assert patch.HELPER.read_text('utf-8-sig')==content
else:patch.HELPER.write_text(content,'utf-8')
source=(HERE.parent/'camera-display-pixels-20261027/run.py').read_text('utf-8-sig')
source=source.replace('camera-display-pixels-1','camera-lower-objects-1')
source=source.replace('backdrop-objects-zero-moving','objects01-zero-moving')
source=source.replace('backdrop-zero-moving','objects0-zero-moving').replace('objects-zero-moving','objects1-zero-moving')
source=source.replace("len(trial['terrainInitial'])==7","len(trial['terrainInitial'])==2")
source=source.replace('camera display contribution / 01a13816','camera lower object layers / 01a13816')
target=HERE/'run.py'
if target.exists():assert target.read_text('utf-8-sig')==source
else:target.write_text(source,'utf-8')
print('Prepared independent lower object layer attribution with exact restoration unchanged')
