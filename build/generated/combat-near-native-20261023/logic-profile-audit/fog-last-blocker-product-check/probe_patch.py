"""Component-only overlay on a copied dense-v2 source tree; no timing arm."""
from pathlib import Path
import shutil


def once(text, old, new):
    assert text.count(old) == 1, ('Changed source anchor', old)
    return text.replace(old, new, 1)


def prepare(source, destination, dense_patcher, helper):
    dense_patcher.prepare(source, destination)
    path = Path(destination) / 'ContinuousSceneMotionProbe.as'
    text = path.read_text('utf-8-sig')
    text = once(text, '    import tests.SceneEncounter;',
                '    import tests.SceneEncounter;\n    import tests.SceneFogProductCheck;')
    text = once(text, '                    if(cfg.drawControl=="backgrounds") {\n                        if(!cfg.presentationCheck',
        '''                    if(cfg.presentationCheck && cfg.drawControl=="rcnative") {
                        if(nativeGroundRun>=10 && w.grafon.sceneViewReady()) {
                            report.fogProductEarlyCheck={groundContactRun:nativeGroundRun,startPose:warmMotion};
                            report.fogProductVerification=SceneFogProductCheck.run(w);
                            check("fogProduct-same-state",report.fogProductVerification.valid && report.fogProductVerification.equal,report.fogProductVerification);
                            check("fogProduct-restored",report.fogProductVerification.restored,report.fogProductVerification);
                            finish();return;
                        }
                        if(++age>240)throw new Error("Fog production component did not reach native ground");
                        return;
                    }
                    if(cfg.drawControl=="backgrounds") {
                        if(!cfg.presentationCheck''')
    path.write_text(text, 'utf-8')
    shutil.copy2(helper, Path(destination) / 'tests/SceneFogProductCheck.as')
