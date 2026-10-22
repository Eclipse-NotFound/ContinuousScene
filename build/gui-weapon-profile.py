"""Prepare an isolated BEFC GUI.setWeapon timing host, never deploy or run AIR.

--compile-only exports the exact baseline and prepares an import for review.
--resume-compiled requires the audit wrapper's explicit, pinned body approval.
The probe supplies nativeAPI.guiWeaponProfile = {} between measured cases.
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
OUT = B/'generated/gui-weapon-profile-20261022'
HOST_SHA = 'BEFCF0509E11FAC9FEF7AFB834708B8B93752A14AE3D5CD72B42AA6D42F9B82A'
XML_SHA = 'E5DBF6959F268078B99F0111EB9720F49C2759C1837C82486D9638A17AB92A66'
TARGET = 'fe.inter.GUI::0:1:setWeapon'
VERSION = 'gui-weapon-profile-1'
GROUPS = ('weaponHtml', 'textWidth', 'ammoText', 'holder')
TIMER_CALLS = 18
LOCAL_SCHEMA = [('csGWWholeStart', 3), ('csGWCarrier', 13), ('csGWApi', 13), ('csGWStats', 13),
                ('csGWPartStart', 3), ('csGWTotal', 3)] + [
    ('csGW' + key + suffix, 3) for key in GROUPS for suffix in ('Ms', 'Calls')]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def instrument(source, parser):
    """Insert timing around eight native statements, then prove reversibility."""
    assert 'csGW' not in source, 'Profiler local-name collision'
    assert 'import flash.utils.getTimer;' not in source, 'Review existing timer import'
    import_anchor = '   import flash.display.MovieClip;'
    assert source.count(import_anchor) == 1
    begin, end = parser._body(source, 'setWeapon')
    original = source[begin+1:end]
    assert not re.search(r'\b(return|try|catch|finally|function)\b', original), 'Unexpected GUI.setWeapon control flow'
    body, edits = original, []
    patterns = [(r'this\.weapon\.htmlText = .*;', 'weaponHtml', 2),
                (r'this\.vis\.textWeapon\.x = 20 \+ this\.weapon\.textWidth;', 'textWidth', 1),
                (r'this\.ammo\.text = .*;', 'ammoText', 4),
                (r'this\.setHolder\(\);', 'holder', 1)]
    matches = []
    for pattern, key, count in patterns:
        found = list(re.finditer(r'(?m)^([ \t]*)(' + pattern + r')$', original))
        assert len(found) == count, ('Native GUI statement count changed', key, len(found))
        matches.extend((match, key) for match in found)
    for match, key in sorted(matches, key=lambda item: item[0].start(), reverse=True):
        line, indent = match.group(0), match.group(1)
        replacement = (indent + 'if(csGWStats != null) csGWPartStart = getTimer();\n' + line + '\n' +
            indent + 'if(csGWStats != null)\n' + indent + '{\n' +
            indent + '   csGW' + key + 'Ms += getTimer() - csGWPartStart;\n' +
            indent + '   ++csGW' + key + 'Calls;\n' + indent + '}')
        body = body[:match.start()] + replacement + body[match.end():]
        edits.append((match.start(), line, replacement))
    restored = body
    for offset, before, after in reversed(edits):
        assert restored[offset:offset+len(after)] == after, 'Reversal offset drift'
        restored = restored[:offset] + before + restored[offset+len(after):]
    assert restored == original, 'Original GUI statement changed'
    declarations = '\n         var csGWWholeStart:int = getTimer();\n'
    for name, kind in LOCAL_SCHEMA[1:]:
        declarations += '         var ' + name + (':Object = null;\n' if kind == 13 else ':int = 0;\n')
    declarations += '''
         csGWCarrier = World.w.main.getChildByName("ContinuousSceneCarrier");
         if(csGWCarrier != null) csGWApi = csGWCarrier["nativeAPI"];
         if(csGWApi != null && "guiWeaponProfile" in csGWApi)
            csGWStats = csGWApi["guiWeaponProfile"] as Object;
'''
    flush = '''
         if(csGWStats != null)
         {
            csGWTotal = getTimer() - csGWWholeStart;
            if(!("version" in csGWStats))
            {
               csGWStats.version = "gui-weapon-profile-1";
               csGWStats.diagnosticOnly = true;
               csGWStats.performanceEligible = false;
               csGWStats.calls = 0;
               csGWStats.totalMs = 0;
               csGWStats.totalMaxMs = 0;
'''
    for key in GROUPS:
        for suffix in ('Ms', 'Calls', 'MaxMs'):
            flush += '               csGWStats.' + key + suffix + ' = 0;\n'
    flush += '''            }
            ++csGWStats.calls;
            csGWStats.totalMs += csGWTotal;
            if(csGWTotal > csGWStats.totalMaxMs) csGWStats.totalMaxMs = csGWTotal;
'''
    for key in GROUPS:
        flush += '            csGWStats.' + key + 'Ms += csGW' + key + 'Ms;\n'
        flush += '            csGWStats.' + key + 'Calls += csGW' + key + 'Calls;\n'
        flush += '            if(csGW' + key + 'Ms > csGWStats.' + key + 'MaxMs) csGWStats.' + key + 'MaxMs = csGW' + key + 'Ms;\n'
    flush += '         }\n'
    result = source[:begin+1] + declarations + body + flush + source[end:]
    a, z = parser._body(result, 'setWeapon')
    assert result[:a+1] == source[:begin+1] and result[z:] == source[end:]
    assert result[a+1:z].count('getTimer()') == TIMER_CALLS and len(LOCAL_SCHEMA) == 14
    return result.replace(import_anchor, import_anchor + '\n   import flash.utils.getTimer;')


def build(wait=300, ffdec_heap=1400, resume=False):
    e = load('gui_weapon_profile_build_helpers', B/'enemy-speed.py')
    audit = B/'gui-weapon-profile-audit.py'
    OUT.mkdir(exist_ok=True)
    with e.motion.Registration(owner='ContinuousScene / GUI weapon diagnosis / 01a13816',
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
                   *map(str, args)], 'GUI.setWeapon FFDec ' + str(args[0]))

        def check(*args):
            child([sys.executable, '-B', str(audit), *map(str, args)], 'GUI.setWeapon offline audit ' + str(args[0]))

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
            ff('-selectclass', 'fe.inter.GUI', '-export', 'script', exported, BASE/'pfe.swf', heap=512)
            original = exported/'scripts/fe/inter/GUI.as'
        source = instrument(original.read_text('utf-8-sig'), e.parser)
        target = OUT/'source/fe/inter/GUI.as'
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
                    timerCalls=TIMER_CALLS, carrier='ContinuousSceneCarrier.nativeAPI.guiWeaponProfile',
                    limitations=['Calls count completed setWeapon invocations, not frames; firing may trigger multiple calls.',
                        'holder includes the complete original setHolder call.',
                        'MaxMs is the largest category sum in one setWeapon invocation.',
                        'Total includes lookup/profiling overhead and excludes final stats aggregation.',
                        'No new catch is added; an escaping exception prevents this invocation from being counted.',
                        'Integer-ms timers are diagnostic only; runtime errors invalidate the sample.'])
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
            lease.outcome = 'passed'; lease.note = 'Import prepared only; body/frame/lexical/layout review still required'
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
