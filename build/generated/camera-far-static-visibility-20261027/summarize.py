def summarize(raw):
    assert raw['ok'] and raw['error'] is None and not raw['samples']
    cfg=raw['config']
    assert cfg['drawControl']=='tilecrop' and cfg['presentationCheck'] and cfg['noLighting'] and cfg['noWall'] and not cfg['vision']
    trial,cleanup=raw['cameraRaster'],raw['cameraRasterCleanup']
    assert trial['nativeMenuChildren'] and all(row['className']!='visMainMenu' for row in trial['nativeMenuChildren'])
    assert trial['version']==VERSION and trial['complete'] and trial['passed'] and not trial['errors']
    assert cleanup==trial['cleanup'] and cleanup['restored'] and not cleanup['errors'] and cleanup['pendingOwnedBitmaps']==0
    assert trial['pixelBitmapsCreated']==trial['pixelBitmapsDisposed']==55 and cleanup['terrainRestored']
    assert trial['pixelsValid'] and len(trial['pixels'])==len(trial['nativeWarmups'])==5
    for warm in trial['nativeWarmups']:
        assert warm['passed'] and len(warm['checks'])==3 and all(check['pixels']['equal'] for check in warm['checks'])
    for row in trial['pixels']:
        assert row['passed'] and len(row['conditions'])==1 and row['conditions'][0]['condition']==1
        for key in ('changed','restored'):
            c=row['conditions'][0][key];assert c['equal'] and c['differentPixels']==c['maxRGB']==c['maxAlpha']==0
    roots=trial['rootSelection']
    assert roots['selected']>0 and sum(roots['byLayer'])==sum(roots['classes'].values())==roots['selected']
    assert roots['scanned']==roots['selected']+sum(roots['skips'].values())
    assert roots['perFrameFullScans']==0 and roots['transitionWrites']==roots['selected']*12 and roots['audits']>=15
    assert trial['testFrameRate']==120 and trial['stabilizationFrames']==12
    assert 1<=len(trial['preparePasses'])<=12 and trial['preparePasses'][-1]['quiet']
    assert all(v==0 for v in trial['preparePasses'][-1]['delta'].values())
    assert trial['zeroRasterWork'] and all(v==0 for v in trial['timingRasterDelta'].values())
    assert len(trial['windows'])==4 and len(trial['framesMs'])==len(trial['sampleAtMs'])==480
    keys=('sceneRedraws','sceneDrawMs','sceneResident','sceneEvictions','sceneMisses','sceneWarmCount','sceneWarmSlices','sceneWarmForced')
    initial=trial['timingStart'];previous=trial['timingStartAtMs'];intervals=[];stamps=[];rows=[]
    modes=('native-moving','far-static-hidden-moving')
    for i,(row,condition) in enumerate(zip(trial['windows'],(0,1,1,0))):
        assert row['index']==i and row['condition']==condition and row['mode']==modes[condition]
        assert row['hidden'] is False and row['moving'] is True and row['startAtMs']==previous
        for key in ('framesMs','sampleAtMs','vx','vy','cameraX','cameraY','gg','scene','workMs','worldVisible','windowVisible','terrain'):
            assert len(row[key])==120,key
        assert all(v is True for v in row['windowVisible']+row['worldVisible'])
        xs,ys=set(row['vx']),set(row['vy']);assert len(xs)>1 and len(ys)>1
        assert all(value==[condition,roots['selected']] for value in row['terrain'])
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
    paired=[dict(nativeIndex=a,candidateIndex=b,candidateMinusNativeMs=rows[b]['frame']['mean']-rows[a]['frame']['mean']) for a,b in ((0,1),(3,2))]
    return dict(version=VERSION,complete=True,diagnosticOnly=True,performanceEligible=False,gameplayAcceptance=False,deployed=False,
        rows=rows,arms=arms,pairs=paired,rootSelection=roots,elapsedMs=sum(intervals),zeroNativeRasterWork=True,
        originalFrameRate=trial['originalFrameRate'],testFrameRate=trial['testFrameRate'],pixels=trial['pixels'],cleanup=cleanup,
        limits=['Paused simulation; live Flash timelines and callbacks; no actual gameplay performance claim.',
                'One fixed route union; production would need lifecycle/activity integration.',
                'Mask/effect/animation-bearing roots excluded, no wrapper or reparenting.',
                'Transition checks/costs retained. Endpoint audits cannot prove all intermediate callback state.',
                'Private native window visible; no user-desktop presentation claim. All spikes retained.'])
