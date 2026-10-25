"""Native terrain scroll cache; reversible trial and frozen three-source change."""
from pathlib import Path
import hashlib
import importlib.util
import shutil

HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-world-motion-20261025/probe_patch.py'
ORIGINAL=HERE.parent/'camera-world-motion-20261025/tests/SceneCameraRasterTrial.as'
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
PRESENTER=HERE/'SceneTilePresentation.as'
CHANGED=['ContinuousSceneMotionProbe.as','SceneTilePresentation.as','tests/SceneCameraRasterTrial.as']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
assert sha(PATCH_SOURCE)=='1B725CA2993C9F59DCFAA1F8FC5133081B79FB3FF420B8E4A898650B9755A110'
assert sha(ORIGINAL)=='D53D246E272B9FB9AE3065C679A398F5DD82028486D43CBC99F6F1A5BB8D540B'
s=importlib.util.spec_from_file_location('scroll_original_patch',PATCH_SOURCE)
base=importlib.util.module_from_spec(s);s.loader.exec_module(base)
EXTRA_INPUTS=(base.ORIGINAL,base.PATCH_SOURCE,PRESENTER)

PIXELS='''        private function pixelCase(point:Object,index:int):void {
            var at:int=getTimer(),result:Object={index:index,x:point.x,y:point.y,passed:false};
            report.pixels.push(result);
            try {
                presenter.clear();applyCamera(point.x,point.y);
                require(world.visual.visible===true && grafon.sceneViewReady(),"Native visible prepared world required");
                var a:BitmapData=capture();
                presenter.update(world,true);require(presenter.active,"Scroll cache not requested");
                result.presentation=presenter.snapshot();var b:BitmapData=capture();
                result.candidate=compare(a,b);
                presenter.clear();var c:BitmapData=capture();result.restore=compare(a,c);
                result.passed=result.candidate.maxRGB<=2 && result.candidate.maxAlpha==0 && result.restore.equal;
                require(result.passed,"Terrain cached scrolling pixels failed");
            } finally {presenter.clear();disposeOwned();result.elapsedMs=getTimer()-at;}
        }

'''

def helper_source():
    source=ORIGINAL.read_text('utf-8-sig');assert source==base.helper_source()
    start=source.index('        private function pixelCase(');end=source.index('        private function capture():BitmapData',start)
    edits=[('version:"camera-world-motion-1"','version:"camera-scroll-cache-1"'),
      ('"Visibility control suppresses the whole world; includes display, hit-testing and native display-tree work, not GPU-only attribution.",','"Native terrain parents request bounded cached scrolling; runtime allocation is not directly observed.",'),
      ('["world-visible-static","world-visible-moving","world-hidden-static","world-hidden-moving"]','["native-static","native-moving","cached-static","cached-moving"]'),
      ('hidden:condition>=2,moving:condition%2==1,','cached:condition>=2,moving:condition%2==1,'),
      ('worldVisible:[],windowVisible:[],start:snapshot()', 'worldVisible:[],windowVisible:[],presentation:[],start:snapshot()'),
      ('row.worldVisible.push(pending.worldVisible);row.windowVisible.push(pending.windowVisible);','row.worldVisible.push(pending.worldVisible);row.windowVisible.push(pending.windowVisible);row.presentation.push(pending.presentation);'),
      ('            world.visual.visible=!row.hidden;','            require(world.visual.visible===true,"World visibility changed");\n            presenter.update(world,row.cached);\n            require(presenter.active===row.cached,"Actual cache request mismatch");'),
      ('windowVisible:stage.nativeWindow.visible};','windowVisible:stage.nativeWindow.visible,presentation:presenter.snapshot()};'),
      ('            cleanup.pendingOwnedBitmaps=owned.length;cleanup.elapsedMs=getTimer()-at;','            cleanup.presentation=presenter.snapshot();\n            cleanup.pendingOwnedBitmaps=owned.length;cleanup.elapsedMs=getTimer()-at;'),
      (source[start:end],PIXELS)]
    out=source
    for old,new in edits:assert out.count(old)==1,old;out=out.replace(old,new,1)
    rev=out
    for old,new in reversed(edits):assert rev.count(new)==1;rev=rev.replace(new,old,1)
    assert rev==source and 'world.visual.visible=false' not in out
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
    runner=HERE.parent/'camera-world-motion-20261025/run.py'
    assert sha(runner)=='9547615A4EB78576526A0DC5286BE9ACADB86756CF8C5EE91BCAA5DE47CDCACC'
    out=runner.read_text('utf-8-sig')
    edits=[("VERSION = 'camera-world-motion-1'","VERSION = 'camera-scroll-cache-1'"),
      ('patch.HELPER, patch.ORIGINAL, patch.PATCH_SOURCE)})','patch.HELPER, patch.ORIGINAL, patch.PATCH_SOURCE, *patch.EXTRA_INPUTS)})'),
      ("    assert r.sha(frozen/'tests/SceneCameraRasterTrial.as') == r.sha(patch.HELPER)","    assert r.sha(frozen/'tests/SceneCameraRasterTrial.as') == r.sha(patch.HELPER)\n    assert r.sha(frozen/'SceneTilePresentation.as') == r.sha(patch.PRESENTER)"),
      ("        assert row['passed'] and row['hidden']['differentPixels'] > 100", "        assert row['passed'] and row['candidate']['maxRGB']<=2 and row['candidate']['maxAlpha']==0\n        assert row['presentation']['active'] and row['presentation']['parents']==4"),
      ("('world-visible-static','world-visible-moving','world-hidden-static','world-hidden-moving')", "('native-static','native-moving','cached-static','cached-moving')"),
      ("row['hidden'] is (condition>=2)","row['cached'] is (condition>=2)"),
      ("'workMs','worldVisible','windowVisible')", "'workMs','worldVisible','windowVisible','presentation')"),
      ("assert all(v is (condition<2) for v in row['worldVisible'])", "assert all(v is True for v in row['worldVisible'])"),
      ("        positions = set(zip(row['vx'],row['vy']))", "        assert all(p['active'] is (condition>=2) and p['parents']==(4 if condition>=2 else 0) for p in row['presentation'])\n        positions = set(zip(row['vx'],row['vy']))"),
      ("    assert cleanup == trial['cleanup'] and cleanup['restored'] and not cleanup['errors'] and cleanup['pendingOwnedBitmaps'] == 0", "    assert cleanup == trial['cleanup'] and cleanup['restored'] and not cleanup['errors'] and cleanup['pendingOwnedBitmaps'] == 0\n    assert not cleanup['presentation']['active'] and cleanup['presentation']['parents']==0\n    assert cleanup['presentation']['enables']==cleanup['presentation']['restores']"),
      ("paired.append(dict(hidden=hidden,staticIndex=static,movingIndex=moving,", "paired.append(dict(cached=hidden,staticIndex=static,movingIndex=moving,"),
      ("'Whole-world visibility includes rendering and native display-tree/hit-test work; not GPU-only attribution.'", "'Bounded cached scrolling requested on four native terrain parents; runtime cache allocation not directly measured.'"),
      ('camera world motion / 01a13816','camera scroll cache / 01a13816'),
      ('960 paused camera/world visibility frames; diagnostic only, no deployment','960 paused native versus cached scrolling frames; diagnostic only, no deployment')]
    for old,new in edits:assert out.count(old) in (1,2),(old,out.count(old));out=out.replace(old,new)
    dest=HERE/'run.py'
    if dest.exists():assert dest.read_text('utf-8-sig')==out
    else:dest.write_text(out,'utf-8')
    print({'helper':sha(HELPER),'presenter':sha(PRESENTER),'runner':sha(dest)})
