from pathlib import Path
import importlib.util
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('native_once_summary_base',HERE.parent/'camera-environment-quiet-20261027/summary.py')
base=importlib.util.module_from_spec(s);s.loader.exec_module(base)
base.base.base.VERSION='camera-native-once-1'

def summarize(raw):
    out=base.summarize(raw);t=raw['cameraRaster']
    assert t['nativeSchedules']==961 and t['nativeCaptures']==960 and t['helperTimedCalcCalls']==0
    assert t['cleanup']['cameraHookRemoved']
    out['nativeCameraScheduling']={k:t[k] for k in ['nativeSchedules','nativeCaptures','helperTimedCalcCalls']}
    out['nativeCameraScheduling']['hookRemoved']=True
    return out
