from pathlib import Path
import importlib.util,inspect
HERE=Path(__file__).resolve().parent;VERSION='camera-persistent-rv-pixels-1'
sp=importlib.util.spec_from_file_location('rv_fixed_pixels_summary',HERE.parent/'camera-persistent-rv-20261027/summary.py')
prior=importlib.util.module_from_spec(sp);sp.loader.exec_module(prior)
p=prior.prior
p.base.VERSION=VERSION;p.base.scope['VERSION']=VERSION
prior.core.__globals__['VERSION']=VERSION;p.base.pool_verified_summary.__globals__['VERSION']=VERSION
s=inspect.getsource(p.base.summarize)
s=p.one(s,"pixels['created']==pixels['disposed']==3","pixels['created']==pixels['disposed']==7")
scope=dict(p.base.__dict__);exec(compile(s,'<fixed-seven-capture-verifier>','exec'),scope);p.base.summarize=scope['summarize']
def summarize(raw):
    result=prior.summarize(raw);pixels=raw['combatAtlasPixels']
    assert pixels['nativeRepeat']['equal'] and pixels['restoreRepeat']['equal']
    assert pixels['atlasRepeat']['maxRGB']<=2 and pixels['atlasRepeat']['maxAlpha']==0
    result['limitations']=[x.replace('Three synchronous terminal combat screenshots','Seven fixed-order synchronous terminal screenshots (initial native capture retained, second/third must match before atlas)') for x in result['limitations']]
    return result
