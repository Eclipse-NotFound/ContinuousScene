"""Build the ContinuousScene product SWF for the culling-scale candidate.

Integration discipline for a shared working tree: a second DSH session is
concurrently editing three aim-related files. Stage the whole src tree, pin
those three files back to their committed (currently deployed) content, and
compile from the staging copy. Nothing under src/, release/ or the game's
formal SWFs is written by this script.

Verifies: entry class present, no test/probe classes, the new method really is
in the emitted bytecode, and records every hash in a receipt.
"""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
MOD = Path(__file__).resolve().parents[1]
ROOT = MOD.parents[1]
SDK = ROOT / 'mods/Sandevistan/build/tools'
JAVA = Path('D:/Program Files/Adobe Animate 2024/jre/bin/java.exe')
FFDEC = SDK / 'ffdec/ffdec-cli.jar'
OUT = MOD / 'build/generated/cull-scale-20261104/product'
# Files owned by the concurrently running aim-v3 session: pinned to HEAD so the
# candidate is measurable against the deployed 0.9.9 behaviour.
PINNED = ('ContinuousSceneMod.as', 'SceneAimController.as', 'tests/SceneAimChecks.as')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def git_show(rel):
    return subprocess.run(['git', 'show', 'HEAD:src/' + rel], cwd=MOD, capture_output=True, check=True).stdout


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    src = OUT / 'src'
    shutil.copytree(MOD / 'src', src)
    for name in PINNED:
        (src / name).write_bytes(git_show(name))
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
        proc = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                              creationflags=subprocess.CREATE_NO_WINDOW)
    if proc.returncode != 0:
        sys.exit('compile failed: see ' + str(OUT / 'compiler.log'))
    definitions = sorted({node.attrib['id'] for node in ET.parse(OUT / 'link.xml').getroot().iter('def')})
    leaked = [name for name in definitions
              if name.startswith(('fe:', 'fe.', 'tests:', 'tests.')) or 'Checks' in name or 'Probe' in name]
    if leaked:
        sys.exit('non-production classes linked: ' + repr(leaked))
    for required in ('ContinuousSceneDoc', 'ContinuousSceneMod', 'SceneObjectCulling',
                     'SceneCullEntry', 'NativeSceneActivity', 'ScenePresentationCoordinator'):
        if required not in definitions:
            sys.exit('missing class ' + required)
    # The optimisation must be visible in the emitted bytecode, not only in source.
    exported = OUT / 'export'
    subprocess.run([str(JAVA), '-Xmx512m', '-jar', str(FFDEC), '-selectclass', 'SceneObjectCulling',
                    '-export', 'script', str(exported), str(output)], check=True,
                   capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    owners = list(exported.rglob('SceneObjectCulling.as'))
    if len(owners) != 1:
        sys.exit('could not export SceneObjectCulling from the product SWF')
    emitted = owners[0].read_text(encoding='utf-8', errors='replace')
    for needle in ('applyScale', 'refreshBase', 'baseLeft', 'event-tracked-2'):
        if needle not in emitted:
            sys.exit('optimisation marker missing from bytecode: ' + needle)
    receipt = {
        'product': 'ContinuousSceneMod culling-scale candidate',
        'compiled': True,
        'swf': sha(output),
        'size': output.stat().st_size,
        'source': {str(p.relative_to(src)): sha(p) for p in sorted(src.rglob('*.as'))},
        'pinnedToHead': {name: sha(src / name) for name in PINNED},
        'workingTreePinnedDiffs': {
            name: {'head': sha(src / name), 'working': sha(MOD / 'src' / name),
                   'equal': sha(src / name) == sha(MOD / 'src' / name)} for name in PINNED},
        'link': {'classes': len(definitions), 'definitions': definitions},
        'bytecodeMarkers': ['applyScale', 'refreshBase', 'baseLeft', 'event-tracked-2'],
        'deployed': False,
        'command': command,
    }
    (OUT / 'build.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'swf': receipt['swf'], 'size': receipt['size'], 'classes': len(definitions),
                      'pinnedEqualWorking': [name for name, row in receipt['workingTreePinnedDiffs'].items()
                                             if row['equal']]}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
