"""Null-slot-aware pose prototype, with exact preparation failure context."""
from pathlib import Path
import importlib.util,ast
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-actor-frames-20261027'
spec=importlib.util.spec_from_file_location('actor_frames_checked_seed',BASE/'prepare.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
one=base.one
def helper_source():
    s=base.helper_source().replace('camera-actor-frames-1','camera-actor-frames-checked-1')
    return s.replace('report.errors.push(error.message);','report.errors.push(error.message);report.failureStack=error.getStackTrace();')
def renderer_source():
    s=base.renderer_source()
    s=one(s,'private var clipIds:Dictionary=', 'private var actorNullSlots:int=0,actorNullReads:int=0;private var actorPhase:String="";\n        private var clipIds:Dictionary=')
    s=one(s,'                    actorRoots.push(node);actorItems.push',
      '                    if(node==null)++actorNullSlots;\n                    actorRoots.push(node);actorItems.push')
    s=one(s,'                require(layer.getChildAt(i)===node,"Actor root order changed");',
      '                require(layer.getChildAt(i)===node,"Actor root order changed");\n                actorPhase="group "+group.index+" root "+i;\n                if(node==null){++actorNullReads;continue;}')
    s=one(s,'                var state:Object=actorState(node);','                actorPhase+=" state";var state:Object=actorState(node);')
    s=one(s,'                var rect:Rectangle=actorRect(node);','                actorPhase+=" bounds";var rect:Rectangle=actorRect(node);')
    s=one(s,'                    var bitmap:Bitmap=directBitmap(node);','                    actorPhase+=" bitmap";var bitmap:Bitmap=directBitmap(node);')
    s=one(s,'                        item.poseKey=poseKey(', '                        actorPhase+=" key";item.poseKey=poseKey(')
    s=one(s,'                        var pose:Object=findPose(', '                        actorPhase+=" pool";var pose:Object=findPose(')
    s=one(s,'for each(node in actorRoots){saved.push(node.visible);if(node.visible)',
      'for each(node in actorRoots){saved.push(node==null?false:node.visible);if(node!=null && node.visible)')
    s=one(s,'if(actorRoots[i].visible!==saved[i])', 'if(actorRoots[i]!=null && actorRoots[i].visible!==saved[i])')
    s=one(s,'                poseHits:poseHits,','                actorPhase:actorPhase,actorNullSlots:actorNullSlots,actorNullReads:actorNullReads,\n                poseHits:poseHits,')
    return s
def runner_source():return base.runner_source().replace('camera-actor-frames-1','camera-actor-frames-checked-1')
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    (HERE/'tests/SceneCameraRasterTrial.as').write_text(helper_source(),'utf-8')
    (HERE/'SceneTilePresentation.as').write_text(renderer_source(),'utf-8')
    s=runner_source();ast.parse(s);(HERE/'run.py').write_text(s,'utf-8')
    print('Prepared null-slot guards and failure context; no build or launch')
