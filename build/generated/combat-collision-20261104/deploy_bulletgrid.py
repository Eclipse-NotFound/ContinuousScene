"""Install a verified bullet-collision host candidate over the production pfe.swf.

Gate: the candidate is method-only (`fe.graph.Grafon::sceneTick` and
`fe.weapon.Bullet::run`, class layout unchanged), its bucket lookup was shown
equivalent to the native loop offline, and an isolated in-game arm ran the formal
13-mod set with all checks green. Backup, atomic replace, read-back and receipt
follow GOVERNANCE §6.

Usage: python deploy_bulletgrid.py <tag> <expectedCurrentSha256> [receiptName]
"""
from pathlib import Path
import hashlib, json, shutil, sys, time

HERE = Path(__file__).resolve().parent
MOD = HERE.parents[2]
ROOT = MOD.parents[1]
TARGET = ROOT / 'pfe.swf'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def main(tag, expect_current, receipt_name=None):
    candidate = HERE / tag / 'candidate.swf'
    receipt = json.loads((HERE / tag / 'build.json').read_text(encoding='utf-8'))
    assert receipt['compiled'] and not receipt['deployed'], 'candidate receipt not installable'
    assert sha(candidate) == receipt['output'], 'candidate bytes changed'
    assert receipt['classesUnchanged'] and set(receipt['changedMethods']) == {
        'fe.graph.Grafon::0:1:sceneTick', 'fe.weapon.Bullet::0:1:run'}, receipt['changedMethods']
    current = sha(TARGET)
    assert current == expect_current.upper(), 'production host is not the expected baseline: ' + current
    out = HERE / (receipt_name or ('deploy-receipt-' + tag + '.json'))
    if out.exists():
        raise SystemExit('receipt exists; already deployed')
    stamp = time.strftime('%Y%m%d-%H%M%S')
    backups = MOD / 'build/backups'
    backups.mkdir(parents=True, exist_ok=True)
    backup = backups / ('pfe_before_' + tag + '_' + stamp + '.swf')
    shutil.copy2(TARGET, backup)
    assert sha(backup) == current
    temporary = ROOT / ('pfe.' + tag + '.tmp')
    shutil.copy2(candidate, temporary)
    assert sha(temporary) == receipt['output']
    temporary.replace(TARGET)
    installed = sha(TARGET)
    assert installed == receipt['output'], 'install read-back mismatch: ' + installed
    record = {
        'deployedAt': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
        'product': 'host pfe.swf: Grafon.sceneTick bullet bucket table + Bullet.run bucket query '
                   '(sceneCU/#1069 channel removed); CS release and scene.xml untouched',
        'previousSha256': current,
        'deployedSha256': installed,
        'backup': str(backup.relative_to(ROOT)),
        'candidateTag': tag,
        'changedMethods': receipt['changedMethods'],
        'classesUnchanged': True,
        'parameters': {'cell': receipt.get('cell'), 'margin': receipt.get('margin')},
        'expectedEffect': receipt.get('expectedEffect', ''),
        'restartRequired': True,
        'rollback': 'copy ' + str(backup.relative_to(ROOT)) + ' over pfe.swf and restart the game',
    }
    out.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding='utf-8')
    receipt['deployed'] = True
    (HERE / tag / 'build.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps(record, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
