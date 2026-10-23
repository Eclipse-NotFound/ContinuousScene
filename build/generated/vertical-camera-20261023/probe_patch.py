# Frozen parent vertical-motion source SHA256 690DBB260A599C70BD3234A6F24ADE96C5BD6837AEEE7212111A50B6CBFF28F0
"""Patch only an isolated source copy; no native methods or shared sources change."""
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
HELPER = 'tests/SceneVerticalMotionProbe.as'


def patch_text(text, grow=False):
    assert grow is False, "Camera diagnosis never expands resident cache"
    replacements = [
        ('    import tests.SceneEncounter;', '    import tests.SceneEncounter;\n    import tests.SceneVerticalMotionProbe;'),
        ('        private static var encounter:SceneEncounter;', '        private static var encounter:SceneEncounter;\n        private static var verticalMotion:SceneVerticalMotionProbe;'),
        ('if(!cfg.fixedEnemies || !cfg.stableMotion || !cfg.playerFire)throw new Error("Combat route requires fixed armed actors, stable movement and player fire");',
         'if(!cfg.nativeInputMotion || !cfg.stableMotion || cfg.encounter || cfg.playerFire)throw new Error("Vertical diagnosis requires native input without fixture combat");'),
        ('if(!cfg.encounter || !cfg.fixedEnemies || !cfg.playerFire || !cfg.stableMotion || cfg.visual || cfg.nativeSprint)\n                throw new Error("Native input fixture requires fixed combat actors and player fire; visual teleport and sprint are unsupported");',
         'if(!cfg.nativeInputMotion || !cfg.combatRoute || !cfg.stableMotion || cfg.encounter || cfg.playerFire || cfg.visual || cfg.nativeSprint)\n                throw new Error("Vertical diagnosis requires real walking/jumping, no fixture combat or visual teleport");'),
        ('                    age=0;phase=3;\n                }else if(phase==3) {',
         '''                    report.nativeInputMotion.limitation="Real walking and jumping; suggested enemy positions were only used to verify terrain, no fixture actors were created";
                    nativeInputRoute.fixtureActorsCreated=0;
                    verticalMotion=new SceneVerticalMotionProbe();
                    report.verticalMotion=verticalMotion.start(w,nativeInputRoute,GROW);
                    age=0;phase=107;
                }else if(phase==107) {
                    if(verticalMotion.step(absoluteStart,lastEnd,band50-startFrame)) {
                        report.verticalMotion=verticalMotion.snapshot();
                        check("vertical-camera-complete",report.verticalMotion.complete&&report.verticalMotion.valid,report.verticalMotion.windows.length);
                        finish();return;
                    }
                }else if(phase==3) {'''.replace('GROW', 'true' if grow else 'false')),
        ('            closeProbeTiming(true);', '''            closeProbeTiming(true);
            if(verticalMotion) {
                try {verticalMotion.clear();report.verticalMotion=verticalMotion.snapshot();}
                catch(verticalCleanup:*) {error=(error?error+"\\n":"")+"Vertical cleanup: "+String(verticalCleanup);}
            }''')]
    for old, new in replacements:
        assert text.count(old) == 1, ('Non-unique frozen source anchor', old[:100], text.count(old))
        text = text.replace(old, new, 1)
    assert 'phase=107' in text and text.count('verticalMotion.start(') == 1
    return text


def prepare(source, destination, grow=False):
    shutil.copytree(source, destination)
    target = destination / 'ContinuousSceneMotionProbe.as'
    target.write_text(patch_text(target.read_text(encoding='utf-8-sig'), grow), encoding='utf-8')
    shutil.copy2(HERE / HELPER, destination / HELPER)
