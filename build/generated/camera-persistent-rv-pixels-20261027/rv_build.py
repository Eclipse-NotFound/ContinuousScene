from pathlib import Path
from xml.sax.saxutils import escape
import shutil,subprocess,uuid
HERE=Path(__file__).resolve().parent;STUB=HERE.parents[2].parent/'RealisticVision/build/GameStubs.swc'
def verify(value,r,base):
    for key,d in value['inputs'].items():assert r.sha(Path(key))==d,key
    assert base.tree_hashes(Path(value['source']))==value['sources']
    assert r.sha(Path(value['output']))==value['sha256']
    assert r.sha(Path(value['config']))==value['configSHA256']
def build(lease,control,r,base):
    control.memory_gate();folder=HERE/'rv-builds'/uuid.uuid4().hex;folder.mkdir(parents=True,exist_ok=False)
    src=folder/'src';shutil.copytree(HERE/'rv-src',src);captured=base.tree_hashes(src);assert len(captured)==6
    assert captured==base.tree_hashes(HERE/'rv-src')
    tools=r.enemy.TOOLS;air=tools/'airsdk/frameworks/libs/air/airglobal.swc'
    inputs={str(p):r.sha(p) for p in [Path(r.enemy.JAVA),tools/'flexsdk/lib/mxmlc.jar',air,STUB,HERE/'rv_build.py']}
    config=folder/'RealisticVisionMod.xml';output=folder/'RealisticVisionMod.swf'
    config.write_text('<flex-config><compiler><external-library-path><path-element>'+escape(str(air))+'</path-element><path-element>'+escape(str(STUB))+'</path-element></external-library-path><source-path><path-element>'+escape(str(src))+'</path-element></source-path><debug>false</debug><optimize>true</optimize><omit-trace-statements>false</omit-trace-statements><theme/></compiler><target-player>32.0</target-player><swf-version>32</swf-version><use-network>false</use-network><static-link-runtime-shared-libraries>true</static-link-runtime-shared-libraries></flex-config>','utf-8')
    command=[str(r.enemy.JAVA),'-Xmx512m','-Dfile.encoding=UTF-8','-jar',str(tools/'flexsdk/lib/mxmlc.jar'),'+flexlib='+str(tools/'flexsdk/frameworks'),'-load-config='+str(config),'-output='+str(output),str(src/'RealisticVisionMod.as')]
    process=None;lease.before_launch('Isolated RV compatibility compiler; no AIR yet')
    try:
        process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);lease.child(process.pid)
        log,_=process.communicate();(folder/'compile.log').write_bytes(log)
        assert process.returncode==0,'RV compiler failed: '+str(folder/'compile.log')
    finally:
        if process is not None:
            if process.poll() is None:process.kill();process.wait(timeout=15)
            lease.child_stopped()
    value=dict(source=str(src),sources=captured,inputs=inputs,output=str(output),sha256=r.sha(output),config=str(config),configSHA256=r.sha(config),command=command,diagnosticOnly=True,deployed=False)
    verify(value,r,base);r.save(folder/'build.json',value);return value
