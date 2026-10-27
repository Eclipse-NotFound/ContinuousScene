"""Skip observed null descendants in the read-only blend inventory."""
from pathlib import Path
import importlib.util,ast
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-actor-frames-checked-20261027'
spec=importlib.util.spec_from_file_location('actor_frames_scan_seed',BASE/'prepare.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
one=base.one
def helper_source():return base.helper_source().replace('camera-actor-frames-checked-1','camera-actor-frames-scan-1')
def renderer_source():
    s=base.renderer_source()
    s=one(s,'private var actorNullSlots:int=0,actorNullReads:int=0;',
      'private var actorNullSlots:int=0,actorNullReads:int=0,inventoryNullChildren:int=0;')
    s=one(s,'                if(part.blendMode!="normal")',
      '                if(part==null){++inventoryNullChildren;continue;}\n                if(part.blendMode!="normal")')
    s=one(s,'                actorPhase:actorPhase,', '                inventoryNullChildren:inventoryNullChildren,actorPhase:actorPhase,')
    return s
def runner_source():return base.runner_source().replace('camera-actor-frames-checked-1','camera-actor-frames-scan-1')
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    (HERE/'tests/SceneCameraRasterTrial.as').write_text(helper_source(),'utf-8')
    (HERE/'SceneTilePresentation.as').write_text(renderer_source(),'utf-8')
    s=runner_source();ast.parse(s);(HERE/'run.py').write_text(s,'utf-8')
    print('Prepared null-safe read-only blend inventory; no build or launch')
