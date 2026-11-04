"""Run the bullet-grid arms in order, each under its own `game` lease.

arm = (label, host directory). The label keeps every run's evidence directory
unique. This wrapper waits for a genuinely quiet window (no rival game lease and
no AIR process) before handing off to run_phase2.py, which still owns the lease,
the memory gates and the isolated storage; it never touches another session's
processes.
"""
from pathlib import Path
import json, os, subprocess, sys, time

HERE = Path(__file__).resolve().parent
MOD = HERE.parents[2]
ROOT = MOD.parents[1]
RUNNER = MOD / 'build/generated/phase-20261104/run_phase2.py'
OPTS = MOD / 'build/generated/opt-20261104'
REGISTRY = ROOT / 'shared-knowledge/knowledge-validation/coordination/test-runs.sqlite3'
ARMS = [
    ('base-r1', OPTS / 'decal-nocancel-v2'),
    ('grid-r1', HERE / 'grid-diag'),
    ('base-r2', OPTS / 'decal-nocancel-v2'),
    ('clean-r1', HERE / 'grid-clean'),
]
BUDGET_S = int(os.environ.get('ARMS_BUDGET_S', '3600'))


def rival_leases():
    """Running `game` leases owned by someone else (read-only view)."""
    import sqlite3
    connection = sqlite3.connect('file:' + str(REGISTRY) + '?mode=ro', uri=True)
    rows = [json.loads(r[0]) for r in connection.execute('select payload from runs order by rowid desc limit 80')]
    connection.close()
    mine = 'ContinuousScene'
    return [r for r in rows if r.get('resource') == 'game' and r.get('state') == 'running'
            and mine not in (r.get('owner') or '')]


def air_running():
    result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq adl64.exe'], capture_output=True, text=True,
                            encoding='utf-8', errors='replace')
    return 'adl64.exe' in (result.stdout or '')


def wait_quiet(deadline, arm):
    while time.time() < deadline:
        rivals = rival_leases()
        if not rivals and not air_running():
            return True
        who = ', '.join(sorted({(r.get('owner') or '?') + '/' + (r.get('purpose') or '?') for r in rivals})) or 'air'
        print('%s waiting for a quiet window (%s)' % (time.strftime('%H:%M:%S'), who), flush=True)
        time.sleep(45)
    return False


def run_arm(label, host, deadline):
    for attempt in range(1, 7):
        if time.time() >= deadline:
            return {'label': label, 'aborted': 'budget exhausted'}
        if not wait_quiet(deadline, label):
            return {'label': label, 'aborted': 'no quiet window'}
        env = dict(os.environ)
        env.update(PHASE_HOST_DIR=str(host), PHASE_PROBE='probe-v6', PHASE_LABEL='bulletgrid-' + label)
        print('%s %s attempt %d -> %s' % (time.strftime('%H:%M:%S'), label, attempt, host.name), flush=True)
        proc = subprocess.run([sys.executable, str(RUNNER), 'combat', '3'], cwd=str(MOD), env=env,
                              capture_output=True, text=True, encoding='utf-8', errors='replace')
        lines = ((proc.stdout or '') + (proc.stderr or '')).strip().splitlines()
        tail = lines[-6:]
        print(json.dumps({'label': label, 'returncode': proc.returncode, 'tail': tail}, ensure_ascii=False),
              flush=True)
        if proc.returncode == 0:
            return {'label': label, 'host': host.name, 'returncode': 0, 'tail': tail}
        if 'no other AIR' in ' '.join(tail) or 'Existing AIR' in ' '.join(tail) or 'Other AIR' in ' '.join(tail):
            time.sleep(60)
            continue
        return {'label': label, 'host': host.name, 'returncode': proc.returncode, 'tail': tail}
    return {'label': label, 'aborted': 'attempts exhausted'}


def main(limit=None):
    deadline = time.time() + BUDGET_S
    arms = ARMS[:int(limit)] if limit else ARMS
    results = []
    for label, host in arms:
        results.append(run_arm(label, host, deadline))
        (HERE / 'arms.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
        if results[-1].get('returncode') != 0:
            break
    print(json.dumps({'arms': [r.get('label') for r in results]}))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else None)
