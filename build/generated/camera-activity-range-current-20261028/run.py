"""Run one registered, silent range ABBA; only the isolated CS and probe differ."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys
import traceback

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('activity_range_build', HERE / 'build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)
CS_PATH = 'mods/ContinuousScene/release/ContinuousSceneMod.swf'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--registry-wait', type=int, default=300)
    args = parser.parse_args()
    build.name_ok(args.name)
    receipt_path = args.build.resolve()
    candidate = build.verify(receipt_path)
    runtime = build.reference()
    m, reuse = runtime.m, runtime.reuse
    snapshot = reuse.prepared()
    folder = reuse.EVIDENCE / args.name
    assert not folder.exists(), 'Preserve prior evidence'
    expected = dict(snapshot['production'])
    expected[CS_PATH] = candidate['outputs']['carrier']['sha256']
    expected[reuse.base.PROBE_PATH] = candidate['outputs']['probe']['sha256']
    inputs = build.script_inputs()
    record = dict(version=build.VERSION, buildReceipt=str(receipt_path), buildReceiptSHA256=build.sha(receipt_path),
        referencePrepared=str(build.REFERENCE / 'prepared.json'), referencePreparedSHA256=build.REFERENCE_PINS['prepared.json'],
        scriptInputs=inputs, probeSHA256=expected[reuse.base.PROBE_PATH], carrierSHA256=expected[CS_PATH],
        options=runtime.options(args.name, 'scene'), startupPolicies=[], diagnosticOnly=True, deployed=False,
        rebuilt=True, reusedOriginalCompilation=False)
    with m.Registration(owner='ContinuousScene / native follow range ABBA / 01a13816', purpose=args.name,
            run_dir=m.RUNTIME, evidence=folder, resource='game', wait=args.registry_wait) as lease:
        original_process = m.HiddenProcess
        try:
            assert not m.air_pids(), 'No foreign AIR is changed'
            record['memoryBefore'] = runtime.memory_gate()
            assert reuse.prepared() == snapshot
            m.prepare()
            for kind, destination in (('carrier', CS_PATH), ('probe', reuse.base.PROBE_PATH)):
                shutil.copy2(candidate['outputs'][kind]['path'], m.RUNTIME / destination)
            for path, digest in expected.items():
                if path not in ('application.xml', 'mods/loader-manifest.txt'):
                    assert build.sha(m.RUNTIME / path) == digest, path
            assert reuse.prepared() == snapshot and build.verify(receipt_path) == candidate
            record['memoryBeforeAir'] = runtime.memory_gate()

            def recorded_process(*positional, **keywords):
                try:
                    assert len(positional) == 1 and len(positional[0]) == 4
                    record['nativeSilence'] = runtime.silence.seed(positional[0][-1], m.RUNTIME)
                    record['memoryImmediatelyBeforeCreate'] = runtime.memory_gate()
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
            finally:
                m.HiddenProcess = original_process
                if folder.exists(): build.save(folder / 'runner-inputs.json', record)
            assert reuse.prepared() == snapshot and inputs == build.script_inputs()
            assert build.verify(receipt_path) == candidate
            validation = build.load('activity_range_retained_validation', HERE / 'verify_run.py')
            summary = validation.verify(folder)
            build.save(folder / 'summary.json', summary)
            lease.outcome, lease.note = 'passed', '1200 native-follow range intervals and per-frame post-checks retained'
            print(json.dumps(dict(name=args.name, complete=True, arms=summary['rangeArms'])))
        except BaseException as error:
            m.HiddenProcess = original_process
            record.update(error=repr(error), traceback=traceback.format_exc(), complete=False)
            folder.mkdir(parents=True, exist_ok=True)
            build.save(folder / 'runner-failure.json', record)
            lease.outcome, lease.note = 'failed', repr(error)
            raise


if __name__ == '__main__': main()
