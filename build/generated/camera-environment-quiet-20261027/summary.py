from pathlib import Path
import importlib.util
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('environment_quiet_summary',HERE.parent/'camera-visible-room-fog-history-20261027/summary.py')
base=importlib.util.module_from_spec(s);s.loader.exec_module(base);base.base.VERSION='camera-environment-quiet-1'
def summarize(raw):
    out=base.summarize(raw);c=raw['cameraRaster']['environmentChecks']
    assert c['passed']
    if c['sceneLarge']:
        assert c['mapEntryRestored'] and c['originRestored'] and c['environmentRestored']
        assert len(c['cases'])>25 and c['fieldsChecked']==20*len(c['cases']) and all(r['matched'] for r in c['cases'])
        assert {'changed-origin-x','changed-origin-y','restored-origin','replaced-entry-same-key','restored-entry-same-key'}<=set(r['label'] for r in c['cases'])
    assert 'cpuSampling' not in raw['cameraRaster']
    out['environmentChecks']=c;return out
