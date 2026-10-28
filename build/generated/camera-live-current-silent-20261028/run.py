"""Current-dependency FA2B reuse: active native LMG combat, follow/held ABBA. No build/deploy."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys
import traceback

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validation = load('camera_live_result_validation', HERE / 'verify_run.py')
silence = load('camera_live_native_silence', HERE / 'silence.py')
reuse = validation.reuse
m, r = reuse.m, reuse.r


def memory_gate():
    value = m.memory_status()
    assert value['availableCommit'] >= 4*1024**3 and value['availablePhysical'] >= 2*1024**3, value
    return value


def options(name):
    return ['--name', name, '--high-qos', '--land', 'random_mane', '--encounter', '--fixed-enemies',
            '--benchmark', 'scene', '--short', '--stable-motion', '--native-input-motion', '--native-sprint',
            '--player-fire', '--combat-route', '--combat-route-length', '200', '--window-width', '2048',
            '--window-height', '1123', '--no-lighting', '--no-wall', '--draw-control', 'rcnative', '--expect-no-signs']


def main():
    assert __debug__, 'Assertions must remain enabled'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    parser.add_argument('--registry-wait', type=int, default=300)
    args = parser.parse_args()
    assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
    folder = reuse.EVIDENCE / args.name
    local = HERE / 'runs' / args.name
    assert not folder.exists() and not local.exists(), 'Keep prior evidence'
    snapshot = reuse.prepared()
    record = dict(version=reuse.VERSION, prepared=snapshot, preparedSHA256=reuse.sha(HERE / 'prepared.json'),
                  probeSHA256=reuse.PROBE_SHA, reusedOriginalCompilation=True, rebuilt=False,
                  options=options(args.name), startupPolicies=[], diagnosticOnly=True, deployed=False)
    with m.Registration(owner='ContinuousScene / current live camera combat / 01a13816', purpose=args.name,
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
                # Recheck at the real creation boundary, after descriptor/config IO.
                try:
                    assert len(positional) == 1 and len(positional[0]) == 4
                    record['nativeSilence'] = silence.seed(positional[0][-1], m.RUNTIME)
                    record['memoryImmediatelyBeforeCreate'] = memory_gate()
                except BaseException:
                    # before_launch has run, but no process constructor was called.
                    # Clear only this known pre-create state; constructor failures
                    # below retain the registry's conservative uncertainty.
                    lease.child_stopped()
                    record['failedBeforeProcessConstruction'] = True
                    raise
                process = original_process(*positional, **keywords)
                record['startupPolicies'].append(dict(pid=process.pid, policy=getattr(process, 'resource_policy', None)))
                return process

            m.HiddenProcess = recorded_process
            execution_error = None
            try:
                m.run_owned(m.parse_args(record['options']), lease)
            except BaseException as error:
                execution_error = error
                record.update(executionError=repr(error), executionTraceback=traceback.format_exc())
            finally:
                m.HiddenProcess = original_process
                # These are successor receipts, never modifications of the 20261024 receipt.
                if folder.exists():
                    reuse.save(folder / 'runner-inputs.json', record)
                    reuse.save(folder / 'historical-compile-receipt-copy.json', reuse.read(reuse.OLD_RECEIPT))
            if execution_error:
                raise execution_error
            assert reuse.prepared() == snapshot
            summary = validation.verify(folder)
            reuse.save(folder / 'summary.json', summary)
            local.mkdir(parents=True)
            reuse.save(local / 'runner-inputs.json', record)
            reuse.save(local / 'review.json', summary)
            lease.outcome = 'passed'
            lease.note = '1200 active native combat intervals; follow/held ABBA; diagnostic only'
            print(json.dumps(dict(name=args.name, complete=True, arms=summary['arms'])), flush=True)
        except BaseException as error:
            m.HiddenProcess = original_process
            record.update(error=repr(error), traceback=traceback.format_exc(), complete=False)
            local.mkdir(parents=True, exist_ok=True)
            reuse.save(local / 'runner-failure.json', record)
            if folder.exists():
                reuse.save(folder / 'runner-failure.json', record)
            lease.outcome = 'failed'
            lease.note = repr(error)
            raise


if __name__ == '__main__':
    main()
