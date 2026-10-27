from pathlib import Path
import ast,importlib.util
HERE=Path(__file__).resolve().parent;BASE=HERE.parent/'camera-persistent-fullpage-20261027'
VERSION='camera-persistent-pagesize-1'
def load(name,p):
    sp=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
base=load('persistent_pagesize_generation',BASE/'prepare.py');one=base.one
def classic_source():return base.persistent_source().replace('class ScenePersistentAtlas','class SceneClassicAtlas')
def persistent_source():
    s=base.persistent_source()
    for a,b in [
        ('PAGE:int=1280','PAGE:int=2560'),('LIMIT:int=8','LIMIT:int=4'),
        ('LAYER_BYTES:Number=1280*1280*4','LAYER_BYTES:Number=2560*2560*4'),
        ('cell<16','cell<64'),
    ]:
        expected=2 if a=='cell<16' else 1
        assert s.count(a)==expected,(a,s.count(a));s=s.replace(a,b)
    assert s.count('new Array(16)')==2;s=s.replace('new Array(16)','new Array(64)')
    assert s.count('(cell%4)*CELL,int(cell/4)*CELL')==2;s=s.replace('(cell%4)*CELL,int(cell/4)*CELL','(cell%8)*CELL,int(cell/8)*CELL')
    s=one(s,'page.px*4+cell%4,cy:int=page.py*4+int(cell/4)','page.px*8+cell%8,cy:int=page.py*8+int(cell/8)')
    return s
def fixture_source():
    s=(BASE/'tests/ScenePersistentAtlasChecks.as').read_text('utf-8-sig')
    s=one(s,'cx<8;++cx','cx<12;++cx')
    s=one(s,'setView(ctx,1300,50);checkpoint(ctx,"cross-page-camera");','setView(ctx,2570,50);checkpoint(ctx,"cross-page-camera");')
    return s
def helper_source():
    s=base.helper_source().replace(base.VERSION,VERSION)
    s=one(s,'["native-","bound-","fullpage-"]','["native-","page1280-","page2560-"]')
    s=one(s,'Compare current native scene, persistent visible-cell atlas, and persistent full-page contents. Full timing and switches retained; no bitmap geometry changes.',
        'Compare native scene, 1280px full pages (8 slots/200MiB) and 2560px full pages (4 slots/400MiB). All timing, preparation and memory costs retained; not a deployed memory policy.')
    return s
def runner_source():return base.runner_source().replace(base.VERSION,VERSION)
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    for name,s in [('SceneClassicAtlas.as',classic_source()),('ScenePersistentAtlas.as',persistent_source()),('tests/ScenePersistentAtlasChecks.as',fixture_source()),('tests/SceneCameraRasterTrial.as',helper_source()),('run.py',runner_source())]:
        p=HERE/name
        if p.suffix=='.py':ast.parse(s)
        if p.exists():assert p.read_text('utf-8-sig')==s
        else:p.write_text(s,'utf-8')
    print('Prepared 1280/2560 full-page comparison with explicit 200/400MiB budgets')
