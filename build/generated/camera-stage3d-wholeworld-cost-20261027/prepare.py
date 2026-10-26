"""Cost attribution with explicit rejected pixels; never relax product acceptance."""
from pathlib import Path
import importlib.util
import ast
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-stage3d-wholeworld-observed-20261027'
spec=importlib.util.spec_from_file_location('wholeworld_cost_base',BASE/'prepare.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
one=base.one
def helper_source():
    s=base.helper_source().replace('camera-stage3d-wholeworld-observed-1','camera-stage3d-wholeworld-cost-1')
    s=one(s,'terminalOnly:true,complete:false,passed:false,pixelsValid:false,',
        'terminalOnly:true,complete:false,passed:false,pixelsValid:false,visualAccepted:true,attributionOnlyWithRejectedPixels:true,')
    s=one(s,'report.pixelsValid=true;', 'report.pixelsValid=report.visualAccepted;')
    s=one(s,'result.passed=result.visualAccepted && result.restore.equal;',
        'result.passed=result.visualAccepted && result.restore.equal;\n                if(!result.visualAccepted)report.visualAccepted=false;')
    s=one(s,'require(result.passed,"GPU whole-world snapshot pixels failed");',
        'require(result.restore.equal,"GPU whole-world restoration pixels failed"); // Candidate rejection remains explicit; attribution only.')
    return s
def renderer_source():return base.renderer_source()
def runner_source():
    s=base.runner_source().replace('camera-stage3d-wholeworld-observed-1','camera-stage3d-wholeworld-cost-1')
    s=one(s,"assert trial['pixelsValid'] and len(trial['pixels'])==13 and len(trial['nativeWarmups'])==18", """assert trial['attributionOnlyWithRejectedPixels']
    assert trial['pixelsValid']==trial['visualAccepted']==all(p['visualAccepted'] for p in trial['pixels'])
    assert len(trial['pixels'])==13 and len(trial['nativeWarmups'])==18""")
    s=one(s,"assert pixel['passed'] and pixel['visualAccepted'] and pixel['candidate']['maxRGB']<=2 and pixel['candidate']['maxAlpha']==0", """assert pixel['visualAccepted']==(pixel['candidate']['maxRGB']<=2 and pixel['candidate']['maxAlpha']==0)
        assert pixel['passed']==pixel['visualAccepted'] # Restore is independently exact below.""")
    s=one(s,'rows=rows,arms=arms,pairs=pairs,elapsedMs=sum(intervals),zeroNativeRasterWork=True,pixels=trial[\'pixels\'],cleanup=cleanup,',
        'rows=rows,arms=arms,pairs=pairs,elapsedMs=sum(intervals),zeroNativeRasterWork=True,pixels=trial[\'pixels\'],cleanup=cleanup,visualAccepted=trial[\'visualAccepted\'],')
    s=one(s,"'Whole-world fixed picture with identically frozen MovieClips; no animated gameplay or combat claim.',",
        "'Candidate pixels may fail RGB2 and remain explicitly rejected; this is only a fixed-picture cost upper bound.',\n                'Whole-world fixed picture with identically frozen MovieClips; no animated gameplay or combat claim.',")
    return s
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    (HERE/'tests/SceneCameraRasterTrial.as').write_text(helper_source(),'utf-8')
    (HERE/'SceneTilePresentation.as').write_text(renderer_source(),'utf-8')
    s=runner_source();ast.parse(s);(HERE/'run.py').write_text(s,'utf-8')
    print('Generated explicitly visual-rejected cost diagnostic; no build or launch')
