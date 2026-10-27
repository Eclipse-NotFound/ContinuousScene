from pathlib import Path
import ast,importlib.util
HERE=Path(__file__).resolve().parent;BASE=HERE.parent/'camera-persistent-repeated-20261027'
VERSION='camera-persistent-jump-1'
def load(name,p):
    sp=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
base=load('persistent_jump_generation',BASE/'prepare.py');one=base.one
def presenter_source():return base.presenter_source()
def helper_source():return base.helper_source()
def transform(source):
    s=base.transform(source).replace(base.VERSION,VERSION)
    s=one(s,'        private static var atlasPriorEnabled:Boolean=false,atlasPriorPresented:Boolean=false;',
          '        private static var nativeJumpCommands:int=0,nativeJumpPressed:int=0;\n        private static var atlasPriorEnabled:Boolean=false,atlasPriorPresented:Boolean=false;')
    s=one(s,'w.ctr.keyRun=moving && Boolean(cfg.nativeSprint);w.ctr.keyJump=false;w.ctr.keyDash=false;',
          '''w.ctr.keyRun=moving && Boolean(cfg.nativeSprint);w.ctr.keyJump=false;w.ctr.keyDash=false;
            if(phase==4 && moving){w.ctr.keyJump=nativeJumpCommands%90<4;++nativeJumpCommands;if(w.ctr.keyJump)++nativeJumpPressed;}''')
    s=one(s,'                report.combatAtlasPixels=SceneCombatAtlasPixels.run(w,rasterPresentation);',
          '''                report.jumpInput={commands:nativeJumpCommands,pressed:nativeJumpPressed,period:90,hold:4};
                report.combatAtlasPixels=SceneCombatAtlasPixels.run(w,rasterPresentation);''')
    return s
def runner_source():return base.runner_source().replace(base.VERSION,VERSION)
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    for name,s in [('SceneRasterPresentation.as',presenter_source()),('tests/SceneCombatAtlasPixels.as',helper_source()),('run.py',runner_source())]:
        p=HERE/name
        if p.suffix=='.py':ast.parse(s)
        if p.exists():assert p.read_text('utf-8-sig')==s
        else:p.write_text(s,'utf-8')
    print('Prepared real jump-key pulses during the same native sprint/fire comparison')
