from pathlib import Path
import ast,importlib.util
HERE=Path(__file__).resolve().parent;BASE=HERE.parent/'camera-persistent-jump-20261027'
VERSION='camera-persistent-jump-steer-1'
def load(name,p):
    sp=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
base=load('persistent_jump_steer_generation',BASE/'prepare.py');one=base.one
def presenter_source():return base.presenter_source()
def helper_source():return base.helper_source()
def transform(source):
    s=base.transform(source).replace(base.VERSION,VERSION)
    s=one(s,'if(nativeDirection>0 && w.gg.X>=x0+path)',
        'var turnX:Number=Number(w.gg.X)+(w.gg.stay?4:30)*Number(w.gg.dx);\n                if(nativeDirection>0 && turnX>=x0+path)')
    s=one(s,'else if(nativeDirection<0 && w.gg.X<=x0)','else if(nativeDirection<0 && turnX<=x0)')
    s=one(s,'report.jumpInput={commands:nativeJumpCommands,pressed:nativeJumpPressed,period:90,hold:4};',
        'report.jumpInput={commands:nativeJumpCommands,pressed:nativeJumpPressed,period:90,hold:4};\n                report.jumpSteering={groundLookahead:4,airLookahead:30,positionOrVelocityWrites:false};')
    return s
def runner_source():return base.runner_source().replace(base.VERSION,VERSION)
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    for name,s in [('SceneRasterPresentation.as',presenter_source()),('tests/SceneCombatAtlasPixels.as',helper_source()),('run.py',runner_source())]:
        p=HERE/name
        if p.suffix=='.py':ast.parse(s)
        if p.exists():assert p.read_text('utf-8-sig')==s
        else:p.write_text(s,'utf-8')
    print('Prepared velocity-aware input steering; original physics and platform boundary retained')
