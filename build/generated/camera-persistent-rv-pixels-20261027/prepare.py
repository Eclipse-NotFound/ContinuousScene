from pathlib import Path
import ast,importlib.util,shutil
HERE=Path(__file__).resolve().parent;BASE=HERE.parent/'camera-persistent-rv-20261027'
VERSION='camera-persistent-rv-pixels-1'
def load(name,p):
    sp=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
base=load('rv_pixel_generation',BASE/'prepare.py');one=base.one;readers=base.readers;RVSOURCE=base.RVSOURCE
def presenter_source():return base.presenter_source()
def rv_sources():return base.rv_sources()
def transform(source):return base.transform(source).replace(base.VERSION,VERSION)
def helper_source():
    s=base.helper_source()
    s=one(s,'                var nativeImage:BitmapData=capture(w,images,result);','''                var coldImage:BitmapData=capture(w,images,result);
                var nativeImage:BitmapData=capture(w,images,result);
                var repeatedNative:BitmapData=capture(w,images,result);
                result.coldNative=compare(coldImage,nativeImage);result.nativeRepeat=compare(nativeImage,repeatedNative);''')
    s=one(s,'                result.stateRestored=w.loc===location', '''                presenter.update(w,true,true);var repeatedAtlas:BitmapData=capture(w,images,result);result.atlasRepeat=compare(nativeImage,repeatedAtlas);
                presenter.beginFrame();var repeatedRestore:BitmapData=capture(w,images,result);result.restoreRepeat=compare(nativeImage,repeatedRestore);
                result.stateRestored=w.loc===location''')
    s=one(s,'result.restore.equal && result.stateRestored;', 'result.restore.equal && result.stateRestored && result.nativeRepeat.equal && result.atlasRepeat.maxRGB<=2 && result.atlasRepeat.maxAlpha==0 && result.restoreRepeat.equal;')
    s=one(s,'                    result.nativePNG=png("combat-native",nativeImage);', '''                    result.coldPNG=png("combat-cold",coldImage);result.nativeRepeatPNG=png("combat-native-repeat",repeatedNative);
                    result.atlasRepeatPNG=png("combat-atlas-repeat",repeatedAtlas);result.restoreRepeatPNG=png("combat-restored-repeat",repeatedRestore);
                    result.nativePNG=png("combat-native",nativeImage);''')
    return s
def runner_source():return base.runner_source().replace(base.VERSION,VERSION)
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    entries=[('SceneRasterPresentation.as',presenter_source()),('tests/SceneCombatAtlasPixels.as',helper_source()),('run.py',runner_source()),('rv_build.py',(BASE/'rv_build.py').read_text('utf-8-sig'))]
    entries += [('rv-src/'+name,source) for name,source in rv_sources().items()]
    for name,s in entries:
        p=HERE/name;p.parent.mkdir(parents=True,exist_ok=True)
        if p.suffix=='.py':ast.parse(s)
        if p.exists():assert p.read_text('utf-8-sig')==s
        else:p.write_text(s,'utf-8')
    print('Prepared fixed native/candidate/native repeat sequence; first capture retained, no retry-until-pass')
