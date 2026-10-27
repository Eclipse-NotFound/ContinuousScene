from pathlib import Path
import importlib.util
HERE=Path(__file__).resolve().parent;VERSION='camera-persistent-rv-1'
sp=importlib.util.spec_from_file_location('rv_repeated_summary',HERE.parent/'camera-persistent-repeated-20261027/summary.py')
prior=importlib.util.module_from_spec(sp);sp.loader.exec_module(prior)
prior.base.VERSION=VERSION;prior.base.scope['VERSION']=VERSION
s=prior.one(prior.s,"cfg['noWall'] and not cfg['vision']","cfg['noWall'] and cfg['vision']")
scope=dict(prior.scope,VERSION=VERSION)
core=prior.compiled(s,scope,{300:60},{300:6})
prior.base.pool_verified_summary.__globals__['pool_summary']=core
prior.base.pool_verified_summary.__globals__['VERSION']=VERSION
def summarize(raw):
    result=prior.summarize(raw);a=raw['rvReaderBefore'];b=raw['rvReaderAfter']
    assert raw['rvProviderRemoved']
    for s in [a,b]:assert s['active'] and s['enabled'] and s['mode']=='current' and s['errorCount']==0
    assert b['calls']-a['calls']>=600 and b['provided']-a['provided']>=200
    result['rvReader']=dict(before=a,after=b,providerRemoved=True)
    result['limitations']=[x.replace('Lighting, vision and WallBlend are off','Lighting and WallBlend are off; current-mode RV uses the explicit isolated candidate reader') for x in result['limitations']]
    return result
