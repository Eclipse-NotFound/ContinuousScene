"""Accept only proven native tail appends; never select new or resurrect dropped tiles."""
from pathlib import Path
import importlib.util
import shutil
HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-far-terrain-detach-20261027/probe_patch.py'
spec=importlib.util.spec_from_file_location('append_terrain_seed',PATCH_SOURCE)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
ORIGINAL=base.HELPER;HELPER=HERE/'tests/SceneCameraRasterTrial.as';CHANGED=base.CHANGED
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,HERE/'prepare.py',HERE/'append.as.inc')

def helper_source():
    s=ORIGINAL.read_text('utf-8-sig');assert s==base.helper_source()
    old='''            var surfaces:Array=grafon.sceneSurfaces();
            require(surfaces.length==surfaceCount,"Prepared surface set changed");
            var seen:Dictionary=new Dictionary(true);
            for each(var surface:Object in surfaces) {
                require(surfaceSet[surface]===true && !seen[surface],"Prepared surface identity changed");seen[surface]=true;
            }'''
    for before,after in [
        ('camera-far-terrain-detach-1','camera-far-terrain-append-1'),
        ('audits:0,visibilityWrites:0','audits:0,visibilityWrites:0,adoptedSurfaces:0,adoptedBitmaps:0,appendAudits:0'),
        (old,'            adoptNativeAppends();'),
        ('        private function auditRoots():void {',(HERE/'append.as.inc').read_text('utf-8-sig')+'        private function auditRoots():void {'),
        ('No support for append/drop during simulation; all native preparation counters must stay unchanged.',
         'Only validated native tail appends are adopted; selected tiles stay fixed, drops remain unsupported. All native preparation counters must stay unchanged during timing.'),
    ]:
        assert s.count(before)==1,before;s=s.replace(before,after)
    return s

def transform(source):return base.transform(source)

def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert not destination.exists() and not (source/CHANGED[1]).exists()
    shutil.copytree(source,destination)
    main=destination/CHANGED[0];main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/CHANGED[1])
