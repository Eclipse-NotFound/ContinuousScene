"""All four terrain buffers on GPU; wrong object occlusion is diagnostic only."""
from pathlib import Path
import importlib.util
import shutil
HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-stage3d-entry-20261027/probe_patch.py'
spec=importlib.util.spec_from_file_location('all_terrain_gpu_seed',PATCH_SOURCE)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
ORIGINAL=base.HELPER
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
PRESENTER=HERE/'SceneTilePresentation.as'
CHANGED=base.CHANGED
WARM=HERE.parent/'camera-objects-warm-alpha-20261027/warmup.as.inc'
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,base.PRESENTER,PRESENTER,HERE/'prepare.py',WARM)

def renderer_source():
    s=base.PRESENTER.read_text('utf-8-sig');assert s==base.renderer_source()
    edits=[
        ('All native object/foreground rendering remains.',
         'All native object rendering remains above terrain. Object/foreground occlusion is intentionally wrong; attribution only.'),
        ('for(var layer:int=1;layer<=2;++layer)','for(var layer:int=0;layer<4;++layer)'),
        ('for(layer=1;layer<=2;++layer) {\n                var parent:DisplayObjectContainer=parents[layer];',
         'for(var parentIndex:int=1;parentIndex<=4;++parentIndex) {\n                layer=[-1,1,2,0,3][parentIndex];\n                var parent:DisplayObjectContainer=parents[parentIndex];'),
        ('parents=[backdrop,g.visBack,g.visBack2];','parents=[backdrop,g.visBack,g.visBack2,g.visFront,g.visVoda];'),
        ('            rememberBackdrop(backdrop);','''            initial.originalTerrainOrder=[world.visual.getChildIndex(g.visBack),world.visual.getChildIndex(g.visBack2),
                world.visual.getChildIndex(g.visFront),world.visual.getChildIndex(g.visVoda)];
            initial.diagnosticWrongOcclusion=true;
            rememberBackdrop(backdrop);'''),
    ]
    for old,new in edits:
        assert s.count(old)==1,(old,s.count(old));s=s.replace(old,new,1)
    return s

def helper_source():
    s=ORIGINAL.read_text('utf-8-sig');assert s==base.helper_source()
    edits=[
        ('camera-stage3d-entry-1','camera-stage3d-terrain-attribution-1'),
        ('terminalOnly:true,complete:false','drawOrderIntentionallyDifferent:true,candidateVisualEquivalent:false,terminalOnly:true,complete:false'),
        ('                var a:BitmapData=capture();','                var a:BitmapData=warmNative(point,index);'),
        ('result.passed=result.candidate.maxRGB<=2 && result.candidate.maxAlpha==0 && result.restore.equal;',
         'result.passed=result.restore.equal; // Only native restoration is an equality requirement for this incomplete-view diagnosis.'),
        ('        private function capture():BitmapData {',WARM.read_text('utf-8-sig')+'\n        private function capture():BitmapData {'),
    ]
    for old,new in edits:
        assert old in s,old;s=s.replace(old,new)
    return s

def transform(source):return base.transform(source)

def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source() and PRESENTER.read_text('utf-8-sig')==renderer_source()
    assert not destination.exists() and not (source/'tests/SceneCameraRasterTrial.as').exists()
    shutil.copytree(source,destination)
    main=destination/'ContinuousSceneMotionProbe.as';main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/'tests/SceneCameraRasterTrial.as')
    shutil.copy2(PRESENTER,destination/'SceneTilePresentation.as')
