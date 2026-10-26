"""Fixed full-offset native preparation, then independent exact checks; no retries."""
from pathlib import Path
import importlib.util
import shutil
HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-world-scroll-cached-20261027/probe_patch.py'
spec=importlib.util.spec_from_file_location('world_routewarm_seed',PATCH_SOURCE)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
ORIGINAL=base.HELPER
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
CHANGED=base.CHANGED
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,HERE/'prepare.py',HERE/'warmup.as.inc')

def helper_source():
    s=ORIGINAL.read_text('utf-8-sig');assert s==base.helper_source()
    for old,new in [
        ('camera-world-scroll-cached-1','camera-world-scroll-routewarm-1'),
        ('prepareRoute=views.concat(route);prepareAt=getTimer();',
         'prepareRoute=views.concat(route);\n                for each(var validationPoint:Object in views)for each(var validationOffset:Object in [{x:1,y:0},{x:0,y:1},{x:120,y:120}])prepareRoute.push({x:validationPoint.x+validationOffset.x,y:validationPoint.y+validationOffset.y});\n                prepareAt=getTimer();'),
        ('One fixed native warm-up, then three exact natural camera invariants before alpha tests.','One fixed full-offset native preparation cycle, then three exact independent natural invariants before candidate tests.'),
    ]:
        assert old in s,old;s=s.replace(old,new)
    start=s.index('        private function warmNative(')
    end=s.index('        private var scrollCondition:',start)
    return s[:start]+(HERE/'warmup.as.inc').read_text('utf-8-sig')+s[end:]

def transform(source):return base.transform(source)

def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert not destination.exists() and not (source/CHANGED[1]).exists()
    shutil.copytree(source,destination)
    main=destination/CHANGED[0];main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/CHANGED[1])
