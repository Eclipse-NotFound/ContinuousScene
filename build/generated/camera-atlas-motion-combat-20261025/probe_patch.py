"""Frozen B7ED real combat, original-size motion-only atlas, read-only telemetry."""
from pathlib import Path
import hashlib
import importlib.util
import shutil

VERSION = 'camera-atlas-motion-combat-1'
HERE = Path(__file__).resolve().parent
MAIN_RAW_SHA256 = 'F87A95E684A88D508679853C2EA2E1377EFC30236DD9BC7097885F4E5756FEE1'
MAIN_SHA256 = '3BEC84CAB5E34B1316DB2FF6DE93FB80C91C86A290514CF852FF27E673654240'
CHANGED = ['ContinuousSceneMotionProbe.as', 'SceneRasterPresentation.as']
_spec = importlib.util.spec_from_file_location('atlas_motion_combat_transform', HERE / 'presentation_transform.py')
variant = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(variant)

EDITS = (
    (
        '        private static var rasterPresentation:SceneRasterPresentation=new SceneRasterPresentation();',
        '        private static var rasterPresentation:SceneRasterPresentation=new SceneRasterPresentation();\n'
        '        private static var atlasPriorEnabled:Boolean=false,atlasPriorPresented:Boolean=false;',
    ),
    (
        '            if(cfg.drawControl)cases=["draw-baseline-a","draw-control-b","draw-control-b-repeat","draw-baseline-a-repeat"];',
        '            if(cfg.drawControl)cases=["draw-baseline-a","draw-control-b","draw-control-b-repeat","draw-baseline-a-repeat"];\n'
        '            if(cfg.drawControl=="atlas") {\n'
        '                if(cfg.benchmark!="scene" || !cfg.nativeInputMotion || !cfg.nativeSprint || !cfg.playerFire ||\n'
        '                    !cfg.fixedEnemies || !cfg.combatRoute || !cfg.stableMotion || cfg.presentationCheck || cfg.sleepingRootShort)\n'
        '                    throw new Error("Motion atlas requires four-window real native-input scene combat");\n'
        '                report.atlasMotion={version:"atlas-motion-combat-1",diagnosticOnly:true,performanceEligible:false,\n'
        '                    order:[false,true,true,false],visualAcceptance:false,\n'
        '                    intervalMeaning:"Continuous intervals retain prior frame presentation and current update/copy cost. Previous-state arrays expose switch boundaries; no frames are removed.",\n'
        '                    limits:"Actual fractional translation and native shake are retained. RGB2/alpha0 compatibility is not established by this timing run."};\n'
        '            }',
    ),
    (
        '            closeProbeTiming(true);',
        '            closeProbeTiming(true);\n'
        '            if(cfg.drawControl=="atlas") {\n'
        '                report.atlasMotionCleanup={restored:false,errors:[]};\n'
        '                try {report.atlasMotionCleanup.before=rasterPresentation.snapshot();}\n'
        '                catch(atlasBeforeError:*) {report.atlasMotionCleanup.errors.push("before: "+String(atlasBeforeError));}\n'
        '                try {rasterPresentation.clear();}\n'
        '                catch(atlasClearError:*) {report.atlasMotionCleanup.errors.push("clear: "+String(atlasClearError));}\n'
        '                try {\n'
        '                    var atlasAfter:Object=rasterPresentation.snapshot();\n'
        '                    report.atlasMotionCleanup.after=atlasAfter;\n'
        '                    report.atlasMotionCleanup.restored=report.atlasMotionCleanup.errors.length==0 &&\n'
        '                        !atlasAfter.presented && atlasAfter.layers==0 && atlasAfter.attached==0 &&\n'
        '                        atlasAfter.liveBitmaps==0 && atlasAfter.pixelStorageBytes==0 && atlasAfter.pendingHidden==0 &&\n'
        '                        !atlasAfter.hasBounds && !atlasAfter.hasLocation && !atlasAfter.poseValid;\n'
        '                } catch(atlasAfterError:*) {report.atlasMotionCleanup.errors.push("after: "+String(atlasAfterError));}\n'
        '                if(!report.atlasMotionCleanup.restored)error=(error?error+"\\n":"")+"Motion atlas cleanup failed";\n'
        '            }',
    ),
    (
        '            row.combatWindows=[];row.denseFrames=denseMetrics.bucket();',
        '            row.combatWindows=[];row.denseFrames=denseMetrics.bucket();\n'
        '            if(cfg.drawControl=="atlas")row.atlasMotion={version:"atlas-motion-combat-1",\n'
        '                enabled:[],presented:[],previousEnabled:[],previousPresented:[],vx:[],vy:[],scale:[],\n'
        '                worldX:[],worldY:[],worldScaleX:[],worldScaleY:[],quakeX:[],quakeY:[],copies:[],rebuilds:[],\n'
        '                start:rasterPresentation.snapshot()};',
    ),
    (
        '                        if(cfg.drawControl=="atlas")rasterPresentation.update(w,altered);',
        '                        if(cfg.drawControl=="atlas") {\n'
        '                            row.atlasMotion.previousEnabled.push(atlasPriorEnabled);\n'
        '                            row.atlasMotion.previousPresented.push(atlasPriorPresented);\n'
        '                            rasterPresentation.update(w,altered);\n'
        '                            row.atlasMotion.enabled.push(altered);row.atlasMotion.presented.push(rasterPresentation.presented);\n'
        '                            row.atlasMotion.vx.push(w.cam.vx);row.atlasMotion.vy.push(w.cam.vy);row.atlasMotion.scale.push(w.cam.scaleV);\n'
        '                            row.atlasMotion.worldX.push(w.visual.x);row.atlasMotion.worldY.push(w.visual.y);\n'
        '                            row.atlasMotion.worldScaleX.push(w.visual.scaleX);row.atlasMotion.worldScaleY.push(w.visual.scaleY);\n'
        '                            row.atlasMotion.quakeX.push(w.cam.quakeX);row.atlasMotion.quakeY.push(w.cam.quakeY);\n'
        '                            row.atlasMotion.copies.push(rasterPresentation.copies);row.atlasMotion.rebuilds.push(rasterPresentation.rebuilds);\n'
        '                            atlasPriorEnabled=altered;atlasPriorPresented=rasterPresentation.presented;\n'
        '                        }',
    ),
    (
        '                    if(cfg.drawControl=="atlas")row.presentation={copies:rasterPresentation.copies,rebuilds:rasterPresentation.rebuilds};',
        '                    if(cfg.drawControl=="atlas") {\n'
        '                        row.presentation={copies:rasterPresentation.copies,rebuilds:rasterPresentation.rebuilds};\n'
        '                        row.atlasMotion.end=rasterPresentation.snapshot();\n'
        '                    }',
    ),
)


def transform(source: str) -> str:
    assert hashlib.sha256(source.encode('utf-8')).hexdigest().upper() == MAIN_SHA256
    result = source
    for before, after in EDITS:
        assert result.count(before) == 1, before
        result = result.replace(before, after, 1)
    restored = result
    for before, after in reversed(EDITS):
        assert restored.count(after) == 1, before
        restored = restored.replace(after, before, 1)
    assert restored == source, 'Unexpected shared-fixture change'
    return result


def prepare(source: Path, destination: Path):
    assert not destination.exists()
    assert len(list(source.rglob('*.as'))) + len(list(source.rglob('*.as.inc'))) == 85
    shutil.copytree(source, destination)
    main = source / CHANGED[0]
    atlas = source / CHANGED[1]
    assert hashlib.sha256(main.read_bytes()).hexdigest().upper() == MAIN_RAW_SHA256
    (destination / CHANGED[0]).write_text(transform(main.read_text('utf-8-sig')), 'utf-8')
    (destination / CHANGED[1]).write_text(variant.transform(atlas.read_text('utf-8-sig')), 'utf-8')
