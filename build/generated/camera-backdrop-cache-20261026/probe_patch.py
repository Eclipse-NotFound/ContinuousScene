"""Only the scenery cache changes; inherit the prior full pixel/timing guards."""
from pathlib import Path
import hashlib
import importlib.util
import shutil

HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-bitmap-fill-20261025/probe_patch.py'
ORIGINAL=HERE.parent/'camera-bitmap-fill-20261025/tests/SceneCameraRasterTrial.as'
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
PRESENTER=HERE/'SceneTilePresentation.as'
CHANGED=['ContinuousSceneMotionProbe.as','SceneTilePresentation.as','tests/SceneCameraRasterTrial.as']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
assert sha(PATCH_SOURCE)=='7FD2A2AAA60CE2166683A8FDEEEDE7F8B7AC1463CD86519994F42016A3709B9D'
s=importlib.util.spec_from_file_location('backdrop_original_patch',PATCH_SOURCE)
base=importlib.util.module_from_spec(s);s.loader.exec_module(base)
EXTRA_INPUTS=(base.ORIGINAL,base.PATCH_SOURCE,*base.EXTRA_INPUTS,PRESENTER)

def helper_source():
    source=ORIGINAL.read_text('utf-8-sig');assert source==base.helper_source()
    edits=[('version:"camera-bitmap-fill-1"','version:"camera-backdrop-cache-1"'),
      ('Four graphics nodes borrow native BitmapData; no own terrain bitmap or pixel copy.','Only native scenery backdrop caching requested; actual internal allocation is not directly measured.'),
      ('["native-static","native-moving","batched-static","batched-moving"]','["native-static","native-moving","backdrop-static","backdrop-moving"]'),
      ('Actual batch presentation mismatch','Actual backdrop cache mismatch'),
      ('Batch presentation not active','Backdrop cache not active'),
      ('Bitmap fill pixels failed','Backdrop cache pixels failed')]
    out=source
    for old,new in edits:assert out.count(old)==1,old;out=out.replace(old,new,1)
    return out

def transform(source):return base.transform(source)

def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert not destination.exists() and not (source/'tests/SceneCameraRasterTrial.as').exists()
    shutil.copytree(source,destination)
    main=destination/'ContinuousSceneMotionProbe.as';main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/'tests/SceneCameraRasterTrial.as');shutil.copy2(PRESENTER,destination/'SceneTilePresentation.as')

if __name__=='__main__':
    output=helper_source();HELPER.parent.mkdir(parents=True,exist_ok=True)
    if HELPER.exists():assert HELPER.read_text('utf-8-sig')==output
    else:HELPER.write_text(output,'utf-8')
    original_runner=HERE.parent/'camera-bitmap-fill-20261025/run.py'
    assert sha(original_runner)=='66C2EDF8D184B0C6AA5624FB5F55D3A9F366094005D6191C053897A06A1F530F'
    out=original_runner.read_text('utf-8-sig')
    edits=[("VERSION = 'camera-bitmap-fill-1'","VERSION = 'camera-backdrop-cache-1'"),
      ("PINS = dict(reference.PINS)","""PINS = dict(reference.PINS)
RC_RECEIPT=HERE.parents[4]/'mods/RConnect/build/m52/a-live-animation-deploy-01/verified.json'
RC_CURRENT='2C49DFD05D524085EA43FB8FFA537D1A9359FEBD52FB13D6A19FAAE6E2563621'
PINS['mods/Rconnect/release/RConnectMod.swf']=RC_CURRENT
LINEAGE=HERE.parent/'camera-terrain-layers-20261025/lineage.py'
lineage=load('backdrop_registry_lineage',LINEAGE)"""),
      ('def runner_inputs():',"""def runner_inputs():
    assert r.sha(RC_RECEIPT)=='5446D95AAA1552622CF1E691BBDE5C962875897014CF5C06A452A95037ACBC3B'"""),
      ("HERE/'run.py', HERE/'README.md', HERE/'probe_patch.py',","HERE/'run.py', HERE/'README.md', HERE/'probe_patch.py', LINEAGE, RC_RECEIPT,"),
      ('reference.fixture_inputs()','lineage.fixture_inputs(reference)'),
      ("(HERE/'probe_patch.py', patch.HELPER","(HERE/'probe_patch.py', LINEAGE, patch.HELPER"),
      ('seed = reference.seed()','seed = lineage.read_seed(reference)'),
      ("    assert cleanup['presentation']['liveNodes']==cleanup['presentation']['liveNativeRecords']==0\n    assert cleanup['presentation']['nodesCreated']==cleanup['presentation']['nodesRemoved']","    assert cleanup['presentation']['actualCache'] is False"),
      ("('native-static','native-moving','batched-static','batched-moving')","('native-static','native-moving','backdrop-static','backdrop-moving')"),
      ("        assert all(p['liveNodes']==(4 if condition>=2 else 0) and (p['commands']>0 if condition>=2 else p['commands']==0) for p in row['presentation'])","        assert all(p['parents']==(1 if condition>=2 else 0) and p['actualCache'] is (condition>=2) for p in row['presentation'])"),
      ('Four graphics nodes share unchanged native buffers; CPU/GPU attribution and real combat performance are unproven.','Only scenery backdrop native caching requested; CPU/GPU attribution and real combat performance are unproven.'),
      ('camera bitmap fill / 01a13816','camera backdrop cache / 01a13816'),
      ('960 paused native versus bitmap fill frames; diagnostic only, no deployment','960 native versus backdrop cache frames; diagnostic only, no deployment')]
    for old,new in edits:
        assert out.count(old)==(2 if old=='seed = reference.seed()' else 1),(old,out.count(old))
        out=out.replace(old,new)
    target=HERE/'run.py'
    if target.exists():assert target.read_text('utf-8-sig')==out
    else:target.write_text(out,'utf-8')
    print({'helper':sha(HELPER),'runner':sha(target),'presenter':sha(PRESENTER)})
