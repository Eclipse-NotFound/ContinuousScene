"""Bounded read-only readiness checks, followed by at most one existing runner.

This wrapper does not register or claim a game test. The selected child retains
its registry and game memory guards. Root supervises the child; no process is
killed or retried here. Importing this file performs no readiness checks.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
MEMORY_HELPER = HERE.parents[1] / 'motion-test.py'
TARGETS = {
    'tail': (HERE.parent / 'camera-tail-sampling-20261028/run.py',
             HERE.parent / 'camera-tail-sampling-20261028/build.json'),
    'range': (HERE.parent / 'camera-activity-range-current-20261028/run.py',
              HERE.parent / 'camera-activity-range-current-20261028/builds/r1/build.json'),
}
WAIT_SECONDS, INTERVAL_SECONDS, REQUIRED_STABLE = 180, 5, 3
COMMIT, PHYSICAL = 5 * 1024**3, 2 * 1024**3


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', required=True, choices=sorted(TARGETS))
    parser.add_argument('--name', required=True)
    args = parser.parse_args()
    assert __debug__ and os.name == 'nt'
    assert 1 <= len(args.name) <= 96 and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
    runner, build_receipt = TARGETS[args.target]
    python = Path(sys.executable).resolve()
    command = [str(python), '-B', str(runner), '--name', args.name, '--registry-wait', '300']
    if args.target == 'range':
        command += ['--build', str(build_receipt)]
    fingerprints = {str(path): sha(path) for path in (Path(__file__).resolve(), runner, build_receipt, MEMORY_HELPER, python)}
    output = HERE / 'runs' / (args.name + '.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    record = dict(version='camera-benchmark-wait-1', name=args.name, target=args.target,
        status='waiting', readinessIsNotATest=True, rootSupervised=True, automaticRetry=False,
        inputSHA256=fingerprints, plannedCommand=command, childCommand=None, pid=None,
        exitCode=None, wrapperExitCode=None, launched=False, ready=False, samples=[],
        requiredCommit=COMMIT, requiredPhysical=PHYSICAL, intervalSeconds=INTERVAL_SECONDS,
        requiredStable=REQUIRED_STABLE, maximumWaitSeconds=WAIT_SECONDS, startedAt=time.time())
    # Exclusive reservation also rejects an existing receipt or symlink.
    with output.open('x', encoding='utf-8') as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)

    def save():
        temporary = output.with_suffix('.json.tmp')
        with temporary.open('w', encoding='utf-8') as stream:
            json.dump(record, stream, ensure_ascii=False, indent=2)
        os.replace(temporary, output)

    child = None
    started, stable = time.monotonic(), 0
    deadline = started + WAIT_SECONDS
    try:
        # Import only the existing read-only memory/process-name helpers. Do not
        # import or prepare either target, and do not claim registry occupancy.
        spec = importlib.util.spec_from_file_location('benchmark_wait_memory', MEMORY_HELPER)
        memory = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(memory)
        while time.monotonic() < deadline:
            status, air = memory.memory_status(), memory.air_pids()
            good = status['availableCommit'] >= COMMIT and status['availablePhysical'] >= PHYSICAL and not air
            stable = stable + 1 if good else 0
            record['samples'].append(dict(elapsed=time.monotonic() - started, memory=status,
                                          air=air, good=good, stable=stable))
            record['waitElapsedSeconds'] = time.monotonic() - started
            if stable == REQUIRED_STABLE:
                record.update(ready=True, status='ready')
                break
            save()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(INTERVAL_SECONDS, remaining))
        if not record['ready']:
            record.update(status='notReady', wrapperExitCode=0, waitElapsedSeconds=time.monotonic() - started)
            save()
            print(json.dumps(dict(status='notReady', receipt=str(output), launched=False)))
            return 0
        assert fingerprints == {path: sha(path) for path in fingerprints}, 'Wait inputs changed before launch'
        record.update(status='launching', childCommand=command, childStartedAt=time.time())
        save()
        # No pipes to fill, no detached helper, no retry, no process termination.
        # Context management waits/reaps this one child; its runner owns AIR and
        # preserves the existing bounded registry wait and game timeout/guards.
        with subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                              creationflags=subprocess.CREATE_NO_WINDOW) as child:
            record.update(status='running', launched=True, pid=child.pid)
            save()
            record['exitCode'] = child.wait()
        record.update(status='completed', wrapperExitCode=record['exitCode'], childEndedAt=time.time())
        save()
        print(json.dumps(dict(status='completed', receipt=str(output), exitCode=record['exitCode'])))
        return record['exitCode']
    except BaseException as error:
        record.update(status='interrupted' if isinstance(error, KeyboardInterrupt) else 'error',
                      error=repr(error), wrapperExitCode=130 if isinstance(error, KeyboardInterrupt) else 1)
        if child is not None:
            record['exitCode'] = child.poll()
        save()
        raise


if __name__ == '__main__':
    raise SystemExit(main())
