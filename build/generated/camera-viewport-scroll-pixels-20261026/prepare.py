from pathlib import Path
import importlib.util
import ast
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'camera-viewport-scroll-20261026'
def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():assert path.read_bytes()==data,path
    else:path.write_bytes(data)
save(HERE/'SceneTilePresentation.as',(OLD/'SceneTilePresentation.as').read_bytes())
spec=importlib.util.spec_from_file_location('viewport_pixels_patch',HERE/'probe_patch.py')
patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)
save(patch.HELPER,patch.helper_source().encode('utf-8'))
runner=(OLD/'run.py').read_text('utf-8-sig').replace('camera-viewport-scroll-1','camera-viewport-scroll-pixels-1')
ast.parse(runner);save(HERE/'run.py',runner.encode('utf-8'))
print('Prepared unchanged renderer with retained failure images.')

