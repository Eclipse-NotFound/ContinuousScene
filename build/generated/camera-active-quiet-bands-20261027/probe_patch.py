from pathlib import Path
import importlib.util,shutil
HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-active-quiet-axis-20261027/probe_patch.py'
def load(name,p):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
base=load('quiet_axis_patch',PATCH_SOURCE)
generation=load('quiet_bands_generation',HERE/'prepare.py')
ORIGINAL=base.HELPER;HELPER=HERE/'tests/SceneCameraRasterTrial.as';CHANGED=base.CHANGED
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,HERE/'prepare.py',HERE/'summary.py',HERE.parent/'camera-active-quiet-axis-20261027/run.py',HERE.parent/'camera-active-quiet-axis-20261027/summary.py')
def helper_source():return generation.helper_source()
def one(s,a,b):
    assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
def transform(source):
    s=base.transform(source)
    edits=[
      ('        private static var report:Object={version:"motion-0.8.2",assertions:[],samples:[]};',
       '        private static var quietPending:Object;\n        private static var report:Object={version:"motion-0.8.2",assertions:[],samples:[],quietBands:[]};'),
      ('absoluteStart=getTimer();rasterPresentation.beginFrame();',
       'absoluteStart=getTimer();if(quietPending && quietPending.nextEnter===null)quietPending.nextEnter=absoluteStart;rasterPresentation.beginFrame();'),
      ('lastEnd=getTimer();completeProbeTimingTail(lastEnd);',
       'lastEnd=getTimer();completeProbeTimingTail(lastEnd);if(quietPending && quietPending.tail===null)quietPending.tail=getTimer();'),
      ('''                }else if(phase==97) {
                    if(cameraRaster.step(w)) {
                        check("camera-raster-complete",report.cameraRaster.complete,report.cameraRaster.complete);
                        finish();return;
                    }
                }else if(phase==90) {''',
       '''                }else if(phase==97) {
                    quietPending={enter:absoluteStart,nativeStart:startFrame,nativeEnd:band50,
                        mods100:band150,mods200:band250,probeStart:getTimer(),probeEnd:null,tail:null,nextEnter:null,
                        before:report.cameraRaster.framesMs.length,after:null};
                    report.quietBands.push(quietPending);
                    var quietDone:Boolean=cameraRaster.step(w);
                    quietPending.probeEnd=getTimer();quietPending.after=report.cameraRaster.framesMs.length;
                    if(quietDone) {phase=98;return;}
                }else if(phase==98) {
                    check("camera-raster-complete",report.cameraRaster.complete,report.cameraRaster.complete);
                    check("quiet-band-tail-complete",quietPending.tail!==null && quietPending.nextEnter!==null);
                    finish();return;
                }else if(phase==90) {''')
    ]
    old=s
    for a,b in edits:s=one(s,a,b)
    restored=s
    for a,b in reversed(edits):restored=one(restored,b,a)
    assert restored==old
    return s
def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert (HERE/'run.py').read_text('utf-8-sig')==generation.runner_source()
    assert not destination.exists() and not (source/'tests/SceneCameraRasterTrial.as').exists()
    shutil.copytree(source,destination)
    p=destination/'ContinuousSceneMotionProbe.as';p.write_text(transform(p.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/'tests/SceneCameraRasterTrial.as')
