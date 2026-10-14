"""Run the existing RV algorithm checks against the installed-lineage scene patch.

Only the copied harness source exposes private fields; production bytes are unchanged.
"""
from pathlib import Path
import re, subprocess, uuid, json
MOD=Path(__file__).resolve().parents[1]
ROOT=MOD.parents[1]
RV=ROOT/'mods/RealisticVision'
SDK=ROOT/'mods/Sandevistan/build/tools/flexsdk'
AIR=ROOT/'mods/Sandevistan/build/tools/airsdk/frameworks/libs/air/airglobal.swc'
JAVA=Path('D:/Program Files/Adobe Animate 2024/jre/bin/java.exe')
OUT=MOD/'build/generated/vision-checks'
OUT.mkdir(parents=True,exist_ok=True)
source=(MOD/'build/generated/rv-production/RealisticVisionMod.as').read_text(encoding='utf-8')
(OUT/'RealisticVisionMod.as').write_text(re.sub(r'\bprivate\b','public',source),encoding='utf-8')
config=OUT/'compiler.xml'
config.write_text('<flex-config><compiler><external-library-path><path-element>'+str(AIR)+
    '</path-element></external-library-path><debug>true</debug><optimize>false</optimize><theme/></compiler>'+
    '<target-player>32.0</target-player><swf-version>32</swf-version></flex-config>',encoding='utf-8')
results=[]
for harness in ('SoftHarness','SharedExplorationHarness'):
    cmd=[str(JAVA),'-Xmx384m','-jar',str(SDK/'lib/mxmlc.jar'),'+flexlib='+str(SDK/'frameworks'),
         '-load-config='+str(config),'-omit-trace-statements=false','-static-link-runtime-shared-libraries=true',
         '-source-path='+','.join(map(str,[OUT,RV/'build/motion-tests',RV/'build/stubs',MOD/'build/generated/rv-production'])),
         '-output='+str(OUT/(harness+'.swf')),str(RV/'build/motion-tests'/(harness+'.as'))]
    subprocess.run(cmd,check=True)
    descriptor=OUT/(harness+'.xml')
    descriptor.write_text('<application xmlns="http://ns.adobe.com/air/application/30.0"><id>pfe-modsettings-cs-vision-'+uuid.uuid4().hex+
        '</id><versionNumber>1.0</versionNumber><filename>RVTest</filename><initialWindow><content>'+harness+
        '.swf</content><visible>false</visible><renderMode>cpu</renderMode></initialWindow></application>',encoding='utf-8')
    run=subprocess.run([str(ROOT/'adl64.exe'),'-runtime',str(ROOT/'runtimes/air/win64'),str(descriptor)],
        cwd=OUT,capture_output=True,text=True,timeout=55,creationflags=subprocess.CREATE_NO_WINDOW)
    log=run.stdout+run.stderr
    (OUT/(harness+'.log')).write_text(log,encoding='utf-8')
    passed=run.returncode==0 and 'COMPLETE' in log and 'FAIL ' not in log and 'MOTION RED' not in log
    results.append(dict(name=harness,passed=passed,checks=log.count('PASS ')))
    print(log,flush=True)
    assert passed,harness+' failed'
print(json.dumps(results))
(OUT/'result.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
