"""Successor recipe: same camera sampling, explicitly recorded startup policy."""
from pathlib import Path
import ast, importlib.util
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-visible-room-sampling-20261027'
VERSION='camera-visible-room-sampling-policy-1'
def load(name,p):
    sp=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
base=load('room_sampling_policy_base',BASE/'prepare.py');one=base.one
SAMPLER=base.SAMPLER
def helper_source():return base.helper_source().replace(base.VERSION,VERSION)
def sampler_source():return base.sampler_source()
def runner_source():
    s=base.runner_source().replace(base.VERSION,VERSION)
    s=s.replace("HERE.parent/'camera-terrain-layers-20261025/lineage.py'", "HERE/'lineage.py'")
    s=one(s,"PINS = dict(reference.PINS)","""PINS = dict(reference.PINS)
STARTUP_POLICIES=[]
original_hidden_process=m.HiddenProcess
def recorded_hidden_process(*args,**kwargs):
    process=original_hidden_process(*args,**kwargs)
    STARTUP_POLICIES.append(dict(pid=process.pid,policy=getattr(process,'resource_policy',None)))
    return process
m.HiddenProcess=recorded_hidden_process
""")
    anchor="patch.HELPER, patch.ORIGINAL, patch.PATCH_SOURCE, *patch.EXTRA_INPUTS)"
    assert s.count(anchor)==2
    s=s.replace(anchor,"patch.HELPER, patch.ORIGINAL, patch.PATCH_SOURCE, *patch.EXTRA_INPUTS, *lineage.tool_paths(reference))")
    s=one(s,"            finally:\n                if folder.exists():", "            finally:\n                record['startupResourcePolicies']=STARTUP_POLICIES\n                if folder.exists():")
    s=one(s,"            summary=summarize(raw)","""            assert len(STARTUP_POLICIES)==1 and STARTUP_POLICIES[0]['pid']==policy['pid']
            applied=STARTUP_POLICIES[0]['policy']
            assert applied['requested']=='test' and not applied['errors'] and not applied['after']['errors']
            assert applied['after']['cpuPriorityClass']==0x20 and applied['after']['memoryPriority']==5
            assert applied['after']['powerThrottling']['highQoS']
            summary=summarize(raw)""")
    return s
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    for name,s in [('tests/SceneCameraRasterTrial.as',helper_source()),('tests/SceneCameraSampler.as',sampler_source()),('run.py',runner_source())]:
        p=HERE/name
        if p.suffix=='.py':ast.parse(s)
        if p.exists():assert p.read_text('utf-8-sig')==s
        else:p.write_text(s,'utf-8')
    print('Prepared sampling successor; private-desktop startup policy retained and recorded')
