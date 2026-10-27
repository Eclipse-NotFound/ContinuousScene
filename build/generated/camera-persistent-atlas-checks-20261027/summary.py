from pathlib import Path
import importlib.util
VERSION='camera-persistent-atlas-checks-1'
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('persistent_checked_summary_base',HERE.parent/'camera-persistent-atlas-20261027/summary.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base);base.VERSION=VERSION

def summarize(raw):
    result=base.summarize(raw)
    c=raw['cameraRaster']['atlasContracts']
    assert c['complete'] and c['passed'] and not c['errors'] and c['holderDetached']
    assert c['sourceCreated']==c['sourceDisposed']==132
    assert c['pixelCreated']==c['pixelDisposed']==34
    assert [x['name'] for x in c['cases']]==['first','steady-repeat','within-cell-camera','cross-cell-camera','cross-page-camera','return-to-first','native-pixel-revision','same-count-native-replacement','invisible-foreign-child','foreign-visibility-fallback','foreign-child-removed','sats-fallback','sats-return','explicit-native-restore','native-to-atlas-return','final-native-restore']
    for case in c['cases']:
        p=case['pixels'];assert p['maxRGB']<=2 and p['maxAlpha']==0
        if not case['presented']:assert p['differentPixels']==0
    for state in [c['afterClear'],c['cleanup']]:
        assert state['allocations']==state['disposals']==32
        assert state['ownedBitmaps']==state['pendingHidden']==state['attached']==state['pixelStorageBytes']==0
    result['atlasContracts']=c
    return result
