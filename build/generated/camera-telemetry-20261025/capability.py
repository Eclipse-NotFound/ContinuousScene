"""One isolated AIR capability check. No game files, save data or deployment edits."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import time
import traceback
import uuid
import capture

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
TOOLS=ROOT/'mods/ModLoader/tools'
EXPECTED={'air_test_process.py':'628FFED886DB293ABE0177FD42C61AC09482E04AEE6AAE358CF2E3D6DEB0D1F9',
          'test_registry.py':'8B35A6D6CA1DD94CFD5CBA9A42979EBD14D9AE65497688FA859D084425922049'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--wait',type=int,default=300);args=parser.parse_args()
    for name,digest in EXPECTED.items():assert sha(TOOLS/name)==digest,name
    sys.path.insert(0,str(TOOLS))
    from air_test_process import HiddenProcess
    from test_registry import Registration
    spec=importlib.util.spec_from_file_location('owned_capability_reference',HERE.parent/'owned-mouse-capability-v4-20261025/run.py')
    prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
    nonce=uuid.uuid4().hex;app_id='com.remains.telemetry.'+nonce
    folder=HERE/'capability-runs'/nonce;folder.mkdir(parents=True,exist_ok=False)
    storage=Path(os.environ['APPDATA'])/app_id/'Local Store';assert not storage.exists()
    swf=HERE/'build/TelemetryCapability.swf';receipt=json.loads((HERE/'build/compile-receipt.json').read_text('utf-8'))
    assert receipt['compiled'] and receipt['sourceSHA256']==sha(HERE/'src/TelemetryCapability.as') and receipt['swfSHA256']==sha(swf)
    shutil.copy2(swf,folder/swf.name)
    descriptor=folder/('app-telemetry-test-'+nonce+'.xml')
    descriptor.write_text('''<?xml version="1.0" encoding="utf-8"?>
<application xmlns="http://ns.adobe.com/air/application/30.0">
<id>'''+app_id+'''</id><versionNumber>1.0.0</versionNumber><filename>TelemetryCapability</filename><name>TelemetryCapability</name>
<initialWindow><content>TelemetryCapability.swf</content><width>640</width><height>480</height><visible>true</visible><renderMode>direct</renderMode></initialWindow>
<supportedProfiles>extendedDesktop</supportedProfiles></application>''','utf-8')
    inputs=[Path(__file__),HERE/'capture.py',HERE/'compile.xml',HERE/'src/TelemetryCapability.as',swf,HERE/'build/compile-receipt.json',
            folder/swf.name,descriptor,ROOT/'adl64.exe',*[TOOLS/name for name in EXPECTED],*sorted((ROOT/'runtimes/air/win64').rglob('*'))]
    pins={str(p):sha(p) for p in inputs if p.is_file()}
    result=dict(appId=app_id,folder=str(folder),storage=str(storage),passed=False,diagnosticOnly=True,inputs=pins)
    process=None
    try:
        with Registration(owner='ContinuousScene / native telemetry capability / 01a13816',purpose='Bounded standalone AIR native spans',
                          resource='game',run_dir=folder,evidence=folder,wait=args.wait) as lease:
            result['registrationId']=lease.id;result['memory']=prior.memory(4*1024**3)
            # Shared registry plus a bounded process query: do not profile user or other-task AIR.
            import subprocess
            check=subprocess.run(['powershell','-NoProfile','-Command',"@(Get-Process -Name adl64,adl -ErrorAction SilentlyContinue).Count"],
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20,creationflags=subprocess.CREATE_NO_WINDOW)
            assert check.returncode==0 and int(check.stdout.strip() or b'0')==0,'Other AIR remains untouched'
            with capture.capture(folder,max_seconds=45) as captured:
                try:
                    lease.before_launch(app_id+' / private standalone native telemetry')
                    with (folder/'stdout.log').open('wb') as out,(folder/'stderr.log').open('wb') as err:
                        process=HiddenProcess([str(ROOT/'adl64.exe'),'-runtime',str(ROOT/'runtimes/air/win64'),str(descriptor)],
                            cwd=folder,stdout=out,stderr=err)
                        lease.child(process.pid);result['pid']=process.pid;result['desktop']=process.desktop
                        end=time.monotonic()+30
                        while process.poll() is None and time.monotonic()<end:
                            prior.memory(512*1024**2);time.sleep(.1)
                        assert process.poll()==0,'Capability failed or timed out'
                finally:
                    if process is not None:
                        if process.poll() is None:process.kill();result['forcedOwnedStop']=True
                        result['exitCode']=process.wait(10);lease.child_stopped();process.close();result['ownedHandlesClosed']=True
            result['capture']=captured
            raw=json.loads((storage/'result.json').read_text('utf-8'));capture.save(folder/'air-result.json',raw)
            assert raw['appId']==app_id and raw['frames']==raw['connectedFrames']==120
            records=capture.metrics(folder/'native.flm')
            named={p['name'] for p in records};custom=[p for p in records if p['name']=='remains.capability.frame']
            assert len(custom)==120 and [p['value']['frame'] for p in custom]==list(range(1,121))
            assert all(p['value']['appId']==app_id for p in custom)
            render=[p for p in records if p['name'].startswith('.rend.') and p.get('span',0)>0]
            assert render,'Missing native render timings'
            busy=[p for p in records if p['name']=='remains.capability.work' and 30<=p['value']<50]
            assert len(busy)==20 and all(p['span']>=2000 for p in busy),'Native span calibration failed'
            assert captured['complete'] and captured['configRemoved'] and not captured['errors'] and not result.get('forcedOwnedStop')
            assert all(sha(Path(p))==digest for p,digest in pins.items())
            result.update(passed=True,metricCount=len(records),metricNames=sorted(named),customFrames=len(custom),
                renderSpans=len(render),busyCalibration=busy,inputsUnchanged=True)
            lease.outcome='passed';lease.note='Native telemetry capability and 120 custom frame anchors validated; no game performance claim'
    except BaseException as error:result.update(error=repr(error),traceback=traceback.format_exc())
    finally:capture.save(folder/'runner-result.json',result)
    print(json.dumps({k:result.get(k) for k in ('passed','folder','error','metricCount','renderSpans')}),flush=True)
    return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
