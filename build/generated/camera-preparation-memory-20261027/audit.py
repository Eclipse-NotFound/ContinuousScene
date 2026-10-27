"""Measure this runner's memory across existing preparation; no compile or AIR."""
from pathlib import Path
import argparse,ctypes,importlib.util,json,traceback,gc,time
from ctypes import wintypes as W
HERE=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('preparation_memory_runner',HERE.parent/'camera-visible-room-fog-history-20261027/run.py')
run=importlib.util.module_from_spec(sp);sp.loader.exec_module(run)
class Counters(ctypes.Structure):
    _fields_=[('cb',W.DWORD),('PageFaultCount',W.DWORD)]+[(n,ctypes.c_size_t) for n in ['PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage','PrivateUsage']]
k=ctypes.WinDLL('kernel32',use_last_error=True);ps=ctypes.WinDLL('psapi',use_last_error=True)
k.GetCurrentProcess.restype=W.HANDLE
ps.GetProcessMemoryInfo.argtypes=[W.HANDLE,ctypes.POINTER(Counters),W.DWORD];ps.GetProcessMemoryInfo.restype=W.BOOL

def snapshot(name):
    c=Counters();c.cb=ctypes.sizeof(c)
    if not ps.GetProcessMemoryInfo(k.GetCurrentProcess(),ctypes.byref(c),c.cb):raise ctypes.WinError(ctypes.get_last_error())
    return dict(stage=name,at=time.monotonic(),system=run.m.memory_status(),
        own={n:getattr(c,n) for n in ['WorkingSetSize','PeakWorkingSetSize','PrivateUsage','PeakPagefileUsage']})

def main():
    p=argparse.ArgumentParser();p.add_argument('--name',required=True);args=p.parse_args()
    assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
    out=HERE/(args.name+'.json');assert not out.exists()
    record=dict(stages=[],airStarted=False,compilerStarted=False,formalUnchanged=False,passed=False)
    with run.m.Registration(owner='ContinuousScene / preparation memory / 01a13816',purpose=args.name,
            run_dir=run.m.RUNTIME,evidence=out,resource='game',wait=60) as lease:
        try:
            assert not run.m.air_pids()
            run.control.memory_gate();record['stages'].append(snapshot('before-inputs'))
            baseline=run.r.baseline();record['stages'].append(snapshot('after-baseline'))
            scripts=run.runner_inputs();record['stages'].append(snapshot('after-runner-inputs'))
            compiler=run.support.compiler_inputs();fixture=run.fixture_inputs();runtime=run.reference.runtime_inputs()
            record['stages'].append(snapshot('after-fixture-inputs'))
            path=HERE.parent/'camera-visible-room-fog-history-20261027/probe-builds/probe-source/614be80bce8f45bbaff44c1d41d4d900/probe-build.json'
            probe=run.verify_probe(path,baseline,scripts,compiler,fixture)
            record['probeSHA256']=probe['probeSHA256'];record['stages'].append(snapshot('after-probe-verification'))
            # Existing launcher only prepares the shared isolated copy. No game,
            # compiler or foreign process is started or terminated by this audit.
            run.m.prepare();record['stages'].append(snapshot('after-runtime-prepare'))
            for key,digest in baseline.items():
                if key not in ('application.xml','mods/loader-manifest.txt'):assert run.r.sha(run.m.RUNTIME/key)==digest,key
            assert baseline==run.r.baseline() and scripts==run.runner_inputs() and runtime==run.reference.runtime_inputs()
            record['stages'].append(snapshot('after-input-recheck'))
            gc.collect();record['stages'].append(snapshot('after-python-gc'))
            record.update(passed=True,formalUnchanged=True,formalCount=len(baseline),runtimeCount=len(runtime))
            lease.outcome='passed';lease.note='Preparation memory observed; no compiler or AIR; not a game performance test'
        except BaseException as error:
            record.update(error=repr(error),traceback=traceback.format_exc())
            lease.outcome='failed';lease.note=repr(error);raise
        finally:
            out.write_text(json.dumps(record,ensure_ascii=False,indent=2),'utf-8')
            print(json.dumps(dict(passed=record['passed'],stages=record['stages'],airStarted=False),ensure_ascii=False))
if __name__=='__main__':main()
