"""Current-product review; unique copy, desktop, app ID and storage per owned run."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, os, shutil, subprocess, sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
sys.path.insert(0, str(ROOT / 'mods/ModLoader/tools'))
from test_registry import Registration
from test_resources import snapshot

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()
def write(path, data):
    with Path(path).open('x', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2)

def build():
    old = ROOT / 'mods/ContinuousScene/build/generated/camera-local-phase-mask7-platform-camera-20261029'
    shutil.copy2(old / 'CameraProbePlatform.as', HERE / 'CameraProbePlatform.as')
    (HERE / 'ProbeDoc.as').write_text('package { import flash.display.Sprite; public class ProbeDoc extends Sprite { public function ProbeDoc(){ ContinuousSceneMotionMod; } } }', 'utf-8')
    flex = ROOT / 'mods/Sandevistan/build/tools/flexsdk'
    config = '<flex-config><target-player>32.0</target-player><compiler><external-library-path><path-element>'+str(ROOT/'mods/Sandevistan/build/tools/airsdk/frameworks/libs/air/airglobal.swc').replace('\\','/')+'</path-element></external-library-path><source-path><path-element>'+str(HERE).replace('\\','/')+'</path-element></source-path><debug>false</debug><optimize>true</optimize><theme/></compiler></flex-config>'
    (HERE/'compiler.xml').write_text(config,'utf-8')
    formal = [ROOT/'pfe.swf', *[ROOT/'mods'/name/'release'/(mod+'.swf') for name,mod in [('ContinuousScene','ContinuousSceneMod'),('RealisticVision','RealisticVisionMod'),('WallBlend','WallBlendMod'),('ModLoader','ModLoaderMod'),('RConnect','RConnectMod'),('TDFC','TDFCMod')]]]
    sources = {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*') if p.suffix in ('.as','.py','.xml')}
    command = ['D:/Program Files/Adobe Animate 2024/jre/bin/java.exe','-Xmx512m','-Dfile.encoding=UTF-8','-jar',str(flex/'lib/mxmlc.jar'),'+flexlib='+str(flex/'frameworks'),'-load-config='+str(HERE/'compiler.xml'),'-swf-version=32','-static-link-runtime-shared-libraries=true','-output='+str(HERE/'ContinuousSceneMotionMod.swf'),'-link-report='+str(HERE/'link.xml'),str(HERE/'ProbeDoc.as')]
    with Registration(owner='ContinuousScene / quality and dense enemy evaluation / 01a13816',purpose='Compile bounded diagnostic',resource='game',run_dir=HERE,evidence=HERE,wait=900) as lease:
        with (HERE/'compiler.log').open('xb') as log:
            lease.before_launch('512 MiB Java compiler')
            p=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);lease.child(p.pid)
            try: code=p.wait(180)
            finally:
                if p.poll() is None:p.kill();p.wait(15)
                lease.child_stopped()
            if code:raise RuntimeError('Compile failed; see compiler.log')
        receipt={'sources':sources,'formal':{str(p.relative_to(ROOT)):sha(p) for p in formal},'probe':sha(HERE/'ContinuousSceneMotionMod.swf'),'command':command}
        write(HERE/'build.json',receipt);lease.outcome='passed';lease.note='Diagnostic compiled; no product modification'
    print(json.dumps({'compiled':True,'probe':receipt['probe']}))

def run(args):
    receipt=json.loads((HERE/'build.json').read_text('utf-8'))
    assert receipt['formal']=={p:sha(ROOT/p) for p in receipt['formal']}, 'Formal package changed'
    assert receipt['probe']==sha(HERE/'ContinuousSceneMotionMod.swf')
    assert receipt['sources']=={p:sha(HERE/p) for p in receipt['sources']}, 'Probe source changed'
    runtime=HERE/('runtime-'+args.name)
    evidence=ROOT/'mods/ContinuousScene/knowledge/experiments/evidence'/args.name
    if runtime.exists() or evidence.exists():raise FileExistsError('Use new evidence/run name')
    motion=load('motion_review',ROOT/'mods/ContinuousScene/build/motion-test.py')
    silence=load('silence_review',ROOT/'mods/ContinuousScene/build/generated/camera-live-current-silent-20261028/silence.py')
    silence.RUNTIME=runtime  # Keep the helper's exact-root check bound to this unique copy.
    motion.RUNTIME=runtime
    with Registration(owner='ContinuousScene / quality and dense enemy evaluation / 01a13816',purpose=args.name,resource='game',run_dir=runtime,evidence=evidence,wait=900) as lease:
        before=snapshot();memory=motion.memory_status()
        if memory['availableCommit']<4*1024**3 or memory['availablePhysical']<2*1024**3:raise RuntimeError('Memory preflight')
        if motion.air_pids():raise RuntimeError('Other AIR present; untouched')
        runtime.mkdir()
        # Copy only reusable assets, not another run's controls, descriptors or storage.
        old=ROOT/'mods/ContinuousScene/build/runtime'
        for p in old.iterdir():
            if p.is_file() and (p.name in ['application.xml','lang.xml'] or p.suffix=='.swf' and p.name!='pfe.swf' or p.name.startswith('text_') and p.suffix=='.xml'):shutil.copy2(p,runtime/p.name)
        for folder in ['Music','Rooms']:shutil.copytree(old/folder,runtime/folder)
        placeholder=runtime/'mods/ContinuousSceneProbe/release/ContinuousSceneProbe.swf'
        placeholder.parent.mkdir(parents=True);shutil.copy2(HERE/'ContinuousSceneMotionMod.swf',placeholder)
        motion.prepare()
        shutil.copy2(HERE/'ContinuousSceneMotionMod.swf',runtime/'mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf')
        candidate=ROOT/'pfe_before_unitvis_20261101-004531.swf'
        expected='9D8662F6CF80E0AD20741EC2A4E7BEAD68446269EBB0ADB641C876DB68698B1D'
        if args.host=='guard':
            candidate=HERE.parent/'camera-turret-guard-r2-20261101/candidate.swf'
            expected=json.loads((candidate.parent/'build.json').read_text('utf-8'))['candidateSHA256']
        assert sha(candidate)==expected
        shutil.copy2(candidate,runtime/'pfe.swf')
        descriptor=runtime/'application.xml'
        original_descriptor=descriptor.read_text('utf-8-sig')
        assert '<allowLowQuality>' not in original_descriptor
        revised_descriptor=original_descriptor.replace('http://ns.adobe.com/air/application/30.0','http://ns.adobe.com/air/application/51.1')
        assert revised_descriptor!=original_descriptor
        revised_descriptor=revised_descriptor.replace('</initialWindow>','<allowLowQuality>true</allowLowQuality></initialWindow>')
        descriptor.write_text(revised_descriptor,'utf-8')
        options={'defaultWindow':args.small,'layers':args.layers,'legacyMenu':args.legacy_menu,'nativePresentation':args.native_presentation,'dense':args.dense}
        write(runtime/'review-controls.json',options)
        original=motion.HiddenProcess
        def start(*a,**kw):
            memory=motion.memory_status()
            if memory['availableCommit']<4*1024**3 or memory['availablePhysical']<2*1024**3:
                lease.child_stopped();raise RuntimeError('Memory gate before launch')
            try:silence.seed(a[0][-1],runtime)
            except BaseException:
                lease.child_stopped();raise
            return original(*a,**kw)
        motion.HiddenProcess=start
        width,height=(1280,720) if args.small else (1920,1080)
        settings=motion.parse_args(['--name',args.name,'--profile','--high-qos','--window-width',str(width),'--window-height',str(height)])
        try:motion.run_owned(settings,lease)
        finally:
            if evidence.exists():write(evidence/'review-inputs.json',{'recipe':receipt,'host':sha(runtime/'pfe.swf'),'options':options,'environmentBefore':before,'environmentAfter':snapshot()})

def player_log():
    f=load('recorder_review',ROOT/'mods/ModLoader/tools/frame_recorder.py')
    destination=HERE/'player-recording'
    if destination.exists():raise FileExistsError(destination)
    shutil.copytree(f.default_log_dir(),destination)
    recording,warnings=f.read_recording(destination)
    write(HERE/'player-recording-summary.json',f.summarize(recording,warnings))
    print(json.dumps({'samples':len(recording['samples']),'source':str(f.default_log_dir()),'files':{p.name:sha(p) for p in destination.iterdir() if p.is_file()}}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['build','run','player-log']);p.add_argument('--name');p.add_argument('--small',action='store_true');p.add_argument('--dense',action='store_true');p.add_argument('--layers',action='store_true');p.add_argument('--legacy-menu',action='store_true');p.add_argument('--native-presentation',action='store_true');p.add_argument('--host',choices=['current','guard'],default='current');a=p.parse_args()
    if a.action=='build':build()
    elif a.action=='player-log':player_log()
    else:run(a)
