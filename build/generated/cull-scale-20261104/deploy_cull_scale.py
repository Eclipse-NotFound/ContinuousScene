"""Deploy the verified culling-scale candidate (ContinuousScene 0.9.9 + event-tracked-2).

Double gate, by design: the candidate must be the audited bytes and the formal
release must still be the deployed 0.9.9 build. A parallel DSH session is
implementing aim-v3 in the same mod; if it has already replaced the release,
this script refuses instead of overwriting its product. Host SWF and scene.xml
are not touched, and their hashes are recorded for the receipt.
"""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import time

sys.dont_write_bytecode = True
MOD = Path(__file__).resolve().parents[3]     # mods/ContinuousScene
ROOT = MOD.parents[1]
RELEASE = MOD / 'release/ContinuousSceneMod.swf'
CANDIDATE = Path(__file__).resolve().parent / 'product/ContinuousSceneMod.swf'
EXPECT_CANDIDATE = '6A538E83CF4BA778BC2899B1D30B4C345FAE776C5540CADDC6B7254002BE425C'
EXPECT_CURRENT = 'D04CD26AA674238BBB2F43A2CA49C57811301E9B9B614352A099F8190D9E0193'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def main():
    current = sha(RELEASE)
    candidate = sha(CANDIDATE)
    if current != EXPECT_CURRENT:
        sys.exit('release is ' + current + ' (not the deployed 0.9.9 build); '
                 'another session may have deployed - refusing to overwrite')
    if candidate != EXPECT_CANDIDATE:
        sys.exit('candidate is ' + candidate + ' (not the audited build); refusing to deploy')
    out = subprocess.run(['powershell', '-NoProfile', '-Command',
                          'Get-Process -Name adl64,adl -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id'],
                         capture_output=True, text=True)
    air_ids = [int(x) for x in out.stdout.split() if x.strip().isdigit()]
    stamp = time.strftime('%Y%m%d-%H%M%S')
    backup = MOD / 'build/backups' / ('ContinuousSceneMod-0.9.9-D04CD26A-before-cullscale-' + stamp + '.swf')
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(RELEASE, backup)
    temp = RELEASE.with_suffix('.candidate')
    shutil.copy2(CANDIDATE, temp)
    temp.replace(RELEASE)
    readback = sha(RELEASE)
    if readback != EXPECT_CANDIDATE:
        shutil.copy2(backup, RELEASE)
        sys.exit('readback mismatch; rolled back')
    receipt = {
        'deployedAt': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
        'product': 'ContinuousSceneMod 0.9.9 + SceneObjectCulling event-tracked-2 (analytic scale box)',
        'candidateTag': 'cull-scale-20261104',
        'candidateSource': 'build/generated/cull-scale-20261104/product',
        'previousSha256': current,
        'deployedSha256': readback,
        'expectedSha256': EXPECT_CANDIDATE,
        'backup': str(backup.relative_to(MOD)),
        'hostUnchanged': sha(ROOT / 'pfe.swf'),
        'sceneXml': sha(MOD / 'release/scene.xml'),
        'airRunningAtDeploy': air_ids,
        'restartRequired': True,
        'deterministicChecks': 'SceneCullingChecks 23/23 + SceneCullingScaleChecks 22/22 (standalone AIR)',
        'performanceClaim': 'none: getBounds count reduced, frame time not paired',
        'rollback': 'copy ' + backup.name + ' over release/ContinuousSceneMod.swf, restart game',
    }
    target = MOD / 'state' / ('culling-scale-deployment-' + time.strftime('%Y%m%d') + '.json')
    target.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(receipt, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
