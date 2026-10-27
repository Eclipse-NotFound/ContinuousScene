from pathlib import Path
import ast,importlib.util
HERE=Path(__file__).resolve().parent;BASE=HERE.parent/'camera-persistent-combat-20261027'
VERSION='camera-persistent-combat-imports-1'
def load(name,p):
    sp=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
base=load('combat_import_fix_base',BASE/'prepare.py');one=base.one
COMBAT=base.COMBAT
window=base.window
combat=base.combat
def presenter_source():return base.presenter_source()
def helper_source():return base.helper_source()
def transform(source):
    s=base.transform(source).replace(base.VERSION,VERSION)
    return one(s,'    import flash.utils.getTimer;','    import flash.utils.getTimer;\n    import flash.utils.getQualifiedClassName;')
def runner_source():return base.runner_source().replace(base.VERSION,VERSION)
if __name__=='__main__':
    for name,s in [('SceneRasterPresentation.as',presenter_source()),('tests/SceneCombatAtlasPixels.as',helper_source()),('run.py',runner_source())]:
        p=HERE/name
        if p.suffix=='.py':ast.parse(s)
        if p.exists():assert p.read_text('utf-8-sig')==s
        else:p.write_text(s,'utf-8')
    print('Prepared only the missing Flash class-name import; prior failed source is unchanged')
