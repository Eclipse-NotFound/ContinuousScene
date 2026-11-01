from pathlib import Path
import hashlib,json,subprocess,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
sys.path.insert(0,str(ROOT/'mods/ModLoader/tools'))
from test_registry import Registration
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
src=HERE/'candidate-src'
flex=ROOT/'mods/Sandevistan/build/tools/flexsdk'
config='<flex-config><target-player>32.0</target-player><compiler><external-library-path><path-element>'+str(ROOT/'mods/Sandevistan/build/tools/airsdk/frameworks/libs/air/airglobal.swc').replace('\\','/')+'</path-element></external-library-path><source-path><path-element>'+str(src).replace('\\','/')+'</path-element></source-path><debug>false</debug><optimize>true</optimize><theme/></compiler></flex-config>'
(HERE/'tdfc-compiler.xml').write_text(config,'utf-8')
command=['D:/Program Files/Adobe Animate 2024/jre/bin/java.exe','-Xmx512m','-Dfile.encoding=UTF-8','-jar',str(flex/'lib/mxmlc.jar'),'+flexlib='+str(flex/'frameworks'),'-load-config='+str(HERE/'tdfc-compiler.xml'),'-swf-version=32','-static-link-runtime-shared-libraries=true','-output='+str(HERE/'TDFCMod.swf'),'-link-report='+str(HERE/'tdfc-link.xml'),str(src/'TDFCMod.as')]
with Registration(owner='ContinuousScene / lossless snapshot survey / 01a13816',purpose='Compile isolated TDFC snapshot reuse candidate',resource='game',run_dir=HERE,evidence=HERE,wait=900) as lease:
    with (HERE/'tdfc-compiler.log').open('xb') as log:
        lease.before_launch('512 MiB Java compiler')
        p=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);lease.child(p.pid)
        try:code=p.wait(180)
        finally:
            if p.poll() is None:p.kill();p.wait(15)
            lease.child_stopped()
        if code:raise RuntimeError('TDFC compile failed')
    receipt={'sources':{str(p.relative_to(src)):sha(p) for p in src.rglob('*.as')},'output':sha(HERE/'TDFCMod.swf'),'command':command}
    (HERE/'tdfc-build.json').write_text(json.dumps(receipt,indent=2),'utf-8')
    lease.outcome='passed';lease.note='Isolated candidate only; production unchanged'
    print(json.dumps({'compiled':True,'tdfc':receipt['output']}))
