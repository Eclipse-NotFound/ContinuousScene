VERSION='camera-persistent-readers-1'
def summarize(raw):
    assert raw['ok'] and raw['error'] is None and not raw['samples'] and all(x['ok'] for x in raw['assertions'])
    assert raw['quietStartBeforeCombatWarmup'] and raw['nativeWindowRestored']
    assert not [e for e in raw['nativeWindowEvents'] if e['phase']>=2]
    t=raw['cameraRaster'];c=raw['cameraRasterCleanup']
    assert t['version']==VERSION and t['functionalOnly'] and t['measurementFrames']==0
    assert t['complete'] and t['passed'] and not t['errors'] and t['pixelsValid']
    assert not t['windows'] and not t['framesMs'] and not t['sampleAtMs']
    assert c==t['cleanup'] and c['restored'] and not c['errors'] and c['pendingOwnedBitmaps']==0
    for kind in ['classic','persistent']:
        end=c['atlas'][kind];initial=t['atlasPrepared'][kind]
        assert initial['allocations']==initial['ownedBitmaps']==32 and initial['pixelStorageBytes']==200*1024**2
        assert end['allocations']==end['disposals']==32
        for key in ['ownedBitmaps','pixelStorageBytes','attached','pendingHidden','poolPages']:assert end[key]==0
    assert t['pixelBitmapsCreated']==t['pixelBitmapsDisposed']==30 and len(t['pixels'])==5
    for p in t['pixels']:
        assert p['passed'] and p['nativeRepeat']['equal'] and p['visibleCoverage']['fraction']>=.15
        for v in p['variants']:assert v['state']['presented'] and v['changed']['maxRGB']<=2 and v['changed']['maxAlpha']==0 and v['restore']['equal']
    f=t['atlasContracts'];assert f['complete'] and f['passed'] and not f['errors'] and f['holderDetached']
    assert f['sourceCreated']==f['sourceDisposed']==132 and f['pixelCreated']==f['pixelDisposed']==34 and len(f['cases'])==16
    for case in f['cases']:
        assert case['pixels']['maxRGB']<=2 and case['pixels']['maxAlpha']==0
        if not case['presented']:assert case['pixels']['differentPixels']==0
    for s in [f['afterClear'],f['cleanup']]:
        assert s['allocations']==s['disposals']==32 and s['ownedBitmaps']==s['attached']==s['pendingHidden']==s['pixelStorageBytes']==0
    r=f['readerContract'];assert r['passed'] and not r['errors'] and r['created']==r['disposed']==12
    assert [x['name'] for x in r['steps']]==['before-change','native-revision-before-presentation','after-presentation-refresh','native-fallback']
    for i,step in enumerate(r['steps']):
        assert step['candidate']['differentPixels']==0
        assert step['expectedStale']==(i==1)
        assert (step['legacy']['differentPixels']>0)==(i==1)
    return dict(version=VERSION,complete=True,functionalOnly=True,diagnosticOnly=True,performanceEligible=False,deployed=False,
        readerContract=r,atlasContracts=f,pixels=t['pixels'],cleanup=c,arms={},pairs=[],
        limits=['Isolated D44 foreground-reader copy; actual RV mod and production entry are not changed.',
            'Proves stale read before atlas refresh and pure native-source correction; does not qualify full RV masks, WB, SATS or long-run performance.'])
