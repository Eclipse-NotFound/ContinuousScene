from pathlib import Path
import copy,importlib.util
HERE=Path(__file__).resolve().parent;VERSION='camera-persistent-fullpage-1'
sp=importlib.util.spec_from_file_location('fullpage_summary_base',HERE.parent/'camera-persistent-atlas-checks-20261027/summary.py')
base=importlib.util.module_from_spec(sp);sp.loader.exec_module(base);base.base.VERSION=VERSION
def summarize(raw):
    # The prior verifier uses fixed labels. Verify the new labels first, then
    # translate a copy for its unchanged timing/pixel/ownership assertions.
    data=copy.deepcopy(raw)
    old=['native','classic','persistent'];new=['native','bound','fullpage']
    axes=['static','horizontal','vertical','combined']
    for row in data['cameraRaster']['windows']:
        assert row['mode']==new[row['variant']]+'-'+axes[row['condition']]
        row['mode']=old[row['variant']]+'-'+axes[row['condition']]
    result=base.summarize(data)
    rename={old[i]+'-'+a:new[i]+'-'+a for i in range(3) for a in axes}
    for key in ['arms','timingBands']:result[key]={rename[k]:v for k,v in result[key].items()}
    result['rendererMapping']={'classic':'previous persistent visible-cell contents','persistent':'new persistent full-page contents'}
    return result
