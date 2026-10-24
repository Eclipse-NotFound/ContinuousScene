"""Paused-world camera raster diagnosis from the exact B7ED/39A source closure."""
from pathlib import Path
import shutil
import importlib.util
import hashlib

VERSION = 'camera-atlas-pow2-1'
HERE = Path(__file__).resolve().parent
HELPER = HERE / 'tests/SceneCameraRasterTrial.as'
CHANGED = ['ContinuousSceneMotionProbe.as', 'SceneRasterPresentation.as', 'tests/SceneCameraRasterTrial.as']
_spec = importlib.util.spec_from_file_location('atlas_pow2_transform', HERE / 'atlas_transform.py')
variant = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(variant)
PATCHES = (
    ('    import tests.SceneDenseCombatMetrics;', '\n    import tests.SceneCameraRasterTrial;'),
    ('        private static var denseMetrics:SceneDenseCombatMetrics=new SceneDenseCombatMetrics();',
     '\n        private static var cameraRaster:SceneCameraRasterTrial=new SceneCameraRasterTrial();'),
    ('                    if(cfg.presentationCheck){',
     '\n                        if(cfg.drawControl=="atlas") {'
     '\n                            report.cameraRaster=cameraRaster.begin(w,rasterPresentation);'
     '\n                            report.diagnosticOnly=true;report.performanceEligible=false;'
     '\n                            phase=97;return;'
     '\n                        }'),
)


def transform(source):
    assert 'cameraRaster' not in source and 'SceneCameraRasterTrial' not in source
    out = source
    for anchor, insertion in PATCHES[:3]:
        assert out.count(anchor) == 1, anchor
        out = out.replace(anchor, anchor + insertion)
    anchor = '                }else if(phase==90) {'
    replacement = '''                }else if(phase==97) {
                    if(cameraRaster.step(w)) {
                        check("camera-raster-complete",report.cameraRaster.complete,report.cameraRaster.complete);
                        finish();return;
                    }
                }else if(phase==90) {'''
    assert out.count(anchor) == 1
    out = out.replace(anchor, replacement)
    anchor2 = '            if(done)return;done=true;'
    cleanup = '''
            try {
                var cameraCleanup:Object=cameraRaster.clear(w);
                if(report.cameraRaster) {
                    report.cameraRasterCleanup=cameraCleanup;
                    if(!cameraCleanup.restored)error=(error?error+"\\n":"")+"Camera raster cleanup failed";
                }
            } catch(cameraCleanupError:*) {error=(error?error+"\\n":"")+"Camera raster cleanup: "+String(cameraCleanupError);}'''
    assert out.count(anchor2) == 1
    out = out.replace(anchor2, anchor2 + cleanup)
    restored = out.replace(anchor2 + cleanup, anchor2).replace(replacement, anchor)
    for before, after in reversed(PATCHES[:3]):
        restored = restored.replace(before + after, before)
    assert restored == source
    return out


def prepare(source: Path, destination: Path):
    assert not destination.exists() and not (source / 'tests/SceneCameraRasterTrial.as').exists()
    shutil.copytree(source, destination)
    main = destination / 'ContinuousSceneMotionProbe.as'
    main.write_text(transform(main.read_text(encoding='utf-8-sig')), encoding='utf-8')
    original_atlas = source / 'SceneRasterPresentation.as'
    assert hashlib.sha256(original_atlas.read_bytes()).hexdigest().upper() == 'C0E40368FD8BF6FE1413EC4C8D533C7034B18297AEB35119FBFEC4ADD5D93175'
    (destination / 'SceneRasterPresentation.as').write_text(variant.transform(original_atlas.read_text('utf-8-sig')), 'utf-8')
    shutil.copyfile(HELPER, destination / 'tests/SceneCameraRasterTrial.as')
