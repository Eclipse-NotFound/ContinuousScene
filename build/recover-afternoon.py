"""Restore the exact pre-afternoon host at the user's explicit request.

Only pfe.swf is replaced. Other owners' releases, saves, and preferences stay
unchanged. Both historical deployment receipts and the current host must match.
"""
from pathlib import Path
from datetime import datetime
import importlib.util, json, shutil

B = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('recovery_helpers', B/'enemy-release.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
m = r.motion
CURRENT = '5432A3B9B6820A94AE15AC0A97B13C4EDC534D3DC6DBED12063E0FE47677B71D'
INTERMEDIATE = '7D423BD7B7DD7D2B997E692BD1E22EF520879CD42387C14653C116C15385BCD4'
RESTORE = 'BEFCF0509E11FAC9FEF7AFB834708B8B93752A14AE3D5CD72B42AA6D42F9B82A'
RECEIPT = B.parent/'state/afternoon-recovery-20261021.json'

def main():
    assert not RECEIPT.exists(), 'Existing recovery receipt requires review'
    impact_path = B.parent/'state/impact-deployment-20261021.json'
    sats_path = B.parent/'state/sats-deployment-20261021.json'
    impact, sats = r.read(impact_path), r.read(sats_path)
    restore_path = Path(sats['backup'])/'pfe.swf'
    assert impact['candidateSHA256'] == CURRENT
    assert impact['beforeSHA256'] == sats['candidateSHA256'] == INTERMEDIATE
    assert sats['beforeSHA256'] == RESTORE
    assert r.sha(Path(impact['backup'])/'pfe.swf') == INTERMEDIATE
    assert r.sha(restore_path) == RESTORE
    assert '<content>pfe.swf</content>' in (r.ROOT/'application.xml').read_text('utf-8-sig')
    with m.Registration(owner='ContinuousScene / afternoon rollback / 01a13816',
                        purpose='Restore pre-afternoon BEFC; installed-file lifecycle verification',
                        run_dir=m.RUNTIME, evidence=RECEIPT, wait=300) as lease:
        assert not m.air_pids(), 'Other AIR present; no files changed'
        before = r.baseline()
        assert before['pfe.swf'] == CURRENT, 'Concurrent host change; no overwrite'
        backup = B/'backups'/('afternoon-recovery-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
        backup.mkdir(parents=True, exist_ok=False)
        shutil.copy2(r.ROOT/'pfe.swf', backup/'pfe.swf')
        for p in (impact_path, sats_path): shutil.copy2(p, backup/p.name)
        assert r.sha(backup/'pfe.swf') == CURRENT
        record = dict(status='backed-up', time=datetime.now().astimezone().isoformat(),
                      reason='User reports regression after afternoon SATS and impact changes',
                      beforeSHA256=CURRENT, afterSHA256=RESTORE, source=str(restore_path),
                      backup=str(backup), baseline=before)
        r.save(RECEIPT, record)
        assert r.baseline() == before, 'Dependencies changed before recovery'
        r.replace(restore_path, r.ROOT/'pfe.swf')
        assert r.sha(r.ROOT/'pfe.swf') == RESTORE
        record['status'] = 'restored-awaiting-smoke'
        r.save(RECEIPT, record)
        for p, value in ((impact_path,impact),(sats_path,sats)):
            value.update(status='rolled-back-by-user', recoveryReceipt=str(RECEIPT))
            r.save(p, value)
        # A failed smoke must not reinstall the performance-regressed host.
        # Preserve the explicitly requested restore and report the failure.
        try:
            m.prepare()
            probe = B/'generated/impact-tests-20261021/ContinuousSceneProbe.swf'
            assert probe.exists()
            shutil.copy2(probe, m.RUNTIME/'mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf')
            name='recovery-20261021-installed-native'
            m.run_owned(m.parse_args(['--name',name,'--suite','native','--vision','--high-qos',
                                     '--window-width','2048','--window-height','1123']),lease)
            result, inputs = r.result(name)
            assert len(result['assertions']) >= 51
            for path, digest in before.items():
                expected = RESTORE if path == 'pfe.swf' else digest
                assert r.sha(r.ROOT/path) == expected, ('Production drift',path)
                if path not in ('application.xml','mods/loader-manifest.txt'):
                    assert inputs[path] == expected, ('Test dependency mismatch',path)
            record.update(status='verified', smoke=dict(name=name,checks=len(result['assertions'])))
            lease.outcome='passed';lease.note='Pre-afternoon host restored; installed-file lifecycle passed'
        except BaseException as exc:
            record.update(status='restored-smoke-failed',error=repr(exc))
            raise
        finally:
            r.save(RECEIPT, record)
        print(json.dumps({k:record[k] for k in ('status','beforeSHA256','afterSHA256','backup','smoke')}))

if __name__ == '__main__': main()
