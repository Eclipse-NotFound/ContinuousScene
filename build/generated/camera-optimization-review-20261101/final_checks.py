"""Final input/provenance checks; no runtime or player process changes."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
REPO = ROOT/'mods/ContinuousScene'
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT/'mods/ModLoader/tools'))
from test_registry import Registry, ACTIVE


def git(*args, data=None):
    return subprocess.run(['git', '-C', str(REPO), *args], input=data,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          check=True).stdout


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


summary = json.loads((HERE/'summary.json').read_text('utf-8'))
archive = json.loads((HERE/'archive.json').read_text('utf-8'))
for rel, expected in archive['foreignFingerprints'].items():
    assert sha(REPO/rel) == expected, ('Foreign work changed', rel)
assert sha(ROOT/'pfe.swf') == summary['currentRootHostSHA256']
assert all(sha(ROOT/k) == v for k, v in summary['formalMods'].items())
records = Registry().status()
active = [r for r in records if r['state'] in ACTIVE and '01a13816' in r['owner']]
assert not active, ('Owned registry entries still active', active)

# Correct only our new note, retaining all pre-existing unstaged author edits.
rel = 'state/MEMORY.md'
path = REPO/rel
old, new = '和其余14模组组合保持'.encode(), '等14模组组合保持'.encode()
raw = path.read_bytes()
if old in raw:
    assert raw.count(old) == 1
    path.write_bytes(raw.replace(old, new, 1))
staged = git('show', ':'+rel)
if old in staged:
    assert staged.count(old) == 1
    blob = git('hash-object', '-w', '--stdin', data=staged.replace(old, new, 1)).decode().strip()
    git('update-index', '--cacheinfo', '100644,'+blob+','+rel)

paths = git('diff', '--cached', '--name-only').decode().splitlines()
generated = [p for p in paths if p.startswith('build/generated/')]
git('add', '-f', '--', '.gitattributes', *generated,
    (HERE/'final_checks.py').relative_to(REPO).as_posix())
git('add', '--renormalize', '--', *generated)
checked = 0
for rel in generated:
    assert git('show', ':'+rel) == (REPO/rel).read_bytes(), ('Frozen bytes differ in index', rel)
    if rel.endswith('/build.json'):
        receipt = json.loads((REPO/rel).read_text('utf-8'))
        for source, expected in receipt.get('sources', {}).items():
            assert sha((REPO/rel).parent/source) == expected, ('Build input changed', rel, source)
            checked += 1
git('diff', '--cached', '--check')
result = dict(rootHostSHA256=sha(ROOT/'pfe.swf'), formalModCount=len(summary['formalMods']),
              formalModsUnchanged=True, ownActiveRegistryEntries=0, preservedForeignFiles=len(archive['foreignFingerprints']),
              verifiedBuildSources=checked, frozenStagedFiles=len(generated),
              frozenStagedBytesExact=True, whitespaceCheckPassed=True,
              declaredWhitespaceExceptions='Only frozen donor/pcode/phase source and failed compiler log',
              diagnosticIntervals=summary['totalIntervals'], performanceTargetAchieved=False)
(HERE/'final-checks.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), 'utf-8')
git('add', '-f', '--', (HERE/'final-checks.json').relative_to(REPO).as_posix())
print(json.dumps(result, ensure_ascii=False))
