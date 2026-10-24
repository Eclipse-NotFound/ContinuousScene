"""Terminal component entry in a copied MotionProbe; no shared/native source writes."""
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
HELPER = 'tests/SceneEntityTintChecks.as'
SOURCE = HERE / 'SceneEntityTintChecks.as'
HELPER_SHA = 'B9F13F3E97C47A0D98E34FEBAC1B049854E826636BCE5725685E7143FEB6931F'
CONTROL = 'scene-tint-controls.json'


def patch_text(text):
    changes = [
        ('    import tests.SceneEncounter;',
         '    import tests.SceneEncounter;\n    import tests.SceneEntityTintChecks;'),
        ('            cfg=JSON.parse(f.readUTFBytes(f.bytesAvailable));f.close();report.config=cfg;',
         '''            cfg=JSON.parse(f.readUTFBytes(f.bytesAvailable));f.close();report.config=cfg;
            var tintControlStream:FileStream=new FileStream();
            tintControlStream.open(File.applicationDirectory.resolvePath("scene-tint-controls.json"),FileMode.READ);
            try {report.tintHostControl=JSON.parse(tintControlStream.readUTFBytes(tintControlStream.bytesAvailable));}
            finally {tintControlStream.close();}
            if(report.tintHostControl.version!=="scene-tint-test-controls-2" ||
               (report.tintHostControl.expectFixed!==true && report.tintHostControl.expectFixed!==false))
                throw new Error("Tint component isolated control mismatch");'''),
        ('                    check("actual-expected-native-map",cfg.benchmark=="normal"?(!w.grafon.sceneLarge && loc.spaceX==48):(w.grafon.sceneLarge && loc.spaceX>48));',
         '''                    check("actual-expected-native-map",cfg.benchmark=="normal"?(!w.grafon.sceneLarge && loc.spaceX==48):(w.grafon.sceneLarge && loc.spaceX>48));
                    report.tintComponents=SceneEntityTintChecks.run(w,check,Boolean(report.tintHostControl.expectFixed));
                    check("tint-terminal-component-complete",report.tintComponents.passed,report.tintComponents.restore);
                    finish();return;''')]
    for old, new in changes:
        assert text.count(old) == 1, ('Unique source anchor required', old[:100], text.count(old))
        text = text.replace(old, new, 1)
    assert text.count('SceneEntityTintChecks.run(') == 1
    return text


def prepare(source, destination):
    shutil.copytree(source, destination)
    main = destination / 'ContinuousSceneMotionProbe.as'
    main.write_text(patch_text(main.read_text(encoding='utf-8-sig')), encoding='utf-8')
    shutil.copy2(SOURCE, destination / HELPER)
