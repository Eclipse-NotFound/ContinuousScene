"""Prepare an isolated BEFC UnitPlayer.animate same-frame guard host, never deploy or run AIR.

--compile-only exports the exact baseline and prepares an import for review.
--resume-compiled requires the audit wrapper's explicit, pinned body approval.
The existing sceneReuseIdleFrame switch also controls these two guards.
No instrumentation or production file is included or changed.
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
OUT = B/'generated/player-airframe-20261022'
HOST_SHA = 'BEFCF0509E11FAC9FEF7AFB834708B8B93752A14AE3D5CD72B42AA6D42F9B82A'
XML_SHA = 'E5DBF6959F268078B99F0111EB9720F49C2759C1837C82486D9638A17AB92A66'
TARGET = 'fe.unit.UnitPlayer::0:1:animate'
VERSION = 'player-airframe-1'
LOCAL_SCHEMA = []
GUARD_SITES = ('stationary-ladder', 'nonlevitating-air')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def instrument(source, parser):
    """Exactly two numeric goto guards; original standing guard stays byte-for-byte."""
    begin,end=parser._body(source,'animate')
    original=source[begin+1:end]
    edits=[]
    old_ladder="""            if(dy == 0)
            {
               vis.osn.body.gotoAndStop(1);
            }
            else
"""
    new_ladder="""            if(dy == 0)
            {
               if(!World.w.grafon.sceneLarge || !World.w.grafon.sceneReuseIdleFrame || vis.osn.body.currentFrame != 1 || vis.osn.body.isPlaying)
               {
                  vis.osn.body.gotoAndStop(1);
               }
            }
            else
"""
    old_air="""               vis.osn.body.gotoAndStop(_loc1_);
            }
         }
         if(vis.osn.body.head.morda)
"""
    new_air="""               if(!World.w.grafon.sceneLarge || !World.w.grafon.sceneReuseIdleFrame || vis.osn.body.currentFrame != _loc1_ || vis.osn.body.isPlaying)
               {
                  vis.osn.body.gotoAndStop(_loc1_);
               }
            }
         }
         if(vis.osn.body.head.morda)
"""
    body=original
    for before,after in ((old_ladder,new_ladder),(old_air,new_air)):
        assert body.count(before)==1, 'Exact native guard anchor changed'
        body=body.replace(before,after);edits.append((before,after))
    restored=body
    for before,after in reversed(edits):
        assert restored.count(after)==1
        restored=restored.replace(after,before)
    assert restored==original, 'A native statement changed'
    assert original.count('sceneReuseIdleFrame')==1 and body.count('sceneReuseIdleFrame')==3
    result=source[:begin+1]+body+source[end:]
    lo,hi=parser._body(result,'animate')
    assert result[:lo+1]==source[:begin+1] and result[hi:]==source[end:]
    assert body.count('gotoAndStop(')==original.count('gotoAndStop(')
    assert body.count('return;')==original.count('return;')==6
    assert body.count('catch(err:*)')==original.count('catch(err:*)')==1
    assert 'getTimer' not in body and body.count('var ')==original.count('var ')
    return result


def build(wait=300, ffdec_heap=1400, resume=False):
    e = load('player_airframe_build_helpers', B/'enemy-speed.py')
    audit = B/'player-airframe-audit.py'
    OUT.mkdir(exist_ok=True)
    with e.motion.Registration(owner='ContinuousScene / player airframe candidate / 01a13816',
            purpose='BEFC two-site timeline guard build; no AIR or deployment', run_dir=OUT,
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
                   *map(str, args)], 'UnitPlayer.animate FFDec ' + str(args[0]))

        def check(*args):
            child([sys.executable, '-B', str(audit), *map(str, args)], 'UnitPlayer.animate offline audit ' + str(args[0]))

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
            ff('-selectclass', 'fe.unit.UnitPlayer', '-export', 'script', exported, BASE/'pfe.swf', heap=512)
            original = exported/'scripts/fe/unit/UnitPlayer.as'
        source = instrument(original.read_text('utf-8-sig'), e.parser)
        target = OUT/'source/fe/unit/UnitPlayer.as'
        assert all(p == target for p in (OUT/'source').rglob('*.as')), 'Unexpected extra import source'
        if resume:
            assert target.read_text('utf-8') == source and digest(target) == prior['instrumentedSource']
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(source, 'utf-8')
        meta = dict(version=VERSION, candidateOnly=True, runtimeValidated=False, performanceEligible=False, deployed=False,
                    base=HOST_SHA, baseXML=XML_SHA, target=TARGET, sourceInputs=inputs,
                    originalPath=str(original), originalSource=digest(original), instrumentedSource=digest(target),
                    sourceTransformReversible=True, originalCallOrderPreserved=True, newClassMembers=False,
                    newClosures=False, newTryCatchFinally=False, newLocals=False, guardSites=GUARD_SITES,
                    switch='World.w.grafon.sceneLarge && World.w.grafon.sceneReuseIdleFrame',
                    preservedStandingGuard=True, timerCalls=0,
                    limitations=['Only two same-frame stopped numeric timeline calls may be skipped.',
                        'Original standing guard and foot marker reset are preserved.',
                        'Candidate requires actual-input action/pixel and performance validation before deployment.'])
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
        lease.outcome = 'passed'; lease.note = 'Strict two-site airframe candidate ready; runtime pending'
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
