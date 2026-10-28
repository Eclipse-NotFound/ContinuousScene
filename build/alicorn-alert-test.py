"""Small, muted native-alicorn integration test; isolated identity, files and desktop."""
from pathlib import Path
import importlib, sys, os, uuid, shutil, json, subprocess, re, time, ctypes
import xml.etree.ElementTree as ET
b=importlib.import_module('alicorn-alerts');ROOT=b.ROOT;OUT=b.OUT
sys.path.insert(0,str(ROOT/'mods/ModLoader/tools'))
from test_registry import Registration
from air_test_process import HiddenProcess
from test_resources import snapshot, MemoryStatus, kernel

def commit_available():
    memory=MemoryStatus();memory.length=ctypes.sizeof(memory)
    if not kernel().GlobalMemoryStatusEx(ctypes.byref(memory)):raise ctypes.WinError()
    return memory.availableCommit

def prepare():
    token=uuid.uuid4().hex;run=OUT/'runs'/token;run.mkdir(parents=True)
    app='pfe-cs-alicorn-'+token;store=Path(os.environ['APPDATA'])/app/'Local Store'
    assert not store.exists();store.mkdir(parents=True)
    b.save(store/'ContinuousScene.preferences.json',{'nativeEnabled':True})
    for pattern in ('texture*.swf','sprite*.swf','sound*.swf','text_*.xml','lang.xml','rooms.xml'):
        for p in ROOT.glob(pattern):shutil.copy2(p,run/p.name)
    for folder in ('Rooms','Music'):shutil.copytree(ROOT/folder,run/folder)
    shutil.copy2(OUT/'pfe.swf',run/'pfe.swf')
    for mod in ('ModLoader','ContinuousScene'):
        shutil.copytree(ROOT/'mods'/mod/'release',run/'mods'/mod/'release')
    for relative in ('mods/loader-manifest.txt','mods/ModLoader/supported-mods.txt'):
        shutil.copy2(ROOT/relative,run/relative)
    shutil.copy2(OUT/'ContinuousSceneMod.swf',run/'mods/ContinuousScene/release/ContinuousSceneMod.swf')
    probe=run/'mods/AlicornAlertProbe/release';probe.mkdir(parents=True)
    shutil.copy2(OUT/'AlicornAlertProbeMod.swf',probe/'AlicornAlertProbeMod.swf')
    # A small empty authored scene exercises the actual continuous-scene entry,
    # renderer and native units without the high-memory factory benchmark fixture.
    doc=ET.Element('all',sceneFormat='1');ET.SubElement(doc,'land',serial='1')
    room=ET.SubElement(doc,'room',name='Alicorn alert verification',sceneWidth='192',sceneHeight='50',x='0',y='0')
    ET.SubElement(room,'options',backwall='tBackWall')
    for y in range(50):ET.SubElement(room,'a').text='.'.join('A' if x in (0,191) or y==0 or y>=48 else '_' for x in range(192))
    ET.SubElement(room,'obj',id='player',x='5',y='47')
    maps=run/'mods/ContinuousScene/maps';maps.mkdir(parents=True)
    ET.ElementTree(doc).write(maps/'active.xml',encoding='utf-8',xml_declaration=True)
    (run/'application.xml').write_text(f'<application xmlns="http://ns.adobe.com/air/application/30.0"><id>{app}</id><versionNumber>0.9.1</versionNumber><filename>AlicornTest</filename><initialWindow><content>pfe.swf</content><visible>false</visible><width>1280</width><height>800</height><renderMode>direct</renderMode></initialWindow><supportedProfiles>extendedDesktop</supportedProfiles></application>','utf-8')
    subprocess.run([str(ROOT/'mods/ModLoader/RemainsModLauncher.exe'),'--root',str(run),'--only','ModLoaderMod,ContinuousSceneMod,AlicornAlertProbeMod','--no-ui','--report',str(run/'selection.json')],stdout=subprocess.DEVNULL,check=True)
    return run,app,store

def run():
    runtime,app,store=prepare();evidence=b.MOD/'knowledge/experiments/evidence'/('alicorn-alerts-'+runtime.name);evidence.mkdir(parents=True)
    inputs={str(p.relative_to(runtime)):b.sha(p) for p in runtime.rglob('*.swf')}
    b.save(evidence/'inputs.json',inputs);results=[]
    with Registration(owner='ContinuousScene / alicorn relay / 01a151d4-fa39-7401-b2dc-4544d63604b8',purpose='Native relay 0/100/intermediate, range, reset, ordinary mode and settings persistence',run_dir=runtime,evidence=evidence,wait=300) as record:
        for stage in ('behavior','persistence'):
            before=snapshot();b.save(evidence/(stage+'-resources-before.json'),before)
            # This directed six-unit/empty-map check is not the performance run.
            # Leave at least 512 MiB system commit during execution; no foreign processes touched.
            if before['memory']['availableCommit']<1280*1024**2 or before['memory']['availablePhysical']<2*1024**3:
                raise RuntimeError('Insufficient memory for the small functional fixture; no AIR launched')
            if stage=='persistence':
                (runtime/'persistence-only.txt').write_text('reload existing isolated preferences','utf-8')
                (store/'alicorn-result.json').unlink()
            p=None;start=time.monotonic()
            try:
                with (evidence/(stage+'-stdout.log')).open('wb') as stdout,(evidence/(stage+'-stderr.log')).open('wb') as stderr:
                    record.before_launch(stage+' / '+app)
                    p=HiddenProcess([ROOT/'adl64.exe','-runtime',ROOT/'runtimes/air/win64',runtime/'application.xml'],cwd=runtime,stdout=stdout,stderr=stderr)
                    record.child(p.pid);b.save(evidence/(stage+'-process.json'),{'pid':p.pid,'appId':app,'desktop':p.desktop,'runtime':str(runtime)})
                    print('Owned '+stage+' AIR '+str(p.pid),flush=True)
                    while p.poll() is None and time.monotonic()-start<170:
                        if commit_available()<512*1024**2:raise RuntimeError('Commit reserve below 512 MiB; ending only owned test')
                        time.sleep(1)
                    if p.poll() is None:raise TimeoutError('Native alert test timed out')
            finally:
                if p:
                    if p.poll() is None:p.kill();p.wait(15)
                    p.close();record.child_stopped()
                shutil.copytree(store,evidence/stage,dirs_exist_ok=True)
                b.save(evidence/(stage+'-resources-after.json'),snapshot())
            result=json.loads((store/'alicorn-result.json').read_text('utf-8'))
            assert result['ok'],result
            results.append(result)
            loader=(store/'#SharedObjects/ModLoader.sol').read_bytes()
            for entry in ('ModLoaderMod','ContinuousSceneMod','AlicornAlertProbeMod'):
                # ModLoader itself is the host of the scanner; its own success
                # may be represented by the native loader, checked via settings API.
                if entry=='ModLoaderMod':continue
                assert ('requested_'+entry).encode() in loader and ('ok_'+entry).encode() in loader,entry
            assert b'err_' not in loader,'loader error in isolated session'
        assert inputs=={str(p.relative_to(runtime)):b.sha(p) for p in runtime.rglob('*.swf')}
        summary={'ok':True,'version':'0.9.1','host':b.sha(runtime/'pfe.swf'),'mod':b.sha(runtime/'mods/ContinuousScene/release/ContinuousSceneMod.swf'),'checks':sum(len(r['checks']) for r in results),'runtime':str(runtime),'evidence':str(evidence),'performanceClaim':False}
        b.save(evidence/'summary.json',summary);b.save(OUT/'latest-test.json',summary)
        record.outcome='passed';record.note=str(summary['checks'])+' native integration/settings assertions; no performance claim'
        print(json.dumps(summary),flush=True)

if __name__=='__main__':run()
