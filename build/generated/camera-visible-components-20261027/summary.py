import math,statistics
VERSION='camera-visible-components-1'
NAMES=['native','no-light','no-terrain','no-decor','no-actors','no-backdrop','no-gui','no-world']
AXES=['static','horizontal','vertical','combined']
def metric(v):
    s=sorted(v);return dict(count=len(s),mean=statistics.mean(s),median=statistics.median(s),p95=s[math.ceil(.95*len(s))-1],maximum=s[-1])
def summarize(raw):
    assert raw['ok'] and raw['error'] is None and not raw['samples']
    assert raw['quietStartBeforeCombatWarmup'] and raw['nativeWindowRestored'] and not [e for e in raw['nativeWindowEvents'] if e['phase']>=2]
    t=raw['cameraRaster'];c=raw['cameraRasterCleanup'];cfg=raw['config'];g=t['components']
    assert t['version']==VERSION and t['complete'] and t['passed'] and not t['errors']
    assert cfg['benchmark']=='scene' and cfg['drawControl']=='tilecrop' and cfg['noLighting'] and cfg['noWall'] and not cfg['vision']
    assert c==t['cleanup'] and c['restored'] and not c['errors'] and c['pendingOwnedBitmaps']==0 and c['componentsRestored']
    assert len(g['targets'])==14 and g['mode']==0 and g['exitChecks']==6720
    assert t['pixelBitmapsCreated']==t['pixelBitmapsDisposed']==80 and t['pixelsValid'] and len(t['pixels'])==5 and t['cameraRouteFollowsInitialPlayer']
    for p in t['pixels']:
        assert p['passed'] and p['nativeRepeat']['equal'] and p['visibleCoverage']['fraction']>=.15
        assert len(p['controls'])==7 and all(v['restore']['equal'] for v in p['controls'])
    assert t['testFrameRate']==120 and t['testZoom']==1 and t['stage']['width']==1920 and t['stage']['height']==1080
    assert t['quietFixture']['nativeSimulationPaused'] is False and t['quietFixture']['hostileChecks']>=6720
    assert t['zeroRasterWork'] and not any(t['timingRasterDelta'].values())
    clock=t['timingStartAtMs'];all_dt=[];all_stamp=[];order=[]
    for axis in range(4):
        for component in range(1,8):order.extend([axis,component*4+axis])
    order+=list(reversed(order))
    assert len(t['windows'])==112 and len(t['framesMs'])==len(t['sampleAtMs'])==6720
    for i,(s,code) in enumerate(zip(t['windows'],order)):
        condition=code%4;component=code//4
        assert s['index']==i and s['code']==code and s['condition']==condition and s['component']==component and s['startAtMs']==clock and s['exitChecks']==60
        assert len(s['framesMs'])==len(s['sampleAtMs'])==60 and s['start']['pause'] is False and s['end']['pause'] is False
        for stamp,dt in zip(s['sampleAtMs'],s['framesMs']):assert stamp-clock==dt and dt>=0;clock=stamp
        assert s['endAtMs']==clock and all(v==(component!=7) for v in s['worldVisible']) and all(s['windowVisible'])
        assert (len(set(s['vx']))>1)==(condition in [1,3]) and (len(set(s['vy']))>1)==(condition in [2,3])
        for pose,x,y in zip(s['gg'],s['vx'],s['vy']):assert 64<pose['x']+x<1856 and 128<pose['y']+y<1016
        all_dt+=s['framesMs'];all_stamp+=s['sampleAtMs']
    assert all_dt==t['framesMs'] and all_stamp==t['sampleAtMs'] and sum(all_dt)==t['timingElapsedMs']==clock-t['timingStartAtMs']
    arms={m:metric([v for s in t['windows'] if s['mode']==m for v in s['framesMs']]) for m in [a+'-'+b for a in NAMES for b in AXES]}
    bands=raw['quietBands'];rows=[]
    assert bands and all(b['tail'] is not None and b['nextEnter'] is not None for b in bands)
    for i,b in enumerate(bands):
        assert b['enter']<=b['nativeStart']<=b['nativeEnd']<=b['mods100']<=b['mods200']<=b['probeStart']<=b['probeEnd']<=b['tail']<=b['nextEnter']
        if b['after']==b['before']:continue
        assert i>0 and b['after']==b['before']+1
        prev=bands[i-1];j=b['before'];stamp=t['sampleAtMs'][j];prior=t['sampleAtMs'][j-1] if j else t['timingStartAtMs']
        assert prev['probeStart']<=prior<=prev['probeEnd'] and b['probeStart']<=stamp<=b['probeEnd'] and prev['nextEnter']==b['enter']
        v=dict(index=j,native=b['nativeEnd']-b['nativeStart'],currentOtherStage=stamp-b['enter']-(b['nativeEnd']-b['nativeStart']),previousTail=prev['tail']-prior,betweenStage=b['enter']-prev['tail'])
        assert sum(v[k] for k in ['native','currentOtherStage','previousTail','betweenStage'])==t['framesMs'][j];rows.append(v)
    assert len(rows)==6720 and [r['index'] for r in rows]==list(range(6720))
    band_metrics={m:{k:metric([v[k] for v in rows if t['windows'][v['index']//60]['mode']==m]) for k in ['native','currentOtherStage','previousTail','betweenStage']} for m in arms}
    pairs=[]
    for i in range(0,112,2):
        a,b=t['windows'][i:i+2];native,control=(a,b) if a['component']==0 else (b,a)
        assert native['component']==0 and control['component']!=0 and a['condition']==b['condition']
        assert native['vx']==control['vx'] and native['vy']==control['vy']
        pairs.append(dict(axis=AXES[a['condition']],component=NAMES[control['component']],native=metric(native['framesMs']),control=metric(control['framesMs']),nativeFirst=a['component']==0))
    return dict(version=VERSION,complete=True,diagnosticOnly=True,performanceEligible=False,gameplayAcceptance=False,deployed=False,arms=arms,pairs=pairs,components=g,pixels=t['pixels'],cleanup=c,elapsedMs=sum(all_dt),timingBands=band_metrics,limits=t['limits'],playerCoordinatesInsideAll6720Intervals=True)
