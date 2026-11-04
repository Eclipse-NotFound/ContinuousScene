"""Mutation tests: prove the culling suites actually detect the bugs they claim.

Each mutation is applied to a scratch copy of the production sources, compiled
into its own AIR app and run. The suite MUST fail, and the expected assertion
must be the one that fails. Nothing under src/ is touched.
"""
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
import sys
import uuid

sys.dont_write_bytecode = True
MOD = Path(__file__).resolve().parents[1]
ROOT = MOD.parents[1]
SDK = ROOT / 'mods/Sandevistan/build/tools'
JAVA = Path('D:/Program Files/Adobe Animate 2024/jre/bin/java.exe')
BASE = MOD / 'build/generated/cull-scale-20261104/mutations'
FILES = ('SceneObjectCulling.as', 'SceneCullEntry.as', 'tests/SceneCullingChecks.as',
         'tests/SceneCullingScaleChecks.as', 'tests/CullingChecksApp.as')
ENTRY = 'tests/CullingChecksApp.as'
MUTATIONS = {
    # A mirror that scales the box but forgets to swap the edges.
    'no-edge-swap': {
        'file': 'SceneObjectCulling.as',
        'old': '            var l:Number=e.baseLeft*sx,r:Number=e.baseRight*sx;\n'
               '            e.left=l<r?l:r;e.right=l<r?r:l;\n'
               '            var t:Number=e.baseTop*sy,b:Number=e.baseBottom*sy;\n'
               '            e.top=t<b?t:b;e.bottom=t<b?b:t;',
        'new': '            e.left=e.baseLeft*sx;e.right=e.baseRight*sx;\n'
               '            e.top=e.baseTop*sy;e.bottom=e.baseBottom*sy;',
        'expect': ('mirror-matches-oracle', 'mixed-scene-oracle-agrees', 'transform-remeasured'),
    },
    # A refresh that updates the box but never re-decides this frame.
    'refresh-no-redecide': {
        'file': 'SceneObjectCulling.as',
        'old': '            storeMeasured(e,b,child.x,child.y,sx,sy,rot);\n            e.checked=false;',
        'new': '            storeMeasured(e,b,child.x,child.y,sx,sy,rot);',
        'expect': ('refresh-rededicates-same-frame', 'art-change-not-redecided'),
    },
    # A degenerate-axis guard that lets the base box divide by zero.
    'zero-axis-in-cache': {
        'file': 'SceneObjectCulling.as',
        'old': '            return rot==0 && sx!=0 && sy!=0 && Math.abs(sx)>=MIN_SCALE && Math.abs(sy)>=MIN_SCALE\n'
               '                && isFinite(sx) && isFinite(sy);',
        'new': '            return rot==0;',
        'expect': ('zero-axis-oracle-agrees', 'mixed-scene-oracle-agrees', 'refresh-rededicates-same-frame'),
    },
    # A guard that never fires, i.e. the layer transform assumption is trusted.
    'guard-removed': {
        'file': 'SceneObjectCulling.as',
        'old': '                if(layer.parent!==visual || m.b!=0 || m.c!=0 || m.tx!=0 || m.ty!=0 || m.a==0 || m.d==0)\n'
               '                    fastPath=false;',
        'new': '                if(!m)fastPath=false;',
        'expect': ('layer-guard-disables-fast-path',),
    },
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def run_case(tag, spec):
    out = BASE / tag
    if out.exists():
        shutil.rmtree(out)
    src = out / 'src'
    for name in FILES:
        target = src / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(MOD / 'src' / name, target)
    target = src / spec['file']
    text = target.read_text(encoding='utf-8')
    if text.count(spec['old']) != 1:
        sys.exit(tag + ': mutation anchor not unique (' + str(text.count(spec['old'])) + ')')
    target.write_text(text.replace(spec['old'], spec['new']), encoding='utf-8')
    config = out / 'compiler.xml'
    config.write_text(
        '<flex-config><target-player>32.0</target-player><compiler>'
        '<external-library-path><path-element>' + str(SDK / 'airsdk/frameworks/libs/air/airglobal.swc').replace('\\', '/') +
        '</path-element></external-library-path><source-path><path-element>' + src.as_posix() +
        '</path-element></source-path><debug>true</debug><optimize>true</optimize><theme/></compiler></flex-config>',
        encoding='utf-8')
    command = [str(JAVA), '-Xmx512m', '-Dfile.encoding=UTF-8', '-jar', str(SDK / 'flexsdk/lib/mxmlc.jar'),
               '+flexlib=' + str(SDK / 'flexsdk/frameworks'), '-load-config=' + str(config), '-swf-version=32',
               '-theme=', '-compiler.fonts.local-fonts-snapshot=',
               '-use-network=false', '-static-link-runtime-shared-libraries=true',
               '-output=' + str(out / 'checks.swf'), str(src / ENTRY)]
    compiled = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace',
                              creationflags=subprocess.CREATE_NO_WINDOW)
    if compiled.returncode != 0:
        return {'tag': tag, 'compiled': False, 'log': (compiled.stdout or '') + (compiled.stderr or '')}
    app_id = 'remains.cs.cullmut.' + uuid.uuid4().hex
    descriptor = out / 'app.xml'
    descriptor.write_text(
        '<application xmlns="http://ns.adobe.com/air/application/30.0"><id>' + app_id +
        '</id><versionNumber>1.0</versionNumber><filename>Mut</filename><initialWindow><content>'
        'checks.swf</content><visible>false</visible><renderMode>cpu</renderMode></initialWindow></application>',
        encoding='utf-8')
    run = subprocess.run([str(ROOT / 'adl64.exe'), '-runtime', str(ROOT / 'runtimes/air/win64'), str(descriptor)],
                         cwd=out, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180,
                         creationflags=subprocess.CREATE_NO_WINDOW)
    log = (run.stdout or '') + (run.stderr or '')
    (out / 'run.log').write_text(log, encoding='utf-8')
    storage = Path.home() / 'AppData/Roaming' / app_id / 'Local Store' / 'cs-culling-checks-result.json'
    payload = None
    if storage.exists():
        payload = json.loads(storage.read_text(encoding='utf-8'))
    detected = payload is not None and payload.get('ok') is False
    failed_names = []
    if payload:
        message = str(payload.get('error', ''))
        if message:
            match = re.search(r'(?:Culling|CullingScale): ([A-Za-z0-9-]+)', message)
            failed_names.append(match.group(1) if match else message[:120])
        failed_names += [row['name'] for row in payload.get('rows', []) if not row.get('ok')]
    expected_hit = any(name in str((payload or {}).get('error', '')) for name in spec['expect'])
    return {'tag': tag, 'compiled': True, 'detected': detected, 'expectedAssertionHit': expected_hit,
            'failedAssertions': failed_names[:6], 'exitCode': run.returncode}


def main():
    results = []
    for tag, spec in MUTATIONS.items():
        results.append(run_case(tag, spec))
    clean = json.loads((MOD / 'build/generated/cull-scale-20261104/checks/checks.json').read_text(encoding='utf-8'))
    summary = {'baselineSuitePasses': bool(clean['result'] and clean['result']['ok']), 'mutations': results,
               'allMutationsDetected': all(r.get('detected') for r in results),
               'allExpectedAssertionsFired': all(r.get('expectedAssertionHit') for r in results)}
    (BASE / 'mutations.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if not (summary['allMutationsDetected'] and summary['allExpectedAssertionsFired']):
        sys.exit(1)


if __name__ == '__main__':
    main()
