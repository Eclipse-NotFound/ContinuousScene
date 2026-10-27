from pathlib import Path
import importlib.util,shutil
HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-room-axis-baseline-v2-20261027/probe_patch.py'
def load(name,p):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
base=load('active_quiet_baseline_patch',PATCH_SOURCE)
generation=load('active_quiet_generation',HERE/'prepare.py')
ORIGINAL=base.HELPER;HELPER=HERE/'tests/SceneCameraRasterTrial.as';CHANGED=base.CHANGED
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,HERE/'prepare.py',HERE/'summary.py',HERE.parent/'camera-far-live-detach-20261027/run.py')
def helper_source():return generation.helper_source()
def one(s,a,b):
    assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
def transform(source):
    s=base.transform(source)
    edits=[
        ('main=host;started=getTimer();var f:FileStream=new FileStream();',
         '''main=host;started=getTimer();var f:FileStream=new FileStream();
            report.nativeWindowInitiallyVisible=main.stage.nativeWindow.visible;
            report.nativeWindowEvents=[];
            main.stage.addEventListener(Event.DEACTIVATE,function(e:Event):void {report.nativeWindowEvents.push({type:e.type,atMs:getTimer(),phase:phase,allStat:w?w.allStat:null});});
            main.stage.addEventListener(Event.ACTIVATE,function(e:Event):void {report.nativeWindowEvents.push({type:e.type,atMs:getTimer(),phase:phase,allStat:w?w.allStat:null});});
            main.stage.nativeWindow.visible=true;'''),
        ('w.mm.active=false;w.newGame(-1,"Scene Motion",{propusk:true});phase=1;',
         'w.mm.mainMenuOff();if(w.mm.active)throw new Error("Native menu shutdown failed");w.newGame(-1,"Scene Motion",{propusk:true});phase=1;'),
        ('                }else if(phase==3) {',
         '''                }else if(phase==3) {
                    if(cfg.drawControl=="tilecrop" && cfg.presentationCheck) {
                        report.quietStartBeforeCombatWarmup=true;
                        report.cameraRaster=cameraRaster.begin(w,tilePresentation);phase=97;return;
                    }'''),
        ('            save("result.json",report);NativeApplication.nativeApplication.exit(report.ok?0:1);',
         '''            main.stage.nativeWindow.visible=report.nativeWindowInitiallyVisible;
            report.nativeWindowRestored=main.stage.nativeWindow.visible===report.nativeWindowInitiallyVisible;
            save("result.json",report);NativeApplication.nativeApplication.exit(report.ok?0:1);''')
    ]
    old=s
    for a,b in edits:s=one(s,a,b)
    check=s
    for a,b in reversed(edits):check=one(check,b,a)
    assert check==old
    return s
def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert (HERE/'run.py').read_text('utf-8-sig')==generation.runner_source()
    assert not destination.exists() and not (source/'tests/SceneCameraRasterTrial.as').exists()
    shutil.copytree(source,destination)
    main=destination/'ContinuousSceneMotionProbe.as';main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/'tests/SceneCameraRasterTrial.as')
