"""Prepare restoration image evidence; no changed rendering intervention."""
from pathlib import Path
import importlib.util
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('display_pixels_patch',HERE/'probe_patch.py')
patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)
content=patch.helper_source();patch.HELPER.parent.mkdir(parents=True,exist_ok=True)
if patch.HELPER.exists():assert patch.HELPER.read_text('utf-8-sig')==content
else:patch.HELPER.write_text(content,'utf-8')
source=(HERE.parent/'camera-display-contribution-20261026/run.py').read_text('utf-8-sig')
assert source.count("VERSION = 'camera-display-contribution-1'")==1
source=source.replace("VERSION = 'camera-display-contribution-1'","VERSION = 'camera-display-pixels-1'")
needle="    trial,cleanup=raw['cameraRaster'],raw['cameraRasterCleanup']"
assert source.count(needle)==1
source=source.replace(needle,needle+"""
    assert trial['nativeMenuChildren'] and all(row['className']!='visMainMenu' for row in trial['nativeMenuChildren'])""",1)
target=HERE/'run.py'
if target.exists():assert target.read_text('utf-8-sig')==source
else:target.write_text(source,'utf-8')
print('Original alpha controls retained; native entry and image evidence added')

