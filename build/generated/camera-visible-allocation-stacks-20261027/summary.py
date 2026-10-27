from pathlib import Path
import importlib.util
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('room_sampling_axis_summary',HERE.parent/'camera-visible-room-fog-history-20261027/summary.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
base.base.VERSION='camera-visible-allocation-stacks-1'

def summarize(raw):
    out=base.summarize(raw)
    s=raw['cameraRaster']['cpuSampling']
    assert s['version']=='room-camera-allocation-sampler-1' and s['valid'] and s['attributionReady'] and not s['errors']
    assert s['cleanup']['stopped'] and s['cleanup']['callbackCleared'] and not s['cleanup']['active']
    assert len(s['windows'])==8 and s['sampleLimitPerWindow']==100000 and not s['internalAllocations']
    for i,w in enumerate(s['windows']):
        assert w['segment']==i and w==raw['cameraRaster']['windows'][i]['cpuSampling']
        assert w['name']==raw['cameraRaster']['windows'][i]['mode']
        assert w['headFrames']==5 and w['firstAge']==115 and w['lastAge']==119 and w['pausedAge']==119
        assert w['valid'] and w['attributionReady'] and not w['errors'] and not w['overflow'] and not w['overLimit']
        c=w['counts'];d=w['timeDiagnostics'];times=d['cpuTimes'];indices=d['cpuGlobalIndices']
        assert c['total']==w['reportedSampleCount']==sum(c[k] for k in ['cpu','newObject','deleteObject','unknown'])<100000
        assert c['unknown']==0 and c['cpu']==len(times)==len(indices)>0 and d['byType']['cpu']['bad']==0
        assert all(t>0 for t in times) and times==sorted(times) and indices==sorted(set(indices))
        assert sum(r['samples'] for r in w['top'])==sum(r['samples'] for r in w['stacks'])==c['cpu']
        assert len(w['newObjectStacks'])<=4096
        assert sum(r['samples'] for r in w['newObjectTop'])==sum(r['samples'] for r in w['newObjectStacks'])==c['newObject']
    out['cpuSampling']=s
    out['performanceEligible']=False
    out['cpuInterpretation']='Raw CPU stack occurrences only; allocation/CPU mixed ordering is not a clock; sampling and aggregation perturb timing. No FPS acceptance.'
    return out
