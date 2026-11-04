"""Reconcile this session's crashed installed-smoke lease.

Checks first: no adl64 process may remain (the recorded runner/children must be
gone), then marks the record interrupted with the checked directory + note.
"""
from pathlib import Path
import subprocess, sys

HERE = Path(__file__).resolve().parent
MOD = HERE.parents[2]
ROOT = MOD.parents[1]
sys.path.insert(0, str(ROOT / 'mods/ModLoader/tools'))
from test_registry import Registry

IDENT = 'ccf5d4f08f3b4ad497cf0206fd0a8d0a'   # ContinuousScene / bullet grid deploy smoke
CHECKED = str(HERE)


def main():
    listing = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq adl64.exe'], capture_output=True, text=True,
                             encoding='utf-8', errors='replace').stdout
    assert 'adl64.exe' not in listing, 'AIR still running; do not reconcile'
    registry = Registry()
    registry.recover(IDENT, 'crash in the smoke script before launch; evidence dir created but no AIR '
                            'was started and no files were copied', CHECKED)


if __name__ == '__main__':
    main()
