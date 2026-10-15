from pathlib import Path
import subprocess,json,uuid,sys,hashlib,shutil
from datetime import datetime,timezone
out=Path(__file__).resolve().parent
mod=out.parent.parent
root=mod.parent.parent
sdk=root/'mods/Sandevistan/build/tools/flexsdk'
air=root/'mods/Sandevistan/build/tools/airsdk/frameworks/libs/air/airglobal.swc'
java=Path('D:/Program Files/Adobe Animate 2024/jre/bin/java.exe')
if sys.argv[1]=='build':
    config=out/'compiler.xml'
    config.write_text('<flex-config><compiler><external-library-path><path-element>'+str(air)+'</path-element></external-library-path><debug>true</debug><optimize>false</optimize><theme/></compiler><target-player>32.0</target-player><swf-version>32</swf-version></flex-config>',encoding='utf-8')
    cmd=[str(java),'-Xmx256m','-jar',str(sdk/'lib/mxmlc.jar'),'+flexlib='+str(sdk/'frameworks'),'-load-config='+str(config),'-omit-trace-statements=false','-static-link-runtime-shared-libraries=true','-output='+str(out/'CopyChannelProbe.swf'),str(out/'CopyChannelProbe.as')]
    run=subprocess.run(cmd,cwd=out,capture_output=True,text=True,timeout=60)
    (out/'compile.log').write_text(run.stdout+run.stderr,encoding='utf-8')
    assert run.returncode==0,run.stdout+run.stderr
    appid='pfe-modsettings-cs-copychannel-'+uuid.uuid4().hex
    (out/'application.xml').write_text('<application xmlns="http://ns.adobe.com/air/application/30.0"><id>'+appid+'</id><versionNumber>1.0</versionNumber><filename>CopyChannelProbe</filename><initialWindow><content>CopyChannelProbe.swf</content><visible>false</visible><renderMode>cpu</renderMode></initialWindow></application>',encoding='utf-8')
    print('Compiled '+appid)
elif sys.argv[1]=='run':
    run=subprocess.run([str(root/'adl64.exe'),'-runtime',str(root/'runtimes/air/win64'),str(out/'application.xml')],cwd=out,capture_output=True,text=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
    log=run.stdout+run.stderr
    (out/'stdout.log').write_text(log,encoding='utf-8')
    lines=[line for line in log.splitlines() if line.startswith('COPYCHANNEL_RESULT ')]
    assert len(lines)==1,(run.returncode,log)
    result=json.loads(lines[0].split(' ',1)[1]);result['exitCode']=run.returncode;result['createdAt']=datetime.now(timezone.utc).isoformat()
    result['sourceSHA256']=hashlib.sha256((out/'CopyChannelProbe.as').read_bytes()).hexdigest()
    (out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    evidence=mod/'knowledge/experiments/evidence'/('copychannel-rounding-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
    evidence.mkdir(parents=True,exist_ok=False)
    for name in ['CopyChannelProbe.as','run.py','result.json','stdout.log','application.xml','compile.log']:
        shutil.copy2(out/name,evidence/name)
    assert run.returncode==0 and result['ok'],result
    for case in result['cases']:
        pixels=case['nonzero']
        print(json.dumps({'kind':case['kind'],'value':case['value'],'pixels':len(pixels),'first':pixels[:1],'last':pixels[-1:]}))
    for case in result['roundTrips']:
        print(json.dumps({'roundTrip':case['origin'],'savedFirstRow':case['savedGreen'][0],'alphaChanges':len(case['alphaChanges']),'firstChanges':case['alphaChanges'][:10]}))
    print('Evidence: '+str(evidence))
