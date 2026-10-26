"""Build an isolated diagnostic host; preserve every formal input and raw asset."""
from pathlib import Path
import importlib.util
import json
import subprocess
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
B=HERE.parents[1]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj

def main():
    a=load('scroll_host_patch',HERE/'host_patch.py')
    e=load('scroll_host_build_support',B/'enemy-speed.py')
    paths=[HERE/'inspect_host.py',HERE/'host_patch.py',Path(__file__),B/'enemy-speed.py',B/'motion-test.py',
        B/'profile-vision.py',B/'bullet-segments-audit.py',B/'stationary-threat-audit.py',B/'native-crop-audit.py',
        a.BASE/'pfe.swf',a.BASE/'pfe.xml']
    inputs={str(p):a.sha(p) for p in paths}
    with e.motion.Registration(owner='ContinuousScene / native scroll diagnostic build / 01a13816',
            purpose='A796 Camera.calc two world setter guards only; no AIR or deployment',run_dir=HERE,evidence=HERE/'host-build.json',wait=60) as lease:
        assert not e.motion.air_pids(), 'Other AIR remains untouched'
        assert not (HERE/'host-build.json').exists() and not (HERE/'pfe.swf').exists()
        def child(command,label):
            process=None;lease.before_launch(label)
            try:
                process=subprocess.Popen(command);lease.child(process.pid);status=process.wait()
                if status:raise subprocess.CalledProcessError(status,command)
            finally:
                if process is not None:
                    if process.poll() is None:process.kill();process.wait(timeout=15)
                    lease.child_stopped()
        def check(step):child([sys.executable,'-B',str(HERE/'host_patch.py'),step],'Exact camera proof '+step)
        def ff(*args):
            assert not e.motion.air_pids() and a.sha(B.parents[2]/'pfe.swf')==a.HOST
            memory=e.motion.memory_status()
            assert memory['availableCommit']>=4*1024**3 and memory['availablePhysical']>=2*1024**3,memory
            child([str(e.JAVA),'-Xmx512m','-jar',str(e.TOOLS/'ffdec/ffdec-cli.jar'),*map(str,args)],'Native scroll FFDec '+str(args[0]))
        check('stage')
        ff('-xml2swf',HERE/'retained.xml',HERE/'serialized.swf')
        ff('-swf2xml',HERE/'serialized.swf',HERE/'serialized.xml')
        check('splice')
        ff('-swf2xml',HERE/'pfe.swf',HERE/'pfe.xml')
        check('audit')
        assert inputs=={p:a.sha(Path(p)) for p in inputs}
        assert a.sha(B.parents[2]/'pfe.swf')==a.HOST
        receipt=dict(version='camera-world-scroll-native-host-1',base=a.HOST,baseXML=a.XML,candidate=a.sha(HERE/'pfe.swf'),
            candidateXML=a.sha(HERE/'pfe.xml'),audit=a.sha(HERE/'audit-proof.json'),sourceInputs=inputs,
            diagnosticOnly=True,performanceEligible=False,deployed=False)
        (HERE/'host-build.json').write_text(json.dumps(receipt,indent=2),'utf-8')
        lease.outcome='passed';lease.note='Exact two world setter guards built; runtime test pending, no deployment'
        print(json.dumps(receipt),flush=True)

if __name__=='__main__':main()
