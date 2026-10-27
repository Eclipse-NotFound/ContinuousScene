"""Post-hoc review; preserve the original tool-drift failure classification."""
from pathlib import Path
import collections,hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent;MOD=HERE.parents[2];ROOT=MOD.parents[1]
E=MOD/'knowledge/experiments/evidence';PRIOR=HERE.parent/'camera-visible-room-sampling-policy-20261027'
OLD='E9F51CB75420C507F6DB1D96BE6B1430374B0B7A797607FF4438A695A717809E'
NEW='E3E43581D677D26C83B7E887C64669634CCC8D901AEFA5A826E1CFED8A5F0CF0'
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def load(p):
    sp=importlib.util.spec_from_file_location('prior_sample_summary',p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
def main():
    registry=ROOT/'mods/ModLoader/tools/test_registry.py';b=registry.read_bytes()
    new=b'text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=15, check=True,'
    old=b'text=True, capture_output=True, timeout=15, check=True,'
    assert sha(registry)==NEW and b.count(new)==1
    assert hashlib.sha256(b.replace(new,old)).hexdigest().upper()==OLD
    records=[];raws={};probes=[]
    for mode in ['scene','normal']:
        name=PRIOR.name+'-'+mode+'-r1';folder=E/name
        r=read(folder/'runner-inputs.json');probe=read(folder/'probe-build.json');raw=read(folder/'storage/result.json')
        assert len(r['baseline'])==526 and len(r['runtimeInputs'])==13
        for key in ['baseline','runtimeInputs']:
            for p,d in r[key].items():assert sha(ROOT/p)==d,(name,p)
        drifts=[]
        for key in ['runnerInputs','fixtureInputs','compilerInputs']:
            for p,d in r[key].items():
                actual=sha(Path(p))
                if actual!=d:
                    assert key=='runnerInputs' and Path(p).resolve()==registry.resolve() and d==OLD and actual==NEW
                    drifts.append(dict(path=p,expected=d,current=actual,reverseExact=True))
        assert len(drifts)==1
        assert len(probe['frozenSourceSHA256'])==87
        for p,d in probe['frozenSourceSHA256'].items():assert sha(Path(probe['frozenSourcePath'])/p)==d
        for p,k in [('sourceOrigin','sourceOriginSHA256'),('configPath','configSHA256')]:assert sha(Path(probe[p]))==probe[k]
        assert sha(Path(probe['probePath']))==probe['probeSHA256']==r['probeSHA256'];probes.append(probe['probeSHA256'])
        actual={p.replace('\\','/'):d for p,d in read(folder/'inputs.json').items()}
        for p,d in r['baseline'].items():
            if p not in ['application.xml','mods/loader-manifest.txt']:assert actual[p]==d
        assert actual['mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf']==probe['probeSHA256']
        policy=read(folder/'process-policy.json');loader=read(folder/'loader-check.json')
        assert policy['desktopPolicy']=='private' and not policy['performanceEligible']
        assert not any(policy.get(k) for k in ['otherAirProcessIds','memoryAbort','runFailure'])
        assert len(loader['sessions'])==1 and all(loader['loaded'].values())
        assert r['memoryBeforeAir']['availableCommit']>=4*1024**3 and r['memoryBeforeAir']['availablePhysical']>=2*1024**3
        startup=r['startupResourcePolicies'];assert len(startup)==1 and startup[0]['pid']==policy['pid']
        applied=startup[0]['policy'];assert not applied['errors'] and not applied['after']['errors']
        assert applied['requested']=='test' and applied['after']['cpuPriorityClass']==32 and applied['after']['memoryPriority']==5
        assert applied['after']['powerThrottling']['highQoS']
        summary=load(PRIOR/'summary.py').summarize(raw)
        assert (folder/'runner-failure.json').exists()==(mode=='normal')
        if mode=='normal':assert read(folder/'runner-failure.json')['error']=='AssertionError()'
        groups={}
        for w in raw['cameraRaster']['cpuSampling']['windows']:
            top=collections.Counter()
            for row in w['stacks']:
                names=row['names'];n=row['samples'];assert isinstance(n,int) and n>0
                top[names[0] or '<anonymous>' if names else '<empty-stack>']+=n
            assert dict(top)=={v['name']:v['samples'] for v in w['top']}
            group=groups.setdefault(w['name'],dict(cpu=0,newObject=0,deleteObject=0,windows=0,top=collections.Counter()))
            for k in ['cpu','newObject','deleteObject']:group[k]+=w['counts'][k]
            group['windows']+=1;group['top'].update(top)
        for v in groups.values():v['top']=v['top'].most_common()
        records.append(dict(name=name,originalRunnerPassed=mode=='scene',actualAIRCompleted=True,
            postHocDiagnosticReview=True,performanceAcceptance=False,probeSHA256=probe['probeSHA256'],
            resultSHA256=sha(folder/'storage/result.json'),knownToolDrift=drifts,groups=groups))
        raws[mode]=raw['cameraRaster']
    assert len(set(probes))==1
    for a,b in zip(raws['normal']['windows'],raws['scene']['windows']):
        assert len(a['cameraX'])==len(b['cameraX'])==120
        assert [v-5760 for v in b['cameraX']]==a['cameraX']
        assert [v-3000 for v in b['cameraY']]==a['cameraY']
    out=HERE/'prior-sampling-review.json';assert not out.exists()
    out.write_text(json.dumps(dict(records=records,matched960CameraCoordinates=True,deployed=False,
        limitation='Original normal run failed its final live-tool hash check; this review does not rewrite that failure. Exact encoding-only registry drift verified. CPU occurrences and AS allocation counts are diagnostic, not durations or FPS.'),ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps(dict(reviewed=True,sha256=sha(out),originalRunnerPasses=[r['originalRunnerPassed'] for r in records])))
if __name__=='__main__':main()
