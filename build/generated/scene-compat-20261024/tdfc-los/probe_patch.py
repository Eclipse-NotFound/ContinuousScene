"""Terminal LOS components in a copied MotionProbe, never shared source."""
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
HELPER = 'tests/SceneTdfcLosChecks.as'
SOURCE = HERE / 'SceneTdfcLosChecks.as'
CONTROL = 'tdfc-los-component-controls.json'
VERSION = 'tdfc-los-terminal-probe-1'

def patch_text(text):
    changes = [
        ('    import tests.SceneEncounter;', '    import tests.SceneEncounter;\n    import tests.SceneTdfcLosChecks;'),
        ('            cfg=JSON.parse(f.readUTFBytes(f.bytesAvailable));f.close();report.config=cfg;',
         '''            cfg=JSON.parse(f.readUTFBytes(f.bytesAvailable));f.close();report.config=cfg;
            var losControlStream:FileStream=new FileStream();
            losControlStream.open(File.applicationDirectory.resolvePath("tdfc-los-component-controls.json"),FileMode.READ);
            try {report.tdfcLosControl=JSON.parse(losControlStream.readUTFBytes(losControlStream.bytesAvailable));}
            finally {losControlStream.close();}
            if(report.tdfcLosControl.version!=="tdfc-los-controls-1")throw new Error("LOS isolated control mismatch");'''),
        ('                    check("actual-expected-native-map",cfg.benchmark=="normal"?(!w.grafon.sceneLarge && loc.spaceX==48):(w.grafon.sceneLarge && loc.spaceX>48));',
         '''                    check("actual-expected-native-map",cfg.benchmark=="normal"?(!w.grafon.sceneLarge && loc.spaceX==48):(w.grafon.sceneLarge && loc.spaceX>48));
                    report.tdfcLosComponents=SceneTdfcLosChecks.run(w,check);
                    finish();return;''')]
    for old,new in changes:
        assert text.count(old)==1, ('Unique anchor',old[:90],text.count(old))
        text=text.replace(old,new,1)
    assert text.count('SceneTdfcLosChecks.run(')==1
    return text

def prepare(source,destination):
    shutil.copytree(source,destination)
    path=destination/'ContinuousSceneMotionProbe.as'
    path.write_text(patch_text(path.read_text(encoding='utf-8-sig')),encoding='utf-8')
    shutil.copy2(SOURCE,destination/HELPER)
