"""Repair one post-processing assumption, preserving failed runner/evidence."""
from pathlib import Path
import importlib.util
import inspect
import hashlib
import json

HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('backdrop_original_runner',HERE/'run.py')
run=importlib.util.module_from_spec(s);s.loader.exec_module(run)
assert run.r.sha(HERE/'run.py')=='0868992796FFD4DD34825DE98DF9259047A7CF81D02330DF7F90FC173441E80E'
folder=run.r.E/'camera-backdrop-cache-20261026-r1'
record=run.r.read(folder/'runner-inputs.json')
assert record['baseline']==run.r.baseline() and record['runnerInputs']==run.runner_inputs()
assert record['compilerInputs']==run.support.compiler_inputs() and record['fixtureInputs']==run.fixture_inputs()
assert record['runtimeInputs']==run.reference.runtime_inputs()
run.verify_probe(Path(record['probeBuildPath']),record['baseline'],record['runnerInputs'],record['compilerInputs'],record['fixtureInputs'])
raw,actual=run.reference.read_retained_result(folder)
for path,digest in record['baseline'].items():
    if path not in ('application.xml','mods/loader-manifest.txt'):assert actual[path]==digest,path
assert actual[run.base.PROBE_PATH]==record['probeSHA256']
policy=run.r.read(folder/'process-policy.json')
assert policy['desktopPolicy']=='private' and not policy['performanceEligible']
assert not policy.get('otherAirProcessIds') and not policy.get('memoryAbort') and not policy.get('runFailure')
failure=run.r.read(folder/'runner-failure.json')
assert 'parents\']==4' in failure['traceback'] and failure['error']=='AssertionError()'
original=inspect.getsource(run.summarize)
old="row['presentation']['active'] and row['presentation']['parents']==4"
new="row['presentation']['active'] and row['presentation']['parents']==1 and row['presentation']['actualCache'] is True"
assert original.count(old)==1
fixed=original.replace(old,new,1)
assert fixed.replace(new,old,1)==original
old_frame="p['active'] is (condition>=2) and p['parents']==(4 if condition>=2 else 0)"
new_frame="p['active'] is (condition>=2) and p['parents']==(1 if condition>=2 else 0)"
assert fixed.count(old_frame)==1
fixed=fixed.replace(old_frame,new_frame,1)
assert fixed.replace(new_frame,old_frame,1).replace(new,old,1)==original
scope=dict(run.__dict__);exec(compile(fixed,'<one-backdrop-summary>','exec'),scope)
summary=scope['summarize'](raw)
summary.update(postprocessCorrected=True,originalRunnerStillFailed=True,
    onlyCorrection='Require one scenery backdrop instead of four terrain layers in pixel snapshots and frame snapshots.',
    resultSHA256=run.r.sha(folder/'storage/result.json'),probeSHA256=record['probeSHA256'],
    inputsUnchanged=True,runtimeInputsUnchanged=True,sourceReverseExact=True)
target=folder/'summary-corrected.json';assert not target.exists()
run.r.save(target,summary)
print(json.dumps(dict(complete=summary['complete'],arms=summary['arms'],originalRunnerStillFailed=True)))
