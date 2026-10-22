"""Build only an isolated, timing-only World.step host from exact BEFC.

No execution by default. --build registers the game resource, exports World
fresh from BEFC, imports one class, retains only its step body, preserves raw
assets, and audits the final exported binary. Never deploys or launches AIR.
The caller must supply ContinuousSceneCarrier.nativeAPI.worldStepProfile = {}.
Use a fresh object between measured windows; times are inclusive diagnostics.
"""
from __future__ import annotations

import argparse
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
OUT = B/'generated/world-step-profile-20261022'
BASE = B/'generated/fog-typed'
HOST_SHA = 'BEFCF0509E11FAC9FEF7AFB834708B8B93752A14AE3D5CD72B42AA6D42F9B82A'
XML_SHA = 'E5DBF6959F268078B99F0111EB9720F49C2759C1837C82486D9638A17AB92A66'
TARGET = 'fe.World::0:1:step'
VERSION = 'world-step-profile-1'
SEGMENTS = [
    ('ctr', 'this.ctr.step();'), ('snd', 'Snd.step();'),
    ('land', 'this.land.step();'), ('satsStep2', 'this.sats.step2();'),
    ('inventory', None), ('cam', 'this.cam.calc(this.gg);'),
    ('gui', 'this.gui.step();'), ('pip', 'this.pip.step();'),
    ('sats', 'this.sats.step();'),
]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def instrument(source, parser):
    """Only insert locals/timing; reverse every insertion to prove source parity."""
    assert 'csWS' not in source, 'Profiler local-name collision'
    assert source.count('   import flash.utils.getTimer;') == 1, 'World must already import the qualified native timer'
    begin, end = parser._body(source, 'step')
    original = source[begin+1:end]
    assert original.count('return;') == 2, 'Review any new early-return path'
    assert original.count('catch(') == 1 and 'finally' not in original, 'Unexpected World.step exception shape'
    assert not re.search(r'\bfunction\b', original), 'World.step unexpectedly contains a closure'
    body, edits = original, []

    def replace_once(before, after):
        nonlocal body
        assert body.count(before) == 1, ('World.step anchor changed', before, body.count(before))
        body = body.replace(before, after)
        edits.append((before, after))

    # Total starts at entry, before carrier lookup; aggregation itself is not
    # included. No new try/finally or closure changes the invocation frame.
    declarations = '\n         var csWSWholeStart:int = getTimer();\n'
    declarations += '         var csWSCarrier:Object = null;\n         var csWSApi:Object = null;\n         var csWSStats:Object = null;\n'
    declarations += '         var csWSPartStart:int = 0;\n         var csWSTotal:int = 0;\n'
    declarations += '         var csWSFailed:Boolean = false;\n         var csWSEarly:Boolean = false;\n'
    for key, _ in SEGMENTS:
        declarations += '         var csWS' + key + 'Ms:int = 0;\n         var csWS' + key + 'Calls:int = 0;\n'
    lookup = '''
            if(this.main != null)
               csWSCarrier = this.main.getChildByName("ContinuousSceneCarrier");
            if(csWSCarrier != null)
               csWSApi = csWSCarrier["nativeAPI"];
            if(csWSApi != null && "worldStepProfile" in csWSApi)
               csWSStats = csWSApi["worldStepProfile"] as Object;
'''
    anchor = '\n         try\n         {'
    replace_once(anchor, anchor + lookup)
    for key, call in SEGMENTS:
        if call is None:
            block = '''               if(this.calcMass)
               {
                  this.invent.calcMass();
                  this.calcMass = false;
               }
               if(this.calcMassW)
               {
                  this.invent.calcWeaponMass();
                  this.calcMassW = false;
               }'''
            indent = '               '
        else:
            found = list(re.finditer(r'(?m)^([ \t]*)' + re.escape(call) + r'$', body))
            assert len(found) == 1, ('Expected one original call', call, len(found))
            block, indent = found[0].group(0), found[0].group(1)
        before = indent + 'if(csWSStats != null) csWSPartStart = getTimer();\n'
        after = '\n' + indent + 'if(csWSStats != null)\n' + indent + '{\n'
        after += indent + '   csWS' + key + 'Ms += getTimer() - csWSPartStart;\n'
        after += indent + '   ++csWS' + key + 'Calls;\n' + indent + '}'
        replace_once(block, before + block + after)
    # Native catch and showError stay intact; any caught failure invalidates
    # the probe window instead of looking like a cheap successful step.
    replace_once('            showError(err);', '            csWSFailed = true;\n            showError(err);')
    flush = '''
         if(csWSStats != null)
         {
            csWSTotal = getTimer() - csWSWholeStart;
            if(!("version" in csWSStats))
            {
               csWSStats.version = "world-step-profile-1";
               csWSStats.diagnosticOnly = true;
               csWSStats.performanceEligible = false;
               csWSStats.calls = 0;
               csWSStats.totalMs = 0;
               csWSStats.totalMaxMs = 0;
               csWSStats.errorCalls = 0;
               csWSStats.earlyReturnCalls = 0;
'''
    for key, _ in SEGMENTS:
        for suffix in ('Calls', 'Ms', 'MaxMs'):
            flush += '               csWSStats.' + key + suffix + ' = 0;\n'
    flush += '''            }
            ++csWSStats.calls;
            csWSStats.totalMs += csWSTotal;
            if(csWSTotal > csWSStats.totalMaxMs) csWSStats.totalMaxMs = csWSTotal;
            if(csWSFailed) ++csWSStats.errorCalls;
            if(csWSEarly) ++csWSStats.earlyReturnCalls;
'''
    for key, _ in SEGMENTS:
        flush += '            csWSStats.' + key + 'Calls += csWS' + key + 'Calls;\n'
        flush += '            csWSStats.' + key + 'Ms += csWS' + key + 'Ms;\n'
        flush += '            if(csWS' + key + 'Ms > csWSStats.' + key + 'MaxMs) csWSStats.' + key + 'MaxMs = csWS' + key + 'Ms;\n'
    flush += '         }\n'
    early = 'csWSEarly = true;\n' + flush + 'return;'
    body = body.replace('return;', early)
    restored = body.replace(early, 'return;')
    assert body.count(early) == 2
    for before, after in reversed(edits):
        assert restored.count(after) == 1, 'Insertion proof is ambiguous'
        restored = restored.replace(after, before)
    assert restored == original, 'Instrumentation altered an original statement'
    result = source[:begin+1] + declarations + body + flush + source[end:]
    final_begin, final_end = parser._body(result, 'step')
    assert source[:begin+1] == result[:final_begin+1] and source[end:] == result[final_end:]
    assert result[final_begin+1:final_end].count('getTimer()') == 22, 'Unexpected timer count'
    return result


def build(wait=300, ffdec_heap=1400, resume_compiled=False):
    e = load('world_step_build_helpers', B/'enemy-speed.py')
    assert ffdec_heap in (512, 1400)
    OUT.mkdir(exist_ok=True)
    audit = B/'world-step-profile-audit.py'
    with e.motion.Registration(owner='ContinuousScene / World step diagnosis / 01a13816',
            purpose='BEFC one-method timing build only; no AIR or deployment',
            run_dir=OUT, evidence=OUT/'build.json', resource='game', wait=wait) as lease:
        assert not e.motion.air_pids(), 'Other AIR present; untouched'
        assert e.digest(ROOT/'pfe.swf') == e.digest(BASE/'pfe.swf') == HOST_SHA
        assert e.digest(BASE/'pfe.xml') == XML_SHA
        assert e.JAVA.is_file() and (e.TOOLS/'ffdec/ffdec-cli.jar').is_file()
        source_inputs = {str(p): e.digest(p) for p in [Path(__file__), audit, B/'bullet-segments-audit.py',
            B/'stationary-threat-audit.py', B/'native-crop-audit.py', B/'enemy-speed.py', B/'profile-vision.py']}

        def registered_process(command, detail):
            process = None
            lease.before_launch(detail)
            try:
                process = subprocess.Popen(command)
                lease.child(process.pid)
                result = process.wait()
                if result:
                    raise subprocess.CalledProcessError(result, command)
            finally:
                if process is not None:
                    if process.poll() is None:
                        process.kill()  # Only this exact owned child handle.
                        process.wait(timeout=15)
                    lease.child_stopped()
                # A failed/uncertain launch without a returned handle leaves
                # the registry's launching marker for explicit reconciliation.

        def ff(*args, heap=None):
            assert not e.motion.air_pids(), 'AIR started during build; stop before next JVM'
            assert e.digest(ROOT/'pfe.swf') == HOST_SHA, 'Formal host drift'
            effective_heap = heap or ffdec_heap
            memory = e.motion.memory_status()
            assert memory['availableCommit'] >= (effective_heap + 512) * 1024**2, ('Insufficient commit for FFDec heap plus 512 MiB reserve', memory)
            assert memory['availablePhysical'] >= 1.5 * 1024**3, ('Insufficient physical memory for isolated FFDec', memory)
            registered_process([str(e.JAVA), '-Xmx' + str(effective_heap) + 'm', '-jar',
                str(e.TOOLS/'ffdec/ffdec-cli.jar'), *map(str, args)], 'World.step FFDec ' + str(args[0]))

        def check(*args):
            registered_process([sys.executable, '-B', str(audit), *map(str, args)], 'World.step offline audit ' + str(args[0]))

        # A fresh export directory cannot accidentally reuse an older host's
        # source. Selected-class export uses 512 MiB; full XML/import stages
        # may need the existing 1400 MiB FFDec budget (override is explicit).
        prior = None
        if resume_compiled:
            # Continue only this reviewed failed import. Preserve its original
            # provenance and sourceInputs; record the two reviewed script
            # revisions separately instead of silently rewriting old evidence.
            prior = json.loads((OUT/'provenance.json').read_text('utf-8-sig'))
            assert prior['base'] == HOST_SHA and prior['baseXml'] == XML_SHA and not prior['compiled']
            approved_old = {'world-step-profile.py': 'E6859F6E6AD94981A469F70297C9CDAAE4A82EFB0E2115926F3EF8156B3FB3E2',
                            'world-step-profile-audit.py': '77E80B8092D77D03AC795CD6009B589A08B77B02D41DFE9E70E0F8650C72ADD2'}
            assert set(prior['sourceInputs']) == set(source_inputs), 'Resume input set changed'
            for path, old_hash in prior['sourceInputs'].items():
                if Path(path).name in approved_old:
                    assert old_hash == approved_old[Path(path).name], 'Unreviewed prior build/audit revision'
                else:
                    assert old_hash == source_inputs[path], ('Unreviewed helper drift', path)
            assert e.digest(OUT/'compiled.xml') == 'BC64179FF4C570CD12F03498E7EFEED6FE3CE6632EF9EE5EA8B05C6C092E45D9'
            assert e.digest(OUT/'compiled.swf') == 'FA8EB47F882BF3C59B6026EE605D16BF1620B4A6E94558910159F85E184E787F'
            original = Path(prior['originalSourcePath'])
            assert original.resolve().is_relative_to(OUT.resolve())
            assert e.digest(original) == prior['originalSource'] == 'F9B5D270AD95A223CA37B0E339DCEE1380856DFF6254A5B1A0D9B12D997AAF16'
        else:
            exported = OUT/('original-' + uuid.uuid4().hex)
            ff('-selectclass', 'fe.World', '-export', 'script', exported, BASE/'pfe.swf', heap=512)
            original = exported/'scripts/fe/World.as'
        source = original.read_text('utf-8-sig')
        target = OUT/'source/fe/World.as'
        assert all(p == target for p in (OUT/'source').rglob('*.as')), 'Unexpected extra import source'
        if resume_compiled:
            assert e.digest(target) == prior['source'] == '7E5D044E527C0BB6CCBE5DEAB42843240AA396C4827102403D8580EFDB42FE47'
            assert target.read_text('utf-8') == instrument(source, e.parser), 'Resume transformation changed'
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(instrument(source, e.parser), 'utf-8')
        meta = dict(version=VERSION, diagnosticOnly=True, performanceEligible=False, deployed=False, compiled=False,
            base=HOST_SHA, baseXml=XML_SHA, originalSourcePath=str(original), originalSource=e.digest(original),
            source=e.digest(target), sourceTransformReversible=True, changedMethods=[TARGET],
            carrier='ContinuousSceneCarrier.nativeAPI.worldStepProfile', segments=[key for key, _ in SEGMENTS],
            statsFields=['calls', 'totalMs', 'totalMaxMs', 'errorCalls', 'earlyReturnCalls'] +
                [key + suffix for key, _ in SEGMENTS for suffix in ('Calls', 'Ms', 'MaxMs')],
            heaps=dict(selectedClassExport=512, fullImportAndXML=ffdec_heap), sourceInputs=source_inputs,
            limitations=['Diagnostic overhead and integer-ms resolution prohibit frame-time acceptance.',
                'Segments include all nested callbacks; total also includes unsegmented native branches and instrumentation.',
                'Inventory counts the contiguous two-condition section, including its flag checks/resets.',
                'errorCalls or native showError invalidates the measurement; no attempt to time an interrupted child call.',
                'Reentrant World.step measurements can overlap; no pure self-time claim.',
                'No render, compositor or deferred event cost is attributed by these native-step counters.'])
        if resume_compiled:
            meta['continuedFrom'] = dict(provenanceSHA256=e.digest(OUT/'provenance.json'),
                originalSourceInputs=prior['sourceInputs'],
                previousResumeAttempts={str(p): e.digest(p) for p in sorted(OUT.glob('resume-provenance-*.json'))},
                reason='Explicit 26-local activation proof and fixed rejected import-layout proof; all earlier provenance retained',
                skipped=['World export', 'AS import', 'compiled XML export'])
            provenance_path = OUT/('resume-provenance-' + uuid.uuid4().hex + '.json')
        else:
            provenance_path = OUT/'provenance.json'
            if provenance_path.exists():
                (OUT/('previous-provenance-' + uuid.uuid4().hex + '.json')).write_bytes(provenance_path.read_bytes())
        provenance_path.write_text(json.dumps(meta, indent=2), 'utf-8')
        if not resume_compiled:
            ff('-importScript', BASE/'pfe.swf', OUT/'compiled.swf', OUT/'source')
            ff('-swf2xml', OUT/'compiled.swf', OUT/'compiled.xml')
        meta['compiledInputs'] = dict(swf=e.digest(OUT/'compiled.swf'), xml=e.digest(OUT/'compiled.xml'))
        provenance_path.write_text(json.dumps(meta, indent=2), 'utf-8')
        check('--retain', '--base', BASE/'pfe.xml', '--candidate', OUT/'compiled.xml', '--out', OUT/'retained.xml')
        retention_path = OUT/'retained.audit.json'
        retention = json.loads(retention_path.read_text('utf-8'))
        assert retention['baseXMLSHA256'] == XML_SHA and retention['importedXMLSHA256'] == meta['compiledInputs']['xml']
        assert retention['outputXMLSHA256'] == e.digest(OUT/'retained.xml')
        assert retention['wrapperSHA256'] == source_inputs[str(audit)], 'Retention wrapper changed'
        assert retention['rejectedImportedLayout']['rejected'] and not retention['rejectedImportedLayout']['importedClassCopied']
        assert retention['preservedOriginalLayout']['preserved'] and retention['preservedOriginalLayout']['onlyCopiedBody'] == TARGET
        meta.update(retentionAudit=e.digest(retention_path), rejectedImportedLayout=retention['rejectedImportedLayout'],
                    preservedOriginalLayout=retention['preservedOriginalLayout'])
        provenance_path.write_text(json.dumps(meta, indent=2), 'utf-8')
        ff('-xml2swf', OUT/'retained.xml', OUT/'serialized.swf')
        ff('-swf2xml', OUT/'serialized.swf', OUT/'serialized.xml')
        check('--splice-abc', '--base', BASE/'pfe.xml', '--candidate', OUT/'serialized.xml',
              '--base-swf', BASE/'pfe.swf', '--candidate-swf', OUT/'serialized.swf', '--out', OUT/'pfe.swf')
        ff('-swf2xml', OUT/'pfe.swf', OUT/'pfe.xml')
        check('--base', BASE/'pfe.xml', '--candidate', OUT/'pfe.xml', '--base-swf', BASE/'pfe.swf',
              '--candidate-swf', OUT/'pfe.swf', '--out', OUT/'semantic-audit.json')
        assert e.digest(ROOT/'pfe.swf') == e.digest(BASE/'pfe.swf') == HOST_SHA
        assert e.digest(BASE/'pfe.xml') == XML_SHA
        assert source_inputs == {p: e.digest(Path(p)) for p in source_inputs}, 'Build/audit source changed during build'
        assert target.read_text('utf-8') == instrument(source, e.parser), 'Instrumented source changed during build'
        meta.update(compiled=True, candidate=e.digest(OUT/'pfe.swf'), candidateXml=e.digest(OUT/'pfe.xml'),
                    audit=e.digest(OUT/'semantic-audit.json'))
        (OUT/'build.json').write_text(json.dumps(meta, indent=2), 'utf-8')
        lease.outcome = 'passed'
        lease.note = 'Isolated World.step profiler built and strict audit passed; runtime pending'
        print(json.dumps(meta), flush=True)
        return meta


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument('--build', action='store_true')
    actions.add_argument('--resume-compiled', action='store_true')
    parser.add_argument('--wait', type=int, default=300)
    parser.add_argument('--ffdec-heap', type=int, choices=[512, 1400], default=1400)
    args = parser.parse_args()
    if args.build or args.resume_compiled:
        build(args.wait, args.ffdec_heap, args.resume_compiled)
    else:
        parser.print_help()
