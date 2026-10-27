from pathlib import Path
import ast
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-far-live-cohort-20261027'
VERSION='camera-far-live-counts-1'
def helper_source():
    s=(BASE/'tests/SceneCameraRasterTrial.as').read_text('utf-8-sig').replace('camera-far-live-cohort-1',VERSION)
    old='--report.rootSelection.classes[getQualifiedClassName(root)];'
    assert s.count(old)==1
    return s.replace(old,'var classKey:String=getQualifiedClassName(root);report.rootSelection.classes[classKey]=int(report.rootSelection.classes[classKey])-1;')
def runner_source():return (BASE/'run.py').read_text('utf-8-sig').replace('camera-far-live-cohort-1',VERSION)
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    for path,code in [(HERE/'tests/SceneCameraRasterTrial.as',helper_source()),(HERE/'run.py',runner_source())]:
        if path.suffix=='.py':ast.parse(code)
        if path.exists():assert path.read_text('utf-8-sig')==code,path
        else:path.write_text(code,'utf-8')
    print('Prepared explicit dynamic class counter update')
