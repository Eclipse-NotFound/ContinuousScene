from pathlib import Path
import ast,importlib.util
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-far-live-visibility-20261027'
WARM=HERE.parent/'camera-native-effects-overlay-20261027/tests/SceneCameraRasterTrial.as'
VERSION='camera-far-live-warm-1'
def helper_source():
    s=(BASE/'tests/SceneCameraRasterTrial.as').read_text('utf-8-sig').replace('camera-far-live-visibility-1',VERSION)
    warm=WARM.read_text('utf-8-sig');a=warm.index('        private function warmNative(');b=warm.index('        private function ',a+20)
    start=s.index('        private function warmNative(');end=s.index('        private var routeBounds:',start)
    return s[:start]+warm[a:b]+s[end:]
def runner_source():
    s=(BASE/'run.py').read_text('utf-8-sig').replace('camera-far-live-visibility-1',VERSION)
    return s.replace("==110 and cleanup['terrainRestored']", "==150 and cleanup['terrainRestored']")
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    for path,code in [(HERE/'tests/SceneCameraRasterTrial.as',helper_source()),(HERE/'run.py',runner_source())]:
        if path.suffix=='.py':ast.parse(code)
        if path.exists():assert path.read_text('utf-8-sig')==code,path
        else:path.write_text(code,'utf-8')
    print('Prepared existing full-offset warm-up with unchanged exact pixel gate')
