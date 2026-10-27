"""Source/installation closure only. Does not compile, start AIR, or prove pixels/FPS."""
from pathlib import Path
import ast,hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def load(name,p):
    s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def main():
    r=load('persistent_offline_run',HERE/'run.py');g=r.patch.generation
    roots=[g.BASE,HERE]
    files={}
    for root in roots:
        for p in sorted(root.rglob('*')):
            if p.is_file() and p.suffix in ['.as','.py','.md']:
                assert 'probe-builds' not in p.parts and 'source-staging' not in p.parts
                if p.suffix=='.py':ast.parse(p.read_text('utf-8-sig'),filename=str(p))
                files[str(p)]=sha(p)
    for name,value in [('SceneClassicAtlas.as',g.classic_source()),('ScenePersistentAtlas.as',g.persistent_source()),('tests/SceneCameraRasterTrial.as',g.helper_source()),('run.py',g.runner_source())]:
        assert (HERE/name).read_text('utf-8-sig')==value,name
    seed=r.lineage.read_seed(r.reference)
    assert len(seed['frozenSourceSHA256'])==85
    baseline=r.r.baseline();runtime=r.reference.runtime_inputs()
    assert len(baseline)==526 and len(runtime)==13
    for p,digest in r.PINS.items():assert baseline[p]==digest,p
    failed=r.r.read(r.r.E/'camera-persistent-atlas-20261027-r1/runner-failure.json')
    assert not failed['complete'] and 'availableCommit' in failed['error']
    assert not (r.r.E/'camera-persistent-atlas-20261027-r1/probe-build.json').exists()
    result=dict(status='prepared-not-compiled',runtimeVerified=False,performanceMeasured=False,deployed=False,
        sourceInputs=files,baseline=baseline,runtimeInputs=runtime,
        runnerInputs=r.runner_inputs(),fixtureInputs=r.fixture_inputs(),compilerInputs=r.support.compiler_inputs(),
        changedSources=r.patch.CHANGED,expectedSourceCount=89,
        memory=r.control.m.memory_status(),airProcessIds=r.m.air_pids(),
        priorFailure=failed['error'],limits=['No AS3 compilation or Flash fixture execution.','No performance claim.','Memory gate remains 4GiB commit and 2GiB physical.'])
    p=HERE/'offline-review.json';assert not p.exists(),'Preserve the prior source review'
    p.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps(dict(status=result['status'],sourceFiles=len(files),sourceCount=89,memory=result['memory'],airProcessIds=result['airProcessIds'],reportSHA256=sha(p))))

if __name__=='__main__':main()
