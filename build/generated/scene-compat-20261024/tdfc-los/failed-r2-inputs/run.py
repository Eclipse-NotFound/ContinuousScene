"""Registered terminal LOS component on actual A796 host; no performance/deploy mode."""
from pathlib import Path
from xml.sax.saxutils import escape
import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
import uuid

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
BUILD=HERE.parents[2]
HOST='A796827173AF7D6FAB9885FB66ECC62182AB5335918A30C7CCE4C44914A238B7'
CS='7F1F2961C6E299D949423591F3C65C610C2EAEFA7FC72E8A583A402770D6B51F'
TDFC='7ACD45193109267DBBF875240528048AD6F1D09FA3B8B36BAA6F98EBB5FDDCE5'
TDFC_PATH='mods/TDFC/release/TDFCMod.swf'
VERSION='tdfc-los-terminal-1'
SEED_RECEIPT=BUILD.parent/'knowledge/experiments/evidence/vertical-camera-band-20261023-combat-candidate-r3/probe-build.json'
SEED_SHA='B7ED1EAB8BEE0DC1024D6EF0A56A965F311B97E8CED9A9F32A2BCDE35B35FF13'
SEED_PROBE='39A1497BE832282CAC25E2A508A954432F9F31B15A2FBE5A650AB8C4D9C97E9E'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

base=load('los_native_support',BUILD/'native-input-combat-run.py')
patch=load('los_probe_patch',HERE/'probe_patch.py')
source=load('los_frozen_candidate',HERE/'prepare.py')
r,m=base.r,base.m
base.FORMAL_HOST=HOST

def candidate_inputs():
    assert r.read(HERE/'source-proof.json')==source.check()
    files=[HERE/name for name in ('prepare.py','source-pins.json','source-proof.json','candidate.diff')]
    files+=sorted((HERE/'source').glob('*.as'))
    return {str(p):r.sha(p) for p in files}

def seed():
    pin=r.read(HERE/'probe-source-pin.json')
    assert pin['receiptSHA256']==SEED_SHA and pin['probeSHA256']==SEED_PROBE and pin['sourceFileCount']==85
    assert r.sha(SEED_RECEIPT)==SEED_SHA,'Historical probe receipt changed'
    value=r.read(SEED_RECEIPT)
    assert value['probeSHA256']==SEED_PROBE==r.sha(Path(value['probePath']))
    assert base.tree_hashes(Path(value['frozenSourcePath']))==value['frozenSourceSHA256']
    assert len(value['frozenSourceSHA256'])==85,'Only the approved 85-file historical tree is accepted'
    return value

def fixture_inputs():
    old=seed()
    pins=r.read(HERE/'component-source-pins.json')
    files=[HERE/name for name in ('SceneTdfcLosChecks.as','probe_patch.py')]
    assert {p.name:r.sha(p) for p in files}==pins['files']
    return dict(candidate_inputs(),**{str(p):r.sha(p) for p in files+[HERE/'component-source-pins.json',
        HERE/'probe-source-pin.json',SEED_RECEIPT,Path(old['probePath'])]})

def runner_inputs():
    files=[HERE/'run.py',HERE/'prepare.py',HERE/'probe_patch.py',patch.SOURCE]
    files += [BUILD/name for name in ('native-input-combat-run.py','sleeping-root-r2-run.py',
        'sleeping-root-r2-build.py','enemy-release.py','enemy-speed.py','motion-test.py','profile-vision.py')]
    files += [r.ROOT/'mods/ModLoader/tools'/name for name in ('test_registry.py','air_test_process.py')]
    files.append(base.support.OUT/'source-provenance.json')
    return {str(p):r.sha(p) for p in files}

base.runner_inputs=runner_inputs
base.candidate_inputs=fixture_inputs
original_runtime_hashes=m.hashes

def runtime_hashes():
    values=original_runtime_hashes()
    p=m.RUNTIME/patch.CONTROL
    if p.exists():values[patch.CONTROL]=r.sha(p)
    return values

m.hashes=runtime_hashes

def memory_gate():
    value=m.memory_status()
    assert value['availableCommit']>=4*1024**3 and value['availablePhysical']>=2*1024**3, value
    return value

def verify_candidate(path,baseline,compiler):
    value=r.read(path)
    assert value['version']==VERSION and value['diagnosticOnly'] and not value['deployed']
    assert value['baseTDFC']==TDFC and value['installedHost']==HOST
    assert value['candidateInputs']==candidate_inputs() and value['productionSHA256']==baseline
    assert value['compilerInputs']==compiler
    frozen=Path(value['sourcePath'])
    assert source.hashes(frozen)==r.read(HERE/'source-proof.json')['after']==value['sourceSHA256']
    assert len(list(frozen.iterdir()))==20 and all(p.suffix=='.as' for p in frozen.iterdir())
    for name,digest in value['artifacts'].items():assert r.sha(path.parent/name)==digest,name
    assert r.sha(Path(value['candidatePath']))==value['candidateSHA256']
    return value

def compile_candidate(lease,baseline,compiler):
    memory_gate();assert not m.air_pids(),'Other AIR remains untouched'
    inputs=candidate_inputs();scripts=runner_inputs()
    folder=HERE/'candidate-builds'/uuid.uuid4().hex
    frozen=folder/'source';shutil.copytree(HERE/'source',frozen)
    assert source.hashes(frozen)==r.read(HERE/'source-proof.json')['after']
    output=folder/'TDFCMod.swf';config=folder/'TDFCMod.xml'
    config.write_text('''<flex-config><target-player>32.0</target-player><compiler>
<external-library-path><path-element>{air}</path-element></external-library-path>
<source-path><path-element>{src}</path-element></source-path><debug>false</debug><optimize>true</optimize><theme/>
</compiler></flex-config>'''.format(air=escape(str(r.enemy.TOOLS/'airsdk/frameworks/libs/air/airglobal.swc')),
                                  src=escape(str(frozen))),'utf-8')
    command=[str(r.enemy.JAVA),'-Xmx512m','-Dfile.encoding=UTF-8','-jar',str(r.enemy.TOOLS/'flexsdk/lib/mxmlc.jar'),
        '+flexlib='+str(r.enemy.TOOLS/'flexsdk/frameworks'),'-load-config='+str(config),'-swf-version=32',
        '-static-link-runtime-shared-libraries=true','-output='+str(output),str(frozen/'TDFCMod.as')]
    process=None;lease.before_launch('Frozen 20-source TDFC LOS diagnostic compiler')
    try:
        process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);lease.child(process.pid)
        log,_=process.communicate();(folder/'compile.log').write_bytes(log)
        if process.returncode:raise RuntimeError('Candidate compile failed; preserved '+str(folder/'compile.log'))
    finally:
        if process is not None:
            if process.poll() is None:process.kill();process.wait(timeout=15)
            lease.child_stopped()
    assert inputs==candidate_inputs() and scripts==runner_inputs() and baseline==r.baseline()
    assert compiler==base.support.compiler_inputs()
    value=dict(version=VERSION,diagnosticOnly=True,deployed=False,performanceEligible=False,
        baseTDFC=TDFC,installedHost=HOST,candidateInputs=inputs,productionSHA256=baseline,
        compilerInputs=compiler,command=command,sourcePath=str(frozen),sourceSHA256=source.hashes(frozen),
        candidatePath=str(output),candidateSHA256=r.sha(output),
        artifacts={name:r.sha(folder/name) for name in ('TDFCMod.swf','TDFCMod.xml','compile.log')})
    path=folder/'candidate-build.json';r.save(path,value)
    verify_candidate(path,baseline,compiler)
    print(json.dumps({'candidateBuild':str(path),'sha256':value['candidateSHA256']}),flush=True)
    return path

def compile_probe(lease,baseline,scripts,compiler,fixture):
    memory_gate()
    old=seed();original=Path(old['frozenSourcePath']);before=old['frozenSourceSHA256']
    staging=HERE/'probe-staging'/uuid.uuid4().hex
    patch.prepare(original,staging/'src');after=base.tree_hashes(staging/'src')
    changed=sorted(k for k in set(before)|set(after) if before.get(k)!=after.get(k))
    assert changed==['ContinuousSceneMotionProbe.as',patch.HELPER]
    assert before==base.tree_hashes(original),'Historical frozen source changed during copy'
    origin=staging/'source-origin.json'
    r.save(origin,dict(seedReceipt=str(SEED_RECEIPT),seedReceiptSHA256=SEED_SHA,seedProbeSHA256=SEED_PROBE,
        seedSource=str(original),seedSourceSHA256=before,stagedSHA256=after,
        changed=changed,terminalOnly=True,diagnosticOnly=True))
    base.B,base.OUT=staging/'build',HERE/'probe-builds'
    path=base.compile_frozen_probe(lease,baseline,scripts,compiler,fixture)
    value=r.read(path);value.update(losProbeVersion=patch.VERSION,terminalOnly=True,
        sourceOrigin=str(origin),sourceOriginSHA256=r.sha(origin))
    r.save(path,value);return path

def verify_probe(path,baseline,scripts,compiler,fixture):
    value=base.verify_probe(path,baseline,scripts,compiler,fixture)
    assert value['losProbeVersion']==patch.VERSION and value['terminalOnly']
    assert r.sha(Path(value['sourceOrigin']))==value['sourceOriginSHA256']
    origin=r.read(Path(value['sourceOrigin']))
    old=seed()
    assert origin['seedReceiptSHA256']==SEED_SHA and origin['seedProbeSHA256']==SEED_PROBE
    assert origin['seedSourceSHA256']==old['frozenSourceSHA256']
    assert origin['changed']==['ContinuousSceneMotionProbe.as',patch.HELPER]
    assert origin['stagedSHA256']==value['frozenSourceSHA256']
    changed=sorted(k for k in set(old['frozenSourceSHA256'])|set(value['frozenSourceSHA256'])
        if old['frozenSourceSHA256'].get(k)!=value['frozenSourceSHA256'].get(k))
    assert changed==['ContinuousSceneMotionProbe.as',patch.HELPER]
    original=(Path(old['frozenSourcePath'])/'ContinuousSceneMotionProbe.as').read_text(encoding='utf-8-sig')
    assert (Path(value['frozenSourcePath'])/'ContinuousSceneMotionProbe.as').read_text(encoding='utf-8-sig')==patch.patch_text(original)
    assert r.sha(Path(value['frozenSourcePath'])/patch.HELPER)==r.sha(patch.SOURCE)
    return value

def main():
    assert __debug__,'Assertions required'
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name',required=True)
    parser.add_argument('--land',default='random_mane')
    candidate=parser.add_mutually_exclusive_group(required=True)
    candidate.add_argument('--compile-candidate',action='store_true')
    candidate.add_argument('--candidate-build',type=Path)
    probe=parser.add_mutually_exclusive_group(required=True)
    probe.add_argument('--compile-probe',action='store_true')
    probe.add_argument('--probe-build',type=Path)
    parser.add_argument('--registry-wait',type=int,default=600)
    args=parser.parse_args()
    assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
    folder=r.E/args.name;assert not folder.exists(),'Fresh evidence name required'
    with m.Registration(owner='ContinuousScene / TDFC LOS / 01a13816',purpose=args.name,
            run_dir=m.RUNTIME,evidence=folder,wait=args.registry_wait) as lease:
        assert not m.air_pids(),'Other AIR remains untouched'
        memory_gate()
        baseline,scripts,compiler,fixture=r.baseline(),runner_inputs(),base.support.compiler_inputs(),fixture_inputs()
        assert baseline['pfe.swf']==HOST and baseline[base.CS_PATH]==CS and baseline[TDFC_PATH]==TDFC
        cp=compile_candidate(lease,baseline,compiler) if args.compile_candidate else args.candidate_build.resolve()
        candidate=verify_candidate(cp,baseline,compiler)
        pp=compile_probe(lease,baseline,scripts,compiler,fixture) if args.compile_probe else args.probe_build.resolve()
        probe=verify_probe(pp,baseline,scripts,compiler,fixture)
        memory_gate();m.prepare()
        assert r.sha(m.RUNTIME/'pfe.swf')==HOST,'Use actual installed host unchanged'
        shutil.copy2(candidate['candidatePath'],m.RUNTIME/TDFC_PATH)
        shutil.copy2(probe['probePath'],m.RUNTIME/base.PROBE_PATH)
        assert r.sha(m.RUNTIME/TDFC_PATH)==candidate['candidateSHA256']
        assert r.sha(m.RUNTIME/base.PROBE_PATH)==probe['probeSHA256']
        control=m.RUNTIME/patch.CONTROL;assert not control.exists(),'Inspect stale control; never overwrite'
        controls=dict(version='tdfc-los-controls-1',hostSHA256=HOST,baseTDFCSHA256=TDFC,
            candidateSHA256=candidate['candidateSHA256'],componentSHA256=r.sha(patch.SOURCE),terminalOnly=True)
        options=['--name',args.name,'--high-qos','--land',args.land,'--benchmark','scene','--short',
            '--window-width','2048','--window-height','1123','--no-lighting','--no-wall','--presentation-check']
        assert baseline==r.baseline() and scripts==runner_inputs() and fixture==fixture_inputs()
        verify_candidate(cp,baseline,compiler);verify_probe(pp,baseline,scripts,compiler,fixture)
        r.save(control,controls);control_sha=r.sha(control)
        try:
            m.run_owned(m.parse_args(options),lease)
        finally:
            if folder.exists():
                r.save(folder/'candidate-build.json',candidate);r.save(folder/'probe-build.json',probe)
                r.save(folder/'runner-inputs.json',dict(options=options,baseline=baseline,runnerInputs=scripts,
                    compilerInputs=compiler,fixtureInputs=fixture,candidateBuildPath=str(cp),probeBuildPath=str(pp),
                    isolatedControl=controls,isolatedControlSHA256=control_sha,
                    overrideSources={TDFC_PATH:candidate['candidatePath'],base.PROBE_PATH:probe['probePath']},
                    copiedActualInstalledHost=True))
            if control.exists():
                assert r.sha(control)==control_sha,'Control changed during run'
                control.unlink()
        result,inputs=r.result(args.name)
        assert baseline==r.baseline() and scripts==runner_inputs() and fixture==fixture_inputs()
        assert compiler==base.support.compiler_inputs()
        verify_candidate(cp,baseline,compiler);verify_probe(pp,baseline,scripts,compiler,fixture)
        for name,digest in baseline.items():
            if name not in ('application.xml','mods/loader-manifest.txt',TDFC_PATH):assert inputs[name]==digest,name
        assert inputs[TDFC_PATH]==candidate['candidateSHA256'] and inputs[base.PROBE_PATH]==probe['probeSHA256']
        assert inputs[patch.CONTROL]==control_sha and result['tdfcLosControl']==controls
        policy=r.read(folder/'process-policy.json')
        assert policy['desktopPolicy']=='private' and not policy['performanceEligible']
        assert not policy.get('runFailure') and not policy.get('memoryAbort') and not policy['otherAirProcessIds']
        c=result['tdfcLosComponents']
        assert c['version']=='tdfc-los-components-1' and c['passed'] and c['terminalOnly'] and not c['performanceEligible']
        assert len(c['cases'])==38 and all(row['passed'] for row in c['cases'])
        assert c['cacheHits']>0 and c['nativeCalls']==76 and c['blockedCases']>=7 and c['fallbackCases']==10
        assert c['restore']['passed'] and c['restore']['restoredTiles']==25 and c['restore']['restoredFields']==125
        assert not c['restore']['errors'] and c['restore']['apiPublicStateRestored'] and c['restore']['terminalProcessRequired']
        assert not c['restore']['privateClassCacheRestored'] and c['noWorldStep']
        assert not result['samples'],'Terminal component must never enter performance windows'
        summary=dict(version=VERSION,name=args.name,qualification={'passed':True},componentsOnly=True,
            hostSHA256=HOST,baseTDFCSHA256=TDFC,candidateSHA256=candidate['candidateSHA256'],
            probeSHA256=probe['probeSHA256'],verification=c,diagnosticOnly=True,performanceEligible=False,
            performanceAcceptance=False,deployed=False,copiedActualInstalledHost=True,
            resultSHA256=r.sha(folder/'storage/result.json'),inputsSHA256=r.sha(folder/'inputs.json'))
        r.save(folder/'summary.json',summary)
        lease.outcome='passed';lease.note='38 real native LOS pairs and restoration passed; terminal component only'
        print(json.dumps(dict(name=args.name,passed=True,cases=len(c['cases']),cacheHits=c['cacheHits'],
            blockedCases=c['blockedCases'],fallbackCases=c['fallbackCases'],performanceEligible=False)),flush=True)

if __name__=='__main__':main()
