"""Finish the already-spliced candidate after the 4 GiB commit precheck stop."""
from pathlib import Path
import importlib.util
import json
import subprocess
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
B=HERE.parents[3]
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def main():
    a=load('tint_resume_audit',HERE/'audit.py');e=load('tint_resume_support',B/'enemy-speed.py')
    paths=[HERE/n for n in ('build.py','audit.py','resume.py')]+[B/n for n in ('enemy-speed.py','motion-test.py','profile-vision.py',
        'bullet-segments-audit.py','stationary-threat-audit.py','native-crop-audit.py')]
    inputs={str(p):a.sha(p) for p in paths}
    assert not (HERE/'build.json').exists()
    prior=json.loads((HERE/'splice.json').read_text('utf-8'))
    assert prior['base']==a.HOST and prior['candidate']==a.sha(HERE/'pfe.swf') and prior['targets']==a.TARGETS
    frozen={n:a.sha(HERE/n) for n in ('retained.xml','serialized.swf','serialized.xml','pfe.swf','splice.json','predicate-proof.json')}
    with e.motion.Registration(owner='ContinuousScene / tint candidate final export',purpose='Resume memory-gated export and exact audit; no AIR',
            run_dir=HERE,evidence=HERE/'build.json',wait=600) as lease:
        assert not e.motion.air_pids() and a.sha(B.parents[2]/'pfe.swf')==a.HOST
        memory=e.motion.memory_status()
        assert memory['availableCommit']>=4*1024**3 and memory['availablePhysical']>=2*1024**3,memory
        assert frozen=={n:a.sha(HERE/n) for n in frozen}
        provenance=dict(reason='Initial build stopped before final export: availableCommit 4204359680 < 4 GiB; existing candidate retained',
            capturedAfterMemoryStop=True,sourceInputs=inputs,frozenOutputs=frozen,memoryBefore=memory)
        (HERE/'resume-provenance.json').write_text(json.dumps(provenance,indent=2),'utf-8')
        def child(command,label):
            process=None;lease.before_launch(label)
            try:
                process=subprocess.Popen(command);lease.child(process.pid);code=process.wait()
                if code:raise subprocess.CalledProcessError(code,command)
            finally:
                if process is not None:
                    if process.poll() is None:process.kill();process.wait(timeout=15)
                    lease.child_stopped()
        child([str(e.JAVA),'-Xmx512m','-jar',str(e.TOOLS/'ffdec/ffdec-cli.jar'),'-swf2xml',str(HERE/'pfe.swf'),str(HERE/'pfe.xml')],'Tint final exact export')
        child([sys.executable,'-B',str(HERE/'audit.py'),'audit'],'Tint final exact audit')
        assert inputs=={p:a.sha(Path(p)) for p in inputs} and frozen=={n:a.sha(HERE/n) for n in frozen}
        assert a.sha(B.parents[2]/'pfe.swf')==a.HOST
        receipt=dict(version='scene-player-region-tint-2',base=a.HOST,baseXML=a.XML,target=a.TARGET,targets=a.TARGETS,
            productionCandidate=True,diagnosticOnly=False,performanceEligible=False,deployed=False,
            candidate=a.sha(HERE/'pfe.swf'),candidateXML=a.sha(HERE/'pfe.xml'),audit=a.sha(HERE/'semantic-audit.json'),
            sourceInputs=inputs,exactPredicateProof=a.sha(HERE/'predicate-proof.json'),resumeProvenance=a.sha(HERE/'resume-provenance.json'))
        (HERE/'build.json').write_text(json.dumps(receipt,indent=2),'utf-8')
        print(json.dumps(receipt),flush=True);lease.outcome='passed';lease.note='Two-method tint candidate exact export/audit complete; runtime pending'

if __name__=='__main__':main()
