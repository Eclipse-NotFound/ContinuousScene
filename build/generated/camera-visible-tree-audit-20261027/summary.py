from pathlib import Path
import importlib.util
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('tree_bands_summary',HERE.parent/'camera-active-quiet-bands-20261027/summary.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base);base.base.VERSION='camera-visible-tree-audit-1'
def summarize(raw):
    out=base.summarize(raw);t=raw['cameraRaster'];assert t['cameraRouteFollowsInitialPlayer']
    assert raw['config']['benchmark']=='scene'
    for p in t['pixels']:assert p['visibleCoverage']['fraction']>=0.15
    for s in t['windows']:
        for pose,x,y in zip(s['gg'],s['vx'],s['vy']):assert 64<pose['x']+x<1216 and 128<pose['y']+y<656
    out['treeAudit']={}
    for k in ['fullTreeBeforeRemoval','quietTree']:
        a=t[k];assert a['complete'] and a['readOnly'] and not a['errors']
        assert len(a['nodes'])<=20000 and a['nodes'][0]['role']=='stage'
        assert [n['id'] for n in a['nodes']]==list(range(len(a['nodes'])))
        assert all(n['parent']<n['id'] for n in a['nodes'])
        assert sum(b['width']*b['height']*4 for b in a['bitmaps'])==a['uniqueBitmapBytes']
        out['treeAudit'][k]={field:a[field] for field in ['effectiveNodes','cachedNodes','filteredNodes','uniqueBitmapBytes','worldUnits','elapsedMs']}
        out['treeAudit'][k].update(nodes=len(a['nodes']),bitmaps=len(a['bitmaps']))
    out['playerVisibleAll960Intervals']=True
    out['visibleCoverage']=[p['visibleCoverage'] for p in t['pixels']]
    return out
