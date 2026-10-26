"""Freeze only after fixed native route preparation, with explicit timeline evidence."""
from pathlib import Path
import importlib.util
import ast
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-stage3d-wholeworld-20261027'
spec=importlib.util.spec_from_file_location('wholeworld_late_base',BASE/'prepare.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
one=base.replace_one
def helper_source():
    s=base.helper_source().replace('camera-stage3d-wholeworld-1','camera-stage3d-wholeworld-late-1')
    s=one(s,'presenter.prepareContext(w);presenter.freezeTimelines(w);','presenter.prepareContext(w);')
    s=one(s,'presenter.prepareWorld(world,captureBounds);','presenter.freezeTimelines(world);presenter.prepareWorld(world,captureBounds);')
    return s
def renderer_source():
    s=base.renderer_source()
    s=one(s,'    import flash.utils.getTimer;','    import flash.utils.getTimer;\n    import flash.utils.getQualifiedClassName;')
    s=one(s,'private var timelinesFrozen:Boolean=false,timelinesRestored:Boolean=false;',
        'private var timelinesFrozen:Boolean=false,timelinesRestored:Boolean=false;\n        private var timelineChanges:Array=[];')
    s=one(s,'var item:Object={clip:mc,frame:mc.currentFrame,total:mc.totalFrames,playing:mc.isPlaying};',
        'var item:Object={clip:mc,frame:mc.currentFrame,total:mc.totalFrames,playing:mc.isPlaying,className:getQualifiedClassName(mc),name:mc.name};')
    s=one(s,'''            for each(var item:Object in clips)require(item.clip.currentFrame==item.frame && item.clip.totalFrames==item.total && !item.clip.isPlaying,
                "A world timeline changed despite the fixed-picture pause");''','''            var changes:int=0;
            for each(var item:Object in clips)if(item.clip.currentFrame!=item.frame || item.clip.totalFrames!=item.total || item.clip.isPlaying) {
                ++changes;
                if(timelineChanges.length<32)timelineChanges.push({audit:timelineAudits,className:item.className,name:item.name,
                    beforeFrame:item.frame,afterFrame:item.clip.currentFrame,beforeTotal:item.total,afterTotal:item.clip.totalFrames,
                    beforePlaying:item.playing,afterPlaying:item.clip.isPlaying});
            }
            require(changes==0,"Fixed-picture timeline changes: "+changes);''')
    s=one(s,'clipsStopped:clipsStopped,clipsResumed:clipsResumed,timelineAudits:timelineAudits,timelinesRestored:timelinesRestored};',
        'clipsStopped:clipsStopped,clipsResumed:clipsResumed,timelineAudits:timelineAudits,timelinesRestored:timelinesRestored,timelineChanges:timelineChanges};')
    return s
def runner_source():return base.runner_source().replace('camera-stage3d-wholeworld-1','camera-stage3d-wholeworld-late-1')
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    (HERE/'tests/SceneCameraRasterTrial.as').write_text(helper_source(),'utf-8')
    (HERE/'SceneTilePresentation.as').write_text(renderer_source(),'utf-8')
    s=runner_source();ast.parse(s);(HERE/'run.py').write_text(s,'utf-8')
    print('Generated late-freeze diagnostic; no build or launch')
