from pathlib import Path
import ast,importlib.util
HERE=Path(__file__).resolve().parent;BASE=HERE.parent/'camera-opaque-tiles-20261027'
VERSION='camera-empty-native-tiles-1'
def load(name,p):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
base=load('empty_opaque_generation',BASE/'prepare.py')
def helper_source():
    s=base.helper_source().replace(base.VERSION,VERSION)
    return s.replace('SceneOpaqueTiles','SceneEmptyTiles').replace('opaque','empty').replace('Opaque','Empty').replace('Only fully empty native terrain buffers use nontransparent copies; original pixels, crop, transform and ordering remain. All intervals retained.','Only wholly transparent native terrain buffers have their display bitmapData temporarily unbound; original pixels, crop, transform and ordering remain. All intervals retained.')
def runner_source():
    return base.runner_source().replace(base.VERSION,VERSION).replace('native opaque terrain copies','native fully transparent terrain').replace('opaque terrain camera','empty terrain camera')
def summary_source():
    s=(BASE/'summary.py').read_text('utf-8-sig').replace(base.VERSION,VERSION).replace('opaque','empty').replace('Opaque','Empty')
    old="g['selected']==g['allocated']==g['disposed']"
    assert s.count(old)==1;s=s.replace(old,"g['selected'] and g['allocated']==g['disposed']==0")
    return s.replace("g['bytes']<=128*1024**2","g['bytes']==0")
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    for name,s in [('tests/SceneCameraRasterTrial.as',helper_source()),('run.py',runner_source()),('summary.py',summary_source())]:
        p=HERE/name
        if p.suffix=='.py':ast.parse(s)
        if p.exists():assert p.read_text('utf-8-sig')==s
        else:p.write_text(s,'utf-8')
    print('Prepared fully transparent native bitmap unbinding; no own pixel stores')
