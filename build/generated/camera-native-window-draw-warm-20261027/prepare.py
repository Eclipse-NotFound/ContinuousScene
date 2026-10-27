"""Realize each transferred Stage once before three independent exact roundtrips."""
from pathlib import Path
import importlib.util,ast
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-native-window-audit-20261027'
spec=importlib.util.spec_from_file_location('window_draw_warm_seed',BASE/'prepare.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
def helper_source():
    s=old.helper_source().replace('camera-native-window-audit-1','camera-native-window-draw-warm-1')
    return old.one(s,'switchNativeWindow(1);switchNativeWindow(2);switchNativeWindow(0);\n                result.roundtrips=[];', '''var warmInitial:BitmapData=capture();result.fixedWarmDraws=[];
                for each(var warmMode:int in [1,2,0]) {
                    switchNativeWindow(warmMode);
                    var warmImage:BitmapData=capture();result.fixedWarmDraws.push({mode:warmMode,change:compare(warmInitial,warmImage)});
                }
                disposeOwned();
                result.roundtrips=[];''')
def runner_source():
    return old.runner_source().replace('camera-native-window-audit-1','camera-native-window-draw-warm-1').replace("trial['pixelBitmapsDisposed']==75","trial['pixelBitmapsDisposed']==95")
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    for path,code in [(HERE/'tests/SceneCameraRasterTrial.as',helper_source()),(HERE/'run.py',runner_source())]:
        if path.suffix=='.py':ast.parse(code)
        if path.exists():assert path.read_text('utf-8-sig')==code,path
        else:path.write_text(code,'utf-8')
    print('Prepared fixed realized-draw warmup; three exact checks still required')
