from pathlib import Path
import ast,importlib.util,shutil
HERE=Path(__file__).resolve().parent;BASE=HERE.parent/'camera-persistent-atlas-checks-20261027'
VERSION='camera-persistent-fullpage-1'
def load(name,p):
    sp=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
base=load('fullpage_generator_base',BASE/'prepare.py');one=base.one

def classic_source():return base.persistent_source().replace('class ScenePersistentAtlas','class SceneClassicAtlas')
def persistent_source():
    s=base.persistent_source()
    s=one(s,'record.shown[1]!==Boolean(expectedVisibility[surface.bitmaps[1]]) ||\n                    record.shown[2]!==Boolean(expectedVisibility[surface.bitmaps[2]]);',
          'record.shown[1]!==true || record.shown[2]!==true;')
    s=one(s,'                    var show:Boolean=Boolean(expectedVisibility[bitmap]);',
          '''                    // Keep all resident cell pixels in this bounded world page.
                    // View changes never change cached cell contents; sources/revisions do.
                    var show:Boolean=true;''')
    return s

def helper_source():
    s=base.helper_source().replace(base.VERSION,VERSION)
    s=one(s,'["native-","classic-","persistent-"]','["native-","bound-","fullpage-"]')
    s=one(s,'            // This is the old renderer\'s required native restoration. The new\n            // renderer deliberately keeps its own display binding through World.step.\n            classic.beginFrame();',
          '            // Both variants keep their display binding through World.step.')
    s=one(s,'Compare native, old merged atlas, and persistent event-indexed merged atlas. Identical pixels/page size, complete intervals and switches retained.',
          'Compare current native scene, persistent visible-cell atlas, and persistent full-page contents. Full timing and switches retained; no bitmap geometry changes.')
    return s
def runner_source():return base.runner_source().replace(base.VERSION,VERSION)

if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    fixture=HERE/'tests/ScenePersistentAtlasChecks.as';source=BASE/'tests/ScenePersistentAtlasChecks.as'
    if fixture.exists():assert fixture.read_bytes()==source.read_bytes()
    else:shutil.copy2(source,fixture)
    for name,s in [('SceneClassicAtlas.as',classic_source()),('ScenePersistentAtlas.as',persistent_source()),('tests/SceneCameraRasterTrial.as',helper_source()),('run.py',runner_source())]:
        p=HERE/name
        if p.suffix=='.py':ast.parse(s)
        if p.exists():assert p.read_text('utf-8-sig')==s
        else:p.write_text(s,'utf-8')
    print('Prepared bounded world-page contents, previous persistent control, native control and unchanged Flash fixture')
