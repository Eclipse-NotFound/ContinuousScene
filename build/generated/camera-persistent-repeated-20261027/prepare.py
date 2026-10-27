from pathlib import Path
import ast,importlib.util
HERE=Path(__file__).resolve().parent;BASE=HERE.parent/'camera-persistent-combat-imports-20261027'
VERSION='camera-persistent-repeated-1'
def load(name,p):
    sp=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
base=load('persistent_repeated_generation',BASE/'prepare.py');one=base.one
COMBAT=base.COMBAT;window=base.window;combat=base.combat
def presenter_source():return base.presenter_source()
def helper_source():return base.helper_source()
def transform(source):
    s=base.transform(source).replace(base.VERSION,VERSION)
    needle='                report.atlasMotion={version:"'+VERSION+'",'
    s=one(s,needle,'''                var atlasCases:Array=cases.concat();cases=[];
                for(var atlasCase:int=0;atlasCase<20;++atlasCase)cases.push(atlasCases[atlasCase%4]);
'''+needle)
    s=one(s,'order:[false,true,true,false],visualAcceptance:false,','order:['+','.join(['false','true','true','false']*5)+'],visualAcceptance:false,')
    assert s.count('report.samples.length==4')==2
    s=s.replace('report.samples.length==4','report.samples.length==20')
    s=one(s,'var controlIndex:int=cfg.sleepingRootShort?index%4:index;',
          'var controlIndex:int=(cfg.sleepingRootShort || cfg.drawControl=="atlas")?index%4:index;')
    s=one(s,'cfg.drawControl=="atlas"?120:','cfg.drawControl=="atlas"?60:')
    s=one(s,'Motion atlas requires four-window real native-input scene combat','Motion atlas requires repeated native-input scene combat')
    return s
def runner_source():return base.runner_source().replace(base.VERSION,VERSION)
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    for name,s in [('SceneRasterPresentation.as',presenter_source()),('tests/SceneCombatAtlasPixels.as',helper_source()),('run.py',runner_source())]:
        p=HERE/name
        if p.suffix=='.py':ast.parse(s)
        if p.exists():assert p.read_text('utf-8-sig')==s
        else:p.write_text(s,'utf-8')
    print('Prepared 20 x 60 native combat intervals; identical presenter, movement, weapon and pixel inputs')
