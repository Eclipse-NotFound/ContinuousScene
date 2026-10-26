"""Observe real frame progression for eight intervals, then stop actual moving clips."""
from pathlib import Path
import importlib.util
import ast
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-stage3d-wholeworld-nullslots-20261027'
spec=importlib.util.spec_from_file_location('wholeworld_observed_base',BASE/'prepare.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
one=base.one
def helper_source():
    s=base.helper_source().replace('camera-stage3d-wholeworld-nullslots-1','camera-stage3d-wholeworld-observed-1')
    s=one(s,'''presenter.freezeTimelines(world);presenter.prepareWorld(world,captureBounds);report.frozenPicture=presenter.snapshot();
                            phase=1;pixelAt=getTimer();''','''presenter.observeTimelines(world);phase=4;settle=0;''')
    s=one(s,'} else if(phase==1) {','''} else if(phase==4) {
                    presenter.observeStep();
                    if(++settle==8) {
                        presenter.freezeTimelines(world);presenter.prepareWorld(world,captureBounds);
                        report.frozenPicture=presenter.snapshot();phase=1;pixelAt=getTimer();
                    }
                } else if(phase==1) {''')
    return s
def renderer_source():
    s=base.renderer_source()
    s=one(s,'private var emptySlots:Array=[],walkedNodes:int=0;', '''private var emptySlots:Array=[],walkedNodes:int=0;
        private var observations:Dictionary=new Dictionary(),observationSteps:int=0,implicitStopped:int=0;
        private var observationReport:Array=[];''')
    marker='        public function freezeTimelines(w:*):void {'
    s=one(s,marker,'''        public function observeTimelines(w:*):void {
            require(w===world && world.onPause && !timelinesFrozen,"Paused observation required");
            var seen:Dictionary=new Dictionary(),stack:Array=[root,backdrop];
            while(stack.length) {
                var node:DisplayObject=stack.pop() as DisplayObject;if(node==null || seen[node])continue;seen[node]=true;
                var mc:MovieClip=node as MovieClip;
                if(mc && mc.totalFrames>1)observations[mc]={first:mc.currentFrame,last:mc.currentFrame,total:mc.totalFrames,
                    moved:false,changes:0,reportedPlaying:mc.isPlaying};
                var container:DisplayObjectContainer=node as DisplayObjectContainer;
                if(container)for(var i:int=0;i<container.numChildren;++i) {
                    var child:DisplayObject=container.getChildAt(i);if(child!=null)stack.push(child);
                }
            }
        }
        public function observeStep():void {
            require(!timelinesFrozen && observationSteps<8,"Fixed eight-interval observation only");
            for(var key:Object in observations) {
                var mc:MovieClip=key as MovieClip,item:Object=observations[key];
                require(mc.totalFrames==item.total,"Timeline shape changed during observation");
                if(mc.currentFrame!=item.last){item.moved=true;++item.changes;}
                item.last=mc.currentFrame;item.reportedPlaying=item.reportedPlaying||mc.isPlaying;
            }
            ++observationSteps;
        }
'''+marker)
    s=one(s,'timelinesFrozen=true;', 'require(observationSteps==8,"Eight observation intervals required");timelinesFrozen=true;')
    s=one(s,'clips.push(item);if(item.playing){mc.stop();++clipsStopped;}', '''var observed:Object=observations[mc];
                    item.implicit=observed!=null && observed.moved && !item.playing;
                    item.resume=item.playing || item.implicit;
                    clips.push(item);
                    if(item.resume){mc.stop();++clipsStopped;}
                    if(item.implicit){++implicitStopped;observationReport.push({path:visit.path,first:observed.first,last:observed.last,changes:observed.changes,reportedPlaying:observed.reportedPlaying});}''')
    s=one(s,'if(item.clip.currentFrame!=item.frame || item.clip.totalFrames!=item.total || item.clip.isPlaying)restoreErrors.push("Timeline state changed");',
        'var untouched:Boolean=item.clip.currentFrame==item.frame && item.clip.totalFrames==item.total && !item.clip.isPlaying;\n                if(!untouched)restoreErrors.push("Timeline state changed");')
    s=one(s,'if(item.playing){item.clip.play();++clipsResumed;}','if(item.resume && untouched){item.clip.play();++clipsResumed;}')
    s=one(s,'if(item.clip.isPlaying!==item.playing)restoreErrors.push("Timeline play state restore failed");',
        'if(item.clip.isPlaying!==item.resume)restoreErrors.push("Timeline play state restore failed");')
    s=one(s,'emptySlots:emptySlots,walkedNodes:walkedNodes};', '''emptySlots:emptySlots,walkedNodes:walkedNodes,
                observationSteps:observationSteps,implicitStopped:implicitStopped,observedImplicit:observationReport,
                playbackRestoreLimit:"Observed implicit movers resume with play; public isPlaying may become true. Terminal diagnostic only."};''')
    return s
def runner_source():return base.runner_source().replace('camera-stage3d-wholeworld-nullslots-1','camera-stage3d-wholeworld-observed-1')
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    (HERE/'tests/SceneCameraRasterTrial.as').write_text(helper_source(),'utf-8')
    (HERE/'SceneTilePresentation.as').write_text(renderer_source(),'utf-8')
    s=runner_source();ast.parse(s);(HERE/'run.py').write_text(s,'utf-8')
    print('Generated observed-progression diagnostic; no build or launch')
