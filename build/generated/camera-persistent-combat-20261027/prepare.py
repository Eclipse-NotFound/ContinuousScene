from pathlib import Path
import ast,importlib.util
HERE=Path(__file__).resolve().parent;BASE=HERE.parent/'camera-persistent-fullpage-20261027'
COMBAT=HERE.parent/'camera-atlas-merged-combat-20261026'
VERSION='camera-persistent-combat-1'
def load(name,p):
    sp=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
base=load('persistent_combat_generation',BASE/'prepare.py');one=base.one
combat=load('persistent_combat_original_patch',COMBAT/'probe_patch.py')
window=load('persistent_combat_window',HERE.parent/'camera-live-parking-range-20261027/probe_patch.py')

def presenter_source():return base.persistent_source().replace('class ScenePersistentAtlas','class SceneRasterPresentation')
def helper_source():
    return one((COMBAT/'tests/SceneCombatAtlasPixels.as').read_text('utf-8-sig'),'                if(!result.passed) {','                { // Always retain the real terminal combat view.')
def transform(source):
    s=combat.transform_main(source).replace(combat.VERSION,VERSION)
    s=one(s,'absoluteStart=getTimer();rasterPresentation.beginFrame();','absoluteStart=getTimer();')
    s=one(s,'w.mm.active=false;w.newGame(-1,"Scene Motion",{propusk:true});phase=1;',
          'w.mm.mainMenuOff();if(w.mm.active)throw new Error("Native menu shutdown failed");w.newGame(-1,"Scene Motion",{propusk:true});phase=1;')
    # Reuse the tested private-window initialization; no far-object parking.
    a,b=window.EDITS[-2];s=one(s,a,b)
    a,b=window.EDITS[-1];s=one(s,a.replace('==20','==4'),b.replace('==20','==4'))
    s=one(s,'                        report.atlasPoolPreparation={startedAtMs:getTimer(),before:rasterPresentation.snapshot(),memoryBefore:System.totalMemory};',
          '''                        report.nativeCombatView={width:main.stage.stageWidth,height:main.stage.stageHeight,frameRate:main.stage.frameRate,visible:main.stage.nativeWindow.visible,worldVisible:w.visual.visible,menuActive:w.mm.active};
                        for(var menuIndex:int=0;menuIndex<main.numChildren;++menuIndex)if(getQualifiedClassName(main.getChildAt(menuIndex))=="visMainMenu")throw new Error("Native menu display remains");
                        report.atlasPoolPreparation={startedAtMs:getTimer(),before:rasterPresentation.snapshot(),memoryBefore:System.totalMemory};''')
    return s
def runner_source():
    s=base.runner_source().replace(base.VERSION,VERSION)
    s=s.replace('len(after) == 89','len(after) == 86').replace("len(value['frozenSourceSHA256']) == 89","len(value['frozenSourceSHA256']) == 86")
    s=s.replace("'tests/SceneCameraRasterTrial.as'","'tests/SceneCombatAtlasPixels.as'")
    s=one(s,"['--draw-control','tilecrop','--presentation-check']","['--draw-control','atlas']")
    s=one(s,"('--window-width','1936'),('--window-height','1119')","('--window-width','2048'),('--window-height','1123')")
    s=one(s,'arms=summary[\'arms\'],pairs=summary[\'pairs\']',"grouped=summary['grouped'],qualification=summary['qualification']")
    return s
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    for name,s in [('SceneRasterPresentation.as',presenter_source()),('tests/SceneCombatAtlasPixels.as',helper_source()),('run.py',runner_source())]:
        p=HERE/name
        if p.suffix=='.py':ast.parse(s)
        if p.exists():assert p.read_text('utf-8-sig')==s
        else:p.write_text(s,'utf-8')
    print('Prepared native sprint/fire combat ABBA using persistent full-page atlas; no game launch')
