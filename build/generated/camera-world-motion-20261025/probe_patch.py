"""Exact-source paused camera/world visibility attribution, never a product patch."""
from pathlib import Path
import hashlib
import importlib.util
import shutil

HERE = Path(__file__).resolve().parent
ORIGINAL = HERE.parent / 'camera-raster-20261024/tests/SceneCameraRasterTrial.as'
ORIGINAL_SHA = '88A44A8AAFDC64C1FCF51F453264BD4FDB4CEA546673610A1587D62622DF2B9B'
PATCH_SOURCE = HERE.parent / 'camera-raster-20261024/probe_patch.py'
PATCH_SHA = '527F6F5D8BD801C92DBB86FAB87E0C719DD23F930F9AA3A9BD89B609BD43843B'
HELPER = HERE / 'tests/SceneCameraRasterTrial.as'
CHANGED = ['ContinuousSceneMotionProbe.as', 'tests/SceneCameraRasterTrial.as']
VERSION = 'camera-world-motion-1'

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest().upper()

assert sha(PATCH_SOURCE) == PATCH_SHA
spec = importlib.util.spec_from_file_location('world_motion_original_patch', PATCH_SOURCE)
original_patch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(original_patch)

QUIET = '''                    if(cursor==prepareRoute.length) {
                        var preparationEnd:Object=counters(),quiet:Boolean=true,changes:Object={};
                        for each(var key:String in ["sceneRedraws","sceneDrawMs","sceneResident","sceneEvictions","sceneMisses","sceneWarmCount","sceneWarmSlices","sceneWarmForced"]) {
                            if(key in preparationEnd && key in prepareBaseline) {
                                changes[key]=Number(preparationEnd[key])-Number(prepareBaseline[key]);
                                if(changes[key]!=0)quiet=false;
                            }
                        }
                        ++preparePass;report.preparePasses.push({pass:preparePass,quiet:quiet,delta:changes});
                        cursor=0;
                        if(quiet) {
                            report.prepareMs=getTimer()-prepareAt;report.prepareEnd=snapshot();
                            phase=1;pixelAt=getTimer();
                        } else {
                            require(preparePass<12,"Native route did not settle in 12 complete passes");
                            prepareBaseline=preparationEnd;
                        }
                    }'''

PIXELS = '''        private function pixelCase(point:Object,index:int):void {
            var at:int=getTimer(),result:Object={index:index,x:point.x,y:point.y,passed:false};
            report.pixels.push(result);
            try {
                world.visual.visible=true;applyCamera(point.x,point.y);
                require(grafon.sceneViewReady(),"Pixel viewport not prepared");
                var a:BitmapData=capture();
                world.visual.visible=false;var b:BitmapData=capture();
                require(world.visual.visible===false,"World hide did not apply");
                result.hidden=compare(a,b);
                world.visual.visible=true;var c:BitmapData=capture();
                result.restore=compare(a,c);
                result.passed=result.hidden.differentPixels>100 && result.restore.equal;
                require(result.passed,"World suppression or same-frame restoration failed");
            } finally {
                world.visual.visible=true;disposeOwned();result.elapsedMs=getTimer()-at;
            }
        }

'''


def helper_source():
    assert sha(ORIGINAL) == ORIGINAL_SHA
    source = ORIGINAL.read_text('utf-8-sig')
    start = source.index('        private function pixelCase(')
    end = source.index('        private function capture():BitmapData', start)
    pixel_original = source[start:end]
    edits = [
        ('    import flash.display.Bitmap;', '    import flash.desktop.NativeApplication;\n    import flash.display.Bitmap;'),
        ('        private var retries:int=0;', '        private var retries:int=0;\n        private var preparePass:int=0;\n        private var prepareBaseline:Object;'),
        ('version:"camera-raster-trial-1"', 'version:"camera-world-motion-1"'),
        ('"Scale 1, zero shake, integer world-to-Stage translation only.",',
         '"Scale 1, zero shake, integer world-to-Stage translation only.",\n'
         '                    "Visibility control suppresses the whole world; includes display, hit-testing and native display-tree work, not GPU-only attribution.",\n'
         '                    "This is not an enemy-free gameplay run: simulation is paused, while timelines and other callbacks can continue.",'),
        ('                saved={pause:w.onPause,camera:fields(cam,CAMERA),',
         '                saved={pause:w.onPause,worldVisible:w.visual.visible,nativeWindowVisible:stage.nativeWindow.visible,camera:fields(cam,CAMERA),'),
        ('                saved.ready=true;',
         '                saved.ready=true;\n'
         '                require(/^pfe-modsettings-continuous-motion-[0-9a-f]{32}$/.test(NativeApplication.nativeApplication.applicationID),"Isolated motion application required");\n'
         '                require(saved.worldVisible===true,"World must start visible");\n'
         '                stage.nativeWindow.visible=true;\n'
         '                require(stage.nativeWindow.visible===true,"Owned private window did not become visible");'),
        ('                report.prepareStart=snapshot();',
         '                report.prepareStart=snapshot();\n                prepareBaseline=counters();report.preparePasses=[];'),
        ('''                    if(cursor==prepareRoute.length) {
                        report.prepareMs=getTimer()-prepareAt;report.prepareEnd=snapshot();
                        phase=1;cursor=0;pixelAt=getTimer();
                    }''', QUIET),
        ('                    row.workMs.push(pending.workMs);',
         '                    row.workMs.push(pending.workMs);row.worldVisible.push(pending.worldVisible);row.windowVisible.push(pending.windowVisible);'),
        ('                    var now:int=getTimer();',
         '                    require(world.visual.visible===pending.worldVisible,"World visibility changed during measured interval");\n                    var now:int=getTimer();'),
        ('["native-static","native-moving","tilecrop-static","tilecrop-moving"]',
         '["world-visible-static","world-visible-moving","world-hidden-static","world-hidden-moving"]'),
        ('tilecrop:condition>=2,moving:condition%2==1,', 'hidden:condition>=2,moving:condition%2==1,'),
        ('start:snapshot(),copiesStart:presenter.copies,allocatedStart:presenter.allocated};',
         'worldVisible:[],windowVisible:[],start:snapshot(),copiesStart:presenter.copies,allocatedStart:presenter.allocated};'),
        ('            presenter.update(world,row.tilecrop);',
         '            world.visual.visible=!row.hidden;'),
        ('scene:counters(),workMs:getTimer()-at};',
         'scene:counters(),workMs:getTimer()-at,worldVisible:world.visual.visible,windowVisible:stage.nativeWindow.visible};'),
        ('                // These restoration operations must still run if an earlier check failed.',
         '                try {world.visual.visible=saved.worldVisible;stage.nativeWindow.visible=saved.nativeWindowVisible;}\n'
         '                catch(eVisibility:Error){cleanup.errors.push("visibility: "+eVisibility.message);}\n'
         '                // These restoration operations must still run if an earlier check failed.'),
        ('                    require(samePlayer(playerState(),saved.gg),"Player simulation changed while paused");',
         '                    require(samePlayer(playerState(),saved.gg),"Player simulation changed while paused");\n'
         '                    require(world.visual.visible===saved.worldVisible && stage.nativeWindow.visible===saved.nativeWindowVisible,"World/window visibility restore mismatch");'),
        ('            require(world.onPause===true && world.allStat==1 && world.t_exit==0 && stage.frameRate==120,"Pause/runtime state changed");',
         '            require(world.onPause===true && world.allStat==1 && world.t_exit==0 && stage.frameRate==120,"Pause/runtime state changed");\n'
         '            require(stage.nativeWindow.visible===true,"Owned window visibility changed during diagnosis");'),
        (pixel_original, PIXELS),
    ]
    out = source
    for before, after in edits:
        assert out.count(before) == 1, before
        out = out.replace(before, after, 1)
    restored = out
    for before, after in reversed(edits):
        assert restored.count(after) == 1
        restored = restored.replace(after, before, 1)
    assert restored == source
    assert 'presenter.update(' not in out and 'row.tilecrop' not in out
    return out


def transform(source): return original_patch.transform(source)


def prepare(source, destination):
    assert HELPER.read_text('utf-8-sig') == helper_source()
    assert not destination.exists() and not (source/'tests/SceneCameraRasterTrial.as').exists()
    shutil.copytree(source, destination)
    main = destination/'ContinuousSceneMotionProbe.as'
    main.write_text(transform(main.read_text('utf-8-sig')), 'utf-8')
    shutil.copy2(HELPER, destination/'tests/SceneCameraRasterTrial.as')


if __name__ == '__main__':
    output = helper_source()
    if HELPER.exists():
        assert HELPER.read_text('utf-8-sig') == output, 'Do not rewrite a frozen helper'
    else:
        HELPER.parent.mkdir(parents=True, exist_ok=True)
        HELPER.write_text(output, 'utf-8')
    print(sha(HELPER))
