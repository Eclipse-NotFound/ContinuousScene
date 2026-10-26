"""Stationary-residency attribution after full-route native preparation, not lifecycle support."""
from pathlib import Path
import importlib.util
import shutil
HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-far-maskguard-20261027/probe_patch.py'
spec=importlib.util.spec_from_file_location('far_terrain_seed',PATCH_SOURCE)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
ORIGINAL=base.HELPER
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
CHANGED=base.CHANGED
WARMUP=HERE.parent/'camera-world-scroll-routewarm-20261027/warmup.as.inc'
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,HERE/'prepare.py',HERE/'detach.as.inc',WARMUP)

def helper_source():
    s=ORIGINAL.read_text('utf-8-sig');assert s==base.helper_source()
    for old,new in [
        ('camera-far-maskguard-1','camera-far-terrain-detach-1'),
        ('far-static-hidden-moving','far-terrain-detached-moving'),
        ('[grafon.visObjs[0],grafon.visObjs[1],grafon.visObjs[2],grafon.visObjs[3],grafon.visObjs[4],grafon.visObjs[5]]','[grafon.visFront,grafon.visBack,grafon.visBack2,grafon.visVoda]'),
        ('prepareRoute=views.concat(route);prepareAt=getTimer();',
         'prepareRoute=views.concat(route);\n                for each(var validationPoint:Object in views)for each(var validationOffset:Object in [{x:1,y:0},{x:0,y:1},{x:120,y:120}])prepareRoute.push({x:validationPoint.x+validationOffset.x,y:validationPoint.y+validationOffset.y});\n                prepareAt=getTimer();'),
        ('if(index==0 || !item.restored.equal)', 'if(index==0 || !item.changed.equal || !item.restored.equal)'),
        ('Offscreen root culling changed pixels','Detached invisible terrain changed pixels'),
        ('Paused attribution only: Only qualified static direct roots outside the whole route plus 320px are hidden. No wrappers or per-frame full tree scans. End/switch audits do not prove every intermediate callback state. One fixed native warm-up, then three exact natural camera invariants before alpha tests. Cold screenshot behavior remains separately recorded.',
         'Paused attribution only: Existing native invisible Bitmap tiles outside the full prepared route plus 320px are detached, with no visibility or data writes. Original order is restored. Fixed full-offset native preparation and independent exact invariants. No support for append/drop during simulation; all native preparation counters must stay unchanged.'),
    ]:
        assert old in s,old;s=s.replace(old,new)
    start=s.index('        private function warmNative(');end=s.index('        private var routeBounds:',start)
    s=s[:start]+WARMUP.read_text('utf-8-sig')+s[end:]
    start=s.index('        private function staticReason(');end=s.index('        private function layerState(',start)
    s=s[:start]+(HERE/'detach.as.inc').read_text('utf-8-sig')+s[end:]
    return s

def transform(source):return base.transform(source)

def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert not destination.exists() and not (source/CHANGED[1]).exists()
    shutil.copytree(source,destination)
    main=destination/CHANGED[0];main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/CHANGED[1])
