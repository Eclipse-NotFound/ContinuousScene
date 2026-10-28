from pathlib import Path
import hashlib, importlib.util, json, subprocess, sys, time
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
sys.path.insert(0,str(ROOT/'mods/ModLoader/tools'))
from test_registry import Registration
spec=importlib.util.spec_from_file_location('boundary_motion',HERE.parents[1]/'motion-test.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
def main():
    assert not (HERE/'probe-build.json').exists()
    old=HERE.parent/'camera-tail-sampling-20261028'
    config=(old/'compiler.xml').read_text().replace(str(old).replace('\\','/'),str(HERE).replace('\\','/'))
    (HERE/'compiler.xml').write_text(config,'utf-8')
    command=json.loads((old/'compile-command.json').read_text())
    command=[x.replace(str(old).replace('\\','/'),str(HERE).replace('\\','/')).replace('ContinuousSceneTailSamplerMod.swf','ContinuousSceneMotionMod.swf').replace('TailSamplerDoc.as','ProbeDoc.as') for x in command]
    inputs={str(HERE/p):sha(HERE/p) for p in ('build_probe.py','ContinuousSceneMotionMod.as','ProbeDoc.as','compiler.xml')}
    record=dict(command=command,inputs=inputs,compiled=False)
    with Registration(owner='ContinuousScene / Unit.run load failure / 01a13816',purpose='Compile native boundary reproduction',run_dir=HERE,evidence=HERE,wait=300) as lease:
        memory=m.memory_status();assert memory['availableCommit']>=2*1024**3
        process=None
        try:
            with (HERE/'compiler.log').open('xb') as log:
                lease.before_launch('Owned Java compiler, heap 512MiB')
                process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                lease.child(process.pid);start=time.monotonic()
                while process.poll() is None:
                    assert time.monotonic()-start<180 and m.memory_status()['availableCommit']>=512*1024**2
                    try:process.wait(.25)
                    except subprocess.TimeoutExpired:pass
                assert process.returncode==0,'Compiler failed'
            assert inputs=={p:sha(p) for p in inputs}
            record.update(compiled=True,outputSHA256=sha(HERE/'ContinuousSceneMotionMod.swf'))
            lease.outcome='passed';lease.note='Probe compiled; not runtime verified'
        finally:
            if process:
                if process.poll() is None:process.kill();process.wait(15)
                lease.child_stopped()
            (HERE/'probe-build.json').write_text(json.dumps(record,indent=2),'utf-8')
    print(json.dumps(record))
if __name__=='__main__':main()
