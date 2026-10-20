"""Isolated authoring/game runs using the shared AIR test registration."""
from pathlib import Path
import importlib.util,sys,subprocess,shutil,json,os,time,uuid,argparse,ctypes,re
from ctypes import wintypes as W
spec=importlib.util.spec_from_file_location('builder',Path(__file__).with_name('large-map.py'));b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
ROOT=b.ROOT;MOD=b.MOD;OUT=b.OUT
def responsive_owned(process):
    class State(ctypes.Structure):_fields_=[('version',W.DWORD),('control',W.DWORD),('state',W.DWORD)]
    k=process.k;k.GetProcessInformation.argtypes=[W.HANDLE,ctypes.c_int,ctypes.c_void_p,W.DWORD];k.SetProcessInformation.argtypes=[W.HANDLE,ctypes.c_int,ctypes.c_void_p,W.DWORD]
    value=State(1,0,0)
    if not k.GetProcessInformation(process._process,4,ctypes.byref(value),ctypes.sizeof(value)):raise ctypes.WinError()
    value.control|=1;value.state&=~1
    if not k.SetProcessInformation(process._process,4,ctypes.byref(value),ctypes.sizeof(value)):raise ctypes.WinError()
def make_runtime(kind,installed):
    run=OUT/('runs/'+kind+'-'+uuid.uuid4().hex[:12]);run.mkdir(parents=True)
    app='pfe-cs-authoring-'+uuid.uuid4().hex
    content='LargeEditorHarness.swf' if kind=='editor' else 'pfe.swf'
    (run/'application.xml').write_text(f'''<application xmlns="http://ns.adobe.com/air/application/30.0"><id>{app}</id><versionNumber>0.9.0</versionNumber><filename>SingleSceneTest</filename><initialWindow><content>{content}</content><visible>false</visible><width>{1800 if kind=='editor' else 1280}</width><height>{950 if kind=='editor' else 800}</height><renderMode>direct</renderMode></initialWindow><supportedProfiles>extendedDesktop</supportedProfiles></application>''',encoding='utf-8')
    for pattern in ('texture*.swf','sprite*.swf','sound*.swf','text_*.xml','lang.xml','rooms.xml','pfe.swf'):
        for f in ROOT.glob(pattern):shutil.copy2(f,run/f.name)
    for folder in ('Rooms','Music','Editor/Resources'):
        shutil.copytree(ROOT/folder,run/folder)
    (run/'Editor/Enhancements').mkdir(parents=True)
    for name in ('EditorTools.swf','NativeScene.swf'):
        src=OUT/name if name=='EditorTools.swf' and not installed else ROOT/'Editor/Enhancements'/name
        shutil.copy2(src,run/'Editor/Enhancements'/name)
    shutil.copy2(ROOT/'Editor.swf' if installed else OUT/'Editor.swf',run/'Editor.swf')
    maps=run/'mods/ContinuousScene/maps';maps.mkdir(parents=True)
    shutil.copy2(MOD/'maps/factory-rd.xml',maps/'factory-rd.xml')
    if kind=='editor':
        shutil.copy2(OUT/'LargeEditorHarness.swf',run/'LargeEditorHarness.swf');content='LargeEditorHarness.swf'
    else:
        launcher=ROOT/'mods/ModLoader/RemainsModLauncher.exe'
        inv=json.loads(subprocess.run([str(launcher),'--list','--json','--no-ui'],capture_output=True,check=True).stdout.decode('utf-8-sig'))
        for m in inv['mods']:
            if not m['enabled']:continue
            src=ROOT/'mods'/m['directory'];dst=run/'mods'/m['directory']
            for folder in ('release','config'):
                if (src/folder).exists():shutil.copytree(src/folder,dst/folder,dirs_exist_ok=True)
            if (src/'atmosphere.json').exists():shutil.copy2(src/'atmosphere.json',dst/'atmosphere.json')
        for rel in ('mods/loader-manifest.txt','mods/ModLoader/supported-mods.txt'):shutil.copy2(ROOT/rel,run/rel)
        probe=run/'mods/SingleSceneProbe/release';probe.mkdir(parents=True);shutil.copy2(OUT/'SingleSceneProbeMod.swf',probe/'SingleSceneProbeMod.swf')
        if not installed:shutil.copy2(OUT/'ContinuousSceneMod.swf',run/'mods/ContinuousScene/release/ContinuousSceneMod.swf')
        shutil.copy2(maps/'factory-rd.xml',maps/'active.xml')
        subprocess.run([str(launcher),'--root',str(run),'--only',','.join(inv['selected']+['SingleSceneProbeMod']),'--no-ui','--report',str(run/'selection.json')],capture_output=True,check=True)
        b.save(run/'inventory.json',inv);content='pfe.swf'
    return run,app
def run(kind,installed,rebuild=False):
    runtime,app=make_runtime(kind,installed);evidence=MOD/'knowledge/experiments/evidence'/runtime.name;evidence.mkdir()
    store=Path(os.environ['APPDATA'])/app/'Local Store';p=None
    inputs={str(f.relative_to(runtime)):b.sha(f) for f in runtime.rglob('*.swf')}
    with b.Registration(owner='ContinuousScene / 单一大地图与编辑器 / 01a151d4-fa39-7401-b2dc-4544d63604b8',purpose=kind+' authoring integration',run_dir=runtime,evidence=evidence,wait=1800) as record:
        try:
            if rebuild:
                assert not installed;b.build()
                shutil.copy2(OUT/'Editor.swf',runtime/'Editor.swf');shutil.copy2(OUT/'EditorTools.swf',runtime/'Editor/Enhancements/EditorTools.swf')
                if kind=='game':shutil.copy2(OUT/'ContinuousSceneMod.swf',runtime/'mods/ContinuousScene/release/ContinuousSceneMod.swf')
            # Compile inside the test reservation to avoid disrupting another performance run.
            if kind=='editor':b.compile('LargeEditorHarness.as',MOD/'src/tests',OUT/'LargeEditorHarness.swf');shutil.copy2(OUT/'LargeEditorHarness.swf',runtime/'LargeEditorHarness.swf')
            else:b.compile('SingleSceneProbeDoc.as',MOD/'src/tests',OUT/'SingleSceneProbeMod.swf');shutil.copy2(OUT/'SingleSceneProbeMod.swf',runtime/'mods/SingleSceneProbe/release/SingleSceneProbeMod.swf')
            inputs={str(f.relative_to(runtime)):b.sha(f) for f in runtime.rglob('*.swf')}
            with (evidence/'stdout.log').open('wb') as stdout,(evidence/'stderr.log').open('wb') as stderr:
                record.before_launch(app)
                p=b.HiddenProcess([ROOT/'adl64.exe','-runtime',ROOT/'runtimes/air/win64',runtime/'application.xml'],cwd=runtime,stdout=stdout,stderr=stderr)
                record.child(p.pid);responsive_owned(p);b.save(evidence/'process.json',{'appId':app,'pid':p.pid,'desktop':p.desktop,'runtime':str(runtime),'installed':installed});print('Owned AIR '+str(p.pid),flush=True)
                start=time.monotonic()
                while p.poll() is None and time.monotonic()-start<240:time.sleep(1)
                if p.poll() is None:raise TimeoutError('Authoring test timeout')
        finally:
            if p:
                if p.poll() is None:p.kill();p.wait(15)
                p.close();record.child_stopped()
            if store.exists():shutil.copytree(store,evidence/'storage')
            b.save(evidence/'inputs.json',inputs)
        result=json.loads((evidence/'storage'/f'{kind}-result.json').read_text(encoding='utf-8'))
        if not result['ok']:raise RuntimeError(json.dumps(result,ensure_ascii=False))
        if kind=='game':
            loader=(evidence/'storage/#SharedObjects/ModLoader.sol').read_bytes();sessions=set(re.findall(rb'run_\d+_\d+',loader))
            selected=[line.split('|')[1] for line in (runtime/'mods/loader-manifest.txt').read_text(encoding='utf-8-sig').splitlines() if len(line.split('|'))==5 and line.split('|')[2]=='1']
            loaded={n:('requested_'+n).encode() in loader and ('ok_'+n).encode() in loader for n in selected}
            b.save(evidence/'loader-check.json',{'sessions':[s.decode() for s in sessions],'loaded':loaded})
            assert len(sessions)==1 and all(loaded.values()) and b'err_' not in loader,'Actual current-session loader failure'
        b.save(evidence/'sample.json',{'sha256':b.sha(MOD/'maps/factory-rd.xml')})
        assert inputs=={str(f.relative_to(runtime)):b.sha(f) for f in runtime.rglob('*.swf')},'SWF inputs changed'
        record.outcome='passed';record.note=f"{len(result['checks'])} authoring assertions; see report for scope"
        print(str(evidence),flush=True);print(json.dumps({'ok':True,'checks':len(result['checks'])}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('kind',choices=['compile','editor','game']);p.add_argument('--installed',action='store_true');p.add_argument('--rebuild',action='store_true');args=p.parse_args()
    if args.kind=='compile':
        b.compile('LargeEditorHarness.as',MOD/'src/tests',OUT/'LargeEditorHarness.swf')
        if (MOD/'src/tests/SingleSceneProbeDoc.as').exists():b.compile('SingleSceneProbeDoc.as',MOD/'src/tests',OUT/'SingleSceneProbeMod.swf')
    else:run(args.kind,args.installed,args.rebuild)
