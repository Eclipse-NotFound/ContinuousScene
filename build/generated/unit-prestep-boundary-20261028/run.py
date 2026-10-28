from pathlib import Path
import argparse, hashlib, importlib.util, json, shutil, sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()
def main():
    p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--host',type=Path);p.add_argument('--fixed',action='store_true');p.add_argument('--rounds',type=int,default=0);a=p.parse_args()
    assert all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in a.name) and 0<=a.rounds<=6
    m=load('boundary_motion',HERE.parents[1]/'motion-test.py')
    silence=load('boundary_silence',HERE.parent/'camera-live-current-silent-20261028/silence.py')
    build=json.loads((HERE/'probe-build.json').read_text());assert build['compiled']
    assert build['inputs']=={s:sha(s) for s in build['inputs']} and sha(HERE/'ContinuousSceneMotionMod.swf')==build['outputSHA256']
    record=dict(name=a.name,host=None,probe=build['outputSHA256'],plan=dict(expectError=not a.fixed,rounds=a.rounds),diagnosticOnly=True)
    evidence=HERE.parents[2]/'knowledge/experiments/evidence'/a.name
    production={str(p):sha(p) for p in (ROOT/'pfe.swf',ROOT/'mods/ContinuousScene/release/ContinuousSceneMod.swf')}
    assert production[str(ROOT/'pfe.swf')]=='4E5FAB45D6F5A2634C83BE5E7EAF387443F9FB4E56B945CD2BF54880F1F73C75'
    with m.Registration(owner='ContinuousScene / Unit.run load failure / 01a13816',purpose=a.name,run_dir=m.RUNTIME,evidence=evidence,wait=300) as lease:
        original=m.HiddenProcess
        plan=m.RUNTIME/'unit-boundary-plan.json'
        try:
            assert m.memory_status()['availableCommit']>=4*1024**3
            m.prepare();shutil.copy2(HERE/'ContinuousSceneMotionMod.swf',m.RUNTIME/'mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf')
            if a.host:shutil.copy2(a.host,m.RUNTIME/'pfe.swf')
            record['host']=sha(m.RUNTIME/'pfe.swf');plan.write_text(json.dumps(record['plan']),'utf-8')
            def start(*args,**kwargs):
                try:
                    record['silence']=silence.seed(args[0][-1],m.RUNTIME)
                    assert m.memory_status()['availableCommit']>=4*1024**3
                except BaseException:
                    lease.child_stopped();raise
                return original(*args,**kwargs)
            m.HiddenProcess=start
            m.run_owned(m.parse_args(['--name',a.name,'--profile']),lease)
            assert production=={s:sha(s) for s in production}
        finally:
            m.HiddenProcess=original
            plan.unlink(missing_ok=True)
            if evidence.exists():(evidence/'boundary-inputs.json').write_text(json.dumps(record,indent=2),'utf-8')
if __name__=='__main__':main()
