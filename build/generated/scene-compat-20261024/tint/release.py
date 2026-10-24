"""Deploy a component-verified exact tint candidate, smoke actual files, roll back failure."""
from pathlib import Path
import argparse
import datetime
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import uuid

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
BUILD=HERE.parents[2]
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def record_failure(r,path,data):
    """A broken evidence sink must never prevent an already-needed rollback."""
    try:
        r.save(path,data)
    except BaseException as error:
        data.setdefault('recordWriteErrors',[]).append(repr(error))
        try:print(json.dumps(dict(record=str(path),state=data),ensure_ascii=False),file=sys.stderr,flush=True)
        except BaseException:pass

def clean_temporary(path,data):
    try:
        if path.exists():path.unlink()
    except BaseException as error:
        data.setdefault('temporaryCleanupErrors',[]).append(dict(path=str(path),error=repr(error)))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence',required=True);p.add_argument('--smoke-name',required=True)
    args=p.parse_args();runner=load('tint_qualified_components',HERE/'r2/run.py')
    r,m=runner.r,runner.m;receipt=HERE/'product/build.json';selected=runner.host_inputs(receipt)
    proof=r.E/args.evidence;summary=r.read(proof/'summary.json');inputs=r.read(proof/'runner-inputs.json')
    assert summary['qualification']['passed'] and summary['hostKind']=='candidate' and summary['hostSHA256']==selected['sha256']
    assert summary['verification']['expectFixed'] and not summary['verification']['residualReproduced']
    assert not summary['verification']['ordinaryResidualReproduced']
    assert summary['verification']['restore']['passed'] and summary['verification']['passed']
    assert all(c['passed'] for c in summary['verification']['cases'])
    assert not (r.E/args.smoke_name).exists()
    before=inputs['baseline'];current=r.baseline();assert before==current, 'Installed dependencies changed since candidate test'
    assert current['pfe.swf']==runner.HOST
    suffix=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]
    backup=BUILD/'backups'/('scene-tint-'+suffix)/'pfe_before_ContinuousScene_tint_20261024.swf'
    record=BUILD.parent/'state/scene-tint-deployment-20261024.json'
    assert not record.exists() and not backup.exists()
    smoke=HERE/'installed/run.py'
    smoke_inputs={str(p):r.sha(p) for p in (smoke,HERE/'installed/probe_patch.py',HERE/'r2/SceneEntityTintChecks.as',Path(__file__))}
    data=dict(version='scene-player-region-tint-2',status='qualified',base=runner.HOST,candidate=selected['sha256'],
        buildReceipt=str(receipt),buildReceiptSHA256=r.sha(receipt),candidateEvidence=str(proof),
        candidateSummarySHA256=r.sha(proof/'summary.json'),backup=str(backup),installedInputsBefore=before,
        smokeName=args.smoke_name,smokeInputs=smoke_inputs,scope=['root pfe.swf'],authorization='GOVERNANCE §6 standing local deployment authorization')
    installed=False
    expected=dict(before);expected['pfe.swf']=selected['sha256']
    try:
        with m.Registration(owner='ContinuousScene / tint deployment',purpose='Exact two-method tint fix, backup and install',
                run_dir=backup.parent,evidence=record,wait=600) as lease:
            assert not m.air_pids() and r.baseline()==before
            assert selected==runner.host_inputs(receipt)
            backup.parent.mkdir(parents=True);shutil.copy2(r.ROOT/'pfe.swf',backup);assert r.sha(backup)==runner.HOST
            data.update(status='backed-up');r.save(record,data)
            temporary=r.ROOT/('.pfe-cs-tint-'+uuid.uuid4().hex+'.tmp')
            try:
                shutil.copy2(selected['path'],temporary);assert r.sha(temporary)==selected['sha256']
                assert not m.air_pids() and r.baseline()==before
                os.replace(temporary,r.ROOT/'pfe.swf')
                installed=True
            finally:
                clean_temporary(temporary,data)
            after=r.baseline();assert after==expected
            data.update(status='installed-awaiting-smoke',installedInputsAfter=after,installedAt=datetime.datetime.now().isoformat())
            r.save(record,data);lease.outcome='passed';lease.note='Exact candidate installed; actual-file smoke follows'
        command=[sys.executable,'-B',str(smoke),'--name',args.smoke_name,'--host-build',str(receipt),'--compile-probe']
        subprocess.run(command,check=True)
        final=r.read(r.E/args.smoke_name/'summary.json')
        assert final['qualification']['passed'] and final['hostKind']=='installed'
        assert final['installedPathSmoke'] is True and final['copiedActualInstalledHost'] is True
        assert final['hostSHA256']==final['installedHostSHA256']==selected['sha256']
        assert final['candidateBaseSHA256']==runner.HOST
        assert final['verification']['passed'] and final['verification']['expectFixed']
        assert not final['verification']['residualReproduced'] and not final['verification']['ordinaryResidualReproduced']
        assert final['verification']['restore']['passed'] and all(c['passed'] for c in final['verification']['cases'])
        assert r.baseline()==expected and smoke_inputs=={p:r.sha(Path(p)) for p in smoke_inputs}
        data.update(status='verified',smokeSummary=str(r.E/args.smoke_name/'summary.json'),
            smokeSummarySHA256=r.sha(r.E/args.smoke_name/'summary.json'),verifiedAt=datetime.datetime.now().isoformat())
        r.save(record,data);print(json.dumps(dict(status='verified',host=selected['sha256'],record=str(record))),flush=True)
    except BaseException as failure:
        data.update(status='deployment-failed' if installed else 'failed-before-install',error=repr(failure),installedByThisRun=installed)
        record_failure(r,record,data)
        if not installed:raise
        try:
            other_air=m.air_pids()
            if other_air:
                data.update(status='rollback-deferred',unrecognizedAirProcessIds=other_air,
                    rollbackReason='AIR is running; no process was closed and no rollback write was attempted')
                raise RuntimeError(data['rollbackReason'])
            with m.Registration(owner='ContinuousScene / tint failure rollback',purpose='Restore only own exact host after failed smoke',
                    run_dir=backup.parent,evidence=record,wait=600) as lease:
                other_air=m.air_pids()
                if other_air:
                    data.update(status='rollback-deferred',unrecognizedAirProcessIds=other_air,
                        rollbackReason='AIR appeared while waiting for rollback; left untouched')
                    raise RuntimeError(data['rollbackReason'])
                assert r.sha(r.ROOT/'pfe.swf')==selected['sha256'], 'Concurrent host change: do not overwrite'
                assert r.sha(backup)==runner.HOST
                temporary=r.ROOT/('.pfe-cs-tint-rollback-'+uuid.uuid4().hex+'.tmp')
                try:
                    shutil.copy2(backup,temporary);assert r.sha(temporary)==runner.HOST
                    other_air=m.air_pids()
                    if other_air:
                        data.update(status='rollback-deferred',unrecognizedAirProcessIds=other_air,
                            rollbackReason='AIR appeared before rollback replacement; left untouched')
                        raise RuntimeError(data['rollbackReason'])
                    assert r.sha(r.ROOT/'pfe.swf')==selected['sha256'], 'Concurrent host change: do not overwrite'
                    assert r.sha(backup)==runner.HOST
                    os.replace(temporary,r.ROOT/'pfe.swf')
                    installed=False
                finally:
                    clean_temporary(temporary,data)
                assert r.sha(r.ROOT/'pfe.swf')==runner.HOST
                data.update(status='rolled-back',installedByThisRun=False,rolledBackAt=datetime.datetime.now().isoformat())
                record_failure(r,record,data)
                lease.outcome='passed';lease.note='Own failed tint deployment restored to exact ABE2; other modules untouched'
        except BaseException as rollback_error:
            if data['status']!='rollback-deferred':data['status']='rollback-blocked'
            data['rollbackError']=repr(rollback_error)
            record_failure(r,record,data)
            raise RuntimeError('Tint deployment failed; rollback deferred or blocked: '+repr(rollback_error)) from failure
        raise

if __name__=='__main__':main()
