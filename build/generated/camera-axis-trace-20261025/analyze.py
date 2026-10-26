"""Native telemetry spans aligned by custom per-frame anchors, never summed nested."""
from collections import defaultdict
import math
import statistics
import json

def metric(values):
    xs=sorted(values);return dict(count=len(xs),mean=statistics.mean(xs),median=statistics.median(xs),p95=xs[math.ceil(len(xs)*.95)-1],maximum=max(xs))

def union_length(items):
    if not items:return 0
    items=sorted(items);total=0;start,end=items[0]
    for a,b in items[1:]:
        if a>end:total+=end-start;start,end=a,b
        else:end=max(end,b)
    return total+end-start

def analyze_stream(factory,raw):
    anchors=[];meta=[];count=0;names=defaultdict(int)
    for item in factory():
        count+=1;names[item['name']]+=1
        if item['name']=='.trace' and isinstance(item.get('value'),str):
            for prefix,kind in [('REMAINS_CAMERA_FRAME ','remains.camera.frame'),('REMAINS_CAMERA_END ','remains.camera.end')]:
                if item['value'].startswith(prefix):
                    anchors.append(dict(name=kind,atUs=item['atUs'],value=json.loads(item['value'][len(prefix):])))
        if item['name'].startswith(('.tlm.category','.platform.gpu','.rend.display.mode')):meta.append(item)
    frames=[p for p in anchors if p['name']=='remains.camera.frame'];ends=[p for p in anchors if p['name']=='remains.camera.end']
    assert len(frames)==960 and len(ends)==1,'All 961 anchors required'
    assert [p['value']['frame'] for p in frames]==list(range(960))
    points=frames+ends
    assert all(points[i+1]['atUs']>points[i]['atUs'] for i in range(960))
    bounds=[(points[s*120]['atUs'],points[(s+1)*120]['atUs']) for s in range(8)]
    merged=[defaultdict(list) for unused in bounds]
    # Span endpoints in the native stream are chronological. Nested parents may
    # start before earlier children: merge backwards, preserving all true gaps.
    for item in factory():
        if item.get('span',0)<=0 or not item['name'].startswith('.'):continue
        a,b=item['atUs']-item['span'],item['atUs']
        if b<=bounds[0][0] or a>=bounds[-1][1]:continue
        for segment,(lo,hi) in enumerate(bounds):
            if b<=lo or a>=hi:continue
            left,right=max(a,lo),min(b,hi);stack=merged[segment][item['name']]
            assert not stack or right>=stack[-1][1],('Native span ends out of order',item['name'])
            while stack and stack[-1][1]>=left:left=min(left,stack.pop()[0])
            stack.append((left,right))
    compressed=list(anchors)
    for bucket in merged:
        for name,intervals in bucket.items():
            compressed.extend(dict(name=name,atUs=b,span=b-a) for a,b in intervals)
    result=analyze(compressed,raw)
    result.update(metricCount=count,metricCounts=dict(names),nativeMetadata=meta,streamFullyParsedTwice=True,
                  retainedUnionIntervals=len(compressed)-len(anchors))
    return result

def analyze(records,raw):
    trial=raw['cameraRaster'];frames=[p for p in records if p['name']=='remains.camera.frame']
    ends=[p for p in records if p['name']=='remains.camera.end']
    assert len(frames)==960 and len(ends)==1
    assert [p['value']['frame'] for p in frames]==list(range(960)) and ends[0]['value']['frame']==960
    app_ids={p['value']['appId'] for p in frames+ends};assert len(app_ids)==1
    anchors=frames+ends
    assert all(anchors[i+1]['atUs']>anchors[i]['atUs'] for i in range(960))
    intervals=[(anchors[i]['atUs'],anchors[i+1]['atUs']) for i in range(960)]
    # Require native/us and getTimer/ms span clocks to agree over the full test;
    # individual getTimer readings are coarse, and anchor writes have small cost.
    duration=(intervals[-1][1]-intervals[0][0])/1000
    assert abs(duration-trial['timingElapsedMs'])<20,(duration,trial['timingElapsedMs'])
    spans=[]
    for p in records:
        if p.get('span',0)<=0 or not p['name'].startswith('.'):continue
        a,b=p['atUs']-p['span'],p['atUs']
        if b>intervals[0][0] and a<intervals[-1][1]:spans.append((a,b,p['name']))
    assert any(name=='.rend.screen' for a,b,name in spans)
    assert any(name=='.rend.paintbits' for a,b,name in spans)
    rows=[]
    for segment in range(8):
        window=trial['windows'][segment];idx=segment*120
        assert all(p['value']['segment']==segment and p['value']['condition']==window['condition'] for p in frames[idx:idx+120])
        start,end=intervals[idx][0],intervals[idx+119][1]
        by_name=defaultdict(list);by_category=defaultdict(list)
        for a,b,name in spans:
            if b<=start or a>=end:continue
            clipped=(max(a,start),min(b,end));by_name[name].append(clipped)
            category='render' if name.startswith('.rend.') else 'script' if name.startswith('.as.') else 'gc' if name.startswith(('.gc.','.memprotect.')) else 'other'
            by_category[category].append(clipped)
        rows.append(dict(index=segment,mode=window['mode'],frame=metric(window['framesMs']),nativeIntervalMs=(end-start)/1000,
            categoriesUnionPerFrameMs={k:union_length(v)/120000 for k,v in by_category.items()},
            nativeSpansUnionPerFrameMs={k:union_length(v)/120000 for k,v in sorted(by_name.items())}))
    arms={}
    for mode in sorted({row['mode'] for row in rows}):
        selected=[row for row in rows if row['mode']==mode]
        keys={k for row in selected for k in row['nativeSpansUnionPerFrameMs']}
        arms[mode]=dict(frameMeanMs=statistics.mean(row['frame']['mean'] for row in selected),
            nativeSpansUnionPerFrameMs={k:statistics.mean(row['nativeSpansUnionPerFrameMs'].get(k,0) for row in selected) for k in sorted(keys)},
            categoriesUnionPerFrameMs={k:statistics.mean(row['categoriesUnionPerFrameMs'].get(k,0) for row in selected) for k in ('render','script','gc','other')})
    return dict(complete=True,frames=960,nativeIntervalMs=duration,clockDifferenceMs=duration-trial['timingElapsedMs'],rows=rows,arms=arms,
        limits=['Native category/name intervals are individually unioned, including boundary-clipped spans; categories can overlap and must not be added.',
                'Paused native camera diagnostic with telemetry overhead; not optimized gameplay or enemy-free gameplay.',
                'Private desktop presentation/swap durations do not by themselves establish user-desktop GPU cost.'])
