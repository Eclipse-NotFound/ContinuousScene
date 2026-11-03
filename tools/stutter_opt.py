"""Build isolated stutter candidates/probes. Formal files are read-only here."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,shutil,subprocess,sys,xml.etree.ElementTree as ET

sys.dont_write_bytecode=True
MOD=Path(__file__).resolve().parents[1]
ROOT=MOD.parents[1]
WORK=MOD/'build/generated/stutter-opt-20261103'
JAVA=Path('D:/Program Files/Adobe Animate 2024/jre/bin/java.exe')
SDK=ROOT/'mods/Sandevistan/build/tools'
sys.path.insert(0,str(ROOT/'mods/ModLoader/tools'))
from test_registry import Registration

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def compile_sources(tag,sources,entry,output,product):
    out=WORK/tag
    out.mkdir(exist_ok=False)
    frozen=out/'src';frozen.mkdir()
    for name,content in sources.items():
        path=frozen/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content,encoding='utf-8')
    baseline=read(WORK/'baseline.json')
    assert all(sha(p)==h for p,h in baseline['formal'].items()),'Formal baseline changed'
    config=out/'compiler.xml'
    config.write_text('<flex-config><target-player>32.0</target-player><compiler>'
        '<external-library-path><path-element>'+str(SDK/'airsdk/frameworks/libs/air/airglobal.swc').replace('\\','/')+
        '</path-element></external-library-path><source-path><path-element>'+frozen.as_posix()+
        '</path-element></source-path><debug>false</debug><optimize>true</optimize><theme/></compiler></flex-config>',encoding='utf-8')
    command=[str(JAVA),'-Xmx512m','-Dfile.encoding=UTF-8','-jar',str(SDK/'flexsdk/lib/mxmlc.jar'),
        '+flexlib='+str(SDK/'flexsdk/frameworks'),'-load-config='+str(config),'-swf-version=32',
        '-use-network=false','-static-link-runtime-shared-libraries=true','-link-report='+str(out/'link.xml'),
        '-output='+str(out/output),str(frozen/entry)]
    receipt={'formal':baseline['formal'],'source':{str(p.relative_to(frozen)):sha(p) for p in frozen.rglob('*.as')},
        'command':command,'product':product,'compiled':False,'deployed':False}
    with Registration(owner='ContinuousScene / stutter optimization',purpose='Compile '+tag,resource='offline',run_dir=out,evidence=out,wait=60) as lease:
        proc=None
        try:
            with (out/'compiler.log').open('wb') as log:
                lease.before_launch('Bounded Java compiler, 512 MiB')
                proc=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                lease.child(proc.pid);proc.wait(180)
            if proc.returncode:raise RuntimeError((out/'compiler.log').read_text(encoding='utf-8',errors='replace'))
            definitions=sorted({n.attrib['id'] for n in ET.parse(out/'link.xml').getroot().iter('def')})
            if product:assert not any(x.startswith(('fe:','fe.','tests:','tests.')) or 'Checks' in x or 'Probe' in x for x in definitions),definitions
            assert entry[:-3] in definitions
            receipt.update(compiled=True,output=sha(out/output),definitions=definitions)
            lease.outcome='passed';lease.note='Compiled; runtime and performance are separate checks'
        finally:
            if proc:
                if proc.poll() is None:proc.kill();proc.wait(15)
                lease.child_stopped()
            (out/'build.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(json.dumps({'tag':tag,'output':receipt['output']}))

def product(tag):
    names=[*read(WORK/'baseline.json')['baselineSource'],'SceneCullEntry.as']
    sources={name:(MOD/'src'/name).read_text(encoding='utf-8-sig') for name in names}
    compile_sources(tag,sources,'ContinuousSceneDoc.as','ContinuousSceneMod.swf',True)

def run(name,product_tag,probe_tag,reverse=False,host_tag=None):
    motion=load('stutter_motion',MOD/'build/motion-test.py')
    silence=load('stutter_silence',MOD/'build/generated/camera-live-current-silent-20261028/silence.py')
    product_file=WORK/product_tag/'ContinuousSceneMod.swf'
    probe_file=WORK/probe_tag/'ContinuousSceneMotionMod.swf'
    for path,tag in [(product_file,product_tag),(probe_file,probe_tag)]:
        receipt=read(WORK/tag/'build.json');assert sha(path)==receipt['output']
        assert all(sha(p)==h for p,h in receipt['formal'].items()),'Formal input changed'
    evidence=MOD/'knowledge/experiments/evidence'/name
    if evidence.exists():raise FileExistsError(evidence)
    with Registration(owner='ContinuousScene / stutter optimization',purpose=name,resource='game',run_dir=motion.RUNTIME,evidence=evidence,wait=900) as lease:
        motion.prepare()
        if host_tag:
            host_file=WORK/host_tag/'candidate.swf';host_receipt=read(WORK/host_tag/'build.json')
            assert host_receipt['compiled'] and sha(host_file)==host_receipt['output']
            assert sha(ROOT/'pfe.swf')==host_receipt['host']
            temporary=motion.RUNTIME/'pfe.candidate';shutil.copy2(host_file,temporary);temporary.replace(motion.RUNTIME/'pfe.swf')
        for source,target in [(product_file,motion.RUNTIME/'mods/ContinuousScene/release/ContinuousSceneMod.swf'),
                              (probe_file,motion.RUNTIME/'mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf')]:
            # Replace rather than write through a possible asset hard link.
            temporary=target.with_suffix('.candidate');shutil.copy2(source,temporary);temporary.replace(target)
        controls=motion.RUNTIME/'lead-controls.json'
        controls.write_text(json.dumps({'combat':True,'enemies':6,'defaultWindow':False,'culling':True,'reverse':reverse}),encoding='utf-8')
        expected=motion.hashes();start=motion.HiddenProcess
        def quiet_start(*args,**kwargs):
            silence.seed(args[0][-1],motion.RUNTIME)
            assert expected==motion.hashes()
            return start(*args,**kwargs)
        motion.HiddenProcess=quiet_start
        try:
            flags=[] if probe_tag.startswith('timing-') else ['--profile']
            args=motion.parse_args(['--name',name,*flags,'--benchmark','scene','--window-width','2048','--window-height','1123'])
            motion.run_owned(args,lease)
        finally:
            motion.HiddenProcess=start;controls.unlink(missing_ok=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['product','run']);p.add_argument('name');p.add_argument('--product');p.add_argument('--probe');p.add_argument('--host');p.add_argument('--reverse',action='store_true');a=p.parse_args()
    if a.action=='product':product(a.name)
    else:run(a.name,a.product,a.probe,a.reverse,a.host)
