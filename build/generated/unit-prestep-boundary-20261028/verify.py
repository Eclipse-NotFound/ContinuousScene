"""Check saved native failure, fixed entries, and exact normal-trajectory parity."""
from pathlib import Path
import hashlib,json

HERE=Path(__file__).resolve().parent
MOD=HERE.parents[2]
EVIDENCE=MOD/'knowledge/experiments/evidence'
BASE='4E5FAB45D6F5A2634C83BE5E7EAF387443F9FB4E56B945CD2BF54880F1F73C75'
FIXED='B84F24280B3C676F4068E1CDC5A6EBEE89988F62BCF7A44D4DD71A4771360184'
CS='9A5E24E13AF2E2E211FAEAC038697D2CA2641CD6482766048BC3B9B4A506AA31'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()
def read(path):return json.loads(Path(path).read_text('utf-8-sig'))


def check_run(name,host,probe):
    directory=EVIDENCE/name
    result=read(directory/'storage/result.json')
    policy=read(directory/'process-policy.json')
    inputs={p.replace('\\','/'):v for p,v in read(directory/'inputs.json').items()}
    loaded=read(directory/'loader-check.json')
    boundaries=read(directory/'boundary-inputs.json')
    assert result['ok'] and result['error'] is None and all(a['ok'] for a in result['assertions'])
    assert policy['functionalOnly'] and policy['performanceEligible'] is False and not policy.get('runFailure')
    assert policy['desktopPolicy']=='private' and policy['appId'].startswith('pfe-modsettings-continuous-motion-')
    assert len(loaded['sessions'])==1 and loaded['loaded'] and all(loaded['loaded'].values())
    assert inputs['pfe.swf']==host==boundaries['host']
    assert inputs['mods/ContinuousScene/release/ContinuousSceneMod.swf']==CS
    assert inputs['mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf']==probe==boundaries['probe']
    assert policy['minimumAvailableCommit']>=512*1024**2
    files=['storage/result.json','process-policy.json','inputs.json','loader-check.json','boundary-inputs.json']
    return result,dict(name=name,path=str(directory),checks=len(result['assertions']),pid=policy['pid'],
        appId=policy['appId'],host=host,probe=probe,foreignAir=policy['otherAirProcessIds'],
        performanceEligible=False,files={f:sha(directory/f) for f in files})


def verify():
    audit=read(HERE/'host-audit.json')
    assert audit['passed'] and audit['candidateReadbackExact'] and audit['onlyMethodChanged']
    assert audit['candidateSHA256']==FIXED==sha(HERE/'pfe-unit-boundary.swf') and audit['baseSHA256']==BASE
    assert audit['sourceInputs']=={p:sha(p) for p in audit['sourceInputs']}
    builds=[HERE,HERE.parent/'unit-run-regression-v2-20261028']
    probes=[]
    for directory in builds:
        build=read(directory/'probe-build.json')
        assert build['compiled'] and build['inputs']=={p:sha(p) for p in build['inputs']}
        assert build['outputSHA256']==sha(directory/'ContinuousSceneMotionMod.swf')
        probes.append(build['outputSHA256'])
    before,a=check_run('unit-prestep-boundary-20261028-base-r2',BASE,probes[0])
    after,b=check_run('unit-prestep-boundary-20261028-fixed-r1',FIXED,probes[0])
    assert len(before['cases'])==len(after['cases'])==2
    assert [c['side'] for c in before['cases']]==['left','right']
    for left,right in zip(before['cases'],after['cases']):
        assert left['error']['id']==1010 and 'fe.unit::Unit/run()' in left['error']['stack']
        assert left['outsideColumn'] and right['outsideColumn'] and right['error'] is None
        assert left['before']==right['before']
    assert len(after['entries'])==6
    assert [e['large'] for e in after['entries']]==[False,True]*3
    assert all(e['stage']==4 and e['seed']==4077752896 for e in after['entries'])
    native,c=check_run('unit-run-regression-v2-20261028-base-r1',BASE,probes[1])
    patched,d=check_run('unit-run-regression-v2-20261028-fixed-r1',FIXED,probes[1])
    assert len(native['cases'])==12 and all(len(case['frames'])==12 for case in native['cases'])
    assert native['cases']==patched['cases'], 'Normal trajectories changed'
    assert native['assertions']==patched['assertions']
    return dict(ok=True,base=BASE,candidate=FIXED,mod=CS,runs=[a,b,c,d],
        deterministicFailuresReproduced=2,boundaryRecoveryPassed=2,manhattanEntries=6,
        normalCases=12,normalStatesEqual=144,normalAssertions=len(native['assertions']),
        auditSHA256=sha(HERE/'host-audit.json'),performanceClaim=False,
        limitations='Controlled native boundary reproduction plus six entries; not every random seed, not a frame-rate test.')


if __name__=='__main__':
    result=verify()
    with (HERE/'verification.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k!='runs'}))
