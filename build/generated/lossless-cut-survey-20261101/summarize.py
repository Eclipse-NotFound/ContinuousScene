"""Freeze a bounded survey without promoting diagnostics into release evidence."""
from pathlib import Path
import hashlib,json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
REPO=ROOT/'mods/ContinuousScene'
BASE=REPO/'knowledge/experiments/evidence'
RUNS=[
    'camera-lossless-snapshot-small-r1-20261101',
    'camera-lossless-snapshot-small-r2-20261101',
    'camera-static-groups-small-r2-20261101',
    'camera-static-groups-large-r1-20261101',
    'camera-runtime-sdk-small-r1-20261101',
    'camera-runtime-installed-small-r2-20261101',
    'camera-gc-scheduling-small-r1-20261101',
    'camera-group-scale-small-r1-20261101',
    'camera-static-group-cache-small-r1-20261101',
    'camera-near-group-cache-small-r1-20261101',
]
GENERATORS=[
    'camera-lossless-survey-v14-20261101',
    'camera-static-groups-v15-20261101',
    'camera-runtime-survey-v16-20261101',
    'camera-gc-scheduling-v17-20261101',
    'camera-group-scale-v18-20261101',
    'camera-static-group-cache-v19-20261101',
    'camera-near-group-cache-v20-20261101',
]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def read(p):return json.loads(p.read_text('utf-8-sig'))
def write(p,value):
    with p.open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2)

def main():
    formal=read(BASE/'camera-static-groups-small-r2-20261101/inputs.json')
    formal={p:h for p,h in formal.items() if p.lower().endswith('mod.swf') and
            'continuousscenemotion' not in p.lower() and 'continuoussceneprobe' not in p.lower()}
    assert len(formal)==14
    expected_host='9D8662F6CF80E0AD20741EC2A4E7BEAD68446269EBB0ADB641C876DB68698B1D'
    out={'diagnosticOnly':True,'performanceDeploymentAccepted':False,'deployment':None,
         'formalMods':formal,'host':expected_host,'runs':[],'totalIntervals':0,
         'failedAndPartialEvidencePreserved':True,
         'notLaunched':['camera-static-groups-small-r1-20261101: registry wait timeout'],
         'acceptanceBoundary':'No proof that every lossless implementation is exhausted; no promotion of legacy profile=false diagnostics.'}
    archive={}
    for name in RUNS:
        folder=BASE/name
        raw=read(folder/'storage/result.json');inputs=read(folder/'inputs.json')
        policy=read(folder/'process-policy.json');review=read(folder/'review-inputs.json')
        analysis=read(folder/'analysis.json')
        expected=dict(formal)
        if name.startswith('camera-lossless-snapshot'):
            key=next(k for k in expected if k.endswith('TDFCMod.swf'))
            expected[key]='767CF2BA4C389C1334FA5EE4DF7A3363385B8D29B8DA3B47905514A538822058'
        assert all(inputs[k]==v for k,v in expected.items()),name
        assert inputs['pfe.swf']==review['host']==expected_host,name
        assert not policy['otherAirProcessIds'],name
        assert raw['nativeHiddenActor']['after'] is False,name
        assert len(raw['assertions'])==analysis['assertions']
        for block in analysis['blocks']:
            if block['complete']:
                assert all(block['delta'][k]==0 for k in ('sceneWarmCount','sceneRedraws','sceneMisses','sceneEvictions','sceneResident')),(name,block['delta'])
        item={'name':name,'ok':raw['ok'],'error':raw.get('error'),
              'assertions':analysis['assertions'],'aggregate':analysis['aggregate'],
              'byAxis':analysis['byAxis'],'probe':review['recipe']['probe'],
              'legacyHarnessPerformanceEligible':policy['performanceEligible'],
              'minimumAvailableCommit':policy.get('minimumAvailableCommit'),
              'entry':{k:raw['entry'].get(k) for k in ('units','scale','stageWidth','stageHeight')},
              'rawSHA256':sha(folder/'storage/result.json')}
        rows=[r for b in raw['blocks'] for r in b.get('rows',[])]
        if rows:
            ranges={raw['columns'][i]:[min(r[i] for r in rows),max(r[i] for r in rows)] for i in (3,4,5,6,7,8,11,12)}
            assert ranges['playerX']==[2055,2055] and ranges['playerY']==[1960,1960],name
            assert ranges['visualX'][1]-ranges['visualX'][0]==320,name
            assert ranges['visualY'][1]-ranges['visualY'][0]==192,name
            assert ranges['screenPlayerX'][0]>=0 and ranges['screenPlayerX'][1]<raw['entry']['stageWidth'],name
            assert ranges['screenPlayerY'][0]>=0 and ranges['screenPlayerY'][1]<raw['entry']['stageHeight'],name
            item['motionRanges']=ranges
        out['totalIntervals']+=sum(g['n'] for g in analysis['aggregate'].values())
        engine=folder/(name+'-engine.json')
        if engine.exists():
            e=read(engine);assert e['ok'] and e['loadedVerified']
            assert all(sha(Path(p))==h for p,h in e['files'].items()),'Runtime files changed after test'
            item['runtime']={k:e[k] for k in ('dllVersion','loadedDLL','loadedSHA256')}
        out['runs'].append(item)
        for path in folder.rglob('*'):
            if path.is_file() and path.suffix.lower() in ('.json','.log'):
                archive[str(path.relative_to(REPO))]=sha(path)
    for name in GENERATORS:
        folder=HERE.parent/name;receipt=read(folder/'build.json')
        assert all(sha(folder/p)==h for p,h in receipt['sources'].items()),name
        assert sha(folder/'ContinuousSceneMotionMod.swf')==receipt['probe'],name
        for path in folder.rglob('*'):
            if not path.is_file() or any(part.startswith('runtime-') for part in path.relative_to(folder).parts):continue
            if path.suffix.lower() in ('.as','.py','.xml','.json','.log','.swf'):
                archive[str(path.relative_to(REPO))]=sha(path)
    out['formalUnchanged']=sha(ROOT/'pfe.swf')==expected_host and all(sha(ROOT/p)==h for p,h in formal.items())
    out['foreignSourceUnchanged']=sha(REPO/'src/tests/SceneRenderChecks.as')=='41DF71EE976EAD95CFFC1989CD9EF70A7C2FF0C24D541C4A3AD78A9F5B050983'
    assert out['formalUnchanged'] and out['foreignSourceUnchanged']
    write(HERE/'archive.json',archive);write(HERE/'summary.json',out)
    print(json.dumps({k:v for k,v in out.items() if k not in ('runs','formalMods')},ensure_ascii=False))
    print(json.dumps({'frozenFiles':len(archive),'completedRuns':sum(r['ok'] for r in out['runs'])}))
if __name__=='__main__':main()
