"""Post-deploy smoke on the installed bytes (isolated app id, hidden window).

Boots root/pfe.swf with the real mods/loader-manifest.txt, waits for the
ContinuousScene heartbeat and every manifest entry's loader `ok_` marker, and
fails if any uncaught `Error #` reaches stderr. Storage is isolated by app id, so
the player's own store is never touched; the process is killed afterwards.
"""
from pathlib import Path
import json, os, subprocess, sys, time

HERE = Path(__file__).resolve().parent
MOD = HERE.parents[2]
ROOT = MOD.parents[1]
sys.path.insert(0, str(ROOT / 'mods/ModLoader/tools'))
from test_registry import Registration

EVIDENCE = MOD / 'knowledge/experiments/evidence'
TIMEOUT = 240


def manifest_entries():
    entries = []
    for line in (ROOT / 'mods/loader-manifest.txt').read_text(encoding='utf-8-sig').splitlines():
        fields = line.split('|')
        if len(fields) == 5 and not line.startswith('#') and fields[2] == '1':
            entries.append(fields[1])
    return entries


def main():
    stamp = time.strftime('%Y%m%d%H%M%S')
    app_id = 'pfe-bulletgrid-smoke-' + stamp
    evidence = EVIDENCE / ('installed-smoke-' + app_id)
    if evidence.exists():
        raise SystemExit('evidence exists')
    evidence.mkdir(parents=True)
    descriptor = HERE / 'installed-smoke.xml'
    descriptor.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<application xmlns="http://ns.adobe.com/air/application/30.0"><id>' + app_id + '</id>'
        '<versionNumber>1.0</versionNumber><filename>BulletGridSmoke</filename>'
        '<initialWindow><content>pfe.swf</content><visible>false</visible>'
        '<width>1280</width><height>800</height><renderMode>direct</renderMode></initialWindow>'
        '<supportedProfiles>extendedDesktop</supportedProfiles></application>\n', encoding='utf-8')
    entries = manifest_entries()
    with Registration(owner='ContinuousScene / bullet grid deploy smoke', purpose='installed smoke',
                      resource='game', run_dir=ROOT, evidence=evidence, wait=900) as lease:
        if subprocess.run(['tasklist', '/FI', 'IMAGENAME eq adl64.exe'], capture_output=True, text=True).stdout.count('adl64.exe') > 0:
            raise RuntimeError('Existing AIR; untouched')
        lease.before_launch('installed pfe.swf, isolated app id')
        with (evidence / 'stdout.log').open('wb') as out, (evidence / 'stderr.log').open('wb') as err:
            proc = subprocess.Popen([str(ROOT / 'adl64.exe'), '-runtime', str(ROOT / 'runtimes/air/win64'),
                                     str(descriptor), str(ROOT)], cwd=str(ROOT),
                                    stdout=out, stderr=err, creationflags=subprocess.CREATE_NO_WINDOW)
            lease.child(proc.pid)
            store = Path(os.environ['APPDATA']) / app_id / 'Local Store'
            loader_sol = store / '#SharedObjects' / 'ModLoader.sol'
            checks = []
            try:
                deadline = time.time() + TIMEOUT
                ready = False
                while time.time() < deadline and proc.poll() is None:
                    if (store / 'ContinuousScene.log').exists() and loader_sol.exists():
                        text = (store / 'ContinuousScene.log').read_text(encoding='utf-8', errors='replace')
                        sol = loader_sol.read_bytes().decode('utf-8', 'replace')
                        if 'heartbeat' in text and all(('ok_' + name) in sol for name in entries):
                            ready = True
                            break
                    time.sleep(1)
                checks.append({'name': 'startup-heartbeat-and-loader-ok', 'passed': ready})
                sol = loader_sol.read_bytes().decode('utf-8', 'replace') if loader_sol.exists() else ''
                scene = (store / 'ContinuousScene.log').read_text(encoding='utf-8', errors='replace') if (store / 'ContinuousScene.log').exists() else ''
                version_line = next((line for line in scene.splitlines() if 'loaded' in line), '')
                checks.append({'name': 'no-loader-errors', 'passed': 'err_' not in sol})
                checks.append({'name': 'scene-loaded-and-heartbeat',
                               'passed': 'loaded' in version_line and 'heartbeat' in scene and 'ERROR' not in scene,
                               'detail': version_line})
                checks.append({'name': 'process-alive', 'passed': proc.poll() is None})
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait(15)
                lease.child_stopped()
            stdout = (evidence / 'stdout.log').read_text(encoding='utf-8', errors='replace')
            stderr = (evidence / 'stderr.log').read_text(encoding='utf-8', errors='replace')
            bad = [line for line in (stdout + '\n' + stderr).splitlines()
                   if 'Error #' in line and not line.startswith('   at ')]
            checks.append({'name': 'no-uncaught-error', 'passed': not bad})
            result = {'passed': all(c['passed'] for c in checks), 'appId': app_id,
                      'hostSha256': __import__('hashlib').sha256((ROOT / 'pfe.swf').read_bytes()).hexdigest().upper(),
                      'checks': checks, 'errorLines': bad[:10], 'manifestEntries': entries,
                      'scope': 'installed bytes boot + loader status; gameplay coverage is the isolated '
                               '1300-sample combat arms that ran on these same host bytes'}
            (evidence / 'InstalledSmoke.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
            lease.outcome = 'passed' if result['passed'] else 'failed'
            lease.note = 'installed smoke on the deployed host'
            print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
