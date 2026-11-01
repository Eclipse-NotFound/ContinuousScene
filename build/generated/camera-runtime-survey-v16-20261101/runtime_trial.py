"""Compare installed AIR with the already-local SDK runtime in isolated copies.

No installation, ACL change, descriptor renderer change, or shared-tool edit.
The exact owned process's loaded AIR DLL is checked, not inferred from -runtime.
"""
from pathlib import Path
import argparse,ctypes as c,hashlib,importlib.util,json,shutil,sys
from ctypes import wintypes as W
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
SOURCE=HERE.parent/'camera-static-groups-v15-20261101'
SDK=ROOT/'mods/Sandevistan/build/tools/airsdk'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
def load(name,p):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def version(p):
    v=c.WinDLL('version',use_last_error=True)
    v.GetFileVersionInfoSizeW.argtypes=[W.LPCWSTR,c.POINTER(W.DWORD)];v.GetFileVersionInfoSizeW.restype=W.DWORD
    v.GetFileVersionInfoW.argtypes=[W.LPCWSTR,W.DWORD,W.DWORD,W.LPVOID]
    v.VerQueryValueW.argtypes=[W.LPVOID,W.LPCWSTR,c.POINTER(W.LPVOID),c.POINTER(W.UINT)]
    size=v.GetFileVersionInfoSizeW(str(p),None);assert size
    data=c.create_string_buffer(size);assert v.GetFileVersionInfoW(str(p),0,size,data)
    ptr=W.LPVOID();length=W.UINT();assert v.VerQueryValueW(data,'\\',c.byref(ptr),c.byref(length))
    fields=c.cast(ptr,c.POINTER(W.DWORD));assert fields[0]==0xFEEF04BD
    return '.'.join(map(str,(fields[2]>>16,fields[2]&65535,fields[3]>>16,fields[3]&65535)))
def loaded_air(process):
    p=c.WinDLL('psapi',use_last_error=True)
    p.EnumProcessModulesEx.argtypes=[W.HANDLE,W.LPVOID,W.DWORD,c.POINTER(W.DWORD),W.DWORD]
    p.GetModuleFileNameExW.argtypes=[W.HANDLE,W.HMODULE,W.LPWSTR,W.DWORD]
    array=(W.HMODULE*1024)();needed=W.DWORD()
    if not p.EnumProcessModulesEx(process._process,array,c.sizeof(array),c.byref(needed),3):raise c.WinError(c.get_last_error())
    assert needed.value<=c.sizeof(array)
    for module in array[:needed.value//c.sizeof(W.HMODULE)]:
        name=c.create_unicode_buffer(32768)
        if p.GetModuleFileNameExW(process._process,module,name,len(name)):
            path=Path(name.value)
            if path.name.lower()=='adobe air.dll':return path.resolve()
    return None
def prepare():
    receipt=json.loads((SOURCE/'build.json').read_text('utf-8'))
    for name,expected in receipt['sources'].items():
        origin=SOURCE/name;assert sha(origin)==expected
        target=HERE/name
        if target.exists():assert sha(target)==expected
        else:shutil.copy2(origin,target)
    for name in ('build.json','ContinuousSceneMotionMod.swf'):
        target=HERE/name
        if target.exists():assert sha(target)==sha(SOURCE/name)
        else:shutil.copy2(SOURCE/name,target)
    assert sha(HERE/'ContinuousSceneMotionMod.swf')==receipt['probe']
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--name',required=True);parser.add_argument('--engine',choices=['installed','sdk'],required=True);parser.add_argument('--large',action='store_true');args=parser.parse_args()
    prepare();work=load('runtime_survey_work',HERE/'work.py');original_load=work.load
    executable=SDK/'bin/adl64.exe' if args.engine=='sdk' else ROOT/'adl64.exe'
    runtime=SDK/'runtimes/air/win64' if args.engine=='sdk' else ROOT/'runtimes/air/win64'
    expected_dll=(runtime/'Adobe AIR/Versions/1.0/Adobe AIR.dll').resolve()
    record={'engine':args.engine,'driver':sha(Path(__file__)),'probe':sha(HERE/'ContinuousSceneMotionMod.swf'),'deployed':False,'loadedVerified':False}
    def load_hook(name,path):
        m=original_load(name,path)
        if name=='motion_review':
            native=m.HiddenProcess;cpu=m.cpu_owned
            def start(command,**kwargs):
                command=list(command)
                assert Path(command[0])==ROOT/'adl64.exe' and command[1]=='-runtime'
                command[0]=executable;command[2]=runtime
                paths=[executable,*sorted(p for p in runtime.rglob('*') if p.is_file())]
                record.update(command=[str(p) for p in command],executableVersion=version(executable),dllVersion=version(expected_dll),files={str(p):sha(p) for p in paths})
                return native(command,**kwargs)
            def sample(process,elapsed):
                result=cpu(process,elapsed)
                if elapsed>=3 and not record['loadedVerified']:
                    actual=loaded_air(process)
                    if actual:
                        assert actual==expected_dll,(actual,expected_dll)
                        record.update(loadedVerified=True,loadedDLL=str(actual),loadedSHA256=sha(actual),verifiedAtSeconds=elapsed,launchInfo=process.launch_info)
                return result
            m.HiddenProcess=start;m.cpu_owned=sample
        return m
    work.load=load_hook
    parameters=argparse.Namespace(name=args.name,small=not args.large,layers=False,legacy_menu=False,native_presentation=False,host='current')
    try:
        work.run(parameters)
        assert record['loadedVerified'],'No owned-process runtime identity proof'
        assert record['files']=={p:sha(p) for p in record['files']},'Runtime files changed'
        record['ok']=True
    except BaseException as e:record.update(ok=False,error=repr(e));raise
    finally:
        destination=ROOT/'mods/ContinuousScene/knowledge/experiments/evidence'/args.name
        if not destination.exists():destination=HERE
        with (destination/(args.name+'-engine.json')).open('x',encoding='utf-8') as f:json.dump(record,f,ensure_ascii=False,indent=2)
    print(json.dumps({'runtimeVerified':record['loadedVerified'],'version':record['dllVersion']}))
if __name__=='__main__':main()
