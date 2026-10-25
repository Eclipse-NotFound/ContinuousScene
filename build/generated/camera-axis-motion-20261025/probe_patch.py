"""Native display remains visible: static, horizontal, vertical, combined camera motion."""
from pathlib import Path
import hashlib
import importlib.util
import shutil

HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-world-motion-20261025/probe_patch.py'
ORIGINAL=HERE.parent/'camera-world-motion-20261025/tests/SceneCameraRasterTrial.as'
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
CHANGED=['ContinuousSceneMotionProbe.as','tests/SceneCameraRasterTrial.as']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
assert sha(PATCH_SOURCE)=='1B725CA2993C9F59DCFAA1F8FC5133081B79FB3FF420B8E4A898650B9755A110'
assert sha(ORIGINAL)=='D53D246E272B9FB9AE3065C679A398F5DD82028486D43CBC99F6F1A5BB8D540B'
s=importlib.util.spec_from_file_location('axis_original_patch',PATCH_SOURCE)
base=importlib.util.module_from_spec(s);s.loader.exec_module(base)
EXTRA_INPUTS=(base.ORIGINAL,base.PATCH_SOURCE)

PIXELS='''        private function pixelCase(point:Object,index:int):void {
            var at:int=getTimer(),result:Object={index:index,x:point.x,y:point.y,passed:false};
            report.pixels.push(result);
            try {
                require(world.visual.visible===true,"World must remain visible");applyCamera(point.x,point.y);
                require(grafon.sceneViewReady(),"Pixel viewport not prepared");
                var a:BitmapData=capture(),b:BitmapData=capture();
                result.nativeRepeat=compare(a,b);result.passed=result.nativeRepeat.equal;
                require(result.passed,"Native consecutive captures changed");
            } finally {disposeOwned();result.elapsedMs=getTimer()-at;}
        }

'''

def helper_source():
    source=ORIGINAL.read_text('utf-8-sig');assert source==base.helper_source()
    start=source.index('        private function pixelCase(')
    end=source.index('        private function capture():BitmapData',start)
    edits=[('version:"camera-world-motion-1"','version:"camera-axis-motion-1"'),
      ('"Visibility control suppresses the whole world; includes display, hit-testing and native display-tree work, not GPU-only attribution.",','"World display stays visible in every arm; compare only native camera axes.",'),
      ('["world-visible-static","world-visible-moving","world-hidden-static","world-hidden-moving"]','["native-static","native-horizontal","native-vertical","native-combined"]'),
      ('hidden:condition>=2,moving:condition%2==1,','hidden:false,moving:condition!=0,'),
      ('            var point:Object=row.moving?route[age]:views[0];',
       '            var target:Object=row.moving?route[age]:views[0];\n            var point:Object={x:row.condition==2?views[0].x:target.x,y:row.condition==1?views[0].y:target.y};'),
      ('            world.visual.visible=!row.hidden;','            require(world.visual.visible===true,"World visibility changed");'),
      (source[start:end],PIXELS)]
    out=source
    for old,new in edits:
        assert out.count(old)==1,old;out=out.replace(old,new,1)
    rev=out
    for old,new in reversed(edits):
        assert rev.count(new)==1;rev=rev.replace(new,old,1)
    assert rev==source and 'world.visual.visible=false' not in out
    return out

def transform(source):return base.transform(source)

def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert not destination.exists() and not (source/'tests/SceneCameraRasterTrial.as').exists()
    shutil.copytree(source,destination)
    main=destination/'ContinuousSceneMotionProbe.as';main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/'tests/SceneCameraRasterTrial.as')

SUMMARY='''def summarize(raw):
    assert raw['ok'] and raw['error'] is None and not raw['samples']
    cfg=raw['config']
    assert cfg['drawControl']=='tilecrop' and cfg['presentationCheck'] and cfg['noLighting'] and cfg['noWall'] and not cfg['vision']
    trial,cleanup=raw['cameraRaster'],raw['cameraRasterCleanup']
    assert trial['version']==VERSION and trial['complete'] and trial['passed'] and not trial['errors']
    assert cleanup==trial['cleanup'] and cleanup['restored'] and not cleanup['errors'] and cleanup['pendingOwnedBitmaps']==0
    assert trial['pixelBitmapsCreated']==trial['pixelBitmapsDisposed']==10
    assert trial['pixelsValid'] and len(trial['pixels'])==5
    for row in trial['pixels']:
        c=row['nativeRepeat'];assert row['passed'] and c['equal'] and c['differentPixels']==c['maxRGB']==c['maxAlpha']==0
    assert trial['testFrameRate']==120 and trial['stabilizationFrames']==12
    assert 1<=len(trial['preparePasses'])<=12 and trial['preparePasses'][-1]['quiet']
    assert all(v==0 for v in trial['preparePasses'][-1]['delta'].values())
    assert trial['zeroRasterWork'] and all(v==0 for v in trial['timingRasterDelta'].values())
    assert len(trial['windows'])==8 and len(trial['framesMs'])==len(trial['sampleAtMs'])==960
    keys=('sceneRedraws','sceneDrawMs','sceneResident','sceneEvictions','sceneMisses','sceneWarmCount','sceneWarmSlices','sceneWarmForced')
    initial=trial['timingStart'];previous=trial['timingStartAtMs'];intervals=[];stamps=[];rows=[]
    modes=('native-static','native-horizontal','native-vertical','native-combined')
    for i,(row,condition) in enumerate(zip(trial['windows'],(0,1,2,3,3,2,1,0))):
        assert row['index']==i and row['condition']==condition and row['mode']==modes[condition]
        assert row['hidden'] is False and row['moving'] is (condition!=0) and row['startAtMs']==previous
        for key in ('framesMs','sampleAtMs','vx','vy','cameraX','cameraY','gg','scene','workMs','worldVisible','windowVisible'):
            assert len(row[key])==120,key
        assert all(v is True for v in row['worldVisible']+row['windowVisible'])
        xs,ys=set(row['vx']),set(row['vy'])
        assert (len(xs)>1)==(condition in (1,3)) and (len(ys)>1)==(condition in (2,3))
        assert all(pose==initial['gg'] for pose in row['gg'])
        for scene in row['scene']:
            for key in keys:assert scene[key]==initial['scene'][key],(key,scene[key],initial['scene'][key])
        for stamp,dt in zip(row['sampleAtMs'],row['framesMs']):
            assert stamp-previous==dt and dt>=0;previous=stamp
        assert row['endAtMs']==previous and row['copiesEnd']==row['copiesStart']==row['allocatedEnd']==row['allocatedStart']==0
        intervals.extend(row['framesMs']);stamps.extend(row['sampleAtMs'])
        rows.append(dict(index=i,condition=condition,mode=row['mode'],frame=metric(row['framesMs']),work=metric(row['workMs']),
            xRange=[min(xs),max(xs)],yRange=[min(ys),max(ys)]))
    assert intervals==trial['framesMs'] and stamps==trial['sampleAtMs']
    assert previous==trial['timingEndAtMs'] and sum(intervals)==trial['timingElapsedMs']==previous-trial['timingStartAtMs']
    arms={name:metric([v for row in trial['windows'] if row['mode']==name for v in row['framesMs']]) for name in modes}
    paired=[dict(staticIndex=static,movingIndex=moving,mode=rows[moving]['mode'],
        movementMinusStaticMs=rows[moving]['frame']['mean']-rows[static]['frame']['mean'])
        for static,moving in ((0,1),(0,2),(0,3),(7,6),(7,5),(7,4))]
    return dict(version=VERSION,complete=True,diagnosticOnly=True,performanceEligible=False,gameplayAcceptance=False,deployed=False,
        rows=rows,arms=arms,pairs=paired,elapsedMs=sum(intervals),zeroNativeRasterWork=True,
        originalFrameRate=trial['originalFrameRate'],testFrameRate=trial['testFrameRate'],pixels=trial['pixels'],cleanup=cleanup,
        limits=['Simulation paused, timelines and other callbacks remain live; not enemy-free gameplay FPS.',
                'Native world stays visible in every interval; static versus axis movement, no rendering optimization.',
                'Private native window visible throughout timing; no user-desktop display or input claim.',
                'All transitions, native camera calculations and observation costs retained; no spikes removed.'])


'''

if __name__=='__main__':
    output=helper_source()
    if HELPER.exists():assert HELPER.read_text('utf-8-sig')==output
    else:HELPER.parent.mkdir(parents=True,exist_ok=True);HELPER.write_text(output,'utf-8')
    runner=HERE.parent/'camera-world-motion-20261025/run.py'
    assert sha(runner)=='9547615A4EB78576526A0DC5286BE9ACADB86756CF8C5EE91BCAA5DE47CDCACC'
    original=runner.read_text('utf-8-sig');a=original.index('def summarize(raw):');b=original.index('def main():',a)
    edits=[("VERSION = 'camera-world-motion-1'","VERSION = 'camera-axis-motion-1'"),
      ('patch.HELPER, patch.ORIGINAL, patch.PATCH_SOURCE)})','patch.HELPER, patch.ORIGINAL, patch.PATCH_SOURCE, *patch.EXTRA_INPUTS)})'),
      (original[a:b],SUMMARY),('camera world motion / 01a13816','camera axis motion / 01a13816'),
      ('960 paused camera/world visibility frames; diagnostic only, no deployment','960 native paused camera axis frames; diagnostic only, no deployment')]
    out=original
    for old,new in edits:
        assert out.count(old) in (1,2);out=out.replace(old,new)
    dest=HERE/'run.py'
    if dest.exists():assert dest.read_text('utf-8-sig')==out
    else:dest.write_text(out,'utf-8')
    print({'helper':sha(HELPER),'runner':sha(dest)})
