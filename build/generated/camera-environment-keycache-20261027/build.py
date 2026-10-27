"""Registered isolated candidate build; no installed files are written."""
from pathlib import Path
import importlib.util,json,subprocess,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;B=HERE.parents[1]
def load(name,p):
    sp=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
def main():
    a=load('environment_candidate_audit',HERE/'audit.py');e=load('environment_candidate_support',B/'enemy-speed.py')
    paths=[HERE/'build.py',HERE/'audit.py',HERE/'README.md',HERE/'source-equivalent.as.inc',HERE.parent/'camera-environment-clamp-20261027/audit.py',B/'enemy-speed.py',B/'motion-test.py',B/'bullet-segments-audit.py',B/'stationary-threat-audit.py',B/'native-crop-audit.py']
    fixture=load('environment_current_inputs',HERE.parent/'camera-visible-allocation-stacks-20261027/run.py')
    paths.extend([e.JAVA,e.TOOLS/'ffdec/ffdec-cli.jar'])
    inputs=dict(fixture.runner_inputs(),**{str(p):a.sha(p) for p in paths});formal=fixture.r.baseline()
    with e.motion.Registration(owner='ContinuousScene / environment allocation / 01a13816',purpose='A796 cached cell key in sceneNativeEnvironment; isolated build only',run_dir=HERE,evidence=HERE/'build.json',wait=300) as lease:
        assert not e.motion.air_pids()
        assert a.sha(B.parents[2]/'pfe.swf')==a.HOST and not (HERE/'pfe.swf').exists()
        def child(command,label):
            process=None;lease.before_launch(label)
            try:
                process=subprocess.Popen(command);lease.child(process.pid);code=process.wait()
                if code:raise subprocess.CalledProcessError(code,command)
            finally:
                if process is not None:
                    if process.poll() is None:process.kill();process.wait(timeout=15)
                    lease.child_stopped()
        def check(step):child([sys.executable,'-B',str(HERE/'audit.py'),step],'Exact method audit '+step)
        def ff(*args):
            memory=e.motion.memory_status();assert memory['availableCommit']>=4*1024**3 and memory['availablePhysical']>=2*1024**3,memory
            assert not e.motion.air_pids() and a.sha(B.parents[2]/'pfe.swf')==a.HOST
            child([str(e.JAVA),'-Xmx512m','-jar',str(e.TOOLS/'ffdec/ffdec-cli.jar'),*map(str,args)],'Environment method FFDec '+str(args[0]))
        check('stage');ff('-xml2swf',HERE/'retained.xml',HERE/'serialized.swf')
        ff('-swf2xml',HERE/'serialized.swf',HERE/'serialized.xml');check('splice')
        ff('-swf2xml',HERE/'pfe.swf',HERE/'pfe.xml');check('audit')
        assert inputs=={p:a.sha(Path(p)) for p in inputs} and formal==fixture.r.baseline()
        result=dict(version='scene-environment-keycache-1',base=a.HOST,candidate=a.sha(HERE/'pfe.swf'),
            audit=a.sha(HERE/'audit-proof.json'),sourceInputs=inputs,deployed=False,runtimeVerified=False)
        out=HERE/'build.json';assert not out.exists();out.write_text(json.dumps(result,indent=2),'utf-8')
        lease.outcome='passed';lease.note='Exact method-only build; runtime and performance pending'
        print(json.dumps({k:v for k,v in result.items() if k!='sourceInputs'}),flush=True)
if __name__=='__main__':main()
