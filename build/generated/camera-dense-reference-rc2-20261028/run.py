"""Current normal/scene dense native combat reference; reuse exact old bytes."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys
import traceback

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('dense_reference_verification', HERE / 'verify_run.py')
validation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validation)
reuse = validation.reuse
silence = validation.silence
m = reuse.m


def memory_gate():
    value = m.memory_status()
    assert value['availableCommit'] >= 4*1024**3 and value['availablePhysical'] >= 2*1024**3, value
    return value


def options(name, mode):
    values = ['--name', name, '--high-qos', '--land', 'random_mane', '--encounter', '--fixed-enemies',
              '--benchmark', mode, '--short', '--stable-motion', '--native-input-motion', '--native-sprint',
              '--player-fire', '--combat-route', '--combat-route-length', '200', '--window-width', '2048',
              '--window-height', '1123', '--no-lighting', '--no-wall', '--draw-control', 'rcnative']
    return values + (['--native-room-x', '2', '--native-room-y', '4', '--native-route-x', '480', '--native-route-y', '119']
                     if mode == 'normal' else ['--expect-no-signs'])


def main():
    assert __debug__, 'Assertions must remain enabled'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    parser.add_argument('--mode', required=True, choices=['normal', 'scene'])
    parser.add_argument('--paired-evidence')
    parser.add_argument('--registry-wait', type=int, default=300)
    args = parser.parse_args()
    validation.evidence_name(args.name)
    assert not args.paired_evidence or args.mode == 'scene', 'Run ordinary reference first'
    folder, local = reuse.EVIDENCE / args.name, HERE / 'runs' / args.name
    assert not folder.exists() and not local.exists(), 'Preserve prior evidence'
    snapshot = reuse.prepared()
    reference = None
    if args.paired_evidence:
        validation.evidence_name(args.paired_evidence)
        reference = validation.verify(reuse.EVIDENCE / args.paired_evidence)
        assert reference['mode'] == 'normal'
    record = dict(version=reuse.VERSION, mode=args.mode, pairedEvidence=args.paired_evidence,
                  pairedResultSHA256=reference['resultSHA256'] if reference else None,
                  prepared=snapshot, preparedSHA256=reuse.sha(HERE / 'prepared.json'),
                  probeSHA256=reuse.PROBE_SHA, rebuilt=False, reusedOriginalCompilation=True,
                  options=options(args.name, args.mode), startupPolicies=[], diagnosticOnly=True, deployed=False)
    with m.Registration(owner='ContinuousScene / current dense reference / 01a13816', purpose=args.name,
                        run_dir=m.RUNTIME, evidence=folder, resource='game', wait=args.registry_wait) as lease:
        original_process = m.HiddenProcess
        try:
            assert not m.air_pids(), 'Benchmark waits for other AIR; no foreign process is changed'
            record['memoryBefore'] = memory_gate()
            assert reuse.prepared() == snapshot
            m.prepare()
            shutil.copy2(snapshot['provenance']['probePath'], m.RUNTIME / reuse.base.PROBE_PATH)
            assert reuse.sha(m.RUNTIME / reuse.base.PROBE_PATH) == reuse.PROBE_SHA
            for path, digest in snapshot['production'].items():
                if path not in ('application.xml', 'mods/loader-manifest.txt'):
                    assert reuse.sha(m.RUNTIME / path) == digest, path
            assert reuse.prepared() == snapshot
            record['memoryBeforeAir'] = memory_gate()

            def recorded_process(*positional, **keywords):
                try:
                    assert len(positional) == 1 and len(positional[0]) == 4
                    record['nativeSilence'] = silence.seed(positional[0][-1], m.RUNTIME)
                    record['memoryImmediatelyBeforeCreate'] = memory_gate()
                except BaseException:
                    lease.child_stopped()  # constructor has definitely not been called
                    record['failedBeforeProcessConstruction'] = True
                    raise
                process = original_process(*positional, **keywords)
                record['startupPolicies'].append(dict(pid=process.pid, policy=process.resource_policy))
                return process

            m.HiddenProcess = recorded_process
            try:
                m.run_owned(m.parse_args(record['options']), lease)
            except BaseException as error:
                record.update(executionError=repr(error), executionTraceback=traceback.format_exc())
                raise
            finally:
                m.HiddenProcess = original_process
                if folder.exists():
                    reuse.save(folder / 'runner-inputs.json', record)
                    reuse.save(folder / 'historical-compile-receipt-copy.json', reuse.read(reuse.OLD_RECEIPT))
            assert reuse.prepared() == snapshot
            summary = validation.verify(folder)
            reuse.save(folder / 'summary.json', summary)
            local.mkdir(parents=True)
            reuse.save(local / 'review.json', summary)
            lease.outcome = 'passed'
            lease.note = '1200 retained real native combat intervals; ordinary/continuous reference only'
            print(json.dumps(dict(name=args.name, mode=args.mode, complete=True,
                                  continuous=summary['continuous'], paired=summary.get('pairedComparison'))), flush=True)
        except BaseException as error:
            m.HiddenProcess = original_process
            record.update(error=repr(error), traceback=traceback.format_exc(), complete=False)
            local.mkdir(parents=True, exist_ok=True)
            reuse.save(local / 'runner-failure.json', record)
            if folder.exists():
                reuse.save(folder / 'runner-failure.json', record)
            lease.outcome, lease.note = 'failed', repr(error)
            raise


if __name__ == '__main__':
    main()
