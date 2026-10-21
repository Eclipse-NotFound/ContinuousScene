"""Current-byte isolated motion test on a private desktop; never edits pfe storage."""
from pathlib import Path
import argparse, ctypes, hashlib, json, os, re, shutil, subprocess, sys, time, uuid
from ctypes import wintypes as W
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[2]
RUNTIME=BASE/'runtime'
sys.path.insert(0,str(ROOT/'mods/ModLoader/tools'))
from air_test_process import HiddenProcess
from test_registry import Registration

def memory_status():
    class Memory(ctypes.Structure):
        _fields_=[('length',W.DWORD),('load',W.DWORD)]+[(name,ctypes.c_ulonglong) for name in
            ('totalPhysical','availablePhysical','totalCommit','availableCommit','totalVirtual','availableVirtual','extended')]
    value=Memory();value.length=ctypes.sizeof(value)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(value)):raise ctypes.WinError()
    return {key:getattr(value,key) for key in ('load','availablePhysical','availableCommit')}

def responsive_owned(process):
    class State(ctypes.Structure):
        _fields_=[('version',W.DWORD),('control',W.DWORD),('state',W.DWORD)]
    k=process.k
    k.GetProcessInformation.argtypes=[W.HANDLE,ctypes.c_int,ctypes.c_void_p,W.DWORD]
    k.SetProcessInformation.argtypes=[W.HANDLE,ctypes.c_int,ctypes.c_void_p,W.DWORD]
    before=State(1,0,0)
    if not k.GetProcessInformation(process._process,4,ctypes.byref(before),ctypes.sizeof(before)):raise ctypes.WinError()
    after=State(1,before.control|1,before.state&~1)
    if not k.SetProcessInformation(process._process,4,ctypes.byref(after),ctypes.sizeof(after)):raise ctypes.WinError()
    actual=State(1,0,0)
    if not k.GetProcessInformation(process._process,4,ctypes.byref(actual),ctypes.sizeof(actual)):raise ctypes.WinError()
    assert actual.control&1 and not actual.state&1
    return {'before':[before.control,before.state],'applied':[actual.control,actual.state]}

def air_pids():
    k=ctypes.WinDLL('kernel32',use_last_error=True);p=ctypes.WinDLL('psapi',use_last_error=True)
    k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE
    k.QueryFullProcessImageNameW.argtypes=[W.HANDLE,W.DWORD,W.LPWSTR,ctypes.POINTER(W.DWORD)]
    k.CloseHandle.argtypes=[W.HANDLE]
    ids=(W.DWORD*16384)();size=W.DWORD()
    if not p.EnumProcesses(ids,ctypes.sizeof(ids),ctypes.byref(size)):raise ctypes.WinError()
    result=[]
    for pid in ids[:size.value//4]:
        h=k.OpenProcess(0x1000,False,pid)
        if not h:continue
        try:
            buf=ctypes.create_unicode_buffer(32768);n=W.DWORD(len(buf))
            if k.QueryFullProcessImageNameW(h,0,buf,ctypes.byref(n)) and Path(buf.value).name.lower()=='adl64.exe':result.append(pid)
        finally:k.CloseHandle(h)
    return result

def hashes():
    paths=[RUNTIME/'pfe.swf',RUNTIME/'mods/loader-manifest.txt',RUNTIME/'mods/LightAndDarkness/atmosphere.json']
    for line in (RUNTIME/'mods/loader-manifest.txt').read_text(encoding='utf-8-sig').splitlines():
        f=line.split('|')
        if len(f)==5 and f[2]=='1':
            directory=RUNTIME/'mods'/f[0]
            paths.append(directory/'release'/(f[1]+'.swf'))
            for folder in ('release','config'):
                paths.extend(p for p in (directory/folder).rglob('*') if p.is_file() and p.suffix!='.swf')
    paths.extend(p for p in (RUNTIME/'scene.xml',RUNTIME/'application.xml') if p.exists())
    return {str(p.relative_to(RUNTIME)):hashlib.sha256(p.read_bytes()).hexdigest().upper() for p in paths}

def prepare(excluded=()):
    if air_pids():raise RuntimeError('Existing AIR; do not mutate test input')
    inventory=subprocess.run([str(ROOT/'mods/ModLoader/RemainsModLauncher.exe'),'--list','--json','--no-ui'],capture_output=True,check=True)
    data=json.loads(inventory.stdout.decode('utf-8-sig'))
    shutil.copy2(ROOT/'pfe.swf',RUNTIME/'pfe.swf')
    shutil.copy2(ROOT/'mods/loader-manifest.txt',RUNTIME/'mods/loader-manifest.txt')
    for m in data['mods']:
        if not m['enabled']:continue
        src=ROOT/'mods'/m['directory'];dst=RUNTIME/'mods'/m['directory']
        for folder in ('release','config'):
            if (src/folder).is_dir():shutil.copytree(src/folder,dst/folder,dirs_exist_ok=True)
        if m['directory']=='LightAndDarkness':shutil.copy2(src/'atmosphere.json',dst/'atmosphere.json')
    shutil.copy2(ROOT/'mods/ModLoader/supported-mods.txt',RUNTIME/'mods/ModLoader/supported-mods.txt')
    with (RUNTIME/'mods/ModLoader/supported-mods.txt').open('a',encoding='utf-8') as catalog:
        catalog.write('\nContinuousSceneMotion|ContinuousSceneMotionMod|1|0|0\n')
    motion=RUNTIME/'mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf'
    motion.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(RUNTIME/'mods/ContinuousSceneProbe/release/ContinuousSceneProbe.swf',motion)
    report=BASE/'generated'/('motion-selection-'+uuid.uuid4().hex+'.json')
    selection=subprocess.run([str(ROOT/'mods/ModLoader/RemainsModLauncher.exe'),'--root',str(RUNTIME),'--only',','.join([name for name in data['selected'] if name not in excluded]+['ContinuousSceneMotionMod']),'--no-ui','--report',str(report)],capture_output=True)
    if selection.returncode:raise RuntimeError(repr(selection.stderr))
    print(json.dumps({'prepared':True,'inputFiles':len(hashes())}))

def run_owned(args,record):
    import msvcrt
    if not args.name or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name):raise ValueError('Evidence name')
    out=BASE.parent/'knowledge/experiments/evidence'/args.name
    if out.exists():raise FileExistsError(out)
    if air_pids():raise RuntimeError('Performance requires no other AIR; untouched')
    memory=memory_status()
    required=(5 if args.suite in ('experience','factory') else 3)*1024**3
    if memory['availableCommit']<required or memory['availablePhysical']<1.5*1024**3:
        raise RuntimeError('Insufficient memory for this single-instance fixture: '+json.dumps(memory))
    out.mkdir();app='pfe-modsettings-continuous-motion-'+uuid.uuid4().hex
    descriptor=RUNTIME/(app+'.xml')
    descriptor_text=(RUNTIME/'application.xml').read_text(encoding='utf-8-sig').replace('<id>pfe-modsettings-continuous-scene</id>','<id>'+app+'</id>')
    if getattr(args,'window_width',0)>0:
        descriptor_text=re.sub(r'<width>\d+</width>','<width>'+str(args.window_width)+'</width>',descriptor_text)
        descriptor_text=re.sub(r'<height>\d+</height>','<height>'+str(args.window_height)+'</height>',descriptor_text)
    descriptor.write_text(descriptor_text,encoding='utf-8')
    cfg={'visual':args.visual,'short':args.short,'expectNoSigns':args.expect_no_signs,'stage':args.stage,'vision':args.vision,'lightingCheck':args.lighting_check,'noLighting':args.no_lighting,'culling':args.culling,'profile':args.profile}
    cfg['rasterCheck']=args.raster_check
    cfg['wallCheck']=args.wall_check
    cfg['benchmark']=args.benchmark
    cfg['noWall']=args.no_wall
    cfg['fogCheck']=args.fog_check
    cfg['fogPerf']=getattr(args,'fog_perf',False)
    cfg['drawControl']=getattr(args,'draw_control',None)
    cfg['bulletSegments']=getattr(args,'bullet_segments',False)
    cfg['blitVerify']=getattr(args,'blit_verify',False)
    cfg['renderPerf']=getattr(args,'render_perf',False)
    cfg['threatCheck']=getattr(args,'threat_check',False)
    cfg['presentationCheck']=getattr(args,'presentation_check',False)
    cfg['satsCheck']=getattr(args,'sats_check',False)
    cfg['impactCheck']=getattr(args,'impact_check',False)
    cfg['impactABBA']=getattr(args,'impact_abba',False)
    cfg['fogABBA']=args.fog_abba
    cfg['fogTypedABBA']=getattr(args,'fog_typed_abba',False)
    cfg['land']=args.land
    cfg['suite']=args.suite
    cfg['syncWarm']=args.sync_warm
    cfg['encounter']=getattr(args,'encounter',False)
    cfg['fixedEnemies']=getattr(args,'fixed_enemies',False)
    cfg['localEnemies']=getattr(args,'local_enemies',False)
    cfg['speed']=getattr(args,'speed',8)
    cfg['windowWidth']=getattr(args,'window_width',0)
    cfg['windowHeight']=getattr(args,'window_height',0)
    suite_flags=[]
    if args.suite:
        if list(RUNTIME.glob('*.flag')):raise RuntimeError('Stale controls must be reviewed before suite')
        if args.suite in ('experience','factory','upcoming'):
            shutil.copy2(RUNTIME/'scene-factory.xml',RUNTIME/'scene.xml')
        if args.suite=='upcoming':suite_flags=['load-native.flag','user-vision-controls.flag']
        if args.suite=='mechanics':suite_flags=['mechanics-controls.flag','user-vision-controls.flag']
        if args.suite=='combat':
            suite_flags=['combat-controls.flag']
            if args.benchmark=='normal':suite_flags.append('native-rooms-controls.flag')
            if not args.vision:suite_flags.append('user-vision-controls.flag')
        for name in suite_flags:(RUNTIME/name).write_text('isolated motion regression','utf-8')
    flag=RUNTIME/'motion-controls.json';inputs=hashes();store=Path(os.environ['APPDATA'])/app/'Local Store'
    lock=open(RUNTIME/'session.lock','a+b');lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    flag.write_text(json.dumps(cfg),encoding='utf-8')
    policy={'appId':app,'desktopPolicy':'private','performanceEligible':not (args.visual or args.lighting_check or args.profile or args.raster_check or args.wall_check or args.fog_check or getattr(args,'fog_perf',False) or getattr(args,'render_perf',False) or getattr(args,'threat_check',False) or getattr(args,'presentation_check',False) or getattr(args,'bullet_segments',False) or args.suite),'otherAirProcessIds':[]}
    policy['memoryBefore']=memory;policy['minimumAvailableCommit']=memory['availableCommit']
    if getattr(args,'sats_check',False):policy['performanceEligible']=False
    if getattr(args,'impact_check',False):policy['performanceEligible']=False
    if getattr(args,'blit_verify',False):policy['performanceEligible']=False
    if getattr(args,'draw_control',None) in ('world','fog','objects','objectgroups','effects','sleepclips','implicitpause','mousetree'):
        policy['performanceEligible']=False
        policy['diagnosticOnly']='Rendering intentionally hidden for attribution'
    if getattr(args,'draw_control',None)=='sleepclips':
        policy['diagnosticOnly']='Read-only sleeping timeline census; no timing acceptance'
    if getattr(args,'draw_control',None)=='implicitpause':
        policy['diagnosticOnly']='Only observed implicit sleeping timelines paused for attribution; production lifecycle not implemented'
    if getattr(args,'draw_control',None)=='mousetree':
        policy['diagnosticOnly']='World display mouse hit testing disabled for attribution; input compatibility not accepted'
    process=None
    try:
        with open(out/'stdout.log','wb') as stdout,open(out/'stderr.log','wb') as stderr:
            record.before_launch(app+' / '+args.name)
            process=HiddenProcess([ROOT/'adl64.exe','-runtime',ROOT/'runtimes/air/win64',descriptor],cwd=RUNTIME,stdout=stdout,stderr=stderr)
            record.child(process.pid)
            if args.high_qos:policy['powerPolicy']=responsive_owned(process)
            policy.update(pid=process.pid,desktop=process.desktop);print('Owned AIR '+str(process.pid),flush=True)
            start=time.monotonic()
            while process.poll() is None and time.monotonic()-start<600:
                time.sleep(1)
                current=memory_status();policy['minimumAvailableCommit']=min(policy['minimumAvailableCommit'],current['availableCommit'])
                if current['availableCommit']<512*1024**2:
                    policy['performanceEligible']=False;policy['memoryAbort']=current
                    raise RuntimeError('Memory pressure; stopped only owned test')
                others=[p for p in air_pids() if p!=process.pid]
                if others:
                    policy['otherAirProcessIds']=others;policy['performanceEligible']=False
                    raise RuntimeError('Other AIR appeared; do not use timing')
            if process.poll() is None:raise TimeoutError('Owned test timed out')
    except BaseException as error:
        policy['performanceEligible']=False
        policy['runFailure']=type(error).__name__+': '+str(error)
        raise
    finally:
        if process:
            if process.poll() is None:process.kill();process.wait(15)
            process.close()
            record.child_stopped()
        if store.exists():shutil.copytree(store,out/'storage')
        (out/'inputs.json').write_text(json.dumps(inputs,indent=2),encoding='utf-8')
        (out/'process-policy.json').write_text(json.dumps(policy,indent=2),encoding='utf-8')
        flag.unlink(missing_ok=True);descriptor.unlink(missing_ok=True)
        for name in suite_flags:(RUNTIME/name).unlink(missing_ok=True)
        lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1);lock.close()
    assert hashes()==inputs,'Test input changed'
    loader=(out/'storage/#SharedObjects/ModLoader.sol').read_bytes()
    sessions=set(re.findall(rb'run_\d+_\d+',loader))
    selected=[]
    for line in (RUNTIME/'mods/loader-manifest.txt').read_text(encoding='utf-8-sig').splitlines():
        fields=line.split('|')
        if len(fields)==5 and fields[2]=='1':selected.append(fields[1])
    loaded={name:('ok_'+name).encode() in loader and ('requested_'+name).encode() in loader for name in selected}
    (out/'loader-check.json').write_text(json.dumps({'sessions':[s.decode() for s in sessions],'loaded':loaded},indent=2),'utf-8')
    assert len(sessions)==1 and all(loaded.values()) and b'err_' not in loader,'Current session loader failed'
    result=json.loads((out/'storage/result.json').read_text(encoding='utf-8-sig'))
    print(json.dumps({'ok':result['ok'],'entryMs':result.get('entryMs'),'internalSigns':result.get('internalSigns'),'samples':len(result.get('samples',[])),'checks':len(result.get('assertions',[])),'error':result.get('error')}))
    if not result['ok']:raise RuntimeError('Probe failed')
    record.outcome='passed'
    record.note='Current loader, unchanged inputs and scene assertions passed; timing conclusions require result review'

def run(args):
    with Registration(owner='ContinuousScene / enemy and high-speed motion / 01a13816-367b-7261-8e11-ca9152565dd9',
                      purpose=args.name or 'motion probe',run_dir=RUNTIME,
                      evidence=BASE.parent/'knowledge/experiments/evidence'/str(args.name),wait=args.registry_wait) as record:
        if args.refresh:prepare()
        run_owned(args,record)

def parse_args(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');p.add_argument('--name');p.add_argument('--visual',action='store_true');p.add_argument('--short',action='store_true');p.add_argument('--expect-no-signs',action='store_true');p.add_argument('--lighting-check',action='store_true');p.add_argument('--no-lighting',action='store_true');p.add_argument('--culling',action='store_true');p.add_argument('--profile',action='store_true');p.add_argument('--raster-check',action='store_true');p.add_argument('--wall-check',action='store_true');p.add_argument('--benchmark',choices=['normal','scene']);p.add_argument('--no-wall',action='store_true');p.add_argument('--high-qos',action='store_true');p.add_argument('--sync-warm',action='store_true');p.add_argument('--suite',choices=['native','experience','factory','upcoming','mechanics','combat']);p.add_argument('--stage',type=int,default=1);p.add_argument('--vision',action='store_true')
    p.add_argument('--fog-check',action='store_true');p.add_argument('--fog-abba',action='store_true')
    p.add_argument('--fog-typed-abba',action='store_true')
    p.add_argument('--fog-perf',action='store_true')
    p.add_argument('--draw-control',choices=['world','fog','objects','objectgroups','effects','sleepclips','implicitpause','mousetree','tilecrop','fogpixels','atlas','nativecrop','stationary','objectviewport','unitblit'])
    p.add_argument('--render-perf',action='store_true')
    p.add_argument('--threat-check',action='store_true')
    p.add_argument('--presentation-check',action='store_true')
    p.add_argument('--bullet-segments',action='store_true')
    p.add_argument('--blit-verify',action='store_true')
    p.add_argument('--sats-check',action='store_true')
    p.add_argument('--impact-check',action='store_true')
    p.add_argument('--impact-abba',action='store_true')
    p.add_argument('--land',choices=['random_mane','random_plant'],default='random_mane')
    p.add_argument('--encounter',action='store_true')
    p.add_argument('--fixed-enemies',action='store_true')
    p.add_argument('--local-enemies',action='store_true')
    p.add_argument('--speed',type=float,default=8);p.add_argument('--window-width',type=int,default=0);p.add_argument('--window-height',type=int,default=0)
    p.add_argument('--refresh',action='store_true');p.add_argument('--registry-wait',type=int,default=30)
    return p.parse_args(argv)

if __name__=='__main__':
    a=parse_args()
    prepare() if a.prepare else run(a)
