from pathlib import Path
import importlib.util
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('quiet_axis_summary',HERE/'axis_summary.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
base.VERSION='camera-visible-room-scout-1'
def summarize(raw):
    out=base.summarize(raw)
    bands=raw['quietBands'];t=raw['cameraRaster'];rows=[]
    assert bands and all(b['tail'] is not None and b['nextEnter'] is not None for b in bands)
    for i,b in enumerate(bands):
        assert b['enter']<=b['nativeStart']<=b['nativeEnd']<=b['mods100']<=b['mods200']<=b['probeStart']<=b['probeEnd']<=b['tail']<=b['nextEnter']
        if b['after']==b['before']:continue
        assert i>0 and b['after']==b['before']+1
        prev=bands[i-1];j=b['before'];stamp=t['sampleAtMs'][j]
        prior=t['sampleAtMs'][j-1] if j else t['timingStartAtMs']
        assert prev['probeStart']<=prior<=prev['probeEnd'] and b['probeStart']<=stamp<=b['probeEnd']
        assert prev['nextEnter']==b['enter']
        v=dict(index=j,native=b['nativeEnd']-b['nativeStart'],
               currentOtherStage=stamp-b['enter']-(b['nativeEnd']-b['nativeStart']),
               previousTail=prev['tail']-prior,betweenStage=b['enter']-prev['tail'])
        assert sum(v[k] for k in ['native','currentOtherStage','previousTail','betweenStage'])==t['framesMs'][j]
        rows.append(v)
    assert len(rows)==960 and [v['index'] for v in rows]==list(range(960))
    out['timingBands']={}
    for condition,name in enumerate(['native-static','native-horizontal','native-vertical','native-combined']):
        selected=[v for v in rows if t['windows'][v['index']//120]['condition']==condition]
        out['timingBands'][name]={k:base.metric([v[k] for v in selected]) for k in ['native','currentOtherStage','previousTail','betweenStage']}
    out['bandLimit']='Stage priority 1000 to -50 includes native MainMenu/World and any other listeners in that band; betweenStage includes rendering, Flash callbacks, runtime/OS scheduling, not a pure GPU measurement.'
    return out
