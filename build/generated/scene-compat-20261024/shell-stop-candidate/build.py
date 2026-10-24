"""Registered offline exact-bytecode candidate build. No AIR or deployment."""
from pathlib import Path
import importlib.util
import json
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
B = HERE.parents[2]
ROOT = B.parents[2]


def load(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


def main():
    p = load('shell_stop_product', HERE / 'product.py')
    e = load('shell_stop_build_support', B / 'enemy-speed.py')
    paths = [HERE/n for n in ('build.py', 'product.py', 'audit.py', 'static-proof.json')]
    paths += [B/n for n in ('enemy-speed.py', 'motion-test.py', 'profile-vision.py',
                           'bullet-segments-audit.py', 'stationary-threat-audit.py', 'native-crop-audit.py')]
    paths += [ROOT/'mods/ModLoader/tools'/n for n in ('test_registry.py', 'air_test_process.py')]
    paths += [p.BASE/'pfe.swf', p.BASE/'pfe.xml', e.JAVA, e.TOOLS/'ffdec/ffdec-cli.jar']
    inputs = {str(path):p.sha(path) for path in paths}
    assert not any((HERE/n).exists() for n in ('build.json', 'build-start.json', 'retained.xml',
                   'serialized.swf', 'serialized.xml', 'pfe.swf', 'pfe.xml', 'semantic-audit.json'))
    steps = []
    with e.motion.Registration(owner='ContinuousScene / shell stop exact build / 01a13816',
            purpose='A796 Part.initVis only plus two appended public constants; no AIR/deployment',
            run_dir=HERE, evidence=HERE/'build.json', wait=600) as lease:

        def guard():
            assert not e.motion.air_pids(), 'Other AIR remains untouched'
            assert p.sha(ROOT/'pfe.swf') == p.HOST, 'Installed A796 changed'
            memory = e.motion.memory_status()
            assert memory['availableCommit'] >= 4*1024**3 and memory['availablePhysical'] >= 2*1024**3, memory
            assert inputs == {path:p.sha(Path(path)) for path in inputs}, 'Frozen input changed'
            return memory

        def child(command, label):
            memory = guard(); process = None; lease.before_launch(label)
            try:
                with (HERE/('step-' + str(len(steps)) + '.log')).open('wb') as log:
                    process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
                    lease.child(process.pid); code = process.wait()
                steps.append(dict(label=label, command=list(map(str,command)), pid=process.pid,
                                  exitCode=code, memoryBefore=memory))
                (HERE/'steps.json').write_text(json.dumps(steps, indent=2) + '\n', encoding='utf-8')
                if code: raise subprocess.CalledProcessError(code, command)
            finally:
                if process is not None:
                    if process.poll() is None: process.kill(); process.wait(timeout=15)
                    lease.child_stopped()

        def audit(action):
            child([sys.executable, '-B', str(HERE/'product.py'), action], 'Shell exact ' + action)

        def ff(action, source, destination):
            assert not destination.exists(), 'Preserve earlier serializer output'
            child([str(e.JAVA), '-Xmx512m', '-jar', str(e.TOOLS/'ffdec/ffdec-cli.jar'),
                   action, str(source), str(destination)], 'Shell FFDec ' + action)

        before = guard()
        (HERE/'build-start.json').write_text(json.dumps(dict(version=p.VERSION, base=p.HOST,
            sourceInputs=inputs, memoryBefore=before, installedBefore=p.sha(ROOT/'pfe.swf')),
            indent=2) + '\n', encoding='utf-8')
        try:
            audit('stage')
            ff('-xml2swf', HERE/'retained.xml', HERE/'serialized.swf')
            ff('-swf2xml', HERE/'serialized.swf', HERE/'serialized.xml')
            audit('splice')
            ff('-swf2xml', HERE/'pfe.swf', HERE/'pfe.xml')
            audit('audit')
            guard()
            result = dict(version=p.VERSION, base=p.HOST, baseXML=p.XML, target=p.TARGET,
                candidate=p.sha(HERE/'pfe.swf'), candidateXML=p.sha(HERE/'pfe.xml'),
                audit=p.sha(HERE/'semantic-audit.json'), sourceInputs=inputs,
                productionCandidate=True, diagnosticOnly=False, runtimeVerified=False,
                performanceEligible=False, deployed=False, installedUnchanged=True,
                staticProof=p.sha(HERE/'static-proof.json'), steps=p.sha(HERE/'steps.json'))
            (HERE/'build.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
            lease.outcome='passed'; lease.note='Exact isolated candidate built; runtime/benefit pending'
            print(json.dumps(result), flush=True)
        finally:
            installed = p.sha(ROOT/'pfe.swf')
            (HERE/'installed-after.json').write_text(json.dumps(dict(expected=p.HOST, actual=installed,
                unchanged=installed == p.HOST), indent=2) + '\n', encoding='utf-8')
            assert installed == p.HOST, 'Installed host changed during offline build'


if __name__ == '__main__': main()
