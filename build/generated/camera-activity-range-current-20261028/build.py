"""Build the reviewed range sources with the pinned 39A compiler; never run AIR."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
VERSION = 'camera-activity-range-current-1'
MANIFEST_SHA = '5EAA844B49B7BF475AF7302968DED8D42357A80345FF1AE80B4FCA5A7C5B6230'
REFERENCE = HERE.parent / 'camera-dense-reference-rc2-20261028'
REFERENCE_PINS = {
    'prepared.json': 'B9A31F67F16863C3A27F56F47B38E8AD0E6A57D02263136E2E2F628AAF6F18EC',
    'run.py': '5A7428773E9015E904DFFD6BC81CDBFA588EDBCAFBC6CF1AEBF35B4D0690BE65',
    'verify_run.py': 'B8FFA411DEA7F308DFA8D85B37938894DBFBB9BD8C42BC7510D4A0DB19E1DB58',
    'verify_reuse.py': '354F1B3EDB332B9D156F04DD4491170424015E1F5ED9088D4001D03C29E516E1',
}
TARGETS = {'carrier': ('source-candidate', 'ContinuousSceneDoc.as', 'ContinuousSceneMod.swf'),
           'probe': ('probe-source', 'ContinuousSceneProbeDoc.as', 'ContinuousSceneProbe.swf')}


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()
def read(path): return json.loads(Path(path).read_text('utf-8-sig'))
def save(path, value): Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), 'utf-8')
def name_ok(value):
    assert value and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in value)
    return value


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reference():
    assert {name: sha(REFERENCE / name) for name in REFERENCE_PINS} == REFERENCE_PINS
    return load('activity_range_rc2_runtime', REFERENCE / 'run.py')


def sources():
    assert __debug__ and sha(HERE / 'source-manifest.json') == MANIFEST_SHA
    manifest = read(HERE / 'source-manifest.json')
    assert sha(HERE / 'prepare.py') == manifest['sourceInputs'][str(HERE / 'prepare.py')]
    load('activity_range_frozen_preparation', HERE / 'prepare.py').prepare(False)
    seed = read(manifest['probe']['seedReceipt'])
    assert sha(seed['configPath']) == seed['configSHA256']
    assert all(sha(path) == digest for path, digest in seed['compilerInputs'].items())
    return manifest, seed


def script_inputs():
    return {str(HERE / name): sha(HERE / name)
            for name in ('build.py', 'run.py', 'verify_run.py', 'BUILD-RUN.md')}


def compiler_memory(runtime):
    # Offline compiler only: run.py retains the full AIR 4 GiB/2 GiB gate.
    # Xmx caps the Java heap, not total process memory.
    value = runtime.m.memory_status()
    assert value['availableCommit'] >= 2*1024**3 and value['availablePhysical'] >= 1024**3, 'Offline compiler memory preflight'
    return value


def invocation(seed, kind, folder):
    source, entry, output = TARGETS[kind]
    output, config = folder / output, folder / (kind + '.xml')
    original = Path(seed['configPath']).read_text('utf-8-sig')
    before = str(Path(seed['frozenSourcePath']))
    assert original.count(before) == 1
    configuration = original.replace(before, str(HERE / source), 1)
    command = list(seed['command'])
    assert '-Xmx512m' in command and Path(command[-1]).name == 'ContinuousSceneProbeDoc.as'
    for old, new in (('-load-config=' + seed['configPath'], '-load-config=' + str(config)),
                     ('-output=' + seed['probePath'], '-output=' + str(output))):
        assert command.count(old) == 1
        command[command.index(old)] = new
    command[-1] = str(HERE / source / entry)
    return command, configuration, config, output


def verify(path):
    path = Path(path).resolve()
    assert path.name == 'build.json' and path.parent.parent == HERE / 'builds'
    assert not (path.parent / 'build-failure.json').exists(), 'Failed build evidence is not an accepted candidate'
    manifest, seed = sources()
    record = read(path)
    assert record['version'] == VERSION and record['sourceManifestSHA256'] == MANIFEST_SHA
    assert record['diagnosticOnly'] is True and record['compiled'] is True and record['airRun'] is False and record['deployed'] is False
    assert record['reusedOriginalCompilation'] is False and record['seedReceipt'] == manifest['probe']['seedReceipt']
    assert record['seedReceiptSHA256'] == sha(record['seedReceipt'])
    assert record['scriptInputs'] == script_inputs() and record['referencePins'] == REFERENCE_PINS
    assert record['compilerInputs'] == seed['compilerInputs'] and set(record['outputs']) == set(TARGETS)
    for kind, artifact in record['outputs'].items():
        command, config, config_path, output = invocation(seed, kind, path.parent)
        assert artifact['command'] == command and artifact['path'] == str(output)
        assert config_path.read_text('utf-8') == config and sha(config_path) == artifact['configSHA256']
        assert sha(output) == artifact['sha256'] and sha(path.parent / (kind + '.log')) == artifact['logSHA256']
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    parser.add_argument('--registry-wait', type=int, default=300)
    args = parser.parse_args()
    folder = HERE / 'builds' / name_ok(args.name)
    assert not folder.exists(), 'Preserve prior build evidence'
    manifest, seed = sources()
    inputs = script_inputs()
    runtime = reference()
    with runtime.m.Registration(owner='ContinuousScene / range source compiler / 01a13816', purpose=args.name,
            run_dir=folder, evidence=folder, resource='game', wait=args.registry_wait) as lease:
        folder.mkdir(parents=True)
        record = dict(version=VERSION, sourceManifestSHA256=MANIFEST_SHA, sourceManifest=str(HERE / 'source-manifest.json'),
            seedReceipt=manifest['probe']['seedReceipt'], seedReceiptSHA256=sha(manifest['probe']['seedReceipt']),
            compilerInputs=seed['compilerInputs'], scriptInputs=inputs, referencePins=REFERENCE_PINS,
            reusedOriginalCompilation=False, diagnosticOnly=True, compiled=False, airRun=False, deployed=False,
            heapLimitMiB=512, processMemoryLimitApplied=False, compilerPreflightCommitGiB=2, compilerPreflightPhysicalGiB=1, outputs={})
        try:
            for kind in TARGETS:
                memory = compiler_memory(runtime)
                minimum_commit = memory['availableCommit']
                command, config, config_path, output = invocation(seed, kind, folder)
                config_path.write_text(config, 'utf-8')
                process = None
                with (folder / (kind + '.log')).open('wb') as log:
                    lease.before_launch('Offline range ' + kind + ' compiler; no AIR')
                    try:
                        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
                        lease.child(process.pid)
                        deadline = time.monotonic() + 180
                        while process.poll() is None:
                            assert time.monotonic() < deadline, 'Compiler exceeded 180 seconds'
                            minimum_commit = min(minimum_commit, runtime.m.memory_status()['availableCommit'])
                            assert minimum_commit >= 512*1024**2, 'Compiler memory abort'
                            try: process.wait(timeout=.25)
                            except subprocess.TimeoutExpired: pass
                        assert process.returncode == 0, 'Compiler failed; retain log'
                    finally:
                        if process is not None:
                            if process.poll() is None: process.kill(); process.wait(timeout=15)
                            lease.child_stopped()
                assert output.is_file() and output.stat().st_size > 1000 and output.read_bytes()[:3] in (b'CWS', b'FWS')
                record['outputs'][kind] = dict(path=str(output), sha256=sha(output), command=command,
                    configSHA256=sha(config_path), logSHA256=sha(folder / (kind + '.log')), memoryBefore=memory,
                    minimumAvailableCommit=minimum_commit, exitCode=process.returncode, bytes=output.stat().st_size)
            sources()
            assert inputs == script_inputs()
            record['compiled'] = True
            save(folder / 'build.json', record)
            verify(folder / 'build.json')
            lease.outcome, lease.note = 'passed', 'Range carrier/probe compiled only; no AIR or deployment'
            print(json.dumps(dict(build=str(folder / 'build.json'), outputs={k:v['sha256'] for k,v in record['outputs'].items()})))
        except BaseException as error:
            record.update(error=repr(error), complete=False)
            save(folder / 'build-failure.json', record)
            lease.outcome, lease.note = 'failed', repr(error)
            raise


if __name__ == '__main__': main()
