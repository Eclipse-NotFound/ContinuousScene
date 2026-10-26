"""Attribution-only unqualified scroll cost; preserve explicit visual rejection."""
from pathlib import Path
import importlib.util
import shutil
HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-world-scroll-routewarm-20261027/probe_patch.py'
spec=importlib.util.spec_from_file_location('world_scroll_cost_seed',PATCH_SOURCE)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
ORIGINAL=base.HELPER
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
CHANGED=base.CHANGED
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,HERE/'prepare.py')

def helper_source():
    s=ORIGINAL.read_text('utf-8-sig');assert s==base.helper_source()
    for old,new in [
        ('camera-world-scroll-routewarm-1','camera-world-scroll-cost-1'),
        ('order:Array=[0,2,2,0]','order:Array=[0,1,1,0]'),
        ('for(var mode:int=2;mode<=2;++mode)','for(var mode:int=1;mode<=1;++mode)'),
        ('pixelsValid','observationsComplete'),
        ('terminalOnly:true,complete:false,passed:false,observationsComplete:false,errors:[],pixels:[],windows:[],',
         'terminalOnly:true,complete:false,passed:false,observationsComplete:false,visualAccepted:true,qualityFailures:[],acceptanceLimitRGB:2,qualityFailureIsMeasuredForAttributionOnly:true,errors:[],pixels:[],windows:[],'),
        ('result:Object={index:index,x:point.x,y:point.y,passed:false,conditions:[]}',
         'result:Object={index:index,x:point.x,y:point.y,observed:false,conditions:[]}'),
        ('result.conditions.push(item);\n                    if(index==0 || !item.restored.equal)',
         'item.accepted=item.changed.maxRGB<=2 && item.changed.maxAlpha==0;\n                    if(!item.accepted){report.visualAccepted=false;report.qualityFailures.push({view:index,condition:mode,changed:item.changed});}\n                    result.conditions.push(item);\n                    if(index==0 || !item.accepted || !item.restored.equal)'),
        ('require(item.changed.maxRGB<=2 && item.changed.maxAlpha==0 && item.restored.equal,"World scrolling changed pixels beyond accepted tolerance or failed exact restore");',
         'require(item.changed.maxAlpha==0 && item.restored.equal,"Attribution requires unchanged alpha and exact native restoration");'),
        ('result.passed=true;','result.observed=true;'),
        ('Original camera calculation plus viewport scroll, without and with native cacheAsBitmap.',
         'ATTRIBUTION ONLY: original camera calculation plus uncached viewport scroll. RGB2 visual rejection is separately retained; timing does not mean candidate acceptance.'),
    ]:
        assert old in s,old;s=s.replace(old,new)
    return s

def transform(source):return base.transform(source)

def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert not destination.exists() and not (source/CHANGED[1]).exists()
    shutil.copytree(source,destination)
    main=destination/CHANGED[0];main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/CHANGED[1])
