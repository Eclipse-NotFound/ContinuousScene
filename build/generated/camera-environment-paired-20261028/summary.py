"""Validate every same-instance interval, branch selection, pixel and cleanup."""
import math,statistics
VERSION='camera-environment-paired-1'
ORDER=[0,4,1,5,2,6,3,7,7,3,6,2,5,1,4,0]
NAMES=['native-static','native-horizontal','native-vertical','native-combined',
       'cached-static','cached-horizontal','cached-vertical','cached-combined']

def metric(values):
    a=sorted(values)
    return dict(count=len(a),mean=statistics.mean(a),median=statistics.median(a),p95=a[math.ceil(.95*len(a))-1],
        maximum=a[-1],over33=sum(v>33 for v in a),over50=sum(v>50 for v in a),over100=sum(v>100 for v in a))

def summarize(raw):
    assert raw['ok'] and raw['error'] is None and not raw['samples']
    assert raw['quietStartBeforeCombatWarmup'] and raw['nativeWindowRestored']
    assert not [e for e in raw['nativeWindowEvents'] if e['phase']>=2]
    t=raw['cameraRaster'];clean=raw['cameraRasterCleanup'];cfg=raw['config']
    assert t['version']==VERSION and t['complete'] and t['passed'] and not t['errors']
    assert cfg['benchmark']=='scene' and cfg['drawControl']=='tilecrop' and cfg['presentationCheck']
    assert cfg['noLighting'] and cfg['noWall'] and not cfg['vision']
    assert clean==t['cleanup'] and clean['restored'] and not clean['errors'] and clean['pendingOwnedBitmaps']==0
    assert clean['fixturePopulationNotRestored'] and clean['environmentSwitchRestored'] and clean['cameraHookRemoved']
    assert t['nativeSchedules']==1921 and t['nativeCaptures']==1920 and t['helperTimedCalcCalls']==0 and t['measurementFrames']==1920
    assert t['pixelBitmapsCreated']==t['pixelBitmapsDisposed']==20 and t['pixelsValid'] and len(t['pixels'])==5
    for p in t['pixels']:
        assert p['passed'] and p['visibleCoverage']['fraction']>=.30
        for key in ['nativeRepeat','cachedCompare','restoredCompare']:
            c=p[key];assert c['equal'] and c['differentPixels']==c['maxRGB']==c['maxAlpha']==0
    for key,cache in [('nativeEnvironmentChecks',False),('environmentChecks',True)]:
        c=t[key]
        assert c['passed'] and c['sceneLarge'] and c['cachePresent'] is cache
        assert c['mapEntryRestored'] and c['originRestored'] and c['environmentRestored']
        assert len(c['cases'])==150 and c['fieldsChecked']==3000 and all(r['matched'] for r in c['cases'])
        assert {'changed-origin-x','changed-origin-y','restored-origin','replaced-entry-same-key','restored-entry-same-key'}<=set(r['label'] for r in c['cases'])
    assert t['nativeEnvironmentChecks']['cases']==t['environmentChecks']['cases']
    assert t['testFrameRate']==120 and t['testZoom']==1 and t['stage']['width']==1280 and t['stage']['height']==720
    assert t['quietFixture']['nativeSimulationPaused'] is False
    assert t['quietFixture']['hostileChecks']>=1920 and t['simulationTicks']>=1920 and t['stabilizationFrames']==60
    assert t['zeroRasterWork'] and not any(t['timingRasterDelta'].values()) and t['roomAxis']['continuous']
    assert t['referenceSite']['spawnCalls']==1 and t['referenceSite']['selected'] and not t['referenceSite']['terrainEdited']
    assert t['fogHistory']['resetCells']==raw['world']['width']*raw['world']['height']
    assert all(c['visi']==c['target']==0 for c in t['fogHistory']['afterReset']['localCells'])
    assert len(t['fogTimingStart']['localCells'])==len(t['fogTimingEnd']['localCells'])==1200
    clock=t['timingStartAtMs'];all_dt=[];all_stamp=[];rows=[]
    assert len(t['windows'])==16 and len(t['framesMs'])==len(t['sampleAtMs'])==1920
    for i,(s,condition) in enumerate(zip(t['windows'],ORDER)):
        axis=condition%4;cached=condition>=4
        assert s['index']==i and s['condition']==condition and s['axis']==axis and s['cacheEnabled'] is cached and s['mode']==NAMES[condition]
        assert s['cacheModes']==[cached]*120 and s['startAtMs']==clock and len(s['framesMs'])==len(s['sampleAtMs'])==120
        assert s['start']['pause'] is False and s['end']['pause'] is False
        for stamp,dt in zip(s['sampleAtMs'],s['framesMs']):assert stamp-clock==dt and dt>=0;clock=stamp
        assert s['endAtMs']==clock and all(s['worldVisible']) and all(s['windowVisible'])
        assert (len(set(s['vx']))>1) is (axis in [1,3]) and (len(set(s['vy']))>1) is (axis in [2,3])
        assert s['copiesStart']==s['copiesEnd']==s['allocatedStart']==s['allocatedEnd']==0
        assert all(v==t['timingStart']['scene'] for v in s['scene'])
        assert all(v==t['windows'][0]['gg'][0] for v in s['gg'])
        all_dt+=s['framesMs'];all_stamp+=s['sampleAtMs']
        rows.append(dict(index=i,condition=condition,mode=s['mode'],frame=metric(s['framesMs']),work=metric(s['workMs'])))
    assert all_dt==t['framesMs'] and all_stamp==t['sampleAtMs'] and sum(all_dt)==t['timingElapsedMs']==clock-t['timingStartAtMs'] and clock==t['timingEndAtMs']
    pairs=[]
    for a,b in [(0,1),(15,14),(2,3),(13,12),(4,5),(11,10),(6,7),(9,8)]:
        left,right=t['windows'][a],t['windows'][b]
        assert left['axis']==right['axis'] and not left['cacheEnabled'] and right['cacheEnabled']
        for key in ['vx','vy','cameraX','cameraY','gg','scene']:assert left[key]==right[key],(a,b,key)
        pairs.append(dict(axis=left['axis'],nativeIndex=a,cachedIndex=b,native=metric(left['framesMs']),cached=metric(right['framesMs'])))
    bands=raw['quietBands'];band_rows=[]
    assert bands and all(b['tail'] is not None and b['nextEnter'] is not None for b in bands)
    for i,b in enumerate(bands):
        assert b['enter']<=b['nativeStart']<=b['nativeEnd']<=b['mods100']<=b['mods200']<=b['probeStart']<=b['probeEnd']<=b['tail']<=b['nextEnter']
        if b['after']==b['before']:continue
        assert i>0 and b['after']==b['before']+1
        prev=bands[i-1];j=b['before'];stamp=t['sampleAtMs'][j]
        prior=t['sampleAtMs'][j-1] if j else t['timingStartAtMs']
        assert prev['probeStart']<=prior<=prev['probeEnd'] and b['probeStart']<=stamp<=b['probeEnd'] and prev['nextEnter']==b['enter']
        v=dict(index=j,native=b['nativeEnd']-b['nativeStart'],currentOtherStage=stamp-b['enter']-(b['nativeEnd']-b['nativeStart']),
            previousTail=prev['tail']-prior,betweenStage=b['enter']-prev['tail'])
        assert sum(v[k] for k in ['native','currentOtherStage','previousTail','betweenStage'])==t['framesMs'][j]
        band_rows.append(v)
    assert len(band_rows)==1920 and [v['index'] for v in band_rows]==list(range(1920))
    timing_bands={name:{k:metric([v[k] for v in band_rows if t['windows'][v['index']//120]['mode']==name])
        for k in ['native','currentOtherStage','previousTail','betweenStage']} for name in NAMES}
    arms={name:metric([dt for s in t['windows'] if s['mode']==name for dt in s['framesMs']]) for name in NAMES}
    moving={name:metric([dt for s in t['windows'] if s['moving'] and s['cacheEnabled'] is cached for dt in s['framesMs']]) for name,cached in [('native',False),('cached',True)]}
    return dict(version=VERSION,complete=True,diagnosticOnly=True,performanceEligible=False,gameplayAcceptance=False,deployed=False,
        rows=rows,arms=arms,pairs=pairs,moving=moving,timingBands=timing_bands,elapsedMs=sum(all_dt),pixels=t['pixels'],cleanup=clean,
        nativeEnvironmentChecks=t['nativeEnvironmentChecks'],environmentChecks=t['environmentChecks'],nativeCameraScheduling={k:t[k] for k in ['nativeSchedules','nativeCaptures','helperTimedCalcCalls']},
        limits=t['limits'],bandLimit='Inclusive Stage bands and mixed between-Stage time; no exclusive GPU or function timing.')
