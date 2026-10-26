def summarize(raw):
    assert raw['ok'] and raw['error'] is None and not raw['samples']
    cfg=raw['config'];assert cfg['drawControl']=='tilecrop' and cfg['presentationCheck']
    assert cfg['noLighting'] and cfg['noWall'] and not cfg['vision']
    trial,cleanup=raw['cameraRaster'],raw['cameraRasterCleanup']
    assert trial['version']==VERSION and trial['complete'] and trial['passed'] and not trial['errors']
    assert trial['nativeMenuChildren'] and all(x['className']!='visMainMenu' for x in trial['nativeMenuChildren'])
    assert cleanup==trial['cleanup'] and cleanup['restored'] and not cleanup['errors'] and cleanup['pendingOwnedBitmaps']==0
    end=cleanup['presentation'];assert not end['active'] and end['parents']==0
    assert end['enables']==end['restores'] and end['allocated']==end['disposed']==end['copies']
    assert end['texturesCreated']==end['texturesDisposed']>1 and end['allocated']==end['texturesCreated']+1
    assert end['contextCreates']==end['contextDisposals']==1 and end['gpuBytes']==0 and not end['ready'] and not end['error']
    assert end['timelinesRestored'] and end['clipsStopped']==end['clipsResumed']
    assert end['worldPrepared'] and end['captureCullRestored'] and end['timelineCount']>0
    assert 'software' not in end['initial']['driverInfo'].lower()
    assert end['captures']==13 and trial['pixelBitmapsCreated']==trial['pixelBitmapsDisposed']==260
    assert trial['pixelsValid'] and len(trial['pixels'])==13 and len(trial['nativeWarmups'])==18
    for warm in trial['nativeWarmups']:
        assert warm['passed'] and len(warm['preparationReturns'])==3 and len(warm['checks'])==3
        assert all(x['pixels']['equal'] and x['pixels']['differentPixels']==0 for x in warm['checks'])
    for pixel in trial['pixels']:
        assert pixel['passed'] and pixel['visualAccepted'] and pixel['candidate']['maxRGB']<=2 and pixel['candidate']['maxAlpha']==0
        assert pixel['restore']['equal'] and pixel['restore']['differentPixels']==0
        assert pixel['presentation']['active'] and pixel['presentation']['parents']==2
    assert trial['testFrameRate']==120 and trial['stabilizationFrames']==12
    assert 1<=len(trial['preparePasses'])<=12 and trial['preparePasses'][-1]['quiet']
    assert all(v==0 for v in trial['preparePasses'][-1]['delta'].values())
    assert trial['zeroRasterWork'] and all(v==0 for v in trial['timingRasterDelta'].values())
    assert len(trial['windows'])==8 and len(trial['framesMs'])==len(trial['sampleAtMs'])==960
    keys=('sceneRedraws','sceneDrawMs','sceneResident','sceneEvictions','sceneMisses','sceneWarmCount','sceneWarmSlices','sceneWarmForced')
    initial=trial['timingStart'];previous=trial['timingStartAtMs'];intervals=[];stamps=[];rows=[]
    modes=('native-static','native-moving','gpu-static','gpu-moving')
    first=trial['windows'][0]['presentation'][0]
    for i,(row,condition) in enumerate(zip(trial['windows'],(0,1,2,3,3,2,1,0))):
        cached=condition>=2
        assert row['index']==i and row['condition']==condition and row['mode']==modes[condition]
        assert row['cached'] is cached and row['moving'] is (condition%2==1) and row['startAtMs']==previous
        for key in ('framesMs','sampleAtMs','vx','vy','cameraX','cameraY','gg','scene','workMs','worldVisible','windowVisible','presentation'):
            assert len(row[key])==120,key
        assert all(v is (not cached) for v in row['worldVisible']) and all(v is True for v in row['windowVisible'])
        positions=set(zip(row['vx'],row['vy']));assert (len(positions)>1) if row['moving'] else len(positions)==1
        assert all(x==initial['gg'] for x in row['gg'])
        for scene in row['scene']:
            assert all(scene[k]==initial['scene'][k] for k in keys)
        for p in row['presentation']:
            assert p['active'] is cached and p['parents']==(2 if cached else 0) and p['actualCache'] is cached
            assert all(p[k]==first[k] for k in ('uploads','texturesCreated','allocated','disposed','copies','clipsStopped'))
            assert p['captures']==13 and p['contextCreates']==1 and p['contextDisposals']==0 and p['clipsResumed']==0
        for stamp,dt in zip(row['sampleAtMs'],row['framesMs']):
            assert stamp-previous==dt and dt>=0;previous=stamp
        assert row['endAtMs']==previous and row['copiesEnd']==row['copiesStart']==first['copies']
        assert row['allocatedStart']==row['allocatedEnd']==first['allocated']
        intervals.extend(row['framesMs']);stamps.extend(row['sampleAtMs'])
        rows.append(dict(index=i,condition=condition,mode=row['mode'],frame=metric(row['framesMs']),workMs=sum(row['workMs'])))
    assert intervals==trial['framesMs'] and stamps==trial['sampleAtMs']
    assert previous==trial['timingEndAtMs'] and sum(intervals)==trial['timingElapsedMs']==previous-trial['timingStartAtMs']
    arms={name:metric([v for row in trial['windows'] if row['mode']==name for v in row['framesMs']]) for name in modes}
    pairs=[dict(nativeIndex=a,gpuIndex=b,meanDeltaMs=rows[b]['frame']['mean']-rows[a]['frame']['mean']) for a,b in ((1,3),(6,4))]
    return dict(version=VERSION,complete=True,diagnosticOnly=True,performanceEligible=False,gameplayAcceptance=False,deployed=False,
        rows=rows,arms=arms,pairs=pairs,elapsedMs=sum(intervals),zeroNativeRasterWork=True,pixels=trial['pixels'],cleanup=cleanup,
        limits=['Whole-world fixed picture with identically frozen MovieClips; no animated gameplay or combat claim.',
                'Direct ENTER_FRAME intervals, not physical presents; all spikes and boundary work retained.',
                'GPU readback plus native Stage.draw, no actual OS-window presentation acceptance.'])

