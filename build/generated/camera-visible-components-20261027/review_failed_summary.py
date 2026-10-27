"""Post-hoc diagnostic review. Does not turn the failed original gate green.

EXIT_FRAME counts do not identify physical presentations and were not sampled
per interval in this recipe. Preserve that limitation; verify the retained full
ENTER_FRAME clock separately without pretending that the counter gate passed.
"""
import math,statistics
NAMES=['native','no-light','no-terrain','no-decor','no-actors','no-backdrop','no-gui','no-world']
AXES=['static','horizontal','vertical','combined']
def metric(v):
    s=sorted(v);return dict(count=len(s),mean=statistics.mean(s),median=statistics.median(s),p95=s[math.ceil(.95*len(s))-1],maximum=s[-1])
def review(raw):
    t=raw['cameraRaster'];c=raw['cameraRasterCleanup'];g=t['components'];cfg=raw['config']
    assert raw['ok'] and raw['error'] is None and not raw['samples'] and t['complete'] and t['passed'] and not t['errors']
    assert raw['quietStartBeforeCombatWarmup'] and raw['nativeWindowRestored'] and not [e for e in raw['nativeWindowEvents'] if e['phase']>=2]
    assert t['version']=='camera-visible-components-1' and t['cameraRouteFollowsInitialPlayer']
    assert cfg['benchmark']=='scene' and cfg['drawControl']=='tilecrop' and cfg['noLighting'] and cfg['noWall'] and not cfg['vision']
    assert c==t['cleanup'] and c['restored'] and c['componentsRestored'] and not c['errors'] and c['pendingOwnedBitmaps']==0
    assert g['mode']==0 and len(g['targets'])==14
    assert t['pixelBitmapsCreated']==t['pixelBitmapsDisposed']==80 and len(t['pixels'])==5 and t['pixelsValid']
    for p in t['pixels']:
        assert p['passed'] and p['nativeRepeat']['equal'] and p['visibleCoverage']['fraction']>=.15
        assert len(p['controls'])==7 and all(q['restore']['equal'] for q in p['controls'])
    assert t['stage']==dict(width=1920,height=1080,quality='HIGH') and t['testZoom']==1 and t['testFrameRate']==120
    assert t['quietFixture']['nativeSimulationPaused'] is False and t['quietFixture']['hostileChecks']>=6720
    assert t['zeroRasterWork'] and not any(t['timingRasterDelta'].values())
    order=[]
    for axis in range(4):
        for component in range(1,8):order.extend([axis,component*4+axis])
    order+=list(reversed(order))
    assert len(t['windows'])==112 and len(t['framesMs'])==len(t['sampleAtMs'])==6720
    # Exact event multiplicity from this run; no claim of one check per frame.
    assert sum(w['exitChecks'] for w in t['windows'])==g['exitChecks']==15738
    assert min(w['exitChecks'] for w in t['windows'])==116 and max(w['exitChecks'] for w in t['windows'])==190
    clock=t['timingStartAtMs'];dt_all=[];stamp_all=[]
    for i,(s,code) in enumerate(zip(t['windows'],order)):
        axis=code%4;component=code//4
        assert s['index']==i and s['code']==code and s['condition']==axis and s['component']==component
        assert s['mode']==NAMES[component]+'-'+AXES[axis] and s['startAtMs']==clock
        assert len(s['framesMs'])==len(s['sampleAtMs'])==len(s['vx'])==len(s['vy'])==len(s['gg'])==60
        assert s['start']['pause'] is False and s['end']['pause'] is False
        for dt,stamp in zip(s['framesMs'],s['sampleAtMs']):assert stamp-clock==dt and dt>=0;clock=stamp
        assert clock==s['endAtMs'] and all(s['windowVisible']) and all(v==(component!=7) for v in s['worldVisible'])
        assert (len(set(s['vx']))>1)==(axis in [1,3]) and (len(set(s['vy']))>1)==(axis in [2,3])
        for p,x,y in zip(s['gg'],s['vx'],s['vy']):assert 64<p['x']+x<1856 and 128<p['y']+y<1016
        dt_all+=s['framesMs'];stamp_all+=s['sampleAtMs']
    assert dt_all==t['framesMs'] and stamp_all==t['sampleAtMs']
    assert sum(dt_all)==t['timingElapsedMs']==clock-t['timingStartAtMs']==155823 and clock==t['timingEndAtMs']
    bands=raw['quietBands'];rows=[]
    for i,b in enumerate(bands):
        assert b['enter']<=b['nativeStart']<=b['nativeEnd']<=b['mods100']<=b['mods200']<=b['probeStart']<=b['probeEnd']<=b['tail']<=b['nextEnter']
        if b['after']==b['before']:continue
        assert i>0 and b['after']==b['before']+1
        prev=bands[i-1];j=b['before'];stamp=t['sampleAtMs'][j];prior=t['sampleAtMs'][j-1] if j else t['timingStartAtMs']
        assert prev['probeStart']<=prior<=prev['probeEnd'] and b['probeStart']<=stamp<=b['probeEnd'] and prev['nextEnter']==b['enter']
        row=dict(index=j,native=b['nativeEnd']-b['nativeStart'],currentOtherStage=stamp-b['enter']-(b['nativeEnd']-b['nativeStart']),previousTail=prev['tail']-prior,betweenStage=b['enter']-prev['tail'])
        assert sum(row[k] for k in ['native','currentOtherStage','previousTail','betweenStage'])==t['framesMs'][j];rows.append(row)
    assert len(rows)==6720 and [r['index'] for r in rows]==list(range(6720))
    arms={m:metric([dt for s in t['windows'] if s['mode']==m for dt in s['framesMs']]) for m in [n+'-'+a for n in NAMES for a in AXES]}
    band_metrics={m:{k:metric([v[k] for v in rows if t['windows'][v['index']//60]['mode']==m]) for k in ['native','currentOtherStage','previousTail','betweenStage']} for m in arms}
    pairs=[]
    for i in range(0,112,2):
        a,b=t['windows'][i:i+2];n,c=(a,b) if a['component']==0 else (b,a)
        assert n['component']==0 and c['component']!=0 and n['condition']==c['condition'] and n['vx']==c['vx'] and n['vy']==c['vy']
        pairs.append(dict(component=NAMES[c['component']],axis=AXES[n['condition']],native=metric(n['framesMs']),control=metric(c['framesMs']),nativeFirst=a['component']==0))
    return dict(originalSummaryGatePassed=False,completeIntervalsVerified=True,frames=6720,exitCallbacks=15738,
        perIntervalExitCoverageUnknown=True,physicalPresentationTiming=False,validPerformanceRun=False,gameplayAcceptance=False,deployed=False,
        arms=arms,pairs=pairs,timingBands=band_metrics,components=g,
        limitation='Original gate incorrectly expected EXIT_FRAME once per interval. Callback multiplicity is retained, not reclassified as frames. Visibility was checked during apply and 15738 callbacks, but no per-interval callback IDs exist. Diagnostic leads only.')
