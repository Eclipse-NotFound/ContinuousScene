"""Build the standalone diagnostic addon; no host patch, AIR or deployment."""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
sys.path.insert(0, str(ROOT / 'mods/ModLoader/tools'))
from test_registry import Registration


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def memory():
    class Status(ctypes.Structure):
        _fields_ = [('length', ctypes.c_uint32), ('load', ctypes.c_uint32)] + [
            (key, ctypes.c_uint64) for key in ('totalPhysical', 'availablePhysical',
            'totalCommit', 'availableCommit', 'totalVirtual', 'availableVirtual', 'extended')]
    value = Status(); value.length = ctypes.sizeof(value)
    assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(value))
    return dict(availableCommit=value.availableCommit, availablePhysical=value.availablePhysical)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry-wait', type=int, default=300)
    args = parser.parse_args()
    assert __debug__
    output = HERE / 'ContinuousSceneTailSamplerMod.swf'
    receipt = HERE / 'build.json'
    assert not output.exists() and not receipt.exists(), 'Preserve an existing build'
    command = json.loads((HERE / 'compile-command.json').read_text('utf-8-sig'))
    assert '-Xmx512m' in command and '-output=' + output.as_posix() in command
    sources = {str(HERE / name): sha(HERE / name) for name in (
        'build.py', 'ContinuousSceneTailSamplerMod.as', 'TailSamplerDoc.as',
        'compiler.xml', 'compile-command.json', 'README.md')}
    compiler_files = [Path(command[0]), Path(command[command.index('-jar') + 1]),
        ROOT / 'mods/Sandevistan/build/tools/airsdk/frameworks/libs/air/airglobal.swc']
    compiler = {str(path): sha(path) for path in compiler_files}
    record = dict(command=command, sourceInputs=sources, directCompilerInputs=compiler,
        diagnosticOnly=True, deployed=False, runtimeVerified=False,
        heapLimitMiB=512, processMemoryLimitApplied=False, complete=False)
    with Registration(owner='ContinuousScene / tail sampler build / 01a13816',
            purpose='Compile standalone four-window diagnostic addon', run_dir=HERE,
            evidence=HERE, resource='game', wait=args.registry_wait) as lease:
        before = memory(); record['memoryBefore'] = before
        assert before['availableCommit'] >= 1024**3 and before['availablePhysical'] >= 1024**3
        process = None
        started = time.monotonic()
        try:
            with (HERE / 'compiler.stdout.log').open('xb') as out, (HERE / 'compiler.stderr.log').open('xb') as err:
                lease.before_launch('Owned Java compiler, no AIR; maximum Java heap 512 MiB')
                process = subprocess.Popen(command, cwd=HERE, stdout=out, stderr=err,
                    creationflags=subprocess.CREATE_NO_WINDOW)
                lease.child(process.pid)
                record['pid'] = process.pid
                while process.poll() is None:
                    if time.monotonic() - started > 120:
                        raise TimeoutError('Owned compiler exceeded 120 seconds')
                    assert memory()['availableCommit'] >= 512*1024**2, 'Memory pressure during compilation'
                    time.sleep(.25)
                record['exitCode'] = process.returncode
            assert process.returncode == 0, 'Read retained compiler logs'
            assert output.is_file() and output.stat().st_size > 1000
            assert output.read_bytes()[:3] in (b'CWS', b'FWS')
            assert sources == {path: sha(path) for path in sources}
            assert compiler == {path: sha(path) for path in compiler}
            record.update(complete=True, outputSHA256=sha(output), outputBytes=output.stat().st_size)
            lease.outcome = 'passed'
            lease.note = 'Compiler succeeded; addon has not been loaded in AIR'
        except BaseException as error:
            record['error'] = repr(error)
            raise
        finally:
            if process is not None:
                if process.poll() is None: process.kill()
                process.wait(timeout=10)
                lease.child_stopped()
            record['elapsedSeconds'] = time.monotonic() - started
            receipt.write_text(json.dumps(record, ensure_ascii=False, indent=2), 'utf-8')
    print(json.dumps({key: record[key] for key in ('complete', 'outputSHA256', 'outputBytes', 'elapsedSeconds')}))


if __name__ == '__main__':
    main()
