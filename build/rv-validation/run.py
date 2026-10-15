"""Isolated validation of the frozen RV candidate; never writes RV or release."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import time
import uuid
from datetime import datetime, timezone

OUT = Path(__file__).resolve().parent
MOD = OUT.parent.parent
ROOT = MOD.parent.parent
RV = ROOT / 'mods/RealisticVision'
FROZEN = MOD / 'build/generated/rv-production'
CANDIDATE = MOD / 'build/runtime/mods/RealisticVision/release/RealisticVisionMod.swf'
SDK = ROOT / 'mods/Sandevistan/build/tools/flexsdk'
AIR = ROOT / 'mods/Sandevistan/build/tools/airsdk/frameworks/libs/air/airglobal.swc'
JAVA = Path('D:/Program Files/Adobe Animate 2024/jre/bin/java.exe')
PINNED_SOURCE = '6979263B178B4DEEDF563A88C560614BD867D4FAD89D806484B5A5B851C0D446'
PINNED_SWF = 'B7695DF82AA45FDB783C4EB88AFFCB0C34A7674E3A052D2FD128867172A83A49'
CASES = [('SoftHarness', 'MOTION COMPLETE', 16),
         ('SharedExplorationHarness', 'SHARED COMPLETE failures=0', 21),
         ('SceneSightHarness', 'SCENE SIGHT COMPLETE failures=0', 5)]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def stamp():
    return datetime.now(timezone.utc).isoformat()


def pin_check():
    assert digest(FROZEN / 'RealisticVisionMod.as') == PINNED_SOURCE, 'Frozen source changed'
    assert CANDIDATE.stat().st_size == 26176, 'Candidate size changed'
    assert digest(CANDIDATE) == PINNED_SWF, 'Candidate SWF changed'


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')


def prepare():
    pin_check()
    manifest = {'createdAt': stamp(), 'candidateSWF': str(CANDIDATE),
                'candidateSHA256': PINNED_SWF, 'candidateSize': 26176,
                'sourceSHA256': PINNED_SOURCE,
                'scope': 'Compiled frozen candidate AS3 with private access made public, linked to controlled game stubs; does not load the production SWF.',
                'files': []}
    # Snapshot only the required harnesses and their controlled type dependencies.
    source_sets = [(FROZEN, OUT / 'frozen', list(FROZEN.rglob('*'))),
                   (RV / 'build/stubs', OUT / 'stubs', list((RV / 'build/stubs').rglob('*.as'))),
                   (RV / 'build/motion-tests', OUT / 'harness',
                    [RV / 'build/motion-tests' / (name + '.as') for name in
                     ('SoftHarness', 'SharedExplorationHarness', 'MotionLocation')]),
                   (MOD / 'src/tests', OUT / 'harness', [MOD / 'src/tests/SceneSightHarness.as'])]
    for source_root, destination_root, paths in source_sets:
        for source in paths:
            if not source.is_file():
                continue
            destination = destination_root / source.relative_to(source_root)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            assert digest(source) == digest(destination)
            manifest['files'].append({'source': str(source), 'snapshot': str(destination.relative_to(OUT)),
                                      'sha256': digest(source), 'bytes': source.stat().st_size})
    source = (OUT / 'frozen/RealisticVisionMod.as').read_text(encoding='utf-8')
    exposed, count = re.subn(r'\bprivate\b', 'public', source)
    (OUT / 'exposed').mkdir(exist_ok=True)
    (OUT / 'exposed/RealisticVisionMod.as').write_text(exposed, encoding='utf-8')
    manifest['accessOnlyChanges'] = count
    manifest['exposedSourceSHA256'] = digest(OUT / 'exposed/RealisticVisionMod.as')
    assert exposed == re.sub(r'\bprivate\b', 'public', source)
    config = OUT / 'compiler.xml'
    config.write_text('<flex-config><compiler><external-library-path><path-element>' + str(AIR) +
                      '</path-element></external-library-path><debug>true</debug><optimize>false</optimize>' +
                      '<theme/></compiler><target-player>32.0</target-player><swf-version>32</swf-version></flex-config>',
                      encoding='utf-8')
    manifest['compiler'] = {'java': str(JAVA), 'mxmlc': str(SDK / 'lib/mxmlc.jar'),
                            'airglobal': str(AIR), 'debug': True, 'optimize': False,
                            'targetPlayer': '32.0', 'swfVersion': 32}
    write_json(OUT / 'provenance.json', manifest)
    for name, marker, expected in CASES:
        cmd = [str(JAVA), '-Xmx384m', '-jar', str(SDK / 'lib/mxmlc.jar'),
               '+flexlib=' + str(SDK / 'frameworks'), '-load-config=' + str(config),
               '-omit-trace-statements=false', '-static-link-runtime-shared-libraries=true',
               '-source-path=' + ','.join(str(OUT / d) for d in ('exposed', 'harness', 'stubs', 'frozen')),
               '-output=' + str(OUT / (name + '.swf')), str(OUT / 'harness' / (name + '.as'))]
        started = time.perf_counter()
        run = subprocess.run(cmd, cwd=OUT, capture_output=True, text=True, timeout=90)
        (OUT / (name + '.compile.log')).write_text(run.stdout + run.stderr, encoding='utf-8')
        assert run.returncode == 0, name + ' compilation failed: ' + run.stdout + run.stderr
        app_id = 'pfe-modsettings-cs-vision-' + uuid.uuid4().hex
        descriptor = OUT / (name + '.xml')
        descriptor.write_text('<application xmlns="http://ns.adobe.com/air/application/30.0"><id>' + app_id +
                              '</id><versionNumber>1.0</versionNumber><filename>RVTest</filename><initialWindow><content>' +
                              name + '.swf</content><visible>false</visible><renderMode>cpu</renderMode>' +
                              '</initialWindow></application>', encoding='utf-8')
        manifest.setdefault('harnessBuilds', []).append({'name': name, 'appId': app_id,
                                                      'sha256': digest(OUT / (name + '.swf')),
                                                      'expectedChecks': expected, 'compileSeconds': round(time.perf_counter() - started, 3)})
        write_json(OUT / 'provenance.json', manifest)
        print(name + ' compiled', flush=True)
    pin_check()


def run_tests():
    pin_check()
    manifest = json.loads((OUT / 'provenance.json').read_text(encoding='utf-8'))
    assert len(manifest['harnessBuilds']) == len(CASES)
    for item in manifest['files']:
        assert digest(OUT / item['snapshot']) == item['sha256'], 'Snapshot changed: ' + item['snapshot']
    assert digest(OUT / 'exposed/RealisticVisionMod.as') == manifest['exposedSourceSHA256']
    results = {'startedAt': stamp(), 'candidateSHA256': PINNED_SWF,
               'sourceSHA256': PINNED_SOURCE, 'scope': manifest['scope'], 'tests': []}
    try:
        for (name, marker, expected), build in zip(CASES, manifest['harnessBuilds']):
            assert build['name'] == name
            assert digest(OUT / (name + '.swf')) == build['sha256']
            cmd = [str(ROOT / 'adl64.exe'), '-runtime', str(ROOT / 'runtimes/air/win64'), str(OUT / (name + '.xml'))]
            started = time.perf_counter()
            try:
                run = subprocess.run(cmd, cwd=OUT, capture_output=True, text=True, timeout=55,
                                     creationflags=subprocess.CREATE_NO_WINDOW)
                log, code = run.stdout + run.stderr, run.returncode
            except subprocess.TimeoutExpired as error:
                def decoded(value):
                    return value.decode(errors='replace') if isinstance(value, bytes) else (value or '')
                log, code = decoded(error.stdout) + decoded(error.stderr) + '\nHARNESS TIMEOUT\n', -999
            (OUT / (name + '.log')).write_text(log, encoding='utf-8')
            checks = len(re.findall(r'^PASS ', log, flags=re.M))
            passed = code == 0 and marker in log and 'FAIL ' not in log and 'MOTION RED' not in log and checks == expected
            results['tests'].append({'name': name, 'passed': passed, 'exitCode': code, 'checks': checks,
                                     'expectedChecks': expected, 'seconds': round(time.perf_counter() - started, 3),
                                     'appId': build['appId'], 'harnessSHA256': build['sha256']})
            write_json(OUT / 'result.json', results)
            print(log, flush=True)
            assert passed, name + ' failed (assertions are unchanged)'
        pin_check()
        results['passed'] = True
        results['completedAt'] = stamp()
    except BaseException as error:
        results['passed'] = False
        results['error'] = str(error)
        raise
    finally:
        write_json(OUT / 'result.json', results)
        evidence = MOD / 'knowledge/experiments/evidence' / ('rv-v05-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
        evidence.mkdir(parents=True, exist_ok=False)
        for filename in ['provenance.json', 'result.json', 'run.py'] + [name + suffix for name, _, _ in CASES for suffix in ('.log', '.compile.log', '.xml')]:
            source = OUT / filename
            if source.exists():
                shutil.copy2(source, evidence / filename)
        print('Evidence: ' + str(evidence), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('prepare', 'run'))
    action = parser.parse_args().action
    prepare() if action == 'prepare' else run_tests()
