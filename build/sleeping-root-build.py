"""Prepare a diagnostic-only sleeping-root callback from frozen CS 7F1F.

The default action only prepares source; --compile-only compiles that reviewed
snapshot under an offline registration. It never starts AIR or deploys. It copies
only the six manifest-verified production classes from the earlier retained
original-source closure. The probe helper is frozen separately, not linked into
the production module. Every insertion is removable byte for byte.
"""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys
from xml.sax.saxutils import escape

sys.dont_write_bytecode = True

B = Path(__file__).resolve().parent
MOD, ROOT = B.parent, B.parent.parent.parent
FROZEN = B / 'generated/activity-telemetry-20261022/original-source'
DEFAULT_OUT = B / 'generated/sleeping-root-20261022'
BASE_SHA = '7F1F2961C6E299D949423591F3C65C610C2EAEFA7FC72E8A583A402770D6B51F'
HOST_SHA = 'BEFCF0509E11FAC9FEF7AFB834708B8B93752A14AE3D5CD72B42AA6D42F9B82A'
MANIFEST_SHA = '832319A1E57B5EEFEAB25818DDB07F726D6FA0A46B8CFDDF68DFC8927F426A95'
RECEIPT_SHA = '592E788BAD01D49DC58A6EBA570EEF7F4032B32D208084581B6849552141EAB8'
FILES = ('ContinuousSceneDoc.as', 'ContinuousSceneMod.as', 'NativeSceneAdapter.as',
         'NativeSceneActivity.as', 'NativeSceneWalls.as', 'SingleSceneDocument.as')


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest().upper()


def sha(path):
    return sha_bytes(path.read_bytes())


def prepare(output):
    assert output.resolve().is_relative_to((B / 'generated').resolve()), 'Output must remain under build/generated'
    assert not output.exists(), 'Use a new output directory; existing evidence is never overwritten'
    assert sha(B / 'large-map/ContinuousSceneMod.swf') == sha(MOD / 'release/ContinuousSceneMod.swf') == BASE_SHA
    assert sha(ROOT / 'pfe.swf') == HOST_SHA
    manifest_path, receipt_path = B / 'large-map/source-manifest.json', MOD / 'state/deployment-v090.json'
    assert sha(manifest_path) == MANIFEST_SHA and sha(receipt_path) == RECEIPT_SHA
    manifest = json.loads(manifest_path.read_text('utf-8-sig'))
    receipt = json.loads(receipt_path.read_text('utf-8-sig'))
    assert receipt['status'] == 'verified'
    assert receipt['after']['mods/ContinuousScene/release/ContinuousSceneMod.swf'] == BASE_SHA
    original = {}
    for name in FILES:
        data = (FROZEN / name).read_bytes()
        key = 'mods\\ContinuousScene\\src\\' + name
        assert sha_bytes(data) == manifest[key], ('Frozen source differs from production manifest', name)
        original[name] = data
    helper = MOD / 'src/tests/SceneSleepingRootPresentation.as'
    helper_bytes = helper.read_bytes()
    after, edits = dict(original), {}

    def edit(name, replacements):
        before = original[name].decode('utf-8')
        source = before
        for old, new in replacements:
            assert source.count(old) == 1, (name, old[:90], source.count(old))
            source = source.replace(old, new, 1)
        reverse = source
        for old, new in reversed(replacements):
            assert reverse.count(new) == 1
            reverse = reverse.replace(new, old, 1)
        assert reverse.encode('utf-8') == original[name], ('Reverse insertion failed', name)
        after[name] = source.encode('utf-8')
        edits[name] = [dict(before=old, after=new) for old, new in replacements]

    entry = '        public static function update(loc:*):Object {'
    gate = '''        // Isolated diagnostic callback only; null keeps the original scheduler.
        public static var presentationGate:Function;
        public static function setPresentationGate(value:Function,expected:Function):Boolean {
            if(presentationGate!==expected)return false;
            presentationGate=value;return true;
        }
'''
    active = 'if(active) {resume(r);delete s.sleeping[u];++s.awake;}'
    sleeping = 's.sleeping[u]=true;u.onCursor=0;++s.asleep;'
    wake = 'if(r){r.engaged=true;resume(r);}'
    edit('NativeSceneActivity.as', [
        (entry, gate + entry),
        (active, 'if(active) {if(presentationGate!=null)presentationGate(u,false,r.clips.length);resume(r);delete s.sleeping[u];++s.awake;}'),
        (sleeping, 's.sleeping[u]=true;if(presentationGate!=null)presentationGate(u,true,r.clips.length);u.onCursor=0;++s.asleep;'),
        (wake, 'if(r){r.engaged=true;if(presentationGate!=null)presentationGate(u,false,r.clips.length);resume(r);}')])
    api = 'wake:NativeSceneActivity.wake,activityStats:NativeSceneActivity.stats};'
    edit('ContinuousSceneMod.as', [(api,
        'wake:NativeSceneActivity.wake,activityStats:NativeSceneActivity.stats,\n'
        '                setActivityPresentationGate:NativeSceneActivity.setPresentationGate};')])
    assert {name for name in FILES if after[name] != original[name]} == {'ContinuousSceneMod.as', 'NativeSceneActivity.as'}
    output.mkdir(parents=True, exist_ok=False)
    for directory, values in (('original-source', original), ('source', after)):
        (output / directory).mkdir()
        for name, data in values.items():
            (output / directory / name).write_bytes(data)
    (output / 'probe-helper').mkdir()
    (output / 'probe-helper/SceneSleepingRootPresentation.as').write_bytes(helper_bytes)
    assert sha(helper) == sha_bytes(helper_bytes), 'Probe helper changed during freeze'
    data = dict(version='sleeping-root-source-1', diagnosticOnly=True, performanceAcceptance=False,
        compiled=False, deployed=False, baseline=BASE_SHA, host=HOST_SHA,
        productionReceiptSHA256=RECEIPT_SHA, productionSourceManifestSHA256=MANIFEST_SHA,
        frozenProductionSourcePath=str(FROZEN), builderSHA256=sha(Path(__file__)), sourceClosure=list(FILES),
        before={n: sha_bytes(original[n]) for n in FILES}, after={n: sha_bytes(after[n]) for n in FILES},
        probeHelperSHA256=sha_bytes(helper_bytes), changed=sorted(edits), edits=edits,
        reverseInsertionCheck=True, api='setActivityPresentationGate(value, expected):Boolean',
        callback='gate(unit, sleeping, nativeClipsLength); active/wake restore before resume, including empty clips',
        algorithm='Active expression, threat bounds, 45-frame grace, engaged latch, freeze/resume bodies and sleep dictionary decisions are unchanged',
        limitations=['Only a source-prepared diagnostic; no timing or visual evidence yet.',
            'Only frozen production classes are compiled into the candidate; source-only alicorn and test/WIP classes are excluded.',
            'The separately frozen probe helper targets exact UnitRaider only, never native addVisual/remVisual.',
            'First integration is an end-of-run diagnostic; strict same-frame pixels and timing remain separate future checks.'])
    (output / 'source-provenance.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), 'utf-8')
    print(json.dumps(dict(output=str(output), before=data['before'], after=data['after'],
        reverseInsertionCheck=True, compiled=False, deployed=False), ensure_ascii=False), flush=True)


def compile_only(output):
    """Compile the retained candidate and helper independently; never load them."""
    assert output.resolve().is_relative_to((B / 'generated').resolve())
    provenance_path = output / 'source-provenance.json'
    proof = json.loads(provenance_path.read_text('utf-8-sig'))
    assert proof['version'] == 'sleeping-root-source-1' and proof['reverseInsertionCheck']
    assert proof['builderSHA256'] == sha(Path(__file__))
    assert proof['baseline'] == BASE_SHA and proof['host'] == HOST_SHA
    assert proof['sourceClosure'] == list(FILES)
    assert sha(ROOT / 'pfe.swf') == HOST_SHA and sha(MOD / 'release/ContinuousSceneMod.swf') == BASE_SHA
    for name in FILES:
        assert sha(output / 'original-source' / name) == proof['before'][name]
        assert sha(output / 'source' / name) == proof['after'][name]
    assert {p.name for p in (output / 'source').glob('*.as')} == set(FILES)
    helper = output / 'probe-helper/SceneSleepingRootPresentation.as'
    assert sha(helper) == proof['probeHelperSHA256']
    assert not (output / 'build.json').exists(), 'Do not overwrite a prior compiled receipt'
    java = Path('D:/Program Files/Adobe Animate 2024/jre/bin/java.exe')
    tools = ROOT / 'mods/Sandevistan/build/tools'
    jar, air = tools / 'flexsdk/lib/mxmlc.jar', tools / 'airsdk/frameworks/libs/air/airglobal.swc'
    compiler = {str(p): sha(p) for p in (java, jar, air)}
    probe_source = output / 'helper-compile-source'
    probe_source.mkdir(exist_ok=False)
    (probe_source / 'tests').mkdir()
    (probe_source / 'tests/SceneSleepingRootPresentation.as').write_bytes(helper.read_bytes())
    (probe_source / 'SleepingRootHelperDoc.as').write_text('''package {
    import flash.display.Sprite;
    import tests.SceneSleepingRootPresentation;
    public class SleepingRootHelperDoc extends Sprite {
        public var retainedClass:Class=SceneSleepingRootPresentation;
    }
}
''', 'utf-8')
    sys.path.insert(0, str(ROOT / 'mods/ModLoader/tools'))
    from test_registry import Registration
    builds = []
    with Registration(owner='ContinuousScene / sleeping-root diagnostic compile / 01a13816',
            purpose='Compile frozen 7F1F callback candidate and standalone probe helper; no AIR',
            run_dir=output, evidence=output / 'build.json', resource='offline', wait=300) as lease:
        for label, source, entry in (('ContinuousSceneMod', output / 'source', 'ContinuousSceneDoc.as'),
                                     ('SleepingRootHelper', probe_source, 'SleepingRootHelperDoc.as')):
            target, config = output / (label + '.swf'), output / (label + '.xml')
            assert not target.exists() and not config.exists(), 'Use a fresh compile directory'
            config.write_text('''<flex-config><target-player>32.0</target-player><compiler>
<external-library-path><path-element>{air}</path-element></external-library-path>
<source-path><path-element>{source}</path-element></source-path><debug>false</debug><optimize>true</optimize><theme/>
</compiler></flex-config>'''.format(air=escape(str(air)), source=escape(str(source))), 'utf-8')
            command = [str(java), '-Xmx512m', '-Dfile.encoding=UTF-8', '-jar', str(jar),
                '+flexlib=' + str(tools / 'flexsdk/frameworks'), '-load-config=' + str(config),
                '-swf-version=32', '-static-link-runtime-shared-libraries=true', '-output=' + str(target), str(source / entry)]
            process = None
            lease.before_launch(label + ' offline compiler')
            try:
                process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                lease.child(process.pid)
                log, _ = process.communicate()
                (output / (label + '-compile.log')).write_bytes(log)
                if process.returncode:
                    raise RuntimeError(label + ' compile failed; inspect retained compile log')
            finally:
                if process is not None:
                    if process.poll() is None:
                        process.kill();process.wait(timeout=15)
                    lease.child_stopped()
            builds.append(dict(name=label, output=str(target), sha256=sha(target), command=command,
                configSHA256=sha(config), compilerLogSHA256=sha(output / (label + '-compile.log'))))
        assert compiler == {str(p): sha(p) for p in (java, jar, air)}
        assert sha(ROOT / 'pfe.swf') == HOST_SHA and sha(MOD / 'release/ContinuousSceneMod.swf') == BASE_SHA
        assert all(sha(output / 'source' / n) == proof['after'][n] for n in FILES)
        assert sha(helper) == sha(probe_source / 'tests/SceneSleepingRootPresentation.as') == proof['probeHelperSHA256']
        record = dict(version='sleeping-root-build-1', diagnosticOnly=True, performanceAcceptance=False,
            deployed=False, airRun=False, sourceProvenanceSHA256=sha(provenance_path),
            baseline=BASE_SHA, host=HOST_SHA, compilerInputs=compiler, builds=builds,
            candidateSHA256=builds[0]['sha256'], helperSHA256=builds[1]['sha256'])
        (output / 'build.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), 'utf-8')
        lease.outcome='passed';lease.note='Frozen candidate and helper compile only; no runtime, pixels or performance acceptance'
        print(json.dumps(record, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    if not __debug__:
        raise RuntimeError('Assertions are required; do not use -O')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUT)
    parser.add_argument('--compile-only', action='store_true')
    args = parser.parse_args()
    (compile_only if args.compile_only else prepare)(args.output.resolve())
