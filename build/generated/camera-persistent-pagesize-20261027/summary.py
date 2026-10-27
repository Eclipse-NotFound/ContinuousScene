from pathlib import Path
import copy,importlib.util,inspect
HERE=Path(__file__).resolve().parent;VERSION='camera-persistent-pagesize-1'
sp=importlib.util.spec_from_file_location('pagesize_checked_base',HERE.parent/'camera-persistent-atlas-checks-20261027/summary.py')
base=importlib.util.module_from_spec(sp);sp.loader.exec_module(base)
def one(s,a,b):
    assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
def compile_function(s,scope):
    local=dict(scope);exec(compile(s,'<explicit-page-budget-verifier>','exec'),local);return local['summarize']
s=inspect.getsource(base.base.summarize)
s=one(s,"assert initial['allocations']==initial['ownedBitmaps']==32 and initial['pixelStorageBytes']==200*1024**2",
    "count=32 if kind=='classic' else 16;size=200 if kind=='classic' else 400\n        assert initial['allocations']==initial['ownedBitmaps']==count and initial['pixelStorageBytes']==size*1024**2")
s=one(s,"assert end['allocations']==end['disposals']==32 and", "assert end['allocations']==end['disposals']==count and")
s=one(s,"for kind in ['classic','persistent']:assert state[kind]['allocations']==32 and state[kind]['ownedBitmaps']==32",
    "for kind in ['classic','persistent']:\n                count=32 if kind=='classic' else 16\n                assert state[kind]['allocations']==count and state[kind]['ownedBitmaps']==count")
base.base.summarize=compile_function(s,dict(base.base.__dict__,VERSION=VERSION))
s=inspect.getsource(base.summarize)
s=one(s,"c['sourceCreated']==c['sourceDisposed']==132","c['sourceCreated']==c['sourceDisposed']==196")
s=one(s,"state['allocations']==state['disposals']==32","state['allocations']==state['disposals']==16")
checked=compile_function(s,base.__dict__)
def summarize(raw):
    data=copy.deepcopy(raw);old=['native','classic','persistent'];new=['native','page1280','page2560'];axes=['static','horizontal','vertical','combined']
    for row in data['cameraRaster']['windows']:
        assert row['mode']==new[row['variant']]+'-'+axes[row['condition']]
        row['mode']=old[row['variant']]+'-'+axes[row['condition']]
    result=checked(data);rename={old[i]+'-'+a:new[i]+'-'+a for i in range(3) for a in axes}
    for key in ['arms','timingBands']:result[key]={rename[k]:v for k,v in result[key].items()}
    result['rendererMapping']={'classic':'1280px full pages, 8 slots, 200MiB','persistent':'2560px full pages, 4 slots, 400MiB'}
    return result
