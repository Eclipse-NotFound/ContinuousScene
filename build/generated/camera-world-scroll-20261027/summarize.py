def summarize(raw):
    assert raw['ok'] and raw['error'] is None and not raw['samples']
    cfg=raw['config']
    assert cfg['drawControl']=='tilecrop' and cfg['presentationCheck'] and cfg['noLighting'] and cfg['noWall'] and not cfg['vision']
    trial,cleanup=raw['cameraRaster'],raw['cameraRasterCleanup']
    assert trial['nativeMenuChildren'] and all(row['className']!='visMainMenu' for row in trial['nativeMenuChildren'])
    assert trial['version']==VERSION and trial['complete'] and trial['passed'] and not trial['errors']
    assert cleanup==trial['cleanup'] and cleanup['restored'] and not cleanup['errors'] and cleanup['pendingOwnedBitmaps']==0
    assert trial['pixelBitmapsCreated']==trial['pixelBitmapsDisposed']==65 and cleanup['terrainRestored']
    assert trial['pixelsValid'] and len(trial['pixels'])==len(trial['nativeWarmups'])==5
    for warm in trial['nativeWarmups']:
        assert warm['passed'] and len(warm['checks'])==3 and all(check['pixels']['equal'] for check in warm['checks'])
    for row in trial['pixels']:
        assert row['passed'] and len(row['conditions'])==2
        for mode,c in enumerate(row['conditions'],1):
            assert c['condition']==mode and c['changed']['maxRGB']<=2 and c['changed']['maxAlpha']==0
            assert c['restored']['equal'] and c['restored']['differentPixels']==c['restored']['maxRGB']==c['restored']['maxAlpha']==0
    assert trial['testFrameRate']==120 and trial['stabilizationFrames']==12
    assert 1<=len(trial['preparePasses'])<=12 and trial['preparePasses'][-1]['quiet']
    assert all(v==0 for v in trial['preparePasses'][-1]['delta'].values())
    assert trial['zeroRasterWork'] and all(v==0 for v in trial['timingRasterDelta'].values())
    assert len(trial['windows'])==6 and len(trial['framesMs'])==len(trial['sampleAtMs'])==720
    keys=('sceneRedraws','sceneDrawMs','sceneResident','sceneEvictions','sceneMisses','sceneWarmCount','sceneWarmSlices','sceneWarmForced')
    initial=trial['timingStart'];previous=trial['timingStartAtMs'];intervals=[];stamps=[];rows=[]
    modes=('native-moving','scroll-moving','scroll-cached-moving')
    for i,(row,condition) in enumerate(zip(trial['windows'],(0,1,2,2,1,0))):
        assert row['index']==i and row['condition']==condition and row['mode']==modes[condition]
        assert row['hidden'] is False and row['moving'] is True and row['startAtMs']==previous
        for key in ('framesMs','sampleAtMs','vx','vy','cameraX','cameraY','gg','scene','workMs','worldVisible','windowVisible','terrain'):
            assert len(row[key])==120,key
        assert all(v is True for v in row['windowVisible']+row['worldVisible'])
        xs,ys=set(row['vx']),set(row['vy']);assert len(xs)>1 and len(ys)>1
        for j,value in enumerate(row['terrain']):
            vx,vy=row['vx'][j],row['vy'][j]
            expected=[0,False,vx,vy,False,0,0,0,0] if condition==0 else [condition,condition==2,0,0,True,-vx,-vy,trial['stage']['width'],trial['stage']['height']]
            assert value==expected
        if i:assert row['vx']==trial['windows'][0]['vx'] and row['vy']==trial['windows'][0]['vy']
        assert all(pose==initial['gg'] for pose in row['gg'])
        for scene in row['scene']:
            for key in keys:assert scene[key]==initial['scene'][key],(key,scene[key],initial['scene'][key])
        for stamp,dt in zip(row['sampleAtMs'],row['framesMs']):
            assert stamp-previous==dt and dt>=0;previous=stamp
        assert row['endAtMs']==previous and row['copiesEnd']==row['copiesStart']==row['allocatedEnd']==row['allocatedStart']==0
        intervals.extend(row['framesMs']);stamps.extend(row['sampleAtMs'])
        rows.append(dict(index=i,condition=condition,mode=row['mode'],frame=metric(row['framesMs']),work=metric(row['workMs']),xRange=[min(xs),max(xs)],yRange=[min(ys),max(ys)]))
    assert intervals==trial['framesMs'] and stamps==trial['sampleAtMs']
    assert previous==trial['timingEndAtMs'] and sum(intervals)==trial['timingElapsedMs']==previous-trial['timingStartAtMs']
    arms={name:metric([v for row in trial['windows'] if row['mode']==name for v in row['framesMs']]) for name in modes}
    paired=[dict(nativeIndex=a,candidateIndex=b,mode=rows[b]['mode'],candidateMinusNativeMs=rows[b]['frame']['mean']-rows[a]['frame']['mean']) for a,b in ((0,1),(0,2),(5,4),(5,3))]
    return dict(version=VERSION,complete=True,diagnosticOnly=True,performanceEligible=False,gameplayAcceptance=False,deployed=False,
        rows=rows,arms=arms,pairs=paired,elapsedMs=sum(intervals),zeroNativeRasterWork=True,
        originalFrameRate=trial['originalFrameRate'],testFrameRate=trial['testFrameRate'],pixels=trial['pixels'],cleanup=cleanup,
        limits=['Paused simulation; live Flash timelines and callbacks; no actual gameplay performance claim.',
                'Original camera transform writes retained before scroll setup; not a host camera rewrite.',
                'Internal runtime bitmap-cache adoption and allocation not established by cacheAsBitmap flag.',
                'Private native window visible; no user-desktop presentation claim. All spikes retained.'])
