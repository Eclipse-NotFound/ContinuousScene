"""Frozen A/B native AIR validation of frame-local lazy threat building.

Uses the existing bounded CS compiler, ModLoader selection, registry, asset
copy helpers and owned private desktop. Never changes the installed product.
"""
from pathlib import Path
import argparse, ctypes, datetime, difflib, hashlib, importlib.util, json, os, re
import shutil, subprocess, sys, time, uuid
from contextlib import nullcontext

sys.dont_write_bytecode = True
MOD = Path(__file__).resolve().parents[1]
GAME = MOD.parents[1]
WORK = MOD / 'build/generated/proof-live-20261104-run03'
RUN = Path('D:/活/AI/测试运行/remains-proof-strategy-20261104/run-03')
sys.path.insert(0, str(GAME/'mods/ModLoader/tools'))
from test_registry import Registration
from air_test_process import HiddenProcess
import test_resources
import mod_debugger

def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p, obj):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(name,p):
    spec=importlib.util.spec_from_file_location(name,p)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def once(s,a,b):
    if s.count(a)!=1: raise ValueError('Anchor count '+str(s.count(a))+': '+a[:100])
    return s.replace(a,b)

def lazy(s):
    start=s.index('            var threats:Array=[];')
    end=s.index('            var deferred:Array=',start)
    block=s[start:end]
    s=s[:start]+'            var threats:Array=null;\n'+s[end:]
    s=once(s,'                    if(!inView)for each(var threat:Object in threats)',
       '                    if(!inView) {\n                        if(threats===null) {\n'+
       block.replace('var threats:Array=[];','threats=[];')+
       '                        }\n                        for each(var threat:Object in threats)')
    s=once(s,'                        }\n                }\n                var active:',
       '                        }\n                    }\n                }\n                var active:')
    return s

def measured(s,arm,diagnostic=False):
    s=once(s,'    import flash.utils.Dictionary;','    import flash.utils.Dictionary;\n    import flash.utils.getTimer;')
    s=once(s,'            var w:*=NativeSceneAdapter.host();',
       '            var proofStart:int=getTimer(),proofQ:int=0,proofBuilds:int=0;\n            var w:*=NativeSceneAdapter.host();')
    if diagnostic:
        s=once(s,'            var threats:Array=', '            ActivityEvidence.begin(loc,w,s);\n            var threats:Array=')
    if arm=='A':
        s=once(s,'            var threats:Array=[];','            var threats:Array=[];++proofBuilds;')
        s=once(s,'                    if(!inView)for each(var threat:Object in threats)',
           '                    if(!inView) {\n                        ++proofQ;'+('ActivityEvidence.boundary(loc);' if diagnostic else '')+'\n                        for each(var threat:Object in threats)')
        s=once(s,'                        }\n                }\n                var active:',
           '                        }\n                    }\n                }\n                var active:')
    else:
        s=once(s,'                    if(!inView) {','                    if(!inView) {\n                        ++proofQ;'+('ActivityEvidence.boundary(loc);' if diagnostic else ''))
        s=once(s,'            threats=[];','            threats=[];++proofBuilds;')
    s=once(s,'            return s.sleeping;',
       '            ActivityEvidence.record(getTimer()-proofStart,proofQ,proofBuilds,s,loc);\n            return s.sleeping;')
    if diagnostic:
        s=once(s,'        public static function sleeping(loc:*):Object {',
           '        public static function proofState(loc:*):Object {return rooms[loc];}\n        public static function sleeping(loc:*):Object {')
    return s

def compile_variant(tag,sources,entry,output,product):
    opt=load('proof_cs_compiler',MOD/'tools/stutter_opt.py');opt.WORK=WORK
    try:opt.compile_sources(tag,sources,entry,output,product)
    finally:
        for src,dst in [('build.json','.json'),('compiler.log','.txt')]:
            if (WORK/tag/src).exists():shutil.copy2(WORK/tag/src,RUN/'logs'/('build-'+tag+dst))

def driver_path(): return WORK/read(WORK/'driver-current.json')['tag']/'ProofActivityMod.swf'

def freeze_guard():
    """Bind later builds to verified frozen inputs after another task deploys."""
    baseline=read(WORK/'baseline.json')
    if (WORK/'baseline.original.json').exists():raise FileExistsError('Already rebound')
    frozen=WORK/'frozen-formal';frozen.mkdir()
    receipt={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'inputs':[]}
    guards={}
    for original,expected in baseline['formal'].items():
        original=Path(original);current=sha(original)
        source=original
        if current.upper()!=expected.upper():
            source=WORK/'runtime'/original.relative_to(GAME)
        if sha(source).upper()!=expected.upper():raise RuntimeError('No matching frozen input '+str(original))
        dest=frozen/original.relative_to(GAME);dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,dest)
        if sha(dest).upper()!=expected.upper():raise RuntimeError('Frozen copy mismatch')
        guards[str(dest)]=expected.upper()
        receipt['inputs'].append({'original':str(original),'expected':expected.lower(),'current':current,
                                 'frozen':str(dest),'matched':sha(dest)})
    shutil.copy2(WORK/'baseline.json',WORK/'baseline.original.json')
    baseline['formalAtStart']=baseline['formal'];baseline['formal']=guards
    write(WORK/'baseline.json',baseline);write(RUN/'inputs/formal-drift-and-frozen-build-guard.json',receipt)
    print(json.dumps(receipt,ensure_ascii=False),flush=True)

def pressure_snapshot():
    from ctypes import wintypes as W
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    def times():
        a,b,c=W.FILETIME(),W.FILETIME(),W.FILETIME()
        if not k.GetSystemTimes(ctypes.byref(a),ctypes.byref(b),ctypes.byref(c)):raise ctypes.WinError()
        return [(int(x.dwHighDateTime)<<32)|int(x.dwLowDateTime) for x in [a,b,c]]
    first=times();time.sleep(.4);last=times();d=[b-a for a,b in zip(first,last)]
    result={'cpuPercent':100*(1-d[0]/max(1,d[1]+d[2])),'cpuWindowSeconds':.4}
    command='Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine | Measure-Object -Property UtilizationPercentage -Maximum -Sum | ConvertTo-Json -Compress'
    try:
        proc=subprocess.run(['pwsh','-NoProfile','-Command',command],capture_output=True,text=True,encoding='utf-8',timeout=20,creationflags=subprocess.CREATE_NO_WINDOW)
        if proc.returncode:raise RuntimeError(proc.stderr)
        result['gpuEngines']=json.loads(proc.stdout)
    except Exception as e:result['gpuError']=str(e)
    return result

def build(tag):
    baseline=read(WORK/'baseline.json')
    baseline['formal']={p:h.upper() for p,h in baseline['formal'].items()}
    write(WORK/'baseline.json',baseline)
    if tag.startswith('driver'):
        sources={p.name:p.read_text(encoding='utf-8') for p in (MOD/'tests/proof_activity').glob('ProofActivity*.as')}
        compile_variant(tag,sources,'ProofActivityDoc.as','ProofActivityMod.swf',False)
        write(WORK/'driver-current.json',{'tag':tag});return
    arm=tag[0];assert arm in 'AB'
    sources={n:(WORK/'frozen'/n).read_text(encoding='utf-8-sig') for n in baseline['baselineSource']}
    core=sources['NativeSceneActivity.as']
    if arm=='B': core=lazy(core)
    pure=core
    if tag.endswith(('perf','diag')):
        diag=tag.endswith('diag');core=measured(core,arm,diag)
        sources['ActivityEvidence.as']=(MOD/'tests/proof_activity/ActivityEvidence.as').read_text(encoding='utf-8').replace('DIAGNOSTIC:Boolean=false','DIAGNOSTIC:Boolean='+str(diag).lower()).replace('ARM:String="?"','ARM:String="'+arm+'"')
        sources['ActivityFixture.as']=(MOD/'tests/proof_activity/ActivityFixture.as').read_text(encoding='utf-8')
        for dryarm in 'AB':
            dry=(WORK/'frozen/NativeSceneActivity.as').read_text(encoding='utf-8-sig')
            if dryarm=='B':dry=lazy(dry)
            dry=dry.replace('class NativeSceneActivity','class DryActivity'+dryarm).replace('NativeSceneAdapter','ActivityFixture')
            dry=dry.replace('if(!bulletClass)bulletClass=getDefinitionByName("fe.weapon.Bullet") as Class;','').replace('p is bulletClass','p.bullet')
            dry=once(dry,'        public static function update(loc:*):Object {','        public static var proofTrace:Array=[];\n        public static function update(loc:*):Object {\n            proofTrace=[];')
            dry=once(dry,'                var active:Boolean=', '                proofTrace.push([loc.units.indexOf(u),proximity,inView,threatened,alerted]);\n                var active:Boolean=')
            dry=once(dry,'                        deferred.push({u:u,r:r,d:ddx*ddx+ddy*ddy});','                        proofTrace.push(["defer",loc.units.indexOf(u)]);\n                        deferred.push({u:u,r:r,d:ddx*ddx+ddy*ddy});')
            extra='''        public static function proofState(loc:*):Object {return rooms[loc];}
        public static function proofSeed(loc:*,tick:int,rs:Array,sleep:Array):void {
            var state:Object={records:new Dictionary(true),sleeping:new Dictionary(true),tick:tick,awake:0,asleep:0,leashed:0};rooms[loc]=state;
            for(var i:int=0;i<loc.units.length;++i)if(loc.units[i]) {
                var r:Object=rs[i];if(r)state.records[loc.units[i]]={hp:r.hp,engaged:r.engaged,leashed:r.leashed,deadline:r.deadline,until:r.until,clips:[]};
                if(sleep[i])state.sleeping[loc.units[i]]=true;
            }
        }
'''
            dry=once(dry,'        public static function sleeping(loc:*):Object {',extra+'        public static function sleeping(loc:*):Object {')
            sources['DryActivity'+dryarm+'.as']=dry
        sources['ContinuousSceneMod.as']=once(sources['ContinuousSceneMod.as'],
           'activity:NativeSceneActivity.update,sleeping:NativeSceneActivity.sleeping,',
           'activity:NativeSceneActivity.update,sleeping:NativeSceneActivity.sleeping,\n                proofActivityStats:ActivityEvidence.snapshot,proofActivityReset:ActivityEvidence.reset,')
        sources['ContinuousSceneMod.as']=once(sources['ContinuousSceneMod.as'],'main.addChild(carrier); log("v"+VERSION+" loaded");',
           'main.addChild(carrier); log("v"+VERSION+" loaded proof-activity-'+tag+'");')
    sources['NativeSceneActivity.as']=core
    patch=''.join(difflib.unified_diff((WORK/'frozen/NativeSceneActivity.as').read_text(encoding='utf-8-sig').splitlines(True),pure.splitlines(True),fromfile='A/NativeSceneActivity.as',tofile='B/NativeSceneActivity.as'))
    if arm=='B': (RUN/'patches/lazy-threats.patch').write_text(patch,encoding='utf-8')
    compile_variant(tag,sources,'ContinuousSceneDoc.as','ContinuousSceneMod.swf',tag.endswith('plain'))

def prepare():
    root=WORK/'runtime'
    if root.exists(): raise FileExistsError(root)
    root.mkdir()
    inv=read(RUN/'inputs/inventory.json'); modes={'link':0,'copy':0}
    for folder in ['runtimes','Rooms','Music']:
        if (GAME/folder).is_dir():
            for k,v in mod_debugger.link_tree(GAME/folder,root/folder).items():modes[k]+=v
    for p in GAME.iterdir():
        if p.is_file() and (p.name in ['adl64.exe','pfe.swf','lang.xml','rooms.xml','pfe60.cfg','steam_appid.txt'] or re.match(r'^(text_.*\.xml|(sound|sprite|texture).*\.swf)$',p.name,re.I)):
            modes[mod_debugger.link_or_copy(p,root/p.name)]+=1
    for m in inv['mods']:
        if m['entry'] not in inv['selected']:continue
        src=GAME/'mods'/m['directory'];dst=root/'mods'/m['directory']
        if m['entry']=='RConnectMod' and read(src/'release/config.txt').get('autoRole') in ['host','join']:
            raise ValueError('Network auto role requires isolated dedicated configuration')
        for folder in ['release','config']:
            if (src/folder).is_dir(): mod_debugger.safe_tree(src/folder,dst/folder)
        if m['directory']=='LightAndDarkness' and (src/'atmosphere.json').exists():
            shutil.copy2(src/'atmosphere.json',dst/'atmosphere.json')
    host=root/'mods/ModLoader';host.mkdir(parents=True,exist_ok=True)
    for name in ['RemainsModLauncher.exe','RemainsModScanner.exe','supported-mods.txt']:
        shutil.copy2(GAME/'mods/ModLoader'/name,host/name)
    with (host/'supported-mods.txt').open('a',encoding='utf-8') as f:f.write('\nProofActivity|ProofActivityMod|1|0|0\n')
    rel=root/'mods/ProofActivity/release';rel.mkdir(parents=True)
    shutil.copy2(driver_path(),rel/'ProofActivityMod.swf')
    app=(GAME/'application.xml').read_text(encoding='utf-8-sig')
    app=re.sub(r'<id>[^<]+</id>','<id>pfe-proof-unstarted</id>',app)
    (root/'application.xml').write_text(app,encoding='utf-8')
    selection=json.loads(mod_debugger.launcher(root,'--only',','.join(inv['selected']+['ProofActivityMod']),'--json'))
    write(RUN/'inputs/selection.json',selection)
    write(WORK/'runtime-inputs.json',{'files':mod_debugger.file_hashes(root),'assets':modes})
    print(json.dumps({'prepared':str(root),'assets':modes,'selected':selection['selected']},ensure_ascii=False),flush=True)

def replace(src,dst):
    dst=Path(dst);tmp=dst.with_name(dst.name+'.'+uuid.uuid4().hex+'.new')
    shutil.copy2(src,tmp);os.replace(tmp,dst)

def run_trial(name,tag,scenario,seconds,diagnostic=False,warmup=20,registration=None,coexist=False):
    out=RUN/'data'/name
    if out.exists():raise FileExistsError(out)
    out.mkdir();root=WORK/'runtime'
    cfg={'name':name,'arm':tag[0],'scenario':scenario,'seconds':seconds,'warmup':warmup,'diagnostic':diagnostic,'seed':4077752896,
         'measurementClass':'functional-only' if diagnostic or coexist else 'timing-preflight-or-protocol'}
    lease=nullcontext(registration) if registration else Registration(owner='ContinuousScene / proof activity real validation',purpose=name,
       resource='game-coexist' if diagnostic or coexist else 'game',run_dir=root,evidence=out,wait=900)
    with lease as reg:
        print('ACQUIRED '+name,flush=True)
        before=test_resources.snapshot();before['pressure']=pressure_snapshot(); write(out/'environment-before.json',before)
        mem=before['memory']
        if mem['availableCommit']<4*1024**3 or mem['availablePhysical']<2*1024**3:
            raise RuntimeError('Insufficient fixture headroom')
        if before['air']['processes'] and not diagnostic and not coexist:raise RuntimeError('Other AIR present; no reliable performance run')
        immutable=read(WORK/'runtime-inputs.json')['files']
        mutable={'mods/ContinuousScene/release/ContinuousSceneMod.swf','mods/ProofActivity/release/ProofActivityMod.swf','application.xml','mods/loader-manifest.txt'}
        for p,h in immutable.items():
            if p not in mutable and sha(root/p).upper()!=h.upper():raise RuntimeError('Frozen runtime drift '+p)
        replace(WORK/tag/'ContinuousSceneMod.swf',root/'mods/ContinuousScene/release/ContinuousSceneMod.swf')
        replace(driver_path(),root/'mods/ProofActivity/release/ProofActivityMod.swf')
        app='pfe-proof-'+uuid.uuid4().hex
        descriptor=root/(name+'.xml')
        text=(root/'application.xml').read_text(encoding='utf-8')
        text=re.sub(r'<id>[^<]+</id>','<id>'+app+'</id>',text)
        descriptor.write_text(text,encoding='utf-8')
        write(root/'proof-controls.json',cfg)
        storage=Path(os.environ['APPDATA'])/app/'Local Store';storage.mkdir(parents=True)
        # Copy the frozen preference template only into this unique test store.
        template=WORK/'store-template'
        if template.exists():
            for p in template.iterdir():shutil.copy2(p,storage/p.name)
        prefs=read(storage/'ContinuousScene.preferences.json') if (storage/'ContinuousScene.preferences.json').exists() else {}
        prefs['nativeEnabled']=True
        write(storage/'ContinuousScene.preferences.json',prefs)
        cmd=[str(root/'adl64.exe'),'-runtime',str(root/'runtimes/air/win64'),str(descriptor)]
        proc=None;start=time.monotonic();code=None;failure=None
        meta={'config':cfg,'appId':app,'descriptor':str(descriptor),'command':cmd,'productSha256':sha(WORK/tag/'ContinuousSceneMod.swf'),'probeSha256':sha(driver_path()),'registration':str(getattr(reg,'id',''))}
        try:
            with (out/'stdout.txt').open('wb') as stdout,(out/'stderr.txt').open('wb') as stderr:
                reg.before_launch(name+' / '+app)
                proc=HiddenProcess(cmd,cwd=str(root),stdout=stdout,stderr=stderr)
                reg.child(proc.pid);meta['pid']=proc.pid;meta['desktop']=proc.desktop;meta['launch']=getattr(proc,'launch_info',None)
                meta['policy']=getattr(proc,'resource_info',getattr(proc,'resource_policy',None))
                write(out/'meta.json',meta)
                deadline=time.monotonic()+seconds+warmup+300
                while proc.poll() is None:
                    if time.monotonic()>deadline:raise RuntimeError('Owned test timed out')
                    memory=test_resources.MemoryStatus();memory.length=ctypes.sizeof(memory)
                    if not test_resources.kernel().GlobalMemoryStatusEx(ctypes.byref(memory)):raise ctypes.WinError()
                    if memory.availableCommit<512*1024**2:raise RuntimeError('Commit safety stop')
                    # Do not read the result while AIR is writing it; only poll own process.
                    time.sleep(5)
                code=proc.wait(30)
        except BaseException as e:
            failure=str(e)
            if proc is None:reg.launching=False
        finally:
            if proc is not None:
                if proc.poll() is None:proc.kill()
                proc.wait(30);reg.child_stopped();proc.close()
            meta.update(exitCode=code,failure=failure,wallSeconds=time.monotonic()-start)
            after=test_resources.snapshot();after['pressure']=pressure_snapshot();write(out/'environment-after.json',after)
            for filename in ['ProofActivity.json','ProofActivity.log','ContinuousScene.log','ModLoader.log','world-start.png','world-end.png']:
                if (storage/filename).exists():shutil.copy2(storage/filename,out/filename)
            meta['resultExists']=(out/'ProofActivity.json').exists();write(out/'meta.json',meta)
            result=read(out/'ProofActivity.json') if meta['resultExists'] else {}
            validity=[];loader=result.get('loader',{})
            wanted=set(read(RUN/'inputs/inventory.json')['selected']+['ProofActivityMod'])
            loaded={k[3:] for k in loader if k.startswith('ok_')}
            requested={k[10:] for k in loader if k.startswith('requested_')}
            if loaded!=wanted or requested!=wanted:validity.append('Runtime loader set differs from frozen selection')
            validity.extend(k+': '+str(v) for k,v in loader.items() if k.startswith('err_'))
            if result.get('audioVolume')!=0:validity.append('Mute not confirmed')
            if any(x.get('phase')==5 for x in result.get('focusEvents',[])):validity.append('Focus changed during measured frames')
            environment=test_resources.comparison_environment('coexist' if diagnostic or coexist else 'benchmark',before,after,meta.get('policy') or {})
            for endpoint in [before,after]:
                pressure=endpoint['pressure']
                if pressure.get('gpuError'):environment['reasons'].append('GPU pressure snapshot unavailable')
                if pressure['cpuPercent']>85 or (pressure.get('gpuEngines',{}).get('Maximum') or 0)>85:environment['reasons'].append('High host CPU/GPU pressure at endpoint')
            environment['performanceEligible']=not environment['reasons'] and not validity
            write(out/'validity.json',{'errors':validity,'environment':environment})
            ok=code==0 and result.get('ok') is True and not validity
            reg.outcome='passed' if ok else 'failed';reg.note='Behavior/probe validity only; performance judged separately. '+str(failure or '')
            print(json.dumps({'name':name,'ok':ok,'exit':code,'failure':failure,'result':str(out)},ensure_ascii=False),flush=True)
    if not ok:raise RuntimeError('Invalid trial '+name)
    return {'name':name,'ok':ok,'performanceEligible':environment['performanceEligible']}

def run_pair(name,scenario,order,seconds,warmup):
    """Reserve both adjacent runs so unrelated registered tests cannot split a pair."""
    log=RUN/'pairs'/(name+'.json')
    if log.exists():raise FileExistsError(log)
    record={'name':name,'scenario':scenario,'order':order,'seconds':seconds,'warmup':warmup,'runs':[]}
    write(log,record)
    with Registration(owner='ContinuousScene / proof activity real validation',purpose=name+' '+order,
       resource='game',run_dir=WORK/'runtime',evidence=log,wait=900) as reg:
        record['registration']=reg.id;write(log,record)
        try:
            for index,arm in enumerate(order):
                result=run_trial(name+'-'+str(index+1)+'-'+arm,arm+'-perf',scenario,seconds,False,warmup,reg)
                record['runs'].append(result);write(log,record)
                if not result['performanceEligible']:raise RuntimeError('Environment invalid; paired timing stopped')
            reg.outcome='passed';record['completed']=True
        except BaseException as e:
            record['error']=str(e);raise
        finally:write(log,record)

if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='action',required=True)
    b=sub.add_parser('build');b.add_argument('tag')
    sub.add_parser('prepare')
    sub.add_parser('freeze-inputs')
    r=sub.add_parser('run');r.add_argument('name');r.add_argument('tag');r.add_argument('scenario',choices=['move','fire','aim','diagnostic']);r.add_argument('--seconds',type=int,default=60);r.add_argument('--warmup',type=int,default=20);r.add_argument('--diagnostic',action='store_true')
    r.add_argument('--coexist',action='store_true',help='Functional/distribution observations only; never performance eligible')
    pair=sub.add_parser('pair');pair.add_argument('name');pair.add_argument('scenario',choices=['move','fire','aim']);pair.add_argument('order',choices=['AA','AB','BA']);pair.add_argument('--seconds',type=int,default=60);pair.add_argument('--warmup',type=int,default=20)
    a=p.parse_args()
    if a.action=='build':build(a.tag)
    elif a.action=='prepare':prepare()
    elif a.action=='freeze-inputs':freeze_guard()
    elif a.action=='pair':run_pair(a.name,a.scenario,a.order,a.seconds,a.warmup)
    else:run_trial(a.name,a.tag,a.scenario,a.seconds,a.diagnostic,a.warmup,coexist=a.coexist)
