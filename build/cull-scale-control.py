"""Control build: every source at HEAD, i.e. the deployed 0.9.9 sources.

If this reproduces the deployed release hash, the candidate SWF differs from
the shipped product only by the two culling files, which pins attribution.
"""
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
OUT = MOD / 'build/generated/cull-scale-20261104/product-control'
DEPLOYED_099 = 'D04CD26AA674238BBB2F43A2CA49C57811301E9B9B614352A099F8190D9E0193'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    src = OUT / 'src'
    for path in (MOD / 'src').rglob('*.as'):
        rel = path.relative_to(MOD / 'src').as_posix()
        target = src / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        data = subprocess.run(['git', 'show', 'HEAD:src/' + rel], cwd=MOD, capture_output=True)
        if data.returncode != 0:
            # Uncommitted test harness (entry app for the deterministic suites is
            # never part of the product); the product entry does not link it.
            if rel.startswith('tests/'):
                continue
            sys.exit('git show failed for ' + rel)
        target.write_bytes(data.stdout)
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
               '-output=' + str(output), str(src / 'ContinuousSceneDoc.as')]
    with (OUT / 'compiler.log').open('w', encoding='utf-8') as log:
        log.write(' '.join(command) + '\n\n')
        log.flush()
        proc = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                              creationflags=subprocess.CREATE_NO_WINDOW)
    if proc.returncode != 0:
        sys.exit('control compile failed: see ' + str(OUT / 'compiler.log'))
    digest = sha(output)
    receipt = {'control': True, 'swf': digest, 'size': output.stat().st_size,
               'deployedRelease': DEPLOYED_099, 'matchesDeployed': digest == DEPLOYED_099,
               'command': command}
    (OUT / 'build.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({k: receipt[k] for k in ('swf', 'size', 'matchesDeployed')}, indent=2))


if __name__ == '__main__':
    main()
