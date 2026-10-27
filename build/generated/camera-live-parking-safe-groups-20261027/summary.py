import math,statistics
VERSION='camera-live-parking-safe-groups-1'
def metric(v):
    a=sorted(v);return dict(count=len(a),mean=statistics.mean(a),median=statistics.median(a),p95=a[math.ceil(.95*len(a))-1],maximum=a[-1])
def summarize(raw):
    assert raw['ok'] and raw['error'] is None and raw['nativeWindowRestored']
    cfg=raw['config'];assert cfg['drawControl']=='rcnative' and not cfg['presentationCheck'] and cfg['noLighting'] and cfg['noWall'] and not cfg['vision']
    t=raw['farParking'];clean=raw['farParkingCleanup'];v=raw['farParkingVerification']
    assert t['version']==VERSION and t['selected']>0 and t['maximumHeld']>0
    assert t['groups']>0 and t['groupBoundsQueries']>0 and t['groupPreparations']>0
    assert clean==t['cleanup'] and clean['restored'] and clean['pendingOwnedRoots']==0 and not clean['errors']
    assert v['afterTiming'] and v['restored'] and v['nativeRemoval']['nativeRemoved'] and v['nativeRemoval']['notResurrected']
    assert all(v['pixels'][k]['passed'] for k in ['changed','restored'])
    assert all(a['ok'] for a in raw['assertions'])
    rows=raw['samples'];assert len(rows)==20
    clock=raw['continuousSampling']['startedAtMs'];begin=clock;deltas=[];out=[]
    for i,row in enumerate(rows):
        on=i%4 in (1,2);xs=[];ys=[]
        assert len(row['frames'])==len(row['continuousFramesMs'])==len(row['sampleAtMs'])==len(row['farParking'])==60
        assert row['empty']==0 and row['nativeInputMotion']['movementRequested']
        for stamp,dt,state in zip(row['sampleAtMs'],row['continuousFramesMs'],row['farParking']):
            assert stamp-clock==dt and dt>=0;clock=stamp;deltas.append(dt)
            assert state['enabled'] is on and state['windowVisible']
            if not on:assert state['held']==0
            xs.append(state['vx']);ys.append(state['vy'])
        out.append(dict(index=i,enabled=on,frame=metric(row['continuousFramesMs']),work=metric([s['workMs'] for s in row['farParking']]),
            heldRange=[min(s['held'] for s in row['farParking']),max(s['held'] for s in row['farParking'])],
            xRange=[min(xs),max(xs)],yRange=[min(ys),max(ys)],playerShots=row['playerShotFrames'],enemyShots=row['enemyShotFrames']))
    assert sum(deltas)==clock-begin and len(deltas)==1200
    assert sum(r['playerShotFrames'] for r in rows)>0 and sum(r['enemyShotFrames'] for r in rows)>0
    arms={str(on):metric([dt for i,row in enumerate(rows) if (i%4 in (1,2)) is on for dt in row['continuousFramesMs']]) for on in (False,True)}
    pairs=[dict(nativeIndex=i+a,candidateIndex=i+b,deltaMs=out[i+b]['frame']['mean']-out[i+a]['frame']['mean']) for i in range(0,20,4) for a,b in [(0,1),(3,2)]]
    return dict(version=VERSION,complete=True,diagnosticOnly=True,performanceEligible=False,gameplayAcceptance=False,deployed=False,
        arms=arms,pairs=pairs,rows=out,elapsedMs=sum(deltas),parking=t,verification=v,cleanup=clean,
        limits=['One live native sprint/combat route; private visible desktop, not physical presented-frame measurement.',
                'Only chain-owned Box/Bonus roots; new roots remain native. Actors/projectiles not parked.',
                'Native removal exercised after timing; lifecycle, pixel and startup work excluded from timing.',
                'All 1200 intervals and transition/management work retained; no global near-original acceptance.'])
