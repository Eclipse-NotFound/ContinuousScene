"""Back up and atomically install only the exact behavior-verified host patch."""
from pathlib import Path
from datetime import datetime,timezone
import json,os,shutil,uuid
import verify as v

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
MOD=HERE.parents[2]


def main():
    proof=v.verify()
    assert proof==v.read(HERE/'verification.json'), 'Saved verification changed'
    target=ROOT/'pfe.swf';candidate=HERE/'pfe-unit-boundary.swf'
    receipt=MOD/'state/unit-boundary-deployment-20261028.json'
    assert not receipt.exists(), 'Preserve prior deployment record'
    assert v.sha(target)==v.BASE and v.sha(candidate)==v.FIXED, 'Concurrent host/candidate update'
    # Reuse only the tested running dependencies, not every historical backup or document.
    inputs={p.replace('\\','/'):s for p,s in v.read(v.EVIDENCE/'unit-prestep-boundary-20261028-fixed-r1/inputs.json').items()}
    dependencies={p:s for p,s in inputs.items() if '/release/' in p and p.endswith('.swf') and
                  not p.startswith('mods/ContinuousSceneMotion/')}
    assert dependencies and all(v.sha(ROOT/p)==s for p,s in dependencies.items()), 'Installed runtime dependency changed'
    unchanged=dict(dependencies)
    for p in ('application.xml','mods/loader-manifest.txt','DLC/pfe.swf','DLC/pfeUI.swf'):
        unchanged[p]=v.sha(ROOT/p)
    assert '<content>pfe.swf</content>' in (ROOT/'application.xml').read_text('utf-8-sig'), 'Active host target changed'
    token=datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]
    backup=MOD/'build/backups'/('unit-boundary-'+token);backup.mkdir(parents=True,exist_ok=False)
    saved=backup/'pfe.swf';shutil.copy2(target,saved);assert v.sha(saved)==v.BASE
    temp=target.with_name('pfe.swf.unit-boundary-'+token+'.tmp')
    assert not temp.exists();shutil.copy2(candidate,temp);assert v.sha(temp)==v.FIXED
    installed=False
    try:
        assert v.sha(target)==v.BASE and all(v.sha(ROOT/p)==s for p,s in unchanged.items()), 'Concurrent installed update'
        os.replace(temp,target);installed=True
        assert v.sha(target)==v.FIXED and all(v.sha(ROOT/p)==s for p,s in unchanged.items())
        record=dict(installedAt=datetime.now(timezone.utc).isoformat(),host=v.FIXED,priorHost=v.BASE,mod=v.CS,
            version='CS 0.9.1 unchanged; native Unit.run column guard',backup=str(backup),
            verification=proof,verificationSHA256=v.sha(HERE/'verification.json'),
            sourceSHA256=v.sha(HERE/'build_host.py'),unchangedRuntimeInputs=unchanged,
            installedReadbackPassed=True,playerStorageTouched=False,playerProcessesTouched=False,
            reuse='Exact tested host, same loader and runtime dependencies; no loading-chain or configuration change.')
        with receipt.open('x',encoding='utf-8') as stream:json.dump(record,stream,indent=2)
    except BaseException:
        if installed and v.sha(target)==v.FIXED:
            rollback=target.with_name('pfe.swf.unit-boundary-rollback-'+token+'.tmp')
            assert not rollback.exists();shutil.copy2(saved,rollback);os.replace(rollback,target)
            assert v.sha(target)==v.BASE
        raise
    finally:
        temp.unlink(missing_ok=True)
    print(json.dumps(dict(installed=True,host=v.FIXED,backup=str(backup),receipt=str(receipt))))


if __name__=='__main__':main()
