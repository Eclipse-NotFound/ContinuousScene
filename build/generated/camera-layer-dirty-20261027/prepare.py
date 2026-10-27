"""Partition native drawing by layer; keep Flash timelines live and invalidate changed layers."""
from pathlib import Path
import importlib.util
import ast
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-stage3d-wholeworld-settle-20261027'
spec=importlib.util.spec_from_file_location('layer_dirty_seed',BASE/'prepare.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
one=base.one


def helper_source():
    s=base.helper_source().replace('camera-stage3d-wholeworld-settle-1','camera-layer-dirty-1')
    s=one(s,'Simulation paused; currently playing world MovieClips stopped identically in both arms. Other callbacks remain live.',
          'Simulation paused, but Flash timelines remain live; no MovieClip stop/play/goto calls by this experiment.')
    s=one(s,'Whole-world fixed snapshot plus backdrop on Stage3D; native UI remains. Frozen animation is a feasibility ceiling, never gameplay acceptance. Readback composition is not an OS screenshot.',
          'Ordered layer caches update on observed timeline frame changes; native UI remains. Not simulation or OS-window acceptance.')
    s=one(s,'Not enemy-free or combat gameplay: world MovieClips and simulation are frozen. No production path or real animation compatibility.',
          'Paused simulation only. Bitmap pixel mutations, arbitrary script property changes, and room lifecycle are not yet tracked; not a production renderer.')
    s=one(s,'presenter.observeTimelines(world);phase=4;settle=0;','phase=6;settle=0;')
    a=s.index('                } else if(phase==4) {');b=s.index('                } else if(phase==6) {',a)
    s=s[:a]+s[b:]
    s=s.replace('report.frozenPicture=presenter.snapshot();','report.layerCache=presenter.snapshot();')
    s=s.replace('Actual GPU whole-world snapshot mismatch','Actual GPU layer cache mismatch')
    return s


def renderer_source():
    s=base.renderer_source()
    s=one(s,'private var quad:Vector.<Number>', '''private var groups:Array=[],worldChildren:Array=[],scratch:BitmapData;
        private var layerRasterCalls:int=0,layerRasterMs:int=0,layerUploadMs:int=0;
        private var animationChanges:int=0,watchReads:int=0,watchNodes:int=0,watchMs:int=0;
        private var liveCPUBytes:Number=0,peakCPUBytes:Number=0;
        private var layerWrites:int=0,layerRestores:int=0;
        private var quad:Vector.<Number>''')
    a=s.index('        public function observeTimelines(');b=s.index('        private function upload(',a)
    methods=(HERE/'layer_methods.as.inc').read_text('utf-8-sig')
    s=s[:a]+methods+s[b:]
    s=s.replace('96*1024*1024','128*1024*1024')
    s=one(s,'if(!active){backdrop.visible=false;root.visible=false;plane.visible=true;active=true;++enables;}',
          'refreshChangedLayers();\n            if(!active){backdrop.visible=false;root.visible=false;plane.visible=true;active=true;++enables;}')
    s=one(s,'for each(var t:Object in textures)drawQuad(t.texture,t.x+m.tx,t.y+m.ty,t.width,t.height);',
          'for each(var group:Object in groups)for each(var t:Object in group.tiles)drawQuad(t.texture,t.x+m.tx,t.y+m.ty,t.width,t.height);')
    s=one(s,'for each(var t:Object in textures){t.texture.dispose();++texturesDisposed;}textures=[];',
          'for each(var group:Object in groups)releaseGroup(group);\n            if(scratch){disposePixels(scratch);scratch=null;}')
    a=s.index('            // Only resume clips stopped by this diagnostic;');b=s.index('        public function snapshot():Object {',a)
    s=s[:a]+'''            timelinesRestored=true; // No animation state was changed by this experiment.
        }
'''+s[b:]
    s=one(s,'worldPrepared:worldPrepared,captureCullRestored:captureCullRestored,timelineCount:clips.length,',
          '''worldPrepared:worldPrepared,captureCullRestored:captureCullRestored,timelineCount:0,
                liveAnimation:true,layerRasterCalls:layerRasterCalls,layerRasterMs:layerRasterMs,layerUploadMs:layerUploadMs,
                animationChanges:animationChanges,watchReads:watchReads,watchNodes:watchNodes,watchMs:watchMs,
                layerWrites:layerWrites,layerRestores:layerRestores,liveCPUBytes:liveCPUBytes,peakCPUBytes:peakCPUBytes,
                groups:groupSummary(),''')
    s=s.replace('Observed implicit movers resume with play; public isPlaying may become true. Terminal diagnostic only.',
                'No stop/play/goto calls. Frame-driven layer changes only; simulation remains paused.')
    s=s.replace('Fixed-picture feasibility only; animations are frozen identically in both arms.',
                'Layer-cache prototype; native Flash timelines remain live in both arms.')
    return s


def runner_source():
    s=base.runner_source().replace('camera-stage3d-wholeworld-settle-1','camera-layer-dirty-1')
    a=s.index('    assert end[\'enables\']');b=s.index("    assert 'software' not in",a)
    s=s[:a]+'''    assert end['enables']==end['restores'] and end['allocated']==end['disposed']
    assert end['texturesCreated']==end['texturesDisposed']>1
    assert end['contextCreates']==end['contextDisposals']==1 and end['gpuBytes']==end['liveCPUBytes']==0 and not end['ready'] and not end['error']
    assert end['liveAnimation'] and end['clipsStopped']==end['clipsResumed']==0
    assert end['timelinesRestored'] and end['worldPrepared'] and end['captureCullRestored']
    assert end['layerWrites']==end['layerRestores'] and end['animationChanges']>0 and end['layerRasterCalls']>len(end['groups'])
'''+s[b:]
    s=one(s,"            assert all(p[k]==first[k] for k in ('uploads','texturesCreated','allocated','disposed','copies','clipsStopped'))",
          "            assert p['liveAnimation'] and p['clipsStopped']==p['clipsResumed']==0\n            assert p['layerWrites']==p['layerRestores'] and 0<=p['liveCPUBytes']<=128*1024*1024")
    s=one(s,"        assert row['endAtMs']==previous and row['copiesEnd']==row['copiesStart']==first['copies']\n        assert row['allocatedStart']==row['allocatedEnd']==first['allocated']",
          "        assert row['endAtMs']==previous and row['copiesEnd']>=row['copiesStart']\n        assert row['allocatedEnd']>=row['allocatedStart']")
    s=s.replace('Whole-world fixed picture with identically frozen MovieClips; no animated gameplay or combat claim.',
                'Layer cache with live Flash timelines; simulation paused, no gameplay/combat claim; mutation tracking incomplete.')
    s=s.replace('Whole-world fixed-picture Stage3D feasibility; not gameplay acceptance.',
                'Native layer caching with live Flash timelines; not gameplay acceptance.')
    s=s.replace('camera whole-world fixed-picture Stage3D','camera live timeline layer cache')
    s=s.replace('960 frozen native versus whole-picture GPU intervals; feasibility only, no deployment',
                '960 native versus live timeline layer-cache intervals; simulation paused, no deployment')
    return s


if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    (HERE/'tests/SceneCameraRasterTrial.as').write_text(helper_source(),'utf-8')
    (HERE/'SceneTilePresentation.as').write_text(renderer_source(),'utf-8')
    s=runner_source();ast.parse(s);(HERE/'run.py').write_text(s,'utf-8')
    print('Prepared live-timeline layer cache; no build or launch')
