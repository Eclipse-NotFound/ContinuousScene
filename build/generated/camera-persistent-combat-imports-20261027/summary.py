from pathlib import Path
import importlib.util
HERE=Path(__file__).resolve().parent;VERSION='camera-persistent-combat-imports-1'
sp=importlib.util.spec_from_file_location('persistent_combat_summary_base',HERE.parent/'camera-atlas-merged-combat-20261026/run.py')
base=importlib.util.module_from_spec(sp);sp.loader.exec_module(base)
legacy_page=base.page_state
def page_state(state):
    assert state['version']=='persistent-atlas-1'
    adapted=dict(state,version='atlas-pool-1');legacy_page(adapted)
base.VERSION=VERSION;base.page_state=page_state;base.scope['page_state']=page_state
def summarize(raw):
    result=base.summarize(raw)
    assert raw['nativeWindowRestored'] and not [e for e in raw['nativeWindowEvents'] if e['phase']>=2]
    v=raw['nativeCombatView'];assert v['visible'] and v['worldVisible'] and not v['menuActive']
    assert v['width']>=1900 and v['height']>=1000
    result['nativeCombatView']=v
    return result
