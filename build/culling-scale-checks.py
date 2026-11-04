"""Compile and run the culling suites in a standalone AIR app (no game).

Frozen copies of the production sources are compiled so the receipt records
exactly which bytes were exercised. The app runs headless (visible=false),
writes its JSON result to its own AIR storage directory and exits with
0 (all pass) / 1 (assertion failure) / 2 (harness fault).
"""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import uuid

sys.dont_write_bytecode = True
MOD = Path(__file__).resolve().parents[1]
ROOT = MOD.parents[1]
SDK = ROOT / 'mods/Sandevistan/build/tools'
JAVA = Path('D:/Program Files/Adobe Animate 2024/jre/bin/java.exe')
OUT = MOD / 'build/generated/cull-scale-20261104'
FROZEN = ('SceneObjectCulling.as', 'SceneCullEntry.as', 'tests/SceneCullingChecks.as',
          'tests/SceneCullingScaleChecks.as', 'tests/CullingChecksApp.as')
ENTRY = 'tests/CullingChecksApp.as'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def main():
    out = OUT / 'checks'
    if out.exists():
        shutil.rmtree(out)
    src = out / 'src'
    frozen = {}
    for name in FROZEN:
        target = src / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(MOD / 'src' / name, target)
        frozen[name] = sha(target)
    config = out / 'compiler.xml'
    config.write_text(
        '<flex-config><target-player>32.0</target-player><compiler>'
        '<external-library-path><path-element>' + str(SDK / 'airsdk/frameworks/libs/air/airglobal.swc').replace('\\', '/') +
        '</path-element></external-library-path><source-path><path-element>' + src.as_posix() +
        '</path-element></source-path><debug>true</debug><optimize>true</optimize><theme/></compiler></flex-config>',
        encoding='utf-8')
    command = [str(JAVA), '-Xmx512m', '-Dfile.encoding=UTF-8', '-jar', str(SDK / 'flexsdk/lib/mxmlc.jar'),
               '+flexlib=' + str(SDK / 'flexsdk/frameworks'), '-load-config=' + str(config), '-swf-version=32',
               # The shared Flex SDK no longer ships frameworks/localFonts.ser;
               # empty overrides restore compilation (see ConditionSystem/build).
               '-theme=', '-compiler.fonts.local-fonts-snapshot=',
               '-use-network=false', '-static-link-runtime-shared-libraries=true',
               '-output=' + str(out / 'checks.swf'), str(src / ENTRY)]
    with (out / 'compiler.log').open('w', encoding='utf-8') as log:
        log.write(' '.join(command) + '\n\n')
        log.flush()
        proc = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                              creationflags=subprocess.CREATE_NO_WINDOW)
    if proc.returncode != 0:
        sys.exit('compile failed: see ' + str(out / 'compiler.log'))
    app_id = 'remains.cs.cullchecks.' + uuid.uuid4().hex
    descriptor = out / 'culling-checks.xml'
    descriptor.write_text(
        '<application xmlns="http://ns.adobe.com/air/application/30.0"><id>' + app_id +
        '</id><versionNumber>1.0</versionNumber><filename>CullingChecks</filename><initialWindow><content>'
        'checks.swf</content><visible>false</visible><renderMode>cpu</renderMode></initialWindow></application>',
        encoding='utf-8')
    run = subprocess.run([str(ROOT / 'adl64.exe'), '-runtime', str(ROOT / 'runtimes/air/win64'), str(descriptor)],
                         cwd=out, capture_output=True, text=True, timeout=180,
                         creationflags=subprocess.CREATE_NO_WINDOW)
    log_text = (run.stdout or '') + (run.stderr or '')
    (out / 'run.log').write_text(log_text, encoding='utf-8')
    payload = None
    for line in log_text.splitlines():
        if line.startswith('CS-CULLING-CHECKS '):
            payload = json.loads(line[len('CS-CULLING-CHECKS '):])
    storage = Path.home() / 'AppData/Roaming' / app_id / 'Local Store' / 'cs-culling-checks-result.json'
    if payload is None and storage.exists():
        try:
            payload = json.loads(storage.read_text(encoding='utf-8'))
        except ValueError:
            payload = None
    receipt = {'compiled': True, 'appId': app_id, 'exitCode': run.returncode,
               'source': frozen, 'swf': sha(out / 'checks.swf'),
               'result': payload, 'log': str((out / 'run.log').relative_to(MOD)),
               'storageResult': str(storage) if storage.exists() else None}
    (out / 'checks.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8')
    if payload is None:
        print(log_text)
        sys.exit('no result block; see ' + str(out / 'run.log'))
    print(json.dumps({'ok': payload['ok'], 'pass': payload['pass'], 'fail': payload['fail'],
                      'error': payload['error'], 'failures': payload['failures']}, ensure_ascii=False, indent=2))
    if not payload['ok'] or run.returncode != 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
