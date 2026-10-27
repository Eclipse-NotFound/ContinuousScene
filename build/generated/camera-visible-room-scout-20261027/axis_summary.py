import math,statistics
VERSION='camera-visible-room-scout-1'
def metric(v):
    a=sorted(v);return dict(count=len(a),mean=statistics.mean(a),median=statistics.median(a),p95=a[math.ceil(.95*len(a))-1],maximum=a[-1])
def summarize(raw):
    assert raw['ok'] and raw['error'] is None and not raw['samples']
    assert raw['quietStartBeforeCombatWarmup'] and raw['nativeWindowRestored']
    assert not [e for e in raw['nativeWindowEvents'] if e['phase']>=2]
    t=raw['cameraRaster'];clean=raw['cameraRasterCleanup'];cfg=raw['config']
    assert t['version']==VERSION and t['complete'] and t['passed'] and not t['errors']
    assert cfg['drawControl']=='tilecrop' and cfg['presentationCheck'] and cfg['noLighting'] and cfg['noWall'] and not cfg['vision']
    assert clean==t['cleanup'] and clean['restored'] and not clean['errors'] and clean['pendingOwnedBitmaps']==0 and clean['fixturePopulationNotRestored']
    assert t['pixelBitmapsCreated']==t['pixelBitmapsDisposed']==10 and t['pixelsValid'] and len(t['pixels'])==5
    for p in t['pixels']:
        c=p['nativeRepeat'];assert p['passed'] and c['equal'] and c['differentPixels']==c['maxRGB']==c['maxAlpha']==0
    assert t['testFrameRate']==120 and t['testZoom']==1 and t['stage']['width']==1280 and t['stage']['height']==720
    assert t['quietFixture']['nativeSimulationPaused'] is False
    assert t['quietFixture']['hostileChecks']>=960 and t['simulationTicks']>=960 and t['stabilizationFrames']==60
    assert t['zeroRasterWork'] and not any(t['timingRasterDelta'].values())
    assert t['roomAxis']['continuous'] is (cfg['benchmark']=='scene')
    assert t['referenceSite']['spawnCalls']==1 and t['referenceSite']['selected'] and not t['referenceSite']['terrainEdited']
    assert all(p['visibleCoverage']['fraction']>=.30 for p in t['pixels'])
    clock=t['timingStartAtMs'];all_dt=[];all_stamp=[];out=[]
    assert len(t['windows'])==8 and len(t['framesMs'])==len(t['sampleAtMs'])==960
    for i,(s,condition) in enumerate(zip(t['windows'],[0,1,2,3,3,2,1,0])):
        assert s['index']==i and s['condition']==condition and s['startAtMs']==clock and len(s['framesMs'])==len(s['sampleAtMs'])==120
        assert s['start']['pause'] is False and s['end']['pause'] is False
        for stamp,dt in zip(s['sampleAtMs'],s['framesMs']):assert stamp-clock==dt and dt>=0;clock=stamp
        assert s['endAtMs']==clock and all(s['worldVisible']) and all(s['windowVisible'])
        assert (len(set(s['vx']))>1) is (condition in [1,3]) and (len(set(s['vy']))>1) is (condition in [2,3])
        assert s['copiesStart']==s['copiesEnd']==s['allocatedStart']==s['allocatedEnd']==0
        all_dt+=s['framesMs'];all_stamp+=s['sampleAtMs']
        out.append(dict(index=i,condition=condition,mode=s['mode'],frame=metric(s['framesMs']),work=metric(s['workMs']),xRange=[min(s['vx']),max(s['vx'])],yRange=[min(s['vy']),max(s['vy'])]))
    assert all_dt==t['framesMs'] and all_stamp==t['sampleAtMs'] and sum(all_dt)==t['timingElapsedMs']==clock-t['timingStartAtMs'] and clock==t['timingEndAtMs']
    arms={name:metric([dt for s in t['windows'] if s['mode']==name for dt in s['framesMs']]) for name in ['native-static','native-horizontal','native-vertical','native-combined']}
    return dict(version=VERSION,complete=True,diagnosticOnly=True,performanceEligible=False,gameplayAcceptance=False,deployed=False,
        rows=out,arms=arms,pairs=[],roomAxis=t['roomAxis'],quietFixture=t['quietFixture'],world=raw['world'],
        referenceSite=t['referenceSite'],
        elapsedMs=sum(all_dt),pixels=t['pixels'],cleanup=clean,limits=t['limits'])
