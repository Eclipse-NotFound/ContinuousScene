"""Registered isolated compilation only; never launch AIR or install a host.

First --compile-only freezes an import for review. --resume-compiled is blocked
until audit.py pins its actual bytecode/frame/namespaces. Original raw assets
and every non-target method/class are retained by the existing strict engine.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
import uuid

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
B = OUT.parents[1]
ROOT = B.parents[2]
BASE = B/'generated/combat-near-native-20261023/logic-profile-audit/fog-last-blocker-production-minimal'
REFERENCE = B/'generated/scripts/fe/inter/Camera.as'
HOST_SHA = '80CFD8CF3138EE59CBF6EDA0A1824A9EC960F413BD95E4B90D41DD0322B4FD3D'
XML_SHA = 'B92260A7A0DFA80EB129C60AEF273645C32BBBA9B3588770BD7083D6984E7E04'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def build(wait, heap, resume):
    recipe = load('vertical_camera_band_build_recipe', OUT/'recipe.py')
    e = load('vertical_camera_band_build_support', B/'enemy-speed.py')
    audit = OUT/'audit.py'
    paths = [Path(__file__), OUT/'recipe.py', audit, B/'enemy-speed.py', B/'profile-vision.py',
        B/'motion-test.py', B/'bullet-segments-audit.py', B/'stationary-threat-audit.py', B/'native-crop-audit.py',
        REFERENCE, BASE/'build.json', BASE/'semantic-audit.json']
    inputs = {str(p):sha(p) for p in paths}
    with e.motion.Registration(owner='ContinuousScene / vertical camera band bound / 01a13816',
            purpose='80CF isolated single-method candidate compilation, no AIR or deployment',
            run_dir=OUT, evidence=OUT/'build.json', resource='game', wait=wait) as lease:
        assert not e.motion.air_pids(), 'Other AIR present; untouched'
        assert sha(ROOT/'pfe.swf') == sha(BASE/'pfe.swf') == HOST_SHA
        assert sha(BASE/'pfe.xml') == XML_SHA

        def child(command, label):
            process = None
            lease.before_launch(label)
            try:
                process = subprocess.Popen(command)
                lease.child(process.pid)
                code = process.wait()
                if code:raise subprocess.CalledProcessError(code, command)
            finally:
                if process is not None:
                    if process.poll() is None:
                        process.kill();process.wait(timeout=15)
                    lease.child_stopped()

        def ff(*args, size=None):
            assert not e.motion.air_pids(), 'AIR appeared; stop before next JVM'
            assert sha(ROOT/'pfe.swf') == HOST_SHA, 'Formal host changed'
            limit = size or heap
            memory = e.motion.memory_status()
            assert memory['availableCommit'] >= (limit+512)*1024**2, ('Insufficient commit', memory)
            assert memory['availablePhysical'] >= 1.5*1024**3, ('Insufficient physical memory', memory)
            child([str(e.JAVA), '-Xmx'+str(limit)+'m', '-jar', str(e.TOOLS/'ffdec/ffdec-cli.jar'),
                *map(str, args)], 'vertical camera band FFDec '+str(args[0]))

        def check(*args):
            child([sys.executable, '-B', str(audit), *map(str, args)], 'vertical camera band strict audit')

        prior = None
        if resume:
            prior = json.loads((OUT/'compiled-provenance.json').read_text('utf-8-sig'))
            assert prior['version'] == recipe.VERSION and prior['base'] == HOST_SHA and prior['baseXML'] == XML_SHA
            assert set(prior['sourceInputs']) == set(inputs), 'Resume source set changed'
            for p, value in prior['sourceInputs'].items():
                if Path(p).resolve() != audit.resolve():assert value == inputs[p], ('Unreviewed input changed', p)
            for name, value in prior['compiledInputs'].items():assert sha(OUT/name) == value, name
            original = Path(prior['originalPath'])
            assert original.resolve().is_relative_to(OUT.resolve()) and sha(original) == prior['originalSource']
        else:
            assert not (OUT/'compiled-provenance.json').exists(), 'Existing import must be preserved; use reviewed resume'
            recipe.read_reference(REFERENCE)
            exported = OUT/('original-'+uuid.uuid4().hex)
            ff('-selectclass','fe.inter.Camera','-export','script',exported,BASE/'pfe.swf',size=512)
            original = exported/'scripts/fe/inter/Camera.as'
            assert original.is_file(), 'Current-host Camera export missing'
        native = original.read_text('utf-8-sig').replace('\r\n','\n')
        source = recipe.transform(native,e.parser,recipe.read_reference(REFERENCE))
        target = OUT/'source/fe/inter/Camera.as'
        assert all(p == target for p in (OUT/'source').rglob('*.as')), 'Unexpected imported source'
        if resume:
            assert target.read_text('utf-8') == source and sha(target) == prior['instrumentedSource']
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(source, 'utf-8')
        meta = dict(version=recipe.VERSION, diagnosticOnly=False, productionCandidate=True, performanceEligible=False, deployed=False,
            base=HOST_SHA, baseXML=XML_SHA, target=recipe.TARGET, sourceInputs=inputs,
            originalPath=str(original), originalSource=sha(original), instrumentedSource=sha(target),
            sourceTransformReversible=True, originalCallOrderPreserved=True, newClassMembers=False,
            newClosures=False, newTryCatchFinally=False, timerCalls=0, carrierStateKey=recipe.STATE_KEY, inspectedReferenceSHA256=recipe.REFERENCE_SHA,
            limitations=['Normal large-scene player follow only; existing carrier owns versioned context state.',
                'No Camera class members, timers or diagnostic counters; exact runtime/visual/performance checks pending.',
                'Normal rooms and look/camRun retain native calculations; ineligible context releases this version state.',
                'Only Camera.calc body is retained; all 80CF non-target bodies/layouts and raw assets remain.'])
        receipt = OUT/('resume-provenance-'+uuid.uuid4().hex+'.json') if resume else OUT/'provenance.json'
        if resume:meta['continuedFrom'] = dict(path=str(OUT/'compiled-provenance.json'), sha256=sha(OUT/'compiled-provenance.json'), sourceInputs=prior['sourceInputs'])
        receipt.write_text(json.dumps(meta, indent=2), 'utf-8')
        if not resume:
            ff('-importScript', BASE/'pfe.swf', OUT/'compiled.swf', OUT/'source')
            ff('-swf2xml', OUT/'compiled.swf', OUT/'compiled.xml')
            meta['compiledInputs'] = {n:sha(OUT/n) for n in ('compiled.swf','compiled.xml')}
            assert inputs == {p:sha(p) for p in inputs}, 'Input changed during compile'
            (OUT/'compiled-provenance.json').write_text(json.dumps(meta, indent=2), 'utf-8')
            check('--inspect-import', '--candidate', OUT/'compiled.xml', '--out', OUT/'import-review.json')
            lease.outcome='passed';lease.note='Import only; bytecode/private/layout review still required'
            return
        check('--retain', '--candidate', OUT/'compiled.xml', '--out', OUT/'retained.xml')
        ff('-xml2swf', OUT/'retained.xml', OUT/'serialized.swf')
        ff('-swf2xml', OUT/'serialized.swf', OUT/'serialized.xml')
        check('--splice-abc', '--candidate', OUT/'serialized.xml', '--candidate-swf', OUT/'serialized.swf', '--out', OUT/'pfe.swf')
        ff('-swf2xml', OUT/'pfe.swf', OUT/'pfe.xml')
        check('--candidate', OUT/'pfe.xml', '--candidate-swf', OUT/'pfe.swf', '--out', OUT/'semantic-audit.json')
        assert inputs == {p:sha(p) for p in inputs}, 'Input changed during retention'
        assert sha(ROOT/'pfe.swf') == sha(BASE/'pfe.swf') == HOST_SHA and sha(BASE/'pfe.xml') == XML_SHA
        meta.update(candidate=sha(OUT/'pfe.swf'), candidateXML=sha(OUT/'pfe.xml'), audit=sha(OUT/'semantic-audit.json'))
        (OUT/'build.json').write_text(json.dumps(meta, indent=2), 'utf-8')
        receipt.write_text(json.dumps(meta, indent=2), 'utf-8')
        lease.outcome='passed';lease.note='Isolated vertical camera band one-method candidate; exact runtime/release checks pending'


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--compile-only', action='store_true')
    g.add_argument('--resume-compiled', action='store_true')
    p.add_argument('--wait',type=int,default=600)
    p.add_argument('--ffdec-heap',type=int,choices=(512,1400),default=512)
    a=p.parse_args();build(a.wait,a.ffdec_heap,a.resume_compiled)
