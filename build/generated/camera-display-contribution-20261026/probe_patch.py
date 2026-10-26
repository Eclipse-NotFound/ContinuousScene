"""Only temporary alpha controls for a paused moving-camera attribution."""
from pathlib import Path
import importlib.util
import shutil
import hashlib

HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-terrain-layers-20261025/probe_patch.py'
ORIGINAL=HERE.parent/'camera-terrain-layers-20261025/tests/SceneCameraRasterTrial.as'
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
CHANGED=['ContinuousSceneMotionProbe.as','tests/SceneCameraRasterTrial.as']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
s=importlib.util.spec_from_file_location('display_contribution_terrain_patch',PATCH_SOURCE)
base=importlib.util.module_from_spec(s);s.loader.exec_module(base)
EXTRA_INPUTS=(base.ORIGINAL,base.PATCH_SOURCE,*base.EXTRA_INPUTS)

def helper_source():
    source=ORIGINAL.read_text('utf-8-sig');assert source==base.helper_source()
    edits=[
        ('version:"camera-terrain-layers-1"','version:"camera-display-contribution-1"'),
        ('[grafon.visBack,grafon.visBack2,grafon.visFront,grafon.visVoda]','[grafon.visFon,grafon.visObjs[0],grafon.visObjs[1],grafon.visObjs[2],grafon.visObjs[3],grafon.visObjs[4],grafon.visObjs[5]]'),
        ('require(layer!=null && layer.parent===world.visual,"Terrain parent identity mismatch");','require(layer!=null && layer.parent!=null && isFinite(layer.alpha),"Display parent identity mismatch");'),
        ('terrain.push({target:layer,visible:layer.visible});','terrain.push({target:layer,parent:layer.parent,alpha:layer.alpha});'),
        ('World stays visible; only native terrain parents are temporarily suppressed, all camera windows moving.',
         'Paused attribution only: native scenery backdrop and six object-layer parents use temporary alpha zero; all camera windows moving.'),
        ('["native-moving","back-hidden-moving","front-hidden-moving","terrain-hidden-moving"]',
         '["native-moving","backdrop-zero-moving","objects-zero-moving","backdrop-objects-zero-moving"]'),
        ('if(terrain.length==4)','if(terrain.length==7)'),
        ('item.target.visible=item.visible && !(i<2?(condition&1):(condition&2));',
         'require(item.target.parent===item.parent,"Display parent changed during attribution");\n                item.target.alpha=(i==0?(condition&1):(condition&2))?0:item.alpha;'),
        ('value.push(item.target.visible)','value.push(item.target.alpha)'),
        ('if(value.length!=4)return false;','if(value.length!=7)return false;'),
        ('for(var i:int=0;i<4;++i)if(value[i]!==Boolean(terrain[i].visible && !(i<2?(condition&1):(condition&2))))return false;',
         'for(var i:int=0;i<7;++i)if(value[i]!==Number((i==0?(condition&1):(condition&2))?0:terrain[i].alpha))return false;')]
    value=source
    for before,after in edits:
        assert value.count(before)==1,(before,value.count(before));value=value.replace(before,after,1)
    reverse=value
    for before,after in reversed(edits):reverse=reverse.replace(after,before,1)
    assert reverse==source
    return value

def transform(source):return base.transform(source)

def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert not destination.exists() and not (source/CHANGED[1]).exists()
    shutil.copytree(source,destination)
    main=destination/CHANGED[0];main.write_text(transform(main.read_text('utf-8-sig')),'utf-8',newline='\n')
    shutil.copy2(HELPER,destination/CHANGED[1])
