"""A distinct no-copy terrain representation, based on the verified paused motion fixture."""
from pathlib import Path
import hashlib
import importlib.util
import shutil

HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-scroll-cache-20261025/probe_patch.py'
ORIGINAL=HERE.parent/'camera-scroll-cache-20261025/tests/SceneCameraRasterTrial.as'
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
PRESENTER=HERE/'SceneTilePresentation.as'
CHANGED=['ContinuousSceneMotionProbe.as','SceneTilePresentation.as','tests/SceneCameraRasterTrial.as']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
assert sha(PATCH_SOURCE)=='F1BDE100545F819F0228EF961440D216C7F0C880A987505CDD6F01ACB74A9C54'
assert sha(ORIGINAL)=='FA584695D5A1AEF3202F0A7580301F8B1854E903AC868CAEE71FF34E59D6DFED'
s=importlib.util.spec_from_file_location('batch_original_patch',PATCH_SOURCE)
base=importlib.util.module_from_spec(s);s.loader.exec_module(base)
EXTRA_INPUTS=(base.ORIGINAL,base.PATCH_SOURCE,*base.EXTRA_INPUTS,PRESENTER)

def helper_source():
    source=ORIGINAL.read_text('utf-8-sig');assert source==base.helper_source()
    edits=[('version:"camera-scroll-cache-1"','version:"camera-bitmap-fill-1"'),
      ('"Native terrain parents request bounded cached scrolling; runtime allocation is not directly observed.",','"Four graphics nodes borrow native BitmapData; no own terrain bitmap or pixel copy.",'),
      ('["native-static","native-moving","cached-static","cached-moving"]','["native-static","native-moving","batched-static","batched-moving"]'),
      ('Actual cache request mismatch','Actual batch presentation mismatch'),('Scroll cache not requested','Batch presentation not active'),
      ('Terrain cached scrolling pixels failed','Bitmap fill pixels failed')]
    out=source
    for old,new in edits:assert out.count(old)==1,old;out=out.replace(old,new,1)
    rev=out
    for old,new in reversed(edits):assert rev.count(new)==1;rev=rev.replace(new,old,1)
    assert rev==source
    return out

def transform(source):return base.transform(source)

def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert not destination.exists() and not (source/'tests/SceneCameraRasterTrial.as').exists()
    shutil.copytree(source,destination)
    main=destination/'ContinuousSceneMotionProbe.as';main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/'tests/SceneCameraRasterTrial.as');shutil.copy2(PRESENTER,destination/'SceneTilePresentation.as')

if __name__=='__main__':
    output=helper_source()
    if HELPER.exists():assert HELPER.read_text('utf-8-sig')==output
    else:HELPER.parent.mkdir(parents=True,exist_ok=True);HELPER.write_text(output,'utf-8')
    runner=HERE.parent/'camera-scroll-cache-20261025/run.py'
    assert sha(runner)=='A176F3623D25457583F6FC4D1BAA339E36FA0F6A9C4C3A448E47531B8C5F209E'
    out=runner.read_text('utf-8-sig')
    edits=[("VERSION = 'camera-scroll-cache-1'","VERSION = 'camera-bitmap-fill-1'"),
      ("('native-static','native-moving','cached-static','cached-moving')","('native-static','native-moving','batched-static','batched-moving')"),
      ("    assert cleanup['presentation']['enables']==cleanup['presentation']['restores']", "    assert cleanup['presentation']['enables']==cleanup['presentation']['restores']\n    assert cleanup['presentation']['liveNodes']==cleanup['presentation']['liveNativeRecords']==0\n    assert cleanup['presentation']['nodesCreated']==cleanup['presentation']['nodesRemoved']\n    assert cleanup['presentation']['ownBitmapAllocations']==cleanup['presentation']['sourcePixelCopies']==0"),
      ("        positions = set(zip(row['vx'],row['vy']))", "        assert all(p['liveNodes']==(4 if condition>=2 else 0) and (p['commands']>0 if condition>=2 else p['commands']==0) for p in row['presentation'])\n        positions = set(zip(row['vx'],row['vy']))"),
      ("'Bounded cached scrolling requested on four native terrain parents; runtime cache allocation not directly measured.'", "'Four graphics nodes share unchanged native buffers; CPU/GPU attribution and real combat performance are unproven.'"),
      ('camera scroll cache / 01a13816','camera bitmap fill / 01a13816'),
      ('960 paused native versus cached scrolling frames; diagnostic only, no deployment','960 paused native versus bitmap fill frames; diagnostic only, no deployment')]
    for old,new in edits:assert out.count(old)==1,(old,out.count(old));out=out.replace(old,new,1)
    dest=HERE/'run.py'
    if dest.exists():assert dest.read_text('utf-8-sig')==out
    else:dest.write_text(out,'utf-8')
    print({'helper':sha(HELPER),'presenter':sha(PRESENTER),'runner':sha(dest)})
