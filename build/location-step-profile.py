"""Prepare an isolated BEFC Location.step timing host, never deploy or run AIR.

--compile-only exports the exact baseline and prepares an import for review.
--resume-compiled requires the audit wrapper's explicit, pinned body approval.
The probe supplies nativeAPI.locationStepProfile = {} between measured cases.
All times are inclusive diagnostics, not performance acceptance measurements.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import uuid

sys.dont_write_bytecode = True
B = Path(__file__).resolve().parent
ROOT = B.parents[2]
BASE = B/'generated/fog-typed'
OUT = B/'generated/location-step-profile-20261022'
HOST_SHA = 'BEFCF0509E11FAC9FEF7AFB834708B8B93752A14AE3D5CD72B42AA6D42F9B82A'
XML_SHA = 'E5DBF6959F268078B99F0111EB9720F49C2759C1837C82486D9638A17AB92A66'
TARGET = 'fe.loc.Location::0:1:step'
VERSION = 'location-step-profile-1'
GROUPS = ('player', 'activity', 'objects', 'unit', 'box', 'bullet', 'other', 'unitCoord', 'lighting', 'post')
TIMER_CALLS = 18
LOCAL_SCHEMA = [('csLSWholeStart', 3), ('csLSCarrier', 13), ('csLSApi', 13), ('csLSStats', 13),
                ('csLSPartStart', 3), ('csLSLoopStart', 3), ('csLSElapsed', 3), ('csLSKind', 3),
                ('csLSTotal', 3), ('csLSErrors', 3)] + [
    ('csLS' + key + suffix, 3) for key in GROUPS for suffix in ('Ms', 'Calls')]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def instrument(source, parser):
    """Reversible insertions into one body, plus one package-function import."""
    assert 'csLS' not in source, 'Profiler local-name collision'
    assert 'import flash.utils.getTimer;' not in source, 'Review existing timer import'
    import_anchor = '   import flash.geom.ColorTransform;'
    assert source.count(import_anchor) == 1
    begin, end = parser._body(source, 'step')
    original = source[begin+1:end]
    assert not re.search(r'\b(return|finally|function)\b', original), 'Unexpected control flow in Location.step'
    assert original.count('catch(') == 1 and original.count('try') == 1
    assert original.count('obj.step();') == 1 and original.count('this.gg.step();') == 1
    body, edits = original, []

    def insert(before, after):
        nonlocal body
        assert body.count(before) == 1, ('Location.step anchor changed', before, body.count(before))
        body = body.replace(before, after)
        edits.append((before, after))

    def timed(call, key):
        matches = list(re.finditer(r'(?m)^([ \t]*)' + re.escape(call) + r'$', body))
        assert len(matches) == 1, ('Expected one exact native call', call)
        line, indent = matches[0].group(0), matches[0].group(1)
        insert(line, indent + 'if(csLSStats != null) csLSPartStart = getTimer();\n' + line + '\n' +
               indent + 'if(csLSStats != null)\n' + indent + '{\n' +
               indent + '   csLS' + key + 'Ms += getTimer() - csLSPartStart;\n' +
               indent + '   ++csLS' + key + 'Calls;\n' + indent + '}')

    timed('this.gg.step();', 'player')
    timed('sceneSleeping = World.w.grafon.sceneLarge ? World.w.grafon.sceneNativeCall("activity",[this]) : null;', 'activity')
    timed('this.unitCoord.step();', 'unitCoord')
    timed('this.lighting();', 'lighting')
    timed('this.lighting2();', 'lighting')
    insert('         numb = 0;', '         if(csLSStats != null) csLSLoopStart = getTimer();\n         numb = 0;')
    loop_end = '         }\n         World.w.grafon.sceneNativeEnvironment(this,this.gg.X,this.gg.Y);'
    insert(loop_end, '''         }
         if(csLSStats != null)
         {
            csLSobjectsMs += getTimer() - csLSLoopStart;
            ++csLSobjectsCalls;
         }
         World.w.grafon.sceneNativeEnvironment(this,this.gg.X,this.gg.Y);''')
    insert('                  obj.step();', '''                  if(csLSStats != null)
                  {
                     csLSKind = 3;
                     if(obj is Unit) csLSKind = 0;
                     else if(obj is Box) csLSKind = 1;
                     else if(obj is Bullet) csLSKind = 2;
                     csLSPartStart = getTimer();
                  }
                  obj.step();
                  if(csLSStats != null)
                  {
                     csLSElapsed = getTimer() - csLSPartStart;
                     if(csLSKind == 0) {csLSunitMs += csLSElapsed; ++csLSunitCalls;}
                     else if(csLSKind == 1) {csLSboxMs += csLSElapsed; ++csLSboxCalls;}
                     else if(csLSKind == 2) {csLSbulletMs += csLSElapsed; ++csLSbulletCalls;}
                     else {csLSotherMs += csLSElapsed; ++csLSotherCalls;}
                  }''')
    insert('               World.w.showError(err,obj.err());',
           '               if(csLSStats != null) ++csLSErrors;\n               World.w.showError(err,obj.err());')
    insert('         this.isRelight = false;',
           '         if(csLSStats != null) csLSPartStart = getTimer();\n         this.isRelight = false;')
    declarations = '\n         var csLSWholeStart:int = getTimer();\n'
    for name, kind in LOCAL_SCHEMA[1:]:
        declarations += '         var ' + name + (':Object = null;\n' if kind == 13 else ':int = 0;\n')
    declarations += '''         csLSCarrier = World.w.main.getChildByName("ContinuousSceneCarrier");
         if(csLSCarrier != null) csLSApi = csLSCarrier["nativeAPI"];
         if(csLSApi != null && "locationStepProfile" in csLSApi)
            csLSStats = csLSApi["locationStepProfile"] as Object;
'''
    flush = '''
         if(csLSStats != null)
         {
            csLSpostMs += getTimer() - csLSPartStart;
            ++csLSpostCalls;
            csLSTotal = getTimer() - csLSWholeStart;
            if(!("version" in csLSStats))
            {
               csLSStats.version = "location-step-profile-1";
               csLSStats.diagnosticOnly = true;
               csLSStats.performanceEligible = false;
               csLSStats.calls = 0;
               csLSStats.totalMs = 0;
               csLSStats.totalMaxMs = 0;
               csLSStats.errorCalls = 0;
'''
    for key in GROUPS:
        for suffix in ('Ms', 'Calls', 'MaxMs'):
            flush += '               csLSStats.' + key + suffix + ' = 0;\n'
    flush += '''            }
            ++csLSStats.calls;
            csLSStats.totalMs += csLSTotal;
            if(csLSTotal > csLSStats.totalMaxMs) csLSStats.totalMaxMs = csLSTotal;
            csLSStats.errorCalls += csLSErrors;
'''
    for key in GROUPS:
        flush += '            csLSStats.' + key + 'Ms += csLS' + key + 'Ms;\n'
        flush += '            csLSStats.' + key + 'Calls += csLS' + key + 'Calls;\n'
        flush += '            if(csLS' + key + 'Ms > csLSStats.' + key + 'MaxMs) csLSStats.' + key + 'MaxMs = csLS' + key + 'Ms;\n'
    flush += '         }\n'
    restored = body
    for before, after in reversed(edits):
        assert restored.count(after) == 1, 'Reversal anchor is ambiguous'
        restored = restored.replace(after, before)
    assert restored == original, 'An original statement changed'
    result = source[:begin+1] + declarations + body + flush + source[end:]
    a, z = parser._body(result, 'step')
    assert result[:a+1] == source[:begin+1] and result[z:] == source[end:]
    assert result[a+1:z].count('getTimer()') == TIMER_CALLS
    assert len(LOCAL_SCHEMA) == 30
    return result.replace(import_anchor, import_anchor + '\n   import flash.utils.getTimer;')


def build(wait=300, ffdec_heap=1400, resume=False):
    e = load('location_profile_build_helpers', B/'enemy-speed.py')
    audit = B/'location-step-profile-audit.py'
    OUT.mkdir(exist_ok=True)
    with e.motion.Registration(owner='ContinuousScene / Location step diagnosis / 01a13816',
            purpose='BEFC one-method diagnostic build; no AIR or deployment', run_dir=OUT,
            evidence=OUT/'build.json', resource='game', wait=wait) as lease:
        assert not e.motion.air_pids(), 'Other AIR present; untouched'
        assert digest(ROOT/'pfe.swf') == digest(BASE/'pfe.swf') == HOST_SHA
        assert digest(BASE/'pfe.xml') == XML_SHA
        inputs = {str(p): digest(p) for p in (Path(__file__), audit, B/'bullet-segments-audit.py',
                  B/'stationary-threat-audit.py', B/'native-crop-audit.py', B/'enemy-speed.py', B/'profile-vision.py')}

        def child(command, label):
            process = None
            lease.before_launch(label)
            try:
                process = subprocess.Popen(command)
                lease.child(process.pid)
                result = process.wait()
                if result:raise subprocess.CalledProcessError(result, command)
            finally:
                if process is not None:
                    if process.poll() is None:
                        process.kill(); process.wait(timeout=15)
                    lease.child_stopped()

        def ff(*args, heap=None):
            assert not e.motion.air_pids(), 'AIR started during build; stop before next JVM'
            assert digest(ROOT/'pfe.swf') == HOST_SHA, 'Formal host drift'
            size = heap or ffdec_heap
            memory = e.motion.memory_status()
            assert memory['availableCommit'] >= (size + 512) * 1024**2, ('Insufficient commit', memory)
            assert memory['availablePhysical'] >= 1.5 * 1024**3, ('Insufficient physical memory', memory)
            child([str(e.JAVA), '-Xmx' + str(size) + 'm', '-jar', str(e.TOOLS/'ffdec/ffdec-cli.jar'),
                   *map(str, args)], 'Location.step FFDec ' + str(args[0]))

        def check(*args):
            child([sys.executable, '-B', str(audit), *map(str, args)], 'Location.step offline audit ' + str(args[0]))

        prior = None
        if resume:
            prior = json.loads((OUT/'compiled-provenance.json').read_text('utf-8-sig'))
            assert prior['version'] == VERSION and prior['base'] == HOST_SHA and prior['baseXML'] == XML_SHA
            assert set(prior['sourceInputs']) == set(inputs), 'Resume input set changed'
            for path, value in prior['sourceInputs'].items():
                if Path(path).resolve() != audit.resolve():
                    assert value == inputs[path], ('Unreviewed build/helper drift', path)
            for name in ('compiled.swf', 'compiled.xml'):
                assert digest(OUT/name) == prior['compiledInputs'][name], 'Compiled input drift: ' + name
            original = Path(prior['originalPath'])
            assert original.resolve().is_relative_to(OUT.resolve()) and digest(original) == prior['originalSource']
        else:
            assert not (OUT/'compiled-provenance.json').exists(), 'Preserve the existing import; use reviewed resume'
            exported = OUT/('original-' + uuid.uuid4().hex)
            ff('-selectclass', 'fe.loc.Location', '-export', 'script', exported, BASE/'pfe.swf', heap=512)
            original = exported/'scripts/fe/loc/Location.as'
        source = instrument(original.read_text('utf-8-sig'), e.parser)
        target = OUT/'source/fe/loc/Location.as'
        assert all(p == target for p in (OUT/'source').rglob('*.as')), 'Unexpected extra import source'
        if resume:
            assert target.read_text('utf-8') == source and digest(target) == prior['instrumentedSource']
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(source, 'utf-8')
        meta = dict(version=VERSION, diagnosticOnly=True, performanceEligible=False, deployed=False,
                    base=HOST_SHA, baseXML=XML_SHA, target=TARGET, sourceInputs=inputs,
                    originalPath=str(original), originalSource=digest(original), instrumentedSource=digest(target),
                    sourceTransformReversible=True, originalCallOrderPreserved=True, newClassMembers=False,
                    newClosures=False, newTryCatchFinally=False, localSchema=LOCAL_SCHEMA, groups=GROUPS,
                    timerCalls=TIMER_CALLS, carrier='ContinuousSceneCarrier.nativeAPI.locationStepProfile',
                    limitations=['objects includes unit/box/bullet/other; these groups must not be added twice.',
                        'Per-object calls include nested rendering, light and damage callbacks.',
                        'lighting covers only Location.step scheduled lighting/lighting2 calls.',
                        'MaxMs is the largest category sum in one Location.step, not the slowest individual object.',
                        'Total includes lookup and profiling overhead, excludes final stats aggregation.',
                        'Integer-ms timers and per-object probes are diagnostic only; errors invalidate the sample.'])
        receipt = OUT/('resume-provenance-' + uuid.uuid4().hex + '.json') if resume else OUT/'provenance.json'
        if resume:
            meta['continuedFrom'] = dict(path=str(OUT/'compiled-provenance.json'), sha256=digest(OUT/'compiled-provenance.json'),
                originalSourceInputs=prior['sourceInputs'],
                previousResumeAttempts={str(p): digest(p) for p in sorted(OUT.glob('resume-provenance-*.json'))})
        receipt.write_text(json.dumps(meta, indent=2), 'utf-8')
        if not resume:
            ff('-importScript', BASE/'pfe.swf', OUT/'compiled.swf', OUT/'source')
            ff('-swf2xml', OUT/'compiled.swf', OUT/'compiled.xml')
            meta['compiledInputs'] = {name: digest(OUT/name) for name in ('compiled.swf', 'compiled.xml')}
            assert inputs == {p: digest(p) for p in inputs}, 'Source changed during compile'
            assert digest(ROOT/'pfe.swf') == HOST_SHA
            (OUT/'compiled-provenance.json').write_text(json.dumps(meta, indent=2), 'utf-8')
            check('--inspect-import', '--candidate', OUT/'compiled.xml', '--out', OUT/'import-review.json')
            lease.outcome = 'passed'; lease.note = 'Import prepared only; activation/catch/layout review still required'
            print(json.dumps(dict(prepared=True, reviewed=False, runtimeReady=False, provenance=str(OUT/'compiled-provenance.json'))))
            return
        check('--retain', '--candidate', OUT/'compiled.xml', '--out', OUT/'retained.xml')
        ff('-xml2swf', OUT/'retained.xml', OUT/'serialized.swf')
        ff('-swf2xml', OUT/'serialized.swf', OUT/'serialized.xml')
        check('--splice-abc', '--candidate', OUT/'serialized.xml', '--candidate-swf', OUT/'serialized.swf', '--out', OUT/'pfe.swf')
        ff('-swf2xml', OUT/'pfe.swf', OUT/'pfe.xml')
        check('--candidate', OUT/'pfe.xml', '--candidate-swf', OUT/'pfe.swf', '--out', OUT/'semantic-audit.json')
        assert inputs == {p: digest(p) for p in inputs}, 'Build/audit source changed during resume'
        assert digest(ROOT/'pfe.swf') == digest(BASE/'pfe.swf') == HOST_SHA and digest(BASE/'pfe.xml') == XML_SHA
        meta.update(candidate=digest(OUT/'pfe.swf'), candidateXML=digest(OUT/'pfe.xml'), audit=digest(OUT/'semantic-audit.json'))
        (OUT/'build.json').write_text(json.dumps(meta, indent=2), 'utf-8')
        receipt.write_text(json.dumps(meta, indent=2), 'utf-8')
        lease.outcome = 'passed'; lease.note = 'Strict one-method Location profiler ready; runtime pending'
        print(json.dumps(meta))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    action = p.add_mutually_exclusive_group()
    action.add_argument('--compile-only', action='store_true')
    action.add_argument('--resume-compiled', action='store_true')
    p.add_argument('--wait', type=int, default=300)
    p.add_argument('--ffdec-heap', type=int, choices=(512, 1400), default=1400)
    args = p.parse_args()
    if args.compile_only or args.resume_compiled:build(args.wait, args.ffdec_heap, args.resume_compiled)
    else:p.print_help()
