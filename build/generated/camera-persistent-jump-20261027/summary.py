from pathlib import Path
import importlib.util,inspect
HERE=Path(__file__).resolve().parent;VERSION='camera-persistent-jump-1'
sp=importlib.util.spec_from_file_location('jump_summary_base',HERE.parent/'camera-persistent-repeated-20261027/summary.py')
prior=importlib.util.module_from_spec(sp);sp.loader.exec_module(prior)
prior.base.VERSION=VERSION;prior.base.scope['VERSION']=VERSION
prior.core.__globals__['VERSION']=VERSION
prior.base.pool_verified_summary.__globals__['VERSION']=VERSION
s=inspect.getsource(prior.base.dense.workload)
s=prior.one(s,"assert data['left'][i] != data['right'][i] and data['runKey'][i] and not data['jumpKey'][i]",
    "assert data['left'][i] != data['right'][i] and data['runKey'][i] and type(data['jumpKey'][i]) is bool")
jump_workload=prior.compiled(s,prior.base.dense.__dict__,{300:60},{300:3})
prior.core.__globals__['dense'].workload=jump_workload
def summarize(raw):
    result=prior.summarize(raw)
    assert raw['jumpInput']==dict(commands=1200,pressed=56,period=90,hold=4)
    axes={}
    for on in (False,True):
        rows=[w for i,w in enumerate(raw['samples']) if (i%4 in (1,2))==on]
        ys=[y for w in rows for y in w['denseFrames']['y']]
        vys=[y for w in rows for y in w['atlasMotion']['vy']]
        airborne=sum(not grounded for w in rows for grounded in w['denseFrames']['stay'])
        keys=sum(x for w in rows for x in w['denseFrames']['jumpKey'])
        assert airborne>=30 and keys>=16 and max(ys)-min(ys)>=50
        assert max(vys)-min(vys)>=10,'Jump did not exercise vertical camera movement'
        axes[str(on)]=dict(playerY=[min(ys),max(ys)],cameraY=[min(vys),max(vys)],airborneFrames=airborne,observedJumpKeys=keys)
    result['jumpEvidence']=axes
    result['limitations']=[x.replace('no jump input or per-frame teleport','native jump-key pulses; no per-frame teleport') for x in result['limitations']]
    return result
