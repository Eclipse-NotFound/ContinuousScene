"""Generate reviewed diagnostic helper/runner before freezing; never compile or launch."""
from pathlib import Path
import importlib.util
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('gpu_background_patch',HERE/'probe_patch.py')
patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)
helper=patch.helper_source()
patch.HELPER.parent.mkdir(parents=True,exist_ok=True)
if patch.HELPER.exists():assert patch.HELPER.read_text('utf-8-sig')==helper
else:patch.HELPER.write_text(helper,'utf-8')
source=(HERE.parent/'camera-native-light-crop-v2-20261027/run.py').read_text('utf-8-sig')
edits=[
 ('Native globally enlarged darkness bitmap scissor; diagnostic only.','Hardware backdrop and native background textures; terminal diagnostic only.'),
 ("VERSION = 'camera-native-light-crop-2'","VERSION = 'camera-stage3d-background-1'"),
 ("    assert cleanup['presentation']['cropActive'] is False\n    assert cleanup['presentation']['ownBitmapAllocations']==cleanup['presentation']['sourcePixelCopies']==0",
  """    end=cleanup['presentation']
    assert end['texturesCreated']==end['texturesDisposed'] and end['texturesCreated']>0
    assert end['allocated']==end['disposed']==end['copies']==1
    assert end['contextCreates']==end['contextDisposals']==1 and end['gpuBytes']==0
    assert end['ready'] is False and end['error']==''
    assert end['initial']['driverInfo'].lower().find('software')<0
    assert end['captures']==13"""),
 ("row['presentation']['parents']==1","row['presentation']['parents']==3"),
 ("('native-static','native-moving','lightcrop-static','lightcrop-moving')","('native-static','native-moving','gpu-static','gpu-moving')"),
 ("p['parents']==(1 if condition>=2 else 0)","p['parents']==(3 if condition>=2 else 0)"),
 ("p['cropActive'] is (condition>=2)","p['actualCache'] is (condition>=2)"),
 ("        assert row['endAtMs']==previous and row['copiesEnd']==row['copiesStart']==row['allocatedEnd']==row['allocatedStart']==0",
  """        assert row['endAtMs']==previous and row['copiesEnd']==row['copiesStart']==row['allocatedEnd']==row['allocatedStart']==1
        for p in row['presentation']:
            assert p['uploads']==trial['windows'][0]['presentation'][0]['uploads']
            assert p['texturesCreated']==trial['windows'][0]['presentation'][0]['texturesCreated']
            assert p['captures']==13 and p['contextCreates']==1 and p['contextDisposals']==0"""),
 ("camera native light crop / 01a13816","camera Stage3D backgrounds / 01a13816"),
 ("Only the native darkness bitmap display extent is cropped; light data and layers remain unchanged; real combat unproven.","Hardware backgrounds only; native remaining display list, readback composition not OS screenshot acceptance."),
 ("960 native versus light crop camera frames; diagnostic only, no deployment","960 native versus hardware background frames; diagnostic only, no deployment")
]
for old,new in edits:
    count=source.count(old)
    if old in ("p['parents']==(1 if condition>=2 else 0)",):
        assert count==2,(old,count)
    else:assert count==1,(old,count)
    source=source.replace(old,new)
target=HERE/'run.py'
if target.exists():assert target.read_text('utf-8-sig')==source
else:target.write_text(source,'utf-8')
print('Stage3D helper and guarded runner prepared')

