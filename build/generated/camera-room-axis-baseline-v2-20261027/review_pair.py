"""Independent comparison of the two completed native camera runs; no new game."""
from pathlib import Path
import hashlib
import json
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
E=ROOT/'knowledge/experiments/evidence'
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
runs={}
for mode in ('normal','scene'):
    folder=E/('camera-room-axis-baseline-v2-20261027-'+mode+'-r1')
    raw=read(folder/'storage/result.json')
    summary=read(folder/'summary.json')
    inputs=read(folder/'runner-inputs.json')
    probe=read(folder/'probe-build.json')
    policy=read(folder/'process-policy.json')
    assert raw['ok'] and raw['error'] is None and all(a['ok'] for a in raw['assertions'])
    assert summary['complete'] and summary['inputsUnchanged'] and summary['runtimeInputsUnchanged']
    assert summary['resultSHA256']==sha(folder/'storage/result.json')
    assert raw['cameraRaster']['pixelBitmapsCreated']==raw['cameraRaster']['pixelBitmapsDisposed']==10
    assert len(raw['cameraRaster']['framesMs'])==960 and raw['cameraRaster']['cleanup']['restored']
    assert policy['desktopPolicy']=='private' and not policy.get('memoryAbort') and not policy.get('runFailure')
    runs[mode]=dict(folder=folder,raw=raw,summary=summary,inputs=inputs,probe=probe)
a,b=runs['normal'],runs['scene']
for key in ('baseline','runnerInputs','compilerInputs','fixtureInputs','runtimeInputs'):
    assert a['inputs'][key]==b['inputs'][key],key
for key in ('probeSHA256','frozenSourceSHA256'):
    assert a['probe'][key]==b['probe'][key],key
assert a['raw']['nativeRoom']['x']==2 and a['raw']['nativeRoom']['y']==4
assert b['raw']['selectedCombatRoom']['x']==2 and b['raw']['selectedCombatRoom']['y']==4
assert a['raw']['selectedCombatRoomTiles']==b['raw']['selectedCombatRoomTiles']==3340386727
assert a['raw']['selectedCombatCorridorTiles']==b['raw']['selectedCombatCorridorTiles']=={'hash':3092338540,'cells':104}
assert a['raw']['cameraRaster']['stage']==b['raw']['cameraRaster']['stage']
for normal,scene in zip(a['raw']['cameraRaster']['windows'],b['raw']['cameraRaster']['windows']):
    assert normal['mode']==scene['mode'] and len(normal['cameraX'])==len(scene['cameraX'])==120
    for x,y,u,v in zip(normal['cameraX'],normal['cameraY'],scene['cameraX'],scene['cameraY']):
        assert u-x==3840 and v-y==4000
    for x,y,u,v in zip(normal['vx'],normal['vy'],scene['vx'],scene['vy']):
        assert x-u==3840 and y-v==4000
rows=[]
static_diff=b['summary']['arms']['native-static']['mean']-a['summary']['arms']['native-static']['mean']
for mode in a['summary']['arms']:
    normal=a['summary']['arms'][mode];scene=b['summary']['arms'][mode]
    delta=scene['mean']-normal['mean']
    rows.append(dict(mode=mode,normal=normal,scene=scene,meanDifferenceMs=delta,
        differenceBeyondStaticMs=delta-static_diff))
out=dict(version='matched-native-room-camera-review-1',complete=True,diagnosticOnly=True,deployed=False,
    commonProbeSHA256=a['probe']['probeSHA256'],formalFiles=len(a['inputs']['baseline']),
    runtimeFiles=len(a['inputs']['runtimeInputs']),matchedRoomTiles=3340386727,matchedCorridorTiles=3092338540,
    stage=a['raw']['cameraRaster']['stage'],framesEach=960,trajectoryTranslationExact=True,
    rows=rows,worldUnits={mode:value['raw']['world']['units'] for mode,value in runs.items()},
    resultSHA256={mode:sha(value['folder']/'storage/result.json') for mode,value in runs.items()},
    limitations=['Same terrain hash and local camera path; dynamic actors and remote world population differ.',
        'Simulation paused but timelines and frame callbacks remain active. Not gameplay FPS.',
        'Camera selected native zoom 0 for both modes and fully restored; not ordinary default fit-to-room mode.',
        'Separate native runs, no performance optimization or CPU/GPU attribution.'])
path=HERE/'pair-review.json';assert not path.exists()
path.write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(dict(commonProbe=out['commonProbeSHA256'],sameGeometry=True,sameTrajectory=True,
    staticDifference=static_diff,rows=[{k:r[k] for k in ('mode','meanDifferenceMs','differenceBeyondStaticMs')} for r in rows]),ensure_ascii=False))

