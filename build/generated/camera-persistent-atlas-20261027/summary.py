import math,statistics
VERSION='camera-persistent-atlas-1'
def metric(v):
    a=sorted(v);return dict(count=len(a),mean=statistics.mean(a),median=statistics.median(a),p95=a[math.ceil(.95*len(a))-1],maximum=a[-1])
def summarize(raw):
    assert raw['ok'] and raw['error'] is None and not raw['samples']
    assert raw['quietStartBeforeCombatWarmup'] and raw['nativeWindowRestored'] and not [e for e in raw['nativeWindowEvents'] if e['phase']>=2]
    t=raw['cameraRaster'];c=raw['cameraRasterCleanup'];cfg=raw['config']
    assert t['version']==VERSION and t['complete'] and t['passed'] and not t['errors']
    assert cfg['benchmark']=='scene' and cfg['drawControl']=='tilecrop' and cfg['noLighting'] and cfg['noWall'] and not cfg['vision']
    assert t['cameraRouteFollowsInitialPlayer'] and t['stage']==dict(width=1920,height=1080,quality='HIGH') and t['testZoom']==1 and t['testFrameRate']==120
    assert c==t['cleanup'] and c['restored'] and not c['errors'] and c['pendingOwnedBitmaps']==0
    for kind in ['classic','persistent']:
        end=c['atlas'][kind];initial=t['atlasPrepared'][kind]
        assert initial['allocations']==initial['ownedBitmaps']==32 and initial['pixelStorageBytes']==200*1024**2
        assert end['allocations']==end['disposals']==32 and end['ownedBitmaps']==end['pixelStorageBytes']==end['attached']==end['pendingHidden']==end['poolPages']==0
    assert t['pixelBitmapsCreated']==t['pixelBitmapsDisposed']==30 and len(t['pixels'])==5 and t['pixelsValid']
    for p in t['pixels']:
        assert p['passed'] and p['nativeRepeat']['equal'] and p['visibleCoverage']['fraction']>=.15
        assert len(p['variants'])==2
        for v in p['variants']:assert v['state']['presented'] and v['changed']['maxRGB']<=2 and v['changed']['maxAlpha']==0 and v['restore']['equal']
    assert t['quietFixture']['nativeSimulationPaused'] is False and t['quietFixture']['hostileChecks']>=2880
    assert t['zeroRasterWork'] and not any(t['timingRasterDelta'].values())
    order=[]
    for a in range(4):order.extend([a,a+4,a+8])
    order+=list(reversed(order));clock=t['timingStartAtMs'];all_dt=[];all_stamp=[]
    assert len(t['windows'])==24 and len(t['framesMs'])==len(t['sampleAtMs'])==2880
    for i,(s,code) in enumerate(zip(t['windows'],order)):
        condition=code%4;variant=code//4
        assert s['index']==i and s['code']==code and s['condition']==condition and s['variant']==variant and s['startAtMs']==clock
        assert len(s['framesMs'])==len(s['sampleAtMs'])==len(s['atlas'])==120
        assert s['start']['pause'] is False and s['end']['pause'] is False and all(s['worldVisible']) and all(s['windowVisible'])
        for dt,stamp in zip(s['framesMs'],s['sampleAtMs']):assert stamp-clock==dt and dt>=0;clock=stamp
        for state in s['atlas']:
            assert state['classic']['presented']==(variant==1) and state['persistent']['presented']==(variant==2)
            for kind in ['classic','persistent']:assert state[kind]['allocations']==32 and state[kind]['ownedBitmaps']==32
            if variant:
                active=state['classic' if variant==1 else 'persistent']
                assert active['fallbackReason']=='' and active['livePages']>0 and active['pendingHidden']>0
        assert s['endAtMs']==clock and (len(set(s['vx']))>1)==(condition in [1,3]) and (len(set(s['vy']))>1)==(condition in [2,3])
        for p,x,y in zip(s['gg'],s['vx'],s['vy']):assert 64<p['x']+x<1856 and 128<p['y']+y<1016
        all_dt+=s['framesMs'];all_stamp+=s['sampleAtMs']
    assert all_dt==t['framesMs'] and all_stamp==t['sampleAtMs'] and sum(all_dt)==t['timingElapsedMs']==clock-t['timingStartAtMs']
    names=[a+'-'+b for a in ['native','classic','persistent'] for b in ['static','horizontal','vertical','combined']]
    arms={m:metric([dt for s in t['windows'] if s['mode']==m for dt in s['framesMs']]) for m in names}
    bands=raw['quietBands'];rows=[]
    for i,b in enumerate(bands):
        assert b['enter']<=b['nativeStart']<=b['nativeEnd']<=b['mods100']<=b['mods200']<=b['probeStart']<=b['probeEnd']<=b['tail']<=b['nextEnter']
        if b['after']==b['before']:continue
        assert i>0 and b['after']==b['before']+1
        prev=bands[i-1];j=b['before'];stamp=t['sampleAtMs'][j];prior=t['sampleAtMs'][j-1] if j else t['timingStartAtMs']
        assert prev['probeStart']<=prior<=prev['probeEnd'] and b['probeStart']<=stamp<=b['probeEnd'] and prev['nextEnter']==b['enter']
        v=dict(index=j,native=b['nativeEnd']-b['nativeStart'],currentOtherStage=stamp-b['enter']-(b['nativeEnd']-b['nativeStart']),previousTail=prev['tail']-prior,betweenStage=b['enter']-prev['tail'])
        assert sum(v[k] for k in ['native','currentOtherStage','previousTail','betweenStage'])==t['framesMs'][j];rows.append(v)
    assert len(rows)==2880 and [v['index'] for v in rows]==list(range(2880))
    band_metrics={m:{k:metric([v[k] for v in rows if t['windows'][v['index']//120]['mode']==m]) for k in ['native','currentOtherStage','previousTail','betweenStage']} for m in names}
    pairs=[]
    for i in range(0,24,3):
        group=sorted(t['windows'][i:i+3],key=lambda s:s['variant']);n,a,p=group
        assert n['vx']==a['vx']==p['vx'] and n['vy']==a['vy']==p['vy']
        pairs.append(dict(axis=n['condition'],native=metric(n['framesMs']),classic=metric(a['framesMs']),persistent=metric(p['framesMs']),nativeFirst=t['windows'][i]['variant']==0))
    return dict(version=VERSION,complete=True,diagnosticOnly=True,performanceEligible=False,gameplayAcceptance=False,deployed=False,
        arms=arms,pairs=pairs,timingBands=band_metrics,cleanup=c,atlasPrepareMs=t['atlasPrepareMs'],pixels=t['pixels'],elapsedMs=sum(all_dt),limits=t['limits'])
