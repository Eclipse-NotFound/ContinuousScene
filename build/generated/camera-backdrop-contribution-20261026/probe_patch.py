from pathlib import Path
import importlib.util
import shutil
import hashlib

HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-display-contribution-20261026/probe_patch.py'
ORIGINAL=HERE.parent/'camera-display-contribution-20261026/tests/SceneCameraRasterTrial.as'
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
CHANGED=['ContinuousSceneMotionProbe.as','tests/SceneCameraRasterTrial.as']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
s=importlib.util.spec_from_file_location('backdrop_display_patch',PATCH_SOURCE)
base=importlib.util.module_from_spec(s);s.loader.exec_module(base)
EXTRA_INPUTS=(base.ORIGINAL,base.PATCH_SOURCE,*base.EXTRA_INPUTS)

def helper_source():
    source=ORIGINAL.read_text('utf-8-sig');assert source==base.helper_source()
    edits=[
        ('version:"camera-display-contribution-1"','version:"camera-backdrop-contribution-1"'),
        ('private var order:Array=[0,1,2,3,3,2,1,0];','private var order:Array=[0,1,1,0,0,1,1,0];'),
        ('[grafon.visFon,grafon.visObjs[0],grafon.visObjs[1],grafon.visObjs[2],grafon.visObjs[3],grafon.visObjs[4],grafon.visObjs[5]]','[grafon.visFon]'),
        ('if(terrain.length==7)','if(terrain.length==1)'),
        ('for(var mode:int=1;mode<=3;++mode)','for(var mode:int=1;mode<=1;++mode)'),
        ('require(condition>=0 && condition<=3,"Invalid terrain condition");','require(condition>=0 && condition<=1,"Invalid backdrop condition");'),
        ('if(value.length!=7)return false;','if(value.length!=1)return false;'),
        ('for(var i:int=0;i<7;++i)','for(var i:int=0;i<1;++i)'),
        ('["native-moving","backdrop-zero-moving","objects-zero-moving","backdrop-objects-zero-moving"]','["native-moving","backdrop-zero-moving"]'),
        ('Paused attribution only: native scenery backdrop and six object-layer parents use temporary alpha zero; all camera windows moving.',
         'Paused attribution only: native scenery backdrop temporarily uses alpha zero; object layers remain untouched; every window moves the camera.')]
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
