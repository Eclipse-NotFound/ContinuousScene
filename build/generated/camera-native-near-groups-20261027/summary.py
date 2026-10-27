import math,statistics
VERSION='camera-native-near-groups-1'
def metric(v):
    s=sorted(v);return dict(count=len(s),mean=statistics.mean(s),median=statistics.median(s),p95=s[math.ceil(.95*len(s))-1],maximum=s[-1])
def summarize(raw):
    assert raw['ok'] and raw['error'] is None and not raw['samples']
    assert raw['quietStartBeforeCombatWarmup'] and raw['nativeWindowRestored'] and not [e for e in raw['nativeWindowEvents'] if e['phase']>=2]
    t=raw['cameraRaster'];c=raw['cameraRasterCleanup'];cfg=raw['config'];g=t['groupCache']
    assert t['version']==VERSION and t['complete'] and t['passed'] and not t['errors']
    assert cfg['benchmark']=='scene' and cfg['drawControl']=='tilecrop' and cfg['noLighting'] and cfg['noWall'] and not cfg['vision']
    assert c==t['cleanup'] and c['restored'] and not c['errors'] and c['pendingOwnedBitmaps']==0
    assert g['cleanup']==c['groupCache'] and c['groupCache']['restored'] and c['groupCache']['pendingHolders']==0 and not c['groupCache']['errors']
    assert g['writes']==g['restores'] and g['selected']>=2 and g['groups']>0 and not g['enabled'] and g['estimatedBytes']<=64*1024**2
    assert t['pixelBitmapsCreated']==t['pixelBitmapsDisposed']==20 and t['pixelsValid'] and len(t['pixels'])==5
    for p in t['pixels']:
        assert p['passed'] and p['nativeRepeat']['equal'] and p['restore']['equal'] and p['cached']['maxRGB']<=2 and p['cached']['maxAlpha']==0
    assert t['testFrameRate']==120 and t['testZoom']==1 and t['stage']['width']==1280 and t['stage']['height']==720
    assert t['quietFixture']['nativeSimulationPaused'] is False and t['quietFixture']['hostileChecks']>=1920
    assert t['zeroRasterWork'] and not any(t['timingRasterDelta'].values())
    clock=t['timingStartAtMs'];all_dt=[];all_stamp=[];order=[0,4,1,5,2,6,3,7,7,3,6,2,5,1,4,0]
    assert len(t['windows'])==16 and len(t['framesMs'])==len(t['sampleAtMs'])==1920
    for i,(s,code) in enumerate(zip(t['windows'],order)):
        condition=code%4
        assert s['index']==i and s['code']==code and s['condition']==condition and s['cached']==(code>=4) and s['startAtMs']==clock
        assert len(s['framesMs'])==len(s['sampleAtMs'])==120 and s['start']['pause'] is False and s['end']['pause'] is False
        for stamp,dt in zip(s['sampleAtMs'],s['framesMs']):assert stamp-clock==dt and dt>=0;clock=stamp
        assert s['endAtMs']==clock and all(s['worldVisible']) and all(s['windowVisible'])
        assert (len(set(s['vx']))>1)==(condition in [1,3]) and (len(set(s['vy']))>1)==(condition in [2,3])
        all_dt+=s['framesMs'];all_stamp+=s['sampleAtMs']
    assert all_dt==t['framesMs'] and all_stamp==t['sampleAtMs'] and sum(all_dt)==t['timingElapsedMs']==clock-t['timingStartAtMs']
    arms={m:metric([v for s in t['windows'] if s['mode']==m for v in s['framesMs']]) for m in [a+'-'+b for a in ['native','cached'] for b in ['static','horizontal','vertical','combined']]}
    return dict(version=VERSION,complete=True,diagnosticOnly=True,performanceEligible=False,gameplayAcceptance=False,deployed=False,
        arms=arms,pairs=[],groupCache=g,pixels=t['pixels'],cleanup=c,elapsedMs=sum(all_dt),limits=t['limits'])
