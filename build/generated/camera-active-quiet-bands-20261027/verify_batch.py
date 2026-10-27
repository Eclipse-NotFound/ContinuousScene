"""Recheck complete raw intervals, camera trajectories, input closure and both modes."""
from pathlib import Path
import hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent;MOD=HERE.parents[2];ROOT=MOD.parents[1]
EVIDENCE=MOD/'knowledge/experiments/evidence'
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def load(name,p):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def verify(name,recipe):
    f=EVIDENCE/name;r=read(f/'runner-inputs.json');b=read(f/'probe-build.json');raw=read(f/'storage/result.json')
    assert len(r['baseline'])==526 and len(r['runtimeInputs'])==13
    for key in ['baseline','runtimeInputs']:
        for path,digest in r[key].items():assert sha(ROOT/path)==digest,(name,key,path)
    for key in ['runnerInputs','fixtureInputs','compilerInputs']:
        for path,digest in r[key].items():assert sha(Path(path))==digest,(name,key,path)
    src=Path(b['frozenSourcePath'])
    expected=87 if '-groups-' in name else 86
    assert len(b['frozenSourceSHA256'])==expected
    for path,digest in b['frozenSourceSHA256'].items():assert sha(src/path)==digest,(name,path)
    assert sha(Path(b['probePath']))==b['probeSHA256']==r['probeSHA256']
    for path,field in [('sourceOrigin','sourceOriginSHA256'),('configPath','configSHA256')]:assert sha(Path(b[path]))==b[field]
    actual={k.replace('\\','/'):v for k,v in read(f/'inputs.json').items()}
    for path,digest in r['baseline'].items():
        if path not in ('application.xml','mods/loader-manifest.txt'):assert actual[path]==digest,(name,path)
    assert actual['mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf']==b['probeSHA256']
    policy=read(f/'process-policy.json');loader=read(f/'loader-check.json')
    assert policy['desktopPolicy']=='private' and not policy['performanceEligible']
    assert not policy.get('otherAirProcessIds') and not policy.get('memoryAbort') and not policy.get('runFailure')
    assert len(loader['sessions'])==1 and all(loader['loaded'].values())
    assert r['memoryBeforeAir']['availableCommit']>=4*1024**3 and r['memoryBeforeAir']['availablePhysical']>=2*1024**3
    s=load(name,recipe/'summary.py').summarize(raw)
    retained=read(f/'summary.json')
    assert all(retained[k]==v for k,v in s.items()) and retained['resultSHA256']==sha(f/'storage/result.json')
    return dict(name=name,resultSHA256=sha(f/'storage/result.json'),probeSHA256=b['probeSHA256'],
                frozenSource=src.parent.name,pid=policy['pid'],sourceCount=expected,arms=s['arms'],
                timingBands=s.get('timingBands'),groupCache=s.get('groupCache'),inputsVerified=True,deployed=False,
                representativeViewVerified='visible-groups' in name,
                scopeCorrection=('Player-centered native/cached PNGs checked, with per-view coverage and per-sample screen position assertions; still not natural jumping/combat acceptance.' if 'visible-groups' in name else 'The matched camera center is below the player floor. The same-route near-groups PNG is mostly black. These timings are not a representative gameplay baseline.')),raw
def pair_check(n,s):
    assert n['selectedCombatRoomTiles']==s['selectedCombatRoomTiles']==3340386727
    assert n['selectedCombatCorridorTiles']==s['selectedCombatCorridorTiles']==dict(hash=3092338540,cells=104)
    a,b=n['cameraRaster'],s['cameraRaster'];assert a['stage']==b['stage'] and a['testZoom']==b['testZoom']==1
    assert not a['roomAxis']['continuous'] and b['roomAxis']['continuous']
    assert a['quietFixture']['remainingUnits']==b['quietFixture']['remainingUnits']==2
    for x,y in zip(a['windows'],b['windows']):
        assert x['condition']==y['condition'] and len(x['vx'])==len(y['vx'])==120
        assert [v-3840 for v in y['cameraX']]==x['cameraX'] and [v-4000 for v in y['cameraY']]==x['cameraY']
        assert [v+3840 for v in y['vx']]==x['vx'] and [v+4000 for v in y['vy']]==x['vy']
    return dict(tiles=True,corridor=True,all960CameraCoordinates=True,offset=[3840,4000],sameStageAndZoom=True)
def main():
    result=dict(runs=[],pairs=[],deployed=False,gameplayAcceptance=False)
    for recipe_name in ['camera-active-quiet-axis-20261027','camera-active-quiet-bands-20261027']:
        raws=[];records=[]
        for mode in ['normal','scene']:
            record,raw=verify(recipe_name+'-'+mode+'-r1',HERE.parent/recipe_name)
            result['runs'].append(record);raws.append(raw);records.append(record)
        assert records[0]['probeSHA256']==records[1]['probeSHA256']
        result['pairs'].append(dict(recipe=recipe_name,checks=pair_check(*raws)))
    for recipe_name in ['camera-native-near-groups-20261027','camera-native-visible-groups-20261027']:
        record,raw=verify(recipe_name+'-r1',HERE.parent/recipe_name)
        result['runs'].append(record)
    p=HERE/'batch-review.json';p.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps(dict(verifiedRuns=len(result['runs']),matchedPairs=len(result['pairs']),reportSHA256=sha(p),deployed=False)))
if __name__=='__main__':main()
