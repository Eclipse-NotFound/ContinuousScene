"""Registered standalone sampler capability; never prepares or loads the game."""
from pathlib import Path
from xml.sax.saxutils import escape
import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
import uuid

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
BUILD = HERE.parents[2]
ROOT = BUILD.parents[2]
JAVA = Path('D:/Program Files/Adobe Animate 2024/jre/bin/java.exe')
TOOLS = ROOT / 'mods/Sandevistan/build/tools'
JAR = TOOLS / 'flexsdk/lib/mxmlc.jar'
AIRGLOBAL = TOOLS / 'airsdk/frameworks/libs/air/airglobal.swc'
ADL = ROOT / 'adl64.exe'
AIR = ROOT / 'runtimes/air/win64'
VERSION = 'sampler-capability-1'


def sha(path):
    with Path(path).open('rb') as stream:
        digest = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest().upper()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def load_motion():
    spec = importlib.util.spec_from_file_location('sampler_motion_support', BUILD / 'motion-test.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inputs():
    support = ROOT / 'mods/ModLoader/tools'
    paths = [HERE/'run.py', HERE/'SamplerCapabilityProbe.as', HERE/'README.md',
             BUILD/'motion-test.py', support/'air_test_process.py', support/'test_registry.py',
             JAVA, JAR, AIRGLOBAL, ADL]
    paths += list((TOOLS/'flexsdk/lib').glob('*.jar'))
    paths += list((TOOLS/'flexsdk/frameworks').glob('*.xml'))
    paths += [p for p in AIR.rglob('*') if p.is_file()]
    for optional in (JAVA.parent/'server/jvm.dll', JAVA.parent.parent/'lib/rt.jar'):
        if optional.exists(): paths.append(optional)
    return {str(p.resolve()): sha(p) for p in sorted(set(paths))}


def memory_gate(m, folder, stage):
    value = m.memory_status()
    save(folder/('memory-'+stage+'.json'), value)
    if value['availableCommit'] < 4*1024**3 or value['availablePhysical'] < 2*1024**3:
        raise RuntimeError('4GiB commit / 2GiB physical precheck failed: '+json.dumps(value))
    if m.air_pids(): raise RuntimeError('Another AIR is running; untouched')
    return value


def monitor(m, process, seconds, record):
    began = time.monotonic()
    while process.poll() is None:
        if time.monotonic()-began > seconds: raise TimeoutError('Owned process timed out')
        current = m.memory_status()
        record['minimumAvailableCommit'] = min(record['minimumAvailableCommit'], current['availableCommit'])
        if current['availableCommit'] < 512*1024**2:
            record['memoryAbort'] = current
            raise RuntimeError('512MiB running commit guard; stop only owned process')
        others = [p for p in m.air_pids() if p != process.pid]
        if others:
            record['otherAIR'] = others
            raise RuntimeError('Other AIR appeared; leave it untouched')
        time.sleep(.25)
    return process.returncode


def cleanup(process, lease, hidden=False):
    if process is None: return
    if process.poll() is None:
        process.kill()
        process.wait(timeout=15)
    if hidden: process.close()
    lease.child_stopped()


def execute(args, m, lease, folder):
    frozen = inputs()
    save(folder/'inputs-before.json', frozen)
    src = folder/'source'; app = folder/'app'
    src.mkdir(); app.mkdir()
    for original in (HERE/'SamplerCapabilityProbe.as', HERE/'run.py', HERE/'README.md'):
        shutil.copy2(original, src/original.name)
    for original in (BUILD/'motion-test.py', ROOT/'mods/ModLoader/tools/air_test_process.py', ROOT/'mods/ModLoader/tools/test_registry.py'):
        shutil.copy2(original, src/original.name)
    app_id = 'cs-sampler-capability-'+uuid.uuid4().hex
    store = Path(os.environ['APPDATA'])/app_id/'Local Store'
    if store.exists(): raise FileExistsError('Unique storage unexpectedly exists')
    config = folder/'compiler.xml'
    config.write_text('''<flex-config><target-player>32.0</target-player><compiler>
<external-library-path><path-element>{air}</path-element></external-library-path>
<source-path><path-element>{src}</path-element></source-path><debug>false</debug><optimize>true</optimize><theme/>
</compiler></flex-config>'''.format(air=escape(str(AIRGLOBAL)), src=escape(str(src))), encoding='utf-8')
    target = app/'SamplerCapabilityProbe.swf'
    command = [str(JAVA), '-Xmx512m', '-Dfile.encoding=UTF-8', '-jar', str(JAR),
               '+flexlib='+str(TOOLS/'flexsdk/frameworks'), '-load-config='+str(config), '-swf-version=32',
               '-static-link-runtime-shared-libraries=true', '-output='+str(target), str(src/'SamplerCapabilityProbe.as')]
    save(folder/'compile-command.json', command)
    memory = memory_gate(m, folder, 'compile')
    record = {'minimumAvailableCommit':memory['availableCommit'], 'otherAIR':[]}
    process = None
    try:
        with (folder/'compile.log').open('wb') as log:
            lease.before_launch('Standalone sampler compiler; debug=false')
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, cwd=folder)
            lease.child(process.pid)
            code = monitor(m, process, 120, record)
            if code: raise RuntimeError('Compiler failed: '+str(folder/'compile.log'))
    finally:
        try: cleanup(process, lease)
        finally: save(folder/'compile-process.json', record)
    assert inputs() == frozen, 'Compile inputs changed'
    save(folder/'compile.json', {'compilerDebug':False, 'optimize':True, 'swfSHA256':sha(target),
         'configSHA256':sha(config), 'sourceSHA256':sha(src/'SamplerCapabilityProbe.as'), 'inputs':frozen})
    if args.compile_only:
        lease.outcome='completed'; lease.note='Compiled only; sampler capability remains untested'
        return {'status':'compiled-only', 'supported':None, 'folder':str(folder)}
    descriptor = app/'application.xml'
    descriptor.write_text('''<?xml version="1.0" encoding="UTF-8"?>
<application xmlns="http://ns.adobe.com/air/application/30.0"><id>{app}</id><versionNumber>1.0</versionNumber>
<filename>SamplerCapabilityProbe</filename><name>Sampler capability</name><initialWindow>
<content>SamplerCapabilityProbe.swf</content><visible>false</visible><width>32</width><height>32</height>
<renderMode>direct</renderMode></initialWindow><supportedProfiles>desktop</supportedProfiles></application>
'''.format(app=app_id), encoding='utf-8')
    save(app/'probe-config.json', {'durationMs':args.duration_ms})
    run_inputs = {str(p.relative_to(app)):sha(p) for p in app.iterdir() if p.is_file()}
    command = [str(ADL), '-runtime', str(AIR), str(descriptor)]
    assert '-nodebug' not in command
    save(folder/'run-command.json', command); save(folder/'app-inputs.json', run_inputs)
    memory = memory_gate(m, folder, 'air')
    policy = {'appId':app_id, 'storagePath':str(store), 'desktopPolicy':'private', 'gameLoaded':False,
              'debuggerDisabled':False, 'memoryBefore':memory, 'minimumAvailableCommit':memory['availableCommit'], 'otherAIR':[]}
    process = None
    try:
        with (folder/'stdout.log').open('wb') as out, (folder/'stderr.log').open('wb') as err:
            lease.before_launch(app_id+' / standalone sampler capability')
            process = m.HiddenProcess(command, cwd=app, stdout=out, stderr=err)
            lease.child(process.pid); policy.update(pid=process.pid, desktop=process.desktop)
            print('Owned AIR '+str(process.pid), flush=True)
            policy['exitCode'] = monitor(m, process, 45, policy)
    except BaseException as error:
        policy['runFailure'] = type(error).__name__+': '+str(error)
        raise
    finally:
        try: cleanup(process, lease, hidden=True)
        finally:
            try:
                if store.exists(): shutil.copytree(store, folder/'storage')
            finally: save(folder/'process-policy.json', policy)
    assert inputs() == frozen, 'Toolchain/source/runtime inputs changed'
    assert run_inputs == {str(p.relative_to(app)):sha(p) for p in app.iterdir() if p.is_file()}, 'Standalone app inputs changed'
    save(folder/'inputs-after.json', inputs())
    result_path = folder/'storage/result.json'
    result = json.loads(result_path.read_text('utf-8'))
    assert result['version']==VERSION and result['applicationID']==app_id and result['gameLoaded'] is False
    counts = result['counts']; examples = result['examples']['knownHotLoop']
    observed_hot = any('knownHotLoop' in (frame.get('name') or '') for sample in examples for frame in sample['stack'])
    supported = bool(result['supported'] and result['status']=='supported' and result['hotLoopExecuted']
                     and result['cleanup']['paused'] and result['cleanup']['stopped'] and not result['truncated']
                     and result['sampleTimesValid'] and counts['cpu']>0 and counts['namedCPU']>0
                     and counts['knownHotLoopCPU']>0 and observed_hot and counts['unknown']==0)
    if result['supported'] != supported: raise AssertionError('Capability claim lacks actual named CPU sample evidence')
    summary = {'version':VERSION, 'status':result['status'], 'supported':supported,
               'capabilityPassed':supported, 'counts':counts, 'loopElapsedMs':result.get('loopElapsedMs'),
               'resultSHA256':sha(result_path), 'folder':str(folder), 'performanceEligible':False,
               'scope':'Only this standalone debug=false SWF under the recorded ADL/runtime; no game attribution proven'}
    save(folder/'summary.json', summary)
    if result['status']=='error' or policy['exitCode']!=0: raise RuntimeError('Probe execution error; inspect preserved result and logs')
    lease.outcome='passed' if supported else 'completed'
    lease.note='Named knownHotLoop CPU samples observed' if supported else 'UNSUPPORTED: no usable named CPU sample; not a pass'
    return summary


def main():
    assert __debug__, 'Run without -O'
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    parser.add_argument('--duration-ms', type=int, default=200, choices=range(100,301))
    parser.add_argument('--registry-wait', type=int, default=600)
    parser.add_argument('--compile-only', action='store_true')
    args=parser.parse_args()
    if not args.name or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name): parser.error('Use a short lowercase run name')
    folder=HERE/'runs'/(args.name+'-'+uuid.uuid4().hex)
    folder.mkdir(parents=True, exist_ok=False)
    m=load_motion()
    try:
        with m.Registration(owner='ContinuousScene / sampler capability / 01a13816-367b-7261-8e11-ca9152565dd9',
                purpose=args.name, resource='game', run_dir=folder, evidence=folder, wait=args.registry_wait) as lease:
            result=execute(args,m,lease,folder)
        print(json.dumps(result, ensure_ascii=False), flush=True)
    except BaseException as error:
        save(folder/'failure.json', {'type':type(error).__name__, 'message':str(error), 'folder':str(folder)})
        raise


if __name__=='__main__': main()
