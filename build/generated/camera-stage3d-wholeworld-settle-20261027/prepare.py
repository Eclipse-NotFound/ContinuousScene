"""One bounded drain of verified bloat_bulk frame1/frame55 scripts, then freeze audit."""
from pathlib import Path
import importlib.util
import ast
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-stage3d-wholeworld-cost-20261027'
spec=importlib.util.spec_from_file_location('wholeworld_settle_base',BASE/'prepare.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
one=base.one
def helper_source():
    s=base.helper_source().replace('camera-stage3d-wholeworld-cost-1','camera-stage3d-wholeworld-settle-1')
    s=one(s,'''presenter.freezeTimelines(world);presenter.prepareWorld(world,captureBounds);
                        report.frozenPicture=presenter.snapshot();phase=1;pixelAt=getTimer();''',
        'presenter.freezeTimelines(world);phase=5;')
    s=one(s,'} else if(phase==1) {','''} else if(phase==5) {
                    presenter.settleFrameScripts();phase=6;
                } else if(phase==6) {
                    presenter.auditTimelines();presenter.prepareWorld(world,captureBounds);
                    report.frozenPicture=presenter.snapshot();phase=1;pixelAt=getTimer();
                } else if(phase==1) {''')
    return s
def renderer_source():
    s=base.renderer_source()
    s=one(s,'private var observationReport:Array=[];',
        'private var observationReport:Array=[];\n        private var frameScriptDrainDone:Boolean=false,frameScriptDrains:Array=[];')
    s=one(s,'        public function auditTimelines():void {','''        public function settleFrameScripts():void {
            require(timelinesFrozen && !frameScriptDrainDone,"Single fixed frame-script drain required");
            frameScriptDrainDone=true;
            for each(var item:Object in clips) {
                if(item.clip.currentFrame==item.frame && item.clip.totalFrames==item.total && !item.clip.isPlaying)continue;
                // Source-verified class only: frame1 -> random play; frame55 -> play(2).
                // Any other post-freeze change remains a hard failure. No retry loop.
                require(item.playing && item.resume && item.className=="pfe_fla::bloat_bulk_896" &&
                    (item.frame==1 || item.frame==55) && item.clip.totalFrames==55 && item.clip.isPlaying,
                    "Unexpected animation change in fixed frame-script drain: "+item.path);
                frameScriptDrains.push({path:item.path,beforeFrame:item.frame,afterFrame:item.clip.currentFrame});
                item.frame=item.clip.currentFrame;item.clip.stop();
            }
        }
        public function auditTimelines():void {''')
    s=one(s,'playbackRestoreLimit:"Observed implicit movers resume with play; public isPlaying may become true. Terminal diagnostic only."};',
        'playbackRestoreLimit:"Observed implicit movers resume with play; public isPlaying may become true. Terminal diagnostic only.",frameScriptDrainDone:frameScriptDrainDone,frameScriptDrains:frameScriptDrains.concat()};')
    s=s.replace('timelineChanges:timelineChanges,','timelineChanges:timelineChanges.concat(),')
    return s
def runner_source():return base.runner_source().replace('camera-stage3d-wholeworld-cost-1','camera-stage3d-wholeworld-settle-1')
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    (HERE/'tests/SceneCameraRasterTrial.as').write_text(helper_source(),'utf-8')
    (HERE/'SceneTilePresentation.as').write_text(renderer_source(),'utf-8')
    s=runner_source();ast.parse(s);(HERE/'run.py').write_text(s,'utf-8')
    print('Generated fixed one-pass frame-script drain; no build or launch')
