"""Same-world checked/unchecked Stage3D draw comparison, with native controls."""
from pathlib import Path
import importlib.util,ast
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-actor-atlas-20261027'
spec=importlib.util.spec_from_file_location('actor_atlas_checks_seed',BASE/'prepare.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
one=base.one
def helper_source():
    s=base.helper_source().replace('camera-actor-atlas-1','camera-actor-atlas-checks-1')
    s=one(s,'[0,1,2,3,3,2,1,0]', '[0,1,2,3,4,5,5,4,3,2,1,0]')
    s=one(s,'getTimer()-beginAt<180000','getTimer()-beginAt<240000')
    s=one(s,'["native-static","native-moving","gpu-static","gpu-moving"][condition]',
      '["native-static","native-moving","gpu-static","gpu-moving","gpu-fast-static","gpu-fast-moving"][condition]')
    s=one(s,'cached:condition>=2,moving:condition%2==1,','checked:condition<4,cached:condition>=2,moving:condition%2==1,')
    s=one(s,'            presenter.update(world,row.cached);','            presenter.setChecks(row.checked);presenter.update(world,row.cached);')
    return s
def renderer_source():
    s=base.renderer_source()
    s=one(s,'private var stage:Stage,plane:Stage3D,', 'private var debugChecks:Boolean=true,checksSwitches:int=0;\n        private var stage:Stage,plane:Stage3D,')
    s=one(s,'        public function update(w:*,enabled:Boolean):void {',
      '''        public function setChecks(value:Boolean):void {
            require(context!=null,"GPU context missing");
            if(debugChecks!==value){context.enableErrorChecking=value;debugChecks=value;++checksSwitches;}
            require(context.enableErrorChecking===value,"GPU debug setting mismatch");
        }
        public function update(w:*,enabled:Boolean):void {''')
    s=one(s,'            verifyActorTiles();render(true,destination);',
      '            setChecks(true);verifyActorTiles();render(true,destination);')
    s=one(s,'            return {active:active,parents:',
      '            return {errorChecking:context?context.enableErrorChecking:null,checksSwitches:checksSwitches,active:active,parents:')
    return s
def runner_source():
    s=base.runner_source().replace('camera-actor-atlas-1','camera-actor-atlas-checks-1')
    s=s.replace("len(trial['windows'])==8 and len(trial['framesMs'])==len(trial['sampleAtMs'])==960", "len(trial['windows'])==12 and len(trial['framesMs'])==len(trial['sampleAtMs'])==1440")
    s=s.replace("modes=('native-static','native-moving','gpu-static','gpu-moving')", "modes=('native-static','native-moving','gpu-static','gpu-moving','gpu-fast-static','gpu-fast-moving')")
    s=s.replace('(0,1,2,3,3,2,1,0)', '(0,1,2,3,4,5,5,4,3,2,1,0)')
    s=one(s,"            assert p['liveAnimation'] and p['clipsStopped']==p['clipsResumed']==0", "            assert p['errorChecking'] is (condition<4)\n            assert p['liveAnimation'] and p['clipsStopped']==p['clipsResumed']==0")
    s=s.replace('((1,3),(6,4))', '((1,3),(10,8),(1,5),(10,6),(3,5),(8,6))')
    s=s.replace('960 native versus live timeline layer-cache intervals', '1440 same-world native/checked/default-async GPU intervals')
    return s
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    (HERE/'tests/SceneCameraRasterTrial.as').write_text(helper_source(),'utf-8')
    (HERE/'SceneTilePresentation.as').write_text(renderer_source(),'utf-8')
    s=runner_source();ast.parse(s);(HERE/'run.py').write_text(s,'utf-8')
    print('Prepared same-world renderer debug-control comparison; no build or launch')
