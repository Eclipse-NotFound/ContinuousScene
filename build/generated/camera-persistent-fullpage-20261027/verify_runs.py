"""Independent retained-input and result review. Never launches a process."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,statistics,math
HERE=Path(__file__).resolve().parent;MOD=HERE.parents[2];ROOT=MOD.parents[1];E=MOD/'knowledge/experiments/evidence'
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def load(name,p):
    sp=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
def metric(v):
    a=sorted(v);return dict(count=len(a),mean=statistics.mean(a),p95=a[math.ceil(.95*len(a))-1],maximum=a[-1])
def verify(name,combat=False):
    f=E/(name+'-r1');r=read(f/'runner-inputs.json');b=read(f/'probe-build.json');raw=read(f/'storage/result.json')
    assert len(r['baseline'])==526 and len(r['runtimeInputs'])==13
    for key in ['baseline','runtimeInputs']:
        for p,d in r[key].items():assert sha(ROOT/p)==d,(name,key,p)
    for key in ['runnerInputs','fixtureInputs','compilerInputs']:
        for p,d in r[key].items():assert sha(Path(p))==d,(name,key,p)
    count=86 if combat else 89
    assert len(b['frozenSourceSHA256'])==count
    for p,d in b['frozenSourceSHA256'].items():assert sha(Path(b['frozenSourcePath'])/p)==d,(name,p)
    assert sha(Path(b['probePath']))==b['probeSHA256']==r['probeSHA256']
    for path,key in [('sourceOrigin','sourceOriginSHA256'),('configPath','configSHA256')]:assert sha(Path(b[path]))==b[key]
    assert sha(Path(b['probePath']).with_name('compile.log'))==b['compilerLogSHA256']
    actual={p.replace('\\','/'):d for p,d in read(f/'inputs.json').items()}
    for p,d in r['baseline'].items():
        if p not in ['application.xml','mods/loader-manifest.txt']:assert actual[p]==d,(name,p)
    assert actual['mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf']==b['probeSHA256']
    policy=read(f/'process-policy.json');loader=read(f/'loader-check.json')
    assert policy['desktopPolicy']=='private' and not policy['performanceEligible']
    assert not any(policy.get(k) for k in ['otherAirProcessIds','memoryAbort','runFailure'])
    assert len(loader['sessions'])==1 and all(loader['loaded'].values())
    assert r['memoryBeforeAir']['availableCommit']>=4*1024**3 and r['memoryBeforeAir']['availablePhysical']>=2*1024**3
    s=load(name,HERE.parent/name/'summary.py').summarize(raw);saved=read(f/'summary.json')
    assert all(saved[k]==v for k,v in s.items()) and saved['resultSHA256']==sha(f/'storage/result.json')
    result=dict(name=name+'-r1',probe=b['probeSHA256'],frozen=Path(b['frozenSourcePath']).parent.name,sourceCount=count,
        resultSHA256=sha(f/'storage/result.json'),pid=policy['pid'],verified=True,deployed=False,gameplayAcceptance=False)
    if not combat:
        t=raw['cameraRaster'];variants=3
        result.update(arms=s['arms'],pairs=s['pairs'],pixels=s['pixels'],contracts=s['atlasContracts'],cleanup=s['cleanup'],
                      frames=len(t['framesMs']),moving={str(v):metric([dt for w in t['windows'] if w['variant']==v and w['condition'] for dt in w['framesMs']]) for v in range(variants)})
    else:result.update(summary=s)
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=['quiet','combat'],required=True);a=p.parse_args()
    names=['camera-persistent-atlas-checks-20261027','camera-persistent-fullpage-20261027'] if a.phase=='quiet' else ['camera-persistent-combat-imports-20261027']
    result=dict(runs=[verify(n,a.phase=='combat') for n in names],deployed=False,gameplayAcceptance=False)
    target=HERE/(a.phase+'-review.json');assert not target.exists(),'Preserve prior review'
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps(dict(phase=a.phase,runs=len(names),sha256=sha(target),movement=[r.get('moving') for r in result['runs']]),ensure_ascii=False))
