"""Independent closure/timing review; retains the census failure as a failure."""
from pathlib import Path
import hashlib,importlib.util,json,math,statistics
HERE=Path(__file__).resolve().parent;MOD=HERE.parents[2];ROOT=MOD.parents[1];E=MOD/'knowledge/experiments/evidence'
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def load(name,p):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def verify(recipe_name,failed=False):
    f=E/(recipe_name+'-r1');r=read(f/'runner-inputs.json');b=read(f/'probe-build.json');raw=read(f/'storage/result.json')
    assert len(r['baseline'])==526 and len(r['runtimeInputs'])==13
    for key in ['baseline','runtimeInputs']:
        for p,digest in r[key].items():assert sha(ROOT/p)==digest,(recipe_name,key,p)
    for key in ['runnerInputs','fixtureInputs','compilerInputs']:
        for p,digest in r[key].items():assert sha(Path(p))==digest,(recipe_name,key,p)
    src=Path(b['frozenSourcePath']);expected=87 if failed or 'opaque-tiles' in recipe_name or 'empty-native-tiles' in recipe_name else 86
    assert len(b['frozenSourceSHA256'])==expected
    for p,digest in b['frozenSourceSHA256'].items():assert sha(src/p)==digest,(recipe_name,p)
    assert sha(Path(b['probePath']))==b['probeSHA256']==r['probeSHA256']
    for path,field in [('sourceOrigin','sourceOriginSHA256'),('configPath','configSHA256')]:assert sha(Path(b[path]))==b[field]
    actual={k.replace('\\','/'):v for k,v in read(f/'inputs.json').items()}
    for p,digest in r['baseline'].items():
        if p not in ('application.xml','mods/loader-manifest.txt'):assert actual[p]==digest,(recipe_name,p)
    assert actual['mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf']==b['probeSHA256']
    policy=read(f/'process-policy.json');loader=read(f/'loader-check.json')
    assert policy['desktopPolicy']=='private' and not policy['performanceEligible']
    assert not policy.get('otherAirProcessIds') and not policy.get('memoryAbort')
    assert len(loader['sessions'])==1 and all(loader['loaded'].values())
    assert r['memoryBeforeAir']['availableCommit']>=4*1024**3 and r['memoryBeforeAir']['availablePhysical']>=2*1024**3
    result=dict(name=recipe_name+'-r1',resultSHA256=sha(f/'storage/result.json'),probeSHA256=b['probeSHA256'],frozen=src.parent.name,pid=policy['pid'],inputsVerified=True,sourceCount=expected,deployed=False)
    t=raw['cameraRaster']
    if failed:
        assert not raw['ok'] and not t['complete'] and t['errors']==['Quiet tree audit failed']
        assert not t['framesMs'] and t['cleanup']['restored'] and t['pixelBitmapsCreated']==t['pixelBitmapsDisposed']==10
        full,quiet=t['fullTreeBeforeRemoval'],t['quietTree']
        assert full['complete'] and full['readOnly'] and not full['errors'] and len(full['nodes'])==15680
        assert not quiet['complete'] and quiet['errors']==['Null display child']*45 and len(quiet['nodes'])==13080
        for audit in [full,quiet]:
            assert [n['id'] for n in audit['nodes']]==list(range(len(audit['nodes'])))
            assert all(n['parent']<n['id'] for n in audit['nodes'])
            assert sum(bm['width']*bm['height']*4 for bm in audit['bitmaps'])==audit['uniqueBitmapBytes']
        result.update(validPerformanceRun=False,limitation='Second census has 45 unlocalized null child slots; only the first census is complete. No timing intervals.',fullCensusNodes=15680,fullBitmapBytes=full['uniqueBitmapBytes'],quietCensusPartialNodes=13080)
    elif 'visible-components' in recipe_name:
        # The frozen runner/summary remain failed. Review its clock independently.
        s=load('failed_component_summary_review',HERE/'review_failed_summary.py').review(raw)
        assert (f/'runner-failure.json').is_file() and not (f/'summary.json').exists()
        result.update(s)
    elif 'opaque-tiles' in recipe_name:
        # Original coverage gate failed correctly: the only eligible tile is offscreen.
        g=t['opaqueTiles'];c=t['cleanup']
        assert raw['ok'] and t['complete'] and t['passed'] and not t['errors']
        assert g['selected']==g['allocated']==g['disposed']==1 and g['bytes']==640000 and g['setupMs']==7
        assert g['tiles']==[dict(layer=1,width=400,cx=1,cy=14,height=400)] and g['enableWrites']==g['restoreWrites']==12
        assert c['restored'] and not c['errors'] and c['opaqueTiles']['restored'] and not c['opaqueTiles']['remaining']
        assert len(t['windows'])==16 and len(t['framesMs'])==len(t['sampleAtMs'])==1920
        assert all(v['visible']==0 for w in t['windows'] for v in w['opaqueVisible'])
        assert t['pixelBitmapsCreated']==t['pixelBitmapsDisposed']==20 and t['zeroRasterWork'] and not any(t['timingRasterDelta'].values())
        for p in t['pixels']:assert p['nativeRepeat']['equal'] and p['opaque']['equal'] and p['restore']['equal'] and p['visibleCoverage']['fraction']>=.15
        clock=t['timingStartAtMs']
        for dt,stamp in zip(t['framesMs'],t['sampleAtMs']):assert stamp-clock==dt;clock=stamp
        assert sum(t['framesMs'])==t['timingElapsedMs']==clock-t['timingStartAtMs']
        assert (f/'runner-failure.json').is_file() and not (f/'summary.json').exists()
        result.update(validPerformanceRun=False,originalSummaryGatePassed=False,completeIntervalsVerified=True,frames=1920,opaqueTiles=g,
                      limitation='Only one whole-buffer opaque tile qualifies; it is outside every timed view. No eligible visible tile, so no performance inference.')
    else:
        assert not policy.get('runFailure')
        s=load(recipe_name,HERE.parent/recipe_name/'summary.py').summarize(raw);saved=read(f/'summary.json')
        assert all(saved[k]==v for k,v in s.items()) and saved['resultSHA256']==result['resultSHA256']
        result.update(validPerformanceRun=True,arms=s['arms'],pairs=s['pairs'],timingBands=s['timingBands'],frames=len(t['framesMs']),pixelBitmapsCreated=t['pixelBitmapsCreated'],pixelBitmapsDisposed=t['pixelBitmapsDisposed'])
        if 'components' in s:result['components']=s['components']
        if 'borderCaches' in s:result['borderCaches']=s['borderCaches']
        if 'opaqueTiles' in s:result['opaqueTiles']=s['opaqueTiles']
        if 'emptyTiles' in s:result['emptyTiles']=s['emptyTiles']
    return result
def main():
    results=[verify('camera-visible-tree-audit-20261027',True),verify('camera-border-cache-20261027'),verify('camera-visible-components-20261027'),verify('camera-opaque-tiles-20261027'),verify('camera-empty-native-tiles-20261027')]
    p=HERE/'batch-review.json';p.write_text(json.dumps(dict(runs=results,deployed=False,gameplayAcceptance=False),ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps(dict(reviewed=len(results),timedRuns=sum(r['validPerformanceRun'] for r in results),reportSHA256=sha(p),deployed=False)))
if __name__=='__main__':main()
