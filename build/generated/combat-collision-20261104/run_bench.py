"""Run the offline bullet-grid bench under a registered lease.

Isolated AIR app (own id `remains.bench.bulletgrid`), invisible window, no game
files, no mods, no network. Output is captured to stdout.txt and the bench also
writes bullet-grid-result.txt next to the descriptor.
"""
from pathlib import Path
import json, subprocess, sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
sys.path.insert(0, str(ROOT / 'mods/ModLoader/tools'))
from test_registry import Registration

ADL = ROOT / 'adl64.exe'
RUNTIME = ROOT / 'runtimes/air/win64'
SWF = HERE / 'BulletGridBench.swf'
RESULT = HERE / 'bullet-grid-result.txt'


def main():
    if RESULT.exists():
        RESULT.unlink()
    with Registration(owner='ContinuousScene / bullet grid bench', purpose='offline bench',
                      resource='offline', run_dir=HERE, evidence=HERE, wait=300) as lease:
        command = [str(ADL), '-runtime', str(RUNTIME), str(HERE / 'app.xml')]
        with (HERE / 'stdout.txt').open('wb') as out, (HERE / 'stderr.txt').open('wb') as err:
            proc = subprocess.Popen(command, cwd=str(ROOT), stdout=out, stderr=err,
                                    creationflags=subprocess.CREATE_NO_WINDOW)
            lease.child(proc.pid)
            try:
                proc.wait(600)
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait(15)
                lease.child_stopped()
        receipt = {'command': command, 'returncode': proc.returncode,
                   'swf': (HERE / 'BulletGridBench.swf').stat().st_size}
        if RESULT.exists():
            receipt['result'] = RESULT.read_text(encoding='utf-8').splitlines()
            lease.outcome = 'passed'
            lease.note = 'offline bench completed'
        else:
            receipt['stdout'] = (HERE / 'stdout.txt').read_text(encoding='utf-8', errors='replace')[-2000:]
            lease.outcome = 'failed'
            lease.note = 'bench produced no result file'
        (HERE / 'bench.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
        print(json.dumps({'returncode': proc.returncode, 'result': receipt.get('result')}, indent=2))


if __name__ == '__main__':
    main()
