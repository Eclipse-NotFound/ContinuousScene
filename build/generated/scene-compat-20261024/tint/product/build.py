"""Registered isolated single-method production candidate; never installs."""
from pathlib import Path
import importlib.util
import json
import subprocess
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
B=HERE.parents[3]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def main():
    a=load('tint_candidate_audit',HERE/'audit.py')
    e=load('tint_candidate_support',B/'enemy-speed.py')
    paths=[Path(__file__),HERE/'audit.py',B/'enemy-speed.py',B/'motion-test.py',B/'profile-vision.py',
        B/'bullet-segments-audit.py',B/'stationary-threat-audit.py',B/'native-crop-audit.py']
    inputs={str(p):a.sha(p) for p in paths}
    with e.motion.Registration(owner='ContinuousScene / player region tint build / 01a13816',
            purpose='ABE2 two tint methods only; no AIR or deployment',run_dir=HERE,evidence=HERE/'build.json',wait=600) as lease:
        assert not e.motion.air_pids(), 'Other AIR remains untouched'
        assert a.sha(B.parents[2]/'pfe.swf')==a.HOST
        assert not (HERE/'pfe.swf').exists() and not (HERE/'build.json').exists(), 'Preserve existing candidate'
        def child(command,label):
            process=None;lease.before_launch(label)
            try:
                process=subprocess.Popen(command);lease.child(process.pid)
                code=process.wait()
                if code:raise subprocess.CalledProcessError(code,command)
            finally:
                if process is not None:
                    if process.poll() is None:process.kill();process.wait(timeout=15)
                    lease.child_stopped()
        def check(step):child([sys.executable,'-B',str(HERE/'audit.py'),step],'Tint exact audit '+step)
        def ff(*args):
            assert not e.motion.air_pids() and a.sha(B.parents[2]/'pfe.swf')==a.HOST
            memory=e.motion.memory_status()
            assert memory['availableCommit']>=4*1024**3 and memory['availablePhysical']>=2*1024**3,memory
            child([str(e.JAVA),'-Xmx512m','-jar',str(e.TOOLS/'ffdec/ffdec-cli.jar'),*map(str,args)],'Tint FFDec '+str(args[0]))
        check('stage')
        ff('-xml2swf',HERE/'retained.xml',HERE/'serialized.swf')
        ff('-swf2xml',HERE/'serialized.swf',HERE/'serialized.xml')
        check('splice')
        ff('-swf2xml',HERE/'pfe.swf',HERE/'pfe.xml')
        check('audit')
        assert inputs=={p:a.sha(Path(p)) for p in inputs}
        assert a.sha(B.parents[2]/'pfe.swf')==a.HOST
        receipt=dict(version='scene-player-region-tint-2',base=a.HOST,baseXML=a.XML,target=a.TARGET,targets=a.TARGETS,
            productionCandidate=True,diagnosticOnly=False,performanceEligible=False,deployed=False,
            candidate=a.sha(HERE/'pfe.swf'),candidateXML=a.sha(HERE/'pfe.xml'),audit=a.sha(HERE/'semantic-audit.json'),
            sourceInputs=inputs,exactPredicateProof=a.sha(HERE/'predicate-proof.json'),sourceTransform='Player bypasses levit gate; all remaining ownership checks retained')
        (HERE/'build.json').write_text(json.dumps(receipt,indent=2),'utf-8')
        print(json.dumps(receipt),flush=True)
        lease.outcome='passed';lease.note='Exact two-method tint candidate built; runtime verification pending'

if __name__=='__main__':main()
