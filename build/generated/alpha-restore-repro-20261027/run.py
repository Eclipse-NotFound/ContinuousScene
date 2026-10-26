"""Registered independent Stage3D capability only; no game loading or deployment."""
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

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
TOOLS = ROOT / 'mods/ModLoader/tools'
MOTION = ROOT / 'mods/ContinuousScene/build/motion-test.py'
SOURCE = HERE / 'src/AlphaRestoreRepro.as'
SWF = HERE / 'build/AlphaRestoreRepro.swf'
RECEIPT = HERE / 'build/compile-receipt.json'
PREVIOUS = ROOT / 'mods/ContinuousScene/knowledge/experiments/evidence/camera-native-light-crop-v2-20261027-r1/runner-inputs.json'
PINS = {
    TOOLS / 'air_test_process.py': '628FFED886DB293ABE0177FD42C61AC09482E04AEE6AAE358CF2E3D6DEB0D1F9',
    TOOLS / 'test_registry.py': 'E9F51CB75420C507F6DB1D96BE6B1430374B0B7A797607FF4438A695A717809E',
    MOTION: '2371AF3E3AB4C6ADC99BC67C949BA6182F3767114A722B65A3EFB7FD5A18CDC6',
    PREVIOUS: 'C62B89217595292447E81D39A31DED9DD187914FEA966AFF03CDBE2643139B10',
}

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()

def read(path):
    return json.loads(path.read_text('utf-8-sig'))

def save(path, value):
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wait', type=float, default=300)
    args = parser.parse_args()
    assert os.name == 'nt' and not HERE.is_symlink()
    for path, digest in PINS.items():
        assert sha(path) == digest, str(path)
    spec = importlib.util.spec_from_file_location('stage3d_owned_helpers', MOTION)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    previous, built = read(PREVIOUS), read(RECEIPT)
    assert built['compiled'] and built['sourceSHA256'] == sha(SOURCE)
    assert built['configSHA256'] == sha(HERE/'compile.xml') and built['swfSHA256'] == sha(SWF)
    assert len(previous['baseline']) == 526 and len(previous['runtimeInputs']) == 13
    nonce = uuid.uuid4().hex
    app_id = 'com.remains.alpharestorerepro.' + nonce
    run_dir = HERE/'runs'/nonce
    run_dir.mkdir(parents=True, exist_ok=False)
    storage = Path(os.environ['APPDATA'])/app_id/'Local Store'
    assert not storage.exists()
    descriptor = run_dir/('app-alpha-restore-' + nonce + '.xml')
    descriptor.write_text('''<?xml version="1.0" encoding="utf-8"?>
<application xmlns="http://ns.adobe.com/air/application/30.0">
  <id>''' + app_id + '''</id><versionNumber>1.0.0</versionNumber>
  <filename>AlphaRestoreRepro</filename><name>AlphaRestoreRepro</name>
  <initialWindow><content>AlphaRestoreRepro.swf</content><title>''' + app_id + '''</title>
    <width>512</width><height>512</height><visible>true</visible>
    <systemChrome>standard</systemChrome><transparent>false</transparent>
    <renderMode>direct</renderMode><resizable>false</resizable><maximizable>false</maximizable>
  </initialWindow><supportedProfiles>extendedDesktop</supportedProfiles>
</application>''', encoding='utf-8')
    save(run_dir/'fixture.json', dict(appId=app_id, nonce=nonce))
    shutil.copyfile(SWF, run_dir/'AlphaRestoreRepro.swf')
    assert sha(run_dir/'AlphaRestoreRepro.swf') == built['swfSHA256']
    frozen = {str(path): digest for path,digest in PINS.items()}
    frozen.update({str(ROOT/path): digest for path,digest in previous['baseline'].items()})
    frozen.update({str(ROOT/path): digest for path,digest in previous['runtimeInputs'].items()})
    frozen.update(built['compilerInputs'])
    frozen.update({str(p):sha(p) for p in (
        Path(__file__), HERE/'README.md', HERE/'build.py', SOURCE, HERE/'compile.xml',
        SWF, RECEIPT, descriptor, run_dir/'fixture.json', run_dir/'AlphaRestoreRepro.swf')})
    report_path = run_dir/'runner-result.json'
    out = dict(version='alpha-restore-runner-1', appId=app_id, nonce=nonce,
        runDir=str(run_dir), storage=str(storage), descriptor=descriptor.read_text('utf-8'),
        inputs=frozen, diagnosticCompleted=False, diagnosticOnly=True, performanceEligible=False,
        deployed=False, cleanup={}, began=time.time())
    process = None
    def persist(): save(report_path, out)
    def verify_inputs():
        changed = [p for p,digest in frozen.items() if sha(p) != digest]
        assert not changed, changed
        return changed
    try:
        with m.Registration(owner='ContinuousScene / Alpha restore reproduction / 01a13816',
                purpose='512px synthetic alpha restoration; no game or timing claim',
                run_dir=run_dir, evidence=report_path, resource='game', wait=args.wait) as record:
            out['registrationId']=record.id
            try:
                assert not m.air_pids(), 'Other AIR remains untouched'
                out['memoryBefore']=m.memory_status()
                assert out['memoryBefore']['availableCommit'] >= 4*1024**3
                assert out['memoryBefore']['availablePhysical'] >= 2*1024**3
                verify_inputs()
                persist()
                record.before_launch(app_id+' / standalone / private desktop')
                with (run_dir/'stdout.log').open('wb') as stdout, (run_dir/'stderr.log').open('wb') as stderr:
                    process=m.HiddenProcess([ROOT/'adl64.exe','-runtime',ROOT/'runtimes/air/win64',descriptor],
                        cwd=run_dir, stdout=stdout, stderr=stderr)
                    record.child(process.pid)
                    out.update(pid=process.pid, privateDesktop=process.desktop)
                    persist()
                    deadline=time.perf_counter()+30
                    while process.poll() is None and time.perf_counter()<deadline:
                        assert m.memory_status()['availableCommit']>=512*1024**2, 'Low commit'
                        time.sleep(.1)
                    assert process.poll() is not None, 'Owned fixture timeout'
                    out['airExitCode']=process.wait(5)
            except BaseException as error:
                out.update(executionError=repr(error), executionTraceback=traceback.format_exc())
            finally:
                if process is not None:
                    try:
                        if process.poll() is None:
                            out['cleanup']['forcedOwnedStop']=True
                            process.kill()
                        out['cleanup']['exitCode']=process.wait(10)
                        record.child_stopped()
                        process.close()
                        out['cleanup']['ownedHandlesClosed']=True
                    except BaseException as error:
                        out['cleanup']['error']=repr(error)
                try:
                    out['inputChanges']=verify_inputs()
                    result_path=storage/'result.json'
                    if result_path.is_file():
                        result=read(result_path)
                        save(run_dir/'air-result.json', result)
                        out['airResult']=result
                    else: result={}
                    out['diagnosticCompleted']=bool(
                        not out.get('executionError') and out.get('airExitCode')==0
                        and out['cleanup'].get('ownedHandlesClosed')
                        and not out['cleanup'].get('forcedOwnedStop')
                        and not out['cleanup'].get('error') and out['inputChanges']==[]
                        and result.get('appId')==app_id and result.get('actualAppId')==app_id
                        and result.get('nonce')==nonce and result.get('passed')
                        and result.get('errors')==[] and result.get('completed')
                        and result.get('allocations')==result.get('disposals')
                        and len(result.get('cases',[]))==16
                        and all(row['nativeRepeat']['equal'] for row in result['cases']))
                except BaseException as error:
                    out.update(verificationError=repr(error), verificationTraceback=traceback.format_exc())
                record.outcome='passed' if out['diagnosticCompleted'] else 'failed'
                record.note='Synthetic alpha restoration diagnosis only; not game acceptance'
                out['ended']=time.time()
                persist()
    except BaseException as error:
        out.update(outerError=repr(error), outerTraceback=traceback.format_exc())
        persist()
    print(json.dumps(dict(report=str(report_path),diagnosticCompleted=out['diagnosticCompleted'],
        restorationFailures=[row['name'] for row in out.get('airResult',{}).get('cases',[]) if not row['restored']['equal']],cleanup=out['cleanup']),ensure_ascii=False),flush=True)
    return 0 if out['diagnosticCompleted'] else 1

if __name__=='__main__': sys.exit(main())

