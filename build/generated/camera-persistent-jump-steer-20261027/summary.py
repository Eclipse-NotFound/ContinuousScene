from pathlib import Path
import importlib.util,inspect
HERE=Path(__file__).resolve().parent;VERSION='camera-persistent-jump-steer-1'
sp=importlib.util.spec_from_file_location('jump_steer_summary_base',HERE.parent/'camera-persistent-jump-20261027/summary.py')
prior=importlib.util.module_from_spec(sp);sp.loader.exec_module(prior)
p=prior.prior
p.base.VERSION=VERSION;p.base.scope['VERSION']=VERSION;p.core.__globals__['VERSION']=VERSION
p.base.pool_verified_summary.__globals__['VERSION']=VERSION
s=inspect.getsource(p.base.dense.workload)
s=p.one(s,"assert data['left'][i] != data['right'][i] and data['runKey'][i] and not data['jumpKey'][i]",
    "assert data['left'][i] != data['right'][i] and data['runKey'][i] and type(data['jumpKey'][i]) is bool")
# A real jump can occupy a complete 60-frame window. Require landing coverage
# for each full comparison arm below, while retaining every per-frame check.
s=p.one(s,"assert max(data['x']) - min(data['x']) > 1 and any(data['floorContact'])",
    "assert max(data['x']) - min(data['x']) > 1")
p.core.__globals__['dense'].workload=p.compiled(s,p.base.dense.__dict__,{300:60},{300:3})
def summarize(raw):
    result=prior.summarize(raw)
    assert raw['jumpSteering']==dict(groundLookahead=4,airLookahead=30,positionOrVelocityWrites=False)
    for on in (False,True):
        rows=[r for i,r in enumerate(raw['samples']) if (i%4 in (1,2))==on]
        contacts=sum(sum(r['denseFrames']['floorContact']) for r in rows)
        assert contacts>=40,'Each full arm must contain genuine floor contact'
        result['jumpEvidence'][str(on)]['floorContactFrames']=contacts
    result['jumpSteering']=raw['jumpSteering']
    return result
