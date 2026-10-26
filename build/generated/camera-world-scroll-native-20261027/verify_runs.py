"""Independent retained-run audit, including exact diagnostic-host lineage."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
MOD=HERE.parents[2];GAME=MOD.parents[1]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def read(p):return json.loads(p.read_text('utf-8-sig'))
def load(name,p):
    spec=importlib.util.spec_from_file_location(name,p)
    obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj

host=read(HERE/'host-build.json')
for path,digest in host['sourceInputs'].items():assert sha(Path(path))==digest,path
assert sha(HERE/'pfe.swf')==host['candidate'] and sha(HERE/'pfe.xml')==host['candidateXML']
assert sha(HERE/'audit-proof.json')==host['audit'] and host['diagnosticOnly'] and not host['deployed']
audit=load('native_scroll_retained_host_proof',HERE/'host_patch.py')
actual_audit=audit.audit(HERE/'pfe.xml',HERE/'pfe.swf')
assert actual_audit==read(HERE/'audit-proof.json')
rows=[]
for name in ('camera-world-scroll-native-20261027','camera-world-scroll-native-cached-20261027'):
    recipe=HERE.parent/name;folder=MOD/'knowledge/experiments/evidence'/(name+'-r1')
    rec=read(folder/'runner-inputs.json');probe=read(folder/'probe-build.json')
    assert rec['hostReceipt']==host
    assert len(rec['baseline'])==526 and len(rec['runtimeInputs'])==13
    for path,digest in rec['baseline'].items():assert sha(GAME/path)==digest,path
    for group in ('runnerInputs','compilerInputs','fixtureInputs'):
        for path,digest in rec[group].items():assert sha(Path(path))==digest,(group,path)
    for path,digest in rec['runtimeInputs'].items():assert sha(GAME/path)==digest,path
    assert len(probe['frozenSourceSHA256'])==86
    for path,digest in probe['frozenSourceSHA256'].items():
        assert sha(Path(probe['frozenSourcePath'])/path)==digest,path
    assert sha(Path(probe['probePath']))==probe['probeSHA256']
    runner=load('native_scroll_review_'+name.replace('-','_'),recipe/'run.py')
    raw,actual=runner.reference.read_retained_result(folder)
    for path,digest in rec['baseline'].items():
        if path not in ('pfe.swf','application.xml','mods/loader-manifest.txt'):assert actual[path]==digest,path
    assert actual['pfe.swf']==host['candidate'] and actual[runner.base.PROBE_PATH]==probe['probeSHA256']
    summary=runner.summarize(raw)
    saved=read(folder/'summary.json')
    assert all(saved[k]==v for k,v in summary.items())
    policy=read(folder/'process-policy.json')
    assert policy['desktopPolicy']=='private' and not policy['performanceEligible']
    assert not any(policy.get(k) for k in ('otherAirProcessIds','memoryAbort','runFailure'))
    rows.append(dict(name=name,resultSHA256=sha(folder/'storage/result.json'),summarySHA256=sha(folder/'summary.json'),
        probeSHA256=probe['probeSHA256'],pid=policy['pid'],inputsUnchanged=True,samples=480,
        visualAccepted=summary['visualAccepted'],arms=summary['arms'],pairs=summary['pairs'],
        nativePositionChecks=raw['cameraRaster']['nativePositionChecks'],
        phaseObservation=summary['phaseObservation'],pixelFailures=summary['qualityFailures'],
        capturesDisposed=raw['cameraRaster']['pixelBitmapsDisposed'],cleanup=summary['cleanup']))
out=dict(complete=True,hostAudit=actual_audit,gameRuns=rows,diagnosticOnly=True,
         candidateAcceptance=False,gameplayAcceptance=False,deployed=False)
target=HERE/'runs-review.json';assert not target.exists();target.write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(dict(review=str(target),runs=[dict(name=r['name'],arms=r['arms'],visualAccepted=r['visualAccepted']) for r in rows]),ensure_ascii=False))
