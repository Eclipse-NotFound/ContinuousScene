"""Attribution audit: which classes differ between the pinned product candidate
and the HEAD-only control build, and whether the deployed release is reachable
from HEAD sources with this compiler at all."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
MOD = Path(__file__).resolve().parents[1]
ROOT = MOD.parents[1]
SDK = ROOT / 'mods/Sandevistan/build/tools'
JAVA = Path('D:/Program Files/Adobe Animate 2024/jre/bin/java.exe')
FFDEC = SDK / 'ffdec/ffdec-cli.jar'
BASE = MOD / 'build/generated/cull-scale-20261104'
CANDIDATE = BASE / 'product/ContinuousSceneMod.swf'
CONTROL = BASE / 'product-control/ContinuousSceneMod.swf'
RELEASE = MOD / 'release/ContinuousSceneMod.swf'
AIMV2 = MOD / 'build/generated/aimv2-20261104/product/ContinuousSceneMod.swf'
CLASSES = ['SceneObjectCulling', 'SceneCullEntry', 'ContinuousSceneMod', 'SceneAimController',
           'NativeSceneActivity', 'ScenePresentationCoordinator', 'SingleSceneDocument']

sys.path.insert(0, str(MOD / 'build'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def export(swf, tag, classes):
    out = BASE / 'audit' / tag
    if out.exists():
        shutil.rmtree(out)
    subprocess.run([str(JAVA), '-Xmx512m', '-jar', str(FFDEC), '-selectclass', ','.join(classes),
                    '-export', 'script', str(out), str(swf)], check=True, capture_output=True,
                   creationflags=subprocess.CREATE_NO_WINDOW)
    found = {}
    for path in out.rglob('*.as'):
        found[path.stem] = hashlib.sha256(path.read_bytes()).hexdigest().upper()
    return found


def main():
    hashes = {name: sha(path) for name, path in
              (('release', RELEASE), ('aimv2Product', AIMV2), ('candidate', CANDIDATE), ('control', CONTROL))
              if path.exists()}
    a = export(CONTROL, 'control', CLASSES)
    b = export(CANDIDATE, 'candidate', CLASSES)
    c = export(RELEASE, 'release', CLASSES)
    differences = sorted(name for name in CLASSES if a.get(name) != b.get(name))
    same = sorted(name for name in CLASSES if a.get(name) == b.get(name))
    pipelineFidelity = sorted(name for name in CLASSES if a.get(name) != c.get(name))
    receipt = {
        'hashes': hashes,
        'releaseEqualsAimv2Product': hashes.get('release') == hashes.get('aimv2Product'),
        'controlDiffersFromRelease': hashes.get('control') != hashes.get('release'),
        'controlSize': CONTROL.stat().st_size,
        'releaseSize': RELEASE.stat().st_size,
        'classesThatDiffer': differences,
        'classesIdentical': same,
        'classesWhereLocalPipelineDiffersFromRelease': pipelineFidelity,
        'expectedDiffering': ['SceneCullEntry', 'SceneObjectCulling'],
        'attributionClean': differences == ['SceneCullEntry', 'SceneObjectCulling'] and not pipelineFidelity,
    }
    (BASE / 'attribution.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(receipt, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
