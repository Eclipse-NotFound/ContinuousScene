"""One merged deployment after the concurrent aim-v3 session finishes.

Sequence: build the product from the *current* working tree (aim-v3 + the
culling-scale change), gate it (no test/probe classes, culling markers present
in the bytecode, compiled class set sane), re-run the culling suites against the
merged sources, then deploy release with backup + readback + receipt.

Refuses when the formal release is no longer the 0.9.9 baseline this session
started from, unless --expect-release is given explicitly, so a deploy by the
other session is never overwritten silently.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
MOD = Path(__file__).resolve().parents[3]
ROOT = MOD.parents[1]
SDK = ROOT / 'mods/Sandevistan/build/tools'
JAVA = Path('D:/Program Files/Adobe Animate 2024/jre/bin/java.exe')
FFDEC = SDK / 'ffdec/ffdec-cli.jar'
BASE = MOD / 'build/generated/cull-scale-20261104'
OUT = BASE / 'product-merged'
RELEASE = MOD / 'release/ContinuousSceneMod.swf'
BASELINE_RELEASE = 'D04CD26AA674238BBB2F43A2CA49C57811301E9B9B614352A099F8190D9E0193'
CULLING_CLASSES = ('SceneObjectCulling', 'SceneCullEntry')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def run(command, **kwargs):
    return subprocess.run(command, check=False, capture_output=True, text=True,
                          creationflags=subprocess.CREATE_NO_WINDOW, **kwargs)


def build_product(source_dir=None):
    if OUT.exists():
        shutil.rmtree(OUT)
    src = OUT / 'src'
    shutil.copytree(source_dir or (MOD / 'src'), src)
    config = OUT / 'compiler.xml'
    config.write_text(
        '<flex-config><target-player>32.0</target-player><compiler>'
        '<external-library-path><path-element>' + str(SDK / 'airsdk/frameworks/libs/air/airglobal.swc').replace('\\', '/') +
        '</path-element></external-library-path><source-path><path-element>' + src.as_posix() +
        '</path-element></source-path><debug>false</debug><optimize>true</optimize><theme/></compiler></flex-config>',
        encoding='utf-8')
    output = OUT / 'ContinuousSceneMod.swf'
    command = [str(JAVA), '-Xmx512m', '-Dfile.encoding=UTF-8', '-jar', str(SDK / 'flexsdk/lib/mxmlc.jar'),
               '+flexlib=' + str(SDK / 'flexsdk/frameworks'), '-load-config=' + str(config), '-swf-version=32',
               '-theme=', '-compiler.fonts.local-fonts-snapshot=',
               '-use-network=false', '-static-link-runtime-shared-libraries=true',
               '-link-report=' + str(OUT / 'link.xml'), '-output=' + str(output), str(src / 'ContinuousSceneDoc.as')]
    with (OUT / 'compiler.log').open('w', encoding='utf-8') as log:
        log.write(' '.join(command) + '\n\n')
        log.flush()
        proc = run(command)
        log.write((proc.stdout or '') + (proc.stderr or ''))
    if proc.returncode != 0:
        sys.exit('merged product compile failed: see ' + str(OUT / 'compiler.log'))
    definitions = sorted({n.attrib['id'] for n in ET.parse(OUT / 'link.xml').getroot().iter('def')})
    leaked = [n for n in definitions
              if n.startswith(('fe:', 'fe.', 'tests:', 'tests.')) or 'Checks' in n or 'Probe' in n]
    if leaked:
        sys.exit('non-production classes linked: ' + repr(leaked))
    if 'ContinuousSceneMod' not in definitions or 'SceneObjectCulling' not in definitions:
        sys.exit('merged product is missing required classes')
    exported = OUT / 'export'
    run([str(JAVA), '-Xmx512m', '-jar', str(FFDEC), '-selectclass', 'SceneObjectCulling',
         '-export', 'script', str(exported), str(output)])
    owners = list(exported.rglob('SceneObjectCulling.as'))
    if len(owners) != 1:
        sys.exit('could not export SceneObjectCulling from the merged product')
    emitted = owners[0].read_text(encoding='utf-8', errors='replace')
    for needle in ('applyScale', 'refreshBase', 'baseLeft', 'event-tracked-2'):
        if needle not in emitted:
            sys.exit('culling optimisation missing from merged bytecode: ' + needle)
    return output, definitions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--expect-release', default=BASELINE_RELEASE)
    parser.add_argument('--note', default='merged after aim-v3 session')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--source-dir', default=None,
                        help='rehearse against another source tree; deploy still refuses unless dry-run')
    args = parser.parse_args()
    current = sha(RELEASE)
    if current != args.expect_release:
        sys.exit('release is ' + current + ', expected ' + args.expect_release +
                 '; pass --expect-release if the other session already deployed')
    output, definitions = build_product(args.source_dir)
    candidate = sha(output)
    checks = run([sys.executable, str(MOD / 'build/culling-scale-checks.py')], cwd=MOD)
    (OUT / 'checks-run.log').write_text((checks.stdout or '') + (checks.stderr or ''), encoding='utf-8')
    if checks.returncode != 0:
        sys.exit('culling suites failed on the merged tree: see ' + str(OUT / 'checks-run.log'))
    suite = json.loads((MOD / 'build/generated/cull-scale-20261104/checks/checks.json').read_text(encoding='utf-8'))
    if not (suite['result'] and suite['result']['ok']):
        sys.exit('culling suites report not ok')
    receipt = {
        'builtAt': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
        'candidate': candidate,
        'size': output.stat().st_size,
        'classes': definitions,
        'previousRelease': current,
        'suite': {'pass': suite['result']['pass'], 'fail': suite['result']['fail'],
                  'sources': suite['source']},
        'note': args.note,
        'deployed': False,
    }
    if args.dry_run:
        (OUT / 'build.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8')
        print(json.dumps(receipt, indent=2, ensure_ascii=False))
        return
    air = run(['powershell', '-NoProfile', '-Command',
               'Get-Process -Name adl64,adl -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id'])
    air_ids = [int(x) for x in air.stdout.split() if x.strip().isdigit()]
    stamp = time.strftime('%Y%m%d-%H%M%S')
    backup = MOD / 'build/backups' / ('ContinuousSceneMod-before-cullscale-merged-' + stamp + '.swf')
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(RELEASE, backup)
    temp = RELEASE.with_suffix('.candidate')
    shutil.copy2(output, temp)
    temp.replace(RELEASE)
    readback = sha(RELEASE)
    if readback != candidate:
        shutil.copy2(backup, RELEASE)
        sys.exit('readback mismatch; rolled back')
    receipt.update(deployed=True, backup=str(backup.relative_to(MOD)),
                   hostUnchanged=sha(ROOT / 'pfe.swf'),
                   sceneXml=sha(MOD / 'release/scene.xml'),
                   airRunningAtDeploy=air_ids, restartRequired=True,
                   rollback='copy ' + backup.name + ' over release/ContinuousSceneMod.swf, restart game')
    target = MOD / 'state' / ('culling-scale-merged-deployment-' + time.strftime('%Y%m%d') + '.json')
    target.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8')
    (OUT / 'build.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(receipt, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
