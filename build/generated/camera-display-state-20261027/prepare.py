"""Prepare bounded read-only metadata probe; no production mutation."""
from pathlib import Path
import importlib.util
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('display_state_patch',HERE/'probe_patch.py')
patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)
content=patch.helper_source();patch.HELPER.parent.mkdir(parents=True,exist_ok=True)
if patch.HELPER.exists():assert patch.HELPER.read_text('utf-8-sig')==content
else:patch.HELPER.write_text(content,'utf-8')
source=(HERE.parent/'camera-display-pixels-20261027/run.py').read_text('utf-8-sig')
source=source.replace("VERSION = 'camera-display-pixels-1'","VERSION = 'camera-display-state-1'")
start=source.index('def summarize(raw):');end=source.index('\n\ndef main():',start)
source=source[:start]+'''def summarize(raw):
    assert raw['ok'] and raw['error'] is None and not raw['samples']
    trial,cleanup=raw['cameraRaster'],raw['cameraRasterCleanup']
    assert trial['version']==VERSION and trial['complete'] and trial['passed'] and not trial['errors']
    assert trial['nativeRepeat']['equal'] and trial['pixelsValid'] and len(trial['pixels'])==1
    assert trial['measurementFrames']==0 and not trial['framesMs'] and not trial['windows']
    assert len(trial['nodeSnapshots'])==15
    assert all(not v['errors'] for v in trial['nodeSnapshots'])
    assert cleanup==trial['cleanup'] and cleanup['restored'] and not cleanup['errors']
    assert cleanup['pendingOwnedBitmaps']==0
    assert trial['pixelBitmapsCreated']==trial['pixelBitmapsDisposed']==8
    return dict(version=VERSION,complete=True,diagnosticOnly=True,performanceEligible=False,
        gameplayAcceptance=False,deployed=False,nativeRepeat=trial['nativeRepeat'],
        pixels=trial['pixels'],nodeSnapshots=len(trial['nodeSnapshots']),cleanup=cleanup)
''' + source[end:]
source=source.replace("arms=summary['arms'],pairs=summary['pairs']","nativeRepeat=summary['nativeRepeat']")
source=source.replace('960 camera backdrop/object-layer alpha controls; diagnostic only, no deployment','Display-state metadata and unchanged alpha restoration; zero timing, no deployment')
source=source.replace('ContinuousScene / camera display contribution / 01a13816','ContinuousScene / camera display state / 01a13816')
target=HERE/'run.py'
if target.exists():assert target.read_text('utf-8-sig')==source
else:target.write_text(source,'utf-8')
print('Prepared display metadata and immediate native repeat; zero timing samples')
