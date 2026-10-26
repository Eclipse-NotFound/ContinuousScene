"""Prepare image retention diagnostic only, no build/run/deployment."""
from pathlib import Path
import importlib.util
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('gpu_pixels_patch',HERE/'probe_patch.py')
patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)
for path,content in ((patch.HELPER,patch.helper_source()),(patch.PRESENTER,patch.renderer_source())):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():assert path.read_text('utf-8-sig')==content
    else:path.write_text(content,'utf-8')
source=(HERE.parent/'camera-stage3d-background-20261027/run.py').read_text('utf-8-sig')
source=source.replace("VERSION = 'camera-stage3d-background-1'","VERSION = 'camera-stage3d-pixels-1'")
target=HERE/'run.py'
if target.exists():assert target.read_text('utf-8-sig')==source
else:target.write_text(source,'utf-8')
print('Image retention diagnostic prepared; drawing commands unchanged')

