from pathlib import Path
import importlib.util
import ast
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'camera-room-axis-baseline-v2-20261027'
def save(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():assert path.read_text('utf-8-sig')==text,path
    else:path.write_text(text,'utf-8')
spec=importlib.util.spec_from_file_location('room_axis_bands_patch',HERE/'probe_patch.py')
patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)
save(patch.HELPER,patch.helper_source())
runner=(OLD/'run.py').read_text('utf-8-sig').replace('camera-room-axis-baseline-2','camera-room-axis-bands-1')
before="    assert intervals==trial['framesMs'] and stamps==trial['sampleAtMs']"
extra="""    clock_rows=[]
    for row in trial['windows']:
        assert all(len(row[k])==120 for k in ('eventClocks','previousTailMs','interFrameGapMs','scriptToSampleMs'))
        prior=row['startAtMs']
        for i,c in enumerate(row['eventClocks']):
            now=row['sampleAtMs'][i]
            assert prior<=c['previousEnd']<=c['first']<=c['start']<=c['nativeEnd']<=c['wallEnd']<=c['sceneEnd']<=c['beforeProbe']<=now
            tail=c['previousEnd']-prior;gap=c['first']-c['previousEnd'];script=now-c['first']
            assert tail==row['previousTailMs'][i] and gap==row['interFrameGapMs'][i] and script==row['scriptToSampleMs'][i]
            assert tail+gap+script==row['framesMs'][i]
            prior=now
        clock_rows.append(dict(index=row['index'],mode=row['mode'],
            previousTail=metric(row['previousTailMs']),interFrameGap=metric(row['interFrameGapMs']),
            scriptToSample=metric(row['scriptToSampleMs']),
            nativeBand=metric([c['nativeEnd']-c['start'] for c in row['eventClocks']]),
            earlyBand=metric([c['start']-c['first'] for c in row['eventClocks']]),
            middleBand=metric([c['sceneEnd']-c['nativeEnd'] for c in row['eventClocks']]),
            lateBand=metric([row['sampleAtMs'][i]-c['sceneEnd'] for i,c in enumerate(row['eventClocks'])])))
"""
assert runner.count(before)==1;runner=runner.replace(before,extra+before,1)
before="        roomAxis=trial['roomAxis'],originalZoom="
assert runner.count(before)==1;runner=runner.replace(before,"        eventClockRows=clock_rows,roomAxis=trial['roomAxis'],originalZoom=",1)
ast.parse(runner);save(HERE/'run.py',runner)
print('Prepared exact interval partition from existing frame clocks; no CPU/GPU attribution claim.')

