import math,statistics
VERSION='camera-empty-native-tiles-1'
def metric(v):
    s=sorted(v);return dict(count=len(s),mean=statistics.mean(s),median=statistics.median(s),p95=s[math.ceil(.95*len(s))-1],maximum=s[-1])
def summarize(raw):
    assert raw['ok'] and raw['error'] is None and not raw['samples']
    assert raw['quietStartBeforeCombatWarmup'] and raw['nativeWindowRestored'] and not [e for e in raw['nativeWindowEvents'] if e['phase']>=2]
    t=raw['cameraRaster'];c=raw['cameraRasterCleanup'];cfg=raw['config'];g=t['emptyTiles']
    assert t['version']==VERSION and t['complete'] and t['passed'] and not t['errors']
    assert cfg['benchmark']=='scene' and cfg['drawControl']=='tilecrop' and cfg['noLighting'] and cfg['noWall'] and not cfg['vision']
    assert c==t['cleanup'] and c['restored'] and not c['errors'] and c['pendingOwnedBitmaps']==0
    assert g['complete'] and g['selected']>0 and len(g['tiles'])==g['selected'] and g['allocated']==g['disposed']==0 and not g['enabled']
    assert g['enableWrites']==g['restoreWrites'] and g['bytes']==0 and g['cleanup']==c['emptyTiles'] and g['cleanup']['restored'] and not g['cleanup']['remaining']
    assert t['pixelBitmapsCreated']==t['pixelBitmapsDisposed']==20 and t['pixelsValid'] and len(t['pixels'])==5 and t['cameraRouteFollowsInitialPlayer']
    for p in t['pixels']:
        assert p['passed'] and p['nativeRepeat']['equal'] and p['restore']['equal'] and p['empty']['maxRGB']<=2 and p['empty']['maxAlpha']==0 and p['visibleCoverage']['fraction']>=.15
    assert t['testFrameRate']==120 and t['testZoom']==1 and t['stage']['width']==1920 and t['stage']['height']==1080
    assert t['quietFixture']['nativeSimulationPaused'] is False and t['quietFixture']['hostileChecks']>=1920
    assert t['zeroRasterWork'] and not any(t['timingRasterDelta'].values())
    clock=t['timingStartAtMs'];all_dt=[];all_stamp=[];order=[0,4,1,5,2,6,3,7,7,3,6,2,5,1,4,0]
    assert len(t['windows'])==16 and len(t['framesMs'])==len(t['sampleAtMs'])==1920
    for i,(s,code) in enumerate(zip(t['windows'],order)):
        condition=code%4
        assert s['index']==i and s['code']==code and s['condition']==condition and s['empty']==(code>=4) and s['startAtMs']==clock
        assert len(s['framesMs'])==len(s['sampleAtMs'])==len(s['emptyVisible'])==120 and s['start']['pause'] is False and s['end']['pause'] is False
        assert all(v['selected']==g['selected'] and v['visible']>0 and v['enabled']==(code>=4) for v in s['emptyVisible'])
        for stamp,dt in zip(s['sampleAtMs'],s['framesMs']):assert stamp-clock==dt and dt>=0;clock=stamp
        assert s['endAtMs']==clock and all(s['worldVisible']) and all(s['windowVisible'])
        assert (len(set(s['vx']))>1)==(condition in [1,3]) and (len(set(s['vy']))>1)==(condition in [2,3])
        for pose,x,y in zip(s['gg'],s['vx'],s['vy']):assert 64<pose['x']+x<1856 and 128<pose['y']+y<1016
        all_dt+=s['framesMs'];all_stamp+=s['sampleAtMs']
    assert all_dt==t['framesMs'] and all_stamp==t['sampleAtMs'] and sum(all_dt)==t['timingElapsedMs']==clock-t['timingStartAtMs']
    arms={m:metric([v for s in t['windows'] if s['mode']==m for v in s['framesMs']]) for m in [a+'-'+b for a in ['native','empty'] for b in ['static','horizontal','vertical','combined']]}
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
    assert len(rows)==1920 and [r['index'] for r in rows]==list(range(1920))
    band_metrics={m:{k:metric([v[k] for v in rows if t['windows'][v['index']//120]['mode']==m]) for k in ['native','currentOtherStage','previousTail','betweenStage']} for m in arms}
    pairs=[]
    for i in range(0,16,2):
        a,b=t['windows'][i:i+2];n,o=(a,b) if not a['empty'] else (b,a)
        assert n['vx']==o['vx'] and n['vy']==o['vy']
        pairs.append(dict(axis=n['condition'],native=metric(n['framesMs']),empty=metric(o['framesMs']),nativeFirst=not a['empty']))
    return dict(version=VERSION,complete=True,diagnosticOnly=True,performanceEligible=False,gameplayAcceptance=False,deployed=False,arms=arms,pairs=pairs,emptyTiles=g,pixels=t['pixels'],cleanup=c,elapsedMs=sum(all_dt),timingBands=band_metrics,limits=t['limits'],playerVisibleAll1920Intervals=True)
