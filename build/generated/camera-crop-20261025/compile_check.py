"""Compile the prepared AS3 helpers/methods in a dynamic syntax harness only.

This produces no game host and runs no AIR. It is not a pixel, behavior, or
performance test; unresolved existing host fields are deliberately dynamic.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import subprocess
import sys
import uuid
from xml.sax.saxutils import escape

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('crop_preparation', HERE / 'prepare.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
motion = p.load('crop_compile_memory', p.B / 'motion-test.py')
JAVA = Path('D:/Program Files/Adobe Animate 2024/jre/bin/java.exe')
TOOLS = p.ROOT / 'mods/Sandevistan/build/tools'


def main():
    args = argparse.ArgumentParser()
    args.add_argument('--prepared', type=Path, required=True)
    folder = args.parse_args().prepared.resolve()
    assert folder.parent == (HERE / 'prepared').resolve(), 'Only this recipe output is allowed'
    provenance = json.loads((folder / 'preparation.json').read_text('utf-8'))
    assert provenance['prepared'] and not provenance['compiledHost']
    for name, expected in provenance['outputs'].items():
        assert p.sha(folder / name) == expected, name
    for name, expected in provenance['inputs'].items():
        assert p.sha(Path(name)) == expected, name
    inputs = dict(provenance['inputs'])
    for path in [Path(__file__), folder / 'preparation.json', JAVA,
                 TOOLS / 'flexsdk/lib/mxmlc.jar', TOOLS / 'airsdk/frameworks/libs/air/airglobal.swc']:
        inputs[str(path)] = p.sha(path)
    output = HERE / 'syntax-builds' / uuid.uuid4().hex
    output.mkdir(parents=True, exist_ok=False)
    source = output / 'GrafonCropCompile.as'
    source.write_text('''package {
import flash.display.*;
import flash.geom.*;
import flash.events.*;
import flash.utils.*;
// Syntax harness only. No game is instantiated; dynamic native fields here
// do not establish compatibility with the sealed production Grafon class.
public dynamic class GrafonCropCompile extends Sprite {
''' + (folder / 'scene-crop-presentation.as.inc').read_text('utf-8') + '\n' +
        (folder / 'candidate-methods.as.inc').read_text('utf-8') + '''
}
}
''', 'utf-8')
    stub = output / 'World.as'
    stub.write_text('package { public class World { public static var w:Object; } }\n', 'utf-8')
    config = output / 'compile.xml'
    config.write_text('''<flex-config><target-player>32.0</target-player><compiler>
<external-library-path><path-element>{air}</path-element></external-library-path>
<source-path><path-element>{source}</path-element></source-path><debug>false</debug><optimize>true</optimize><theme/>
</compiler></flex-config>'''.format(air=escape(str(TOOLS / 'airsdk/frameworks/libs/air/airglobal.swc')),
                                  source=escape(str(output))), 'utf-8')
    source_hash, config_hash, stub_hash = p.sha(source), p.sha(config), p.sha(stub)
    with motion.Registration(owner='ContinuousScene / crop source syntax / 01a13816',
                             purpose='Offline AS3 syntax harness only; no AIR or host build',
                             resource='offline', run_dir=output, evidence=output / 'result.json', wait=0) as lease:
        memory = motion.memory_status()
        assert memory['availableCommit'] >= 4 * 1024**3 and memory['availablePhysical'] >= 2 * 1024**3, memory
        command = [str(JAVA), '-Xmx512m', '-Dfile.encoding=UTF-8', '-jar',
                   str(TOOLS / 'flexsdk/lib/mxmlc.jar'), '+flexlib=' + str(TOOLS / 'flexsdk/frameworks'),
                   '-load-config=' + str(config), '-swf-version=32', '-static-link-runtime-shared-libraries=true',
                   '-output=' + str(output / 'SyntaxOnly.swf'), str(source)]
        process = None
        lease.before_launch('512MiB offline AS3 compiler; not AIR')
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            lease.child(process.pid)
            log, _ = process.communicate()
            (output / 'compile.log').write_bytes(log)
            assert process.returncode == 0, 'Compile failed: ' + str(output / 'compile.log')
        finally:
            if process is not None:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=15)
                lease.child_stopped()
        assert inputs == {name: p.sha(Path(name)) for name in inputs}, 'Input changed during compilation'
        assert p.sha(source) == source_hash and p.sha(config) == config_hash and p.sha(stub) == stub_hash
        report = dict(syntaxCompiled=True, compiledHost=False, launchedAir=False, deployed=False,
                      performanceEligible=False, inputs=inputs, prepared=str(folder),
                      sourceSHA256=source_hash, configSHA256=config_hash, stubSHA256=stub_hash, command=command,
                      compileLogSHA256=p.sha(output / 'compile.log'), swfSHA256=p.sha(output / 'SyntaxOnly.swf'),
                      limitation='Dynamic syntax harness; no sealed host integration, gameplay, pixels, or performance acceptance.')
        (output / 'result.json').write_text(json.dumps(report, indent=2), 'utf-8')
        lease.outcome = 'passed'
        lease.note = 'AS3 syntax compiled only; no host integration or game test'
        print(json.dumps(dict(syntaxCompiled=True, result=str(output / 'result.json'), compiledHost=False, launchedAir=False)))


if __name__ == '__main__':
    main()
