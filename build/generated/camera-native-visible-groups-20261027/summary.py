from pathlib import Path
import importlib.util
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('near_groups_summary',HERE.parent/'camera-native-near-groups-20261027/summary.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base);base.VERSION='camera-native-visible-groups-1'
def summarize(raw):
    out=base.summarize(raw);t=raw['cameraRaster'];assert t['cameraRouteFollowsInitialPlayer']
    for p in t['pixels']:assert p['visibleCoverage']['fraction']>=0.15
    for s in t['windows']:
        for pose,x,y in zip(s['gg'],s['vx'],s['vy']):
            assert 64<pose['x']+x<1216 and 128<pose['y']+y<656
    out['playerVisibleAll1920Intervals']=True
    out['visibleCoverage']=[p['visibleCoverage'] for p in t['pixels']]
    out['roomAxis']=t['roomAxis']
    return out
