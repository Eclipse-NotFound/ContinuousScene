"""Registered player-only Unit.step attribution, on a strictly retained BEFC host.

Compile one frozen probe and reuse its receipt for scene/normal room comparisons.
Four 300-frame segments preserve six armed enemies and real fire on both sides.
This runner never deploys; instrumented frame times are not acceptance evidence.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import math
import shutil
import sys

sys.dont_write_bytecode = True
B = Path(__file__).resolve().parent
OUT = B/'generated/player-step-profile-20261022'
FORMAL_HOST = 'BEFCF0509E11FAC9FEF7AFB834708B8B93752A14AE3D5CD72B42AA6D42F9B82A'
FORMAL_CS = '7F1F2961C6E299D949423591F3C65C610C2EAEFA7FC72E8A583A402770D6B51F'
HOST = '00A1D7A3A652164D439806966810D620D32102C156E9DA03E378C7D7DD862007'
HOST_XML = '8019E38496E34F1176E76E74FFDBD286DD2F41133A6DCC7DD4205BC0F7495307'
AUDIT = '696EB91601C67714F7216044F5FE420D500B6F89A0A24D15625239BEA8720358'
TARGET = 'fe.unit.Unit::0:1:step'
GROUPS = ('pre','forces','control','run','checkWater','actions','position','animate','children','sound')
CS_PATH = 'mods/ContinuousScene/release/ContinuousSceneMod.swf'
PROBE_PATH = 'mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


n=load('player_step_frozen_probe_helpers',B/'native-combat-baseline-run.py')
r,m=n.r,n.m
# Private module configuration only: the shared helper file remains unchanged.
n.OUT=OUT/'frozen-probes'


def runner_inputs():
    paths=(Path(__file__),B/'native-combat-baseline-run.py',B/'enemy-release.py',B/'enemy-speed.py',
        B/'motion-test.py',B/'profile-vision.py',r.ROOT/'mods/ModLoader/tools/test_registry.py',
        r.ROOT/'mods/ModLoader/tools/air_test_process.py')
    return {str(p):r.sha(p) for p in paths}


n.runner_inputs=runner_inputs


def audited_host():
    for label,digest in (('host',HOST),('XML',HOST_XML),('audit',AUDIT)):
        if not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789ABCDEF' for c in digest):
            raise RuntimeError('Unpinned player profiler '+label+'; no compile or AIR allowed')
    build,audit=r.read(OUT/'build.json'),r.read(OUT/'semantic-audit.json')
    assert build['version']=='player-step-profile-1' and build['target']==TARGET
    assert build['diagnosticOnly'] and not build['performanceEligible'] and not build['deployed']
    assert build['base']==FORMAL_HOST and build['groups']==list(GROUPS)
    assert r.sha(OUT/'pfe.swf')==build['candidate']==audit['candidateSHA256']==HOST
    assert r.sha(OUT/'pfe.xml')==build['candidateXML']==audit['candidateXMLSHA256']==HOST_XML
    assert r.sha(OUT/'semantic-audit.json')==build['audit']==AUDIT
    assert audit['passed'] and audit['diagnosticOnly'] and not audit['performanceEligible']
    assert audit['auditTarget']==TARGET and audit['actualChangedBodies']==[TARGET]
    assert audit['baseSHA256']==FORMAL_HOST and audit['preservedOriginalLayout'] is True
    assert audit['constructorsPreserved'] and audit['nonABCSWFEnvelopePreserved'] and audit['originalConstantPoolPreserved']
    assert not audit['addedFields'] and not audit['addedMethods']
    assert audit['unchangedMethodBodies']==5770 and audit['unchangedClassLayouts']==1016
    assert audit['timerBinding']['callCount']==build['timerCalls']==25
    assert audit['timerBinding']['allCallsDirectQualified']
    assert audit['activationProof']['diagnosticLocals']==4
    assert audit['activationProof']['receiverEvidence']['staticSlotAccess'] is False
    assert audit['nativeProjectionProof']['nativeCanonicalInstructions']==355
    assert audit['nativeProjectionProof']['originalCallAndBranchOrderPreserved']
    assert audit['wrapperSHA256']==r.sha(B/'player-step-profile-audit.py')
    assert all(r.sha(Path(path))==digest for path,digest in build['sourceInputs'].items())
    return build


def check_stats(stats):
    assert stats['version']=='player-step-profile-1'
    assert stats['diagnosticOnly'] is True and stats['performanceEligible'] is False
    keys=('calls','totalMs','totalMaxMs','normalCalls','disabledCalls','emergenceCalls','errorCalls')+tuple(
        group+suffix for group in GROUPS for suffix in ('Ms','Calls','MaxMs'))
    for key in keys:
        value=stats[key]
        assert isinstance(value,(int,float)) and not isinstance(value,bool)
        assert math.isfinite(value) and value>=0 and value==int(value),(key,value)
    assert stats['calls']==stats['normalCalls']==300
    assert stats['disabledCalls']==stats['emergenceCalls']==stats['errorCalls']==0
    assert stats['totalMaxMs']<=stats['totalMs']
    for group in GROUPS:
        assert stats[group+'Calls']==300
        assert stats[group+'MaxMs']<=stats[group+'Ms']
    assert sum(stats[g+'Ms'] for g in GROUPS)<=stats['totalMs']


def summarize(result,name,mode,build):
    # Reuse the exact native-platform, camera, seed, shot and 30-frame population
    # assertions. Their camera/population limitations remain in the full receipt.
    summary=n.summarize(result,name,mode)
    cfg=result['config']
    assert cfg['playerStepProfile'] and not cfg.get('emptyTerrain',False)
    assert not any(cfg.get(key,False) for key in ('worldProfile','locationProfile','guiWeaponProfile','activityTelemetry'))
    summary.update(purpose='player-only native Unit.step section attribution',performanceEligible=False,
        diagnosticOnly=True,performanceAcceptance=False,deployed=False,hostSHA256=HOST,continuousSceneSHA256=FORMAL_CS,
        profilerLimitations=build['limitations'])
    for source,row in zip(result['samples'],summary['samples']):
        stats=source['playerStepProfile'];check_stats(stats)
        row.update(profile=stats,profilePerFrame={group:stats[group+'Ms']/300 for group in GROUPS},
            playerTotalMsPerFrame=stats['totalMs']/300,
            unattributedDiagnosticOverheadMsPerFrame=(stats['totalMs']-sum(stats[g+'Ms'] for g in GROUPS))/300)
    return summary


def main():
    if not __debug__:raise RuntimeError('Assertions required; do not use -O')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name',required=True)
    parser.add_argument('--mode',choices=['scene','normal'],default='scene')
    probe_source=parser.add_mutually_exclusive_group(required=True)
    probe_source.add_argument('--compile-probe',action='store_true')
    probe_source.add_argument('--probe-build',type=Path)
    parser.add_argument('--registry-wait',type=int,default=600)
    args=parser.parse_args()
    assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
    assert not (r.E/args.name).exists(),'Use fresh evidence name'
    audited_host()
    with m.Registration(owner='ContinuousScene / player step attribution / 01a13816',purpose=args.name,
            run_dir=m.RUNTIME,evidence=r.E/args.name,wait=args.registry_wait) as lease:
        assert not m.air_pids(),'Other AIR present; untouched'
        baseline,scripts,compiler=r.baseline(),runner_inputs(),n.compiler_inputs()
        assert baseline['pfe.swf']==FORMAL_HOST and baseline[CS_PATH]==FORMAL_CS
        build=audited_host()
        receipt=n.compile_frozen_probe(lease,baseline,scripts,compiler) if args.compile_probe else args.probe_build.resolve()
        probe=n.verify_probe(receipt,baseline,scripts,compiler)
        m.prepare()
        shutil.copy2(OUT/'pfe.swf',m.RUNTIME/'pfe.swf')
        shutil.copy2(probe['probePath'],m.RUNTIME/PROBE_PATH)
        assert r.sha(m.RUNTIME/'pfe.swf')==HOST and r.sha(m.RUNTIME/CS_PATH)==FORMAL_CS
        assert r.sha(m.RUNTIME/PROBE_PATH)==probe['probeSHA256']
        assert baseline==r.baseline() and scripts==runner_inputs() and compiler==n.compiler_inputs()
        assert build==audited_host();n.verify_probe(receipt,baseline,scripts,compiler)
        options=['--name',args.name,'--high-qos','--land','random_mane','--encounter','--fixed-enemies',
            '--benchmark',args.mode,'--speed','4','--short','--stable-motion','--player-fire',
            '--combat-route','--combat-route-length','200','--window-width','2048','--window-height','1123',
            '--no-lighting','--no-wall','--player-step-profile']
        if args.mode=='normal':options+=['--native-room-x','2','--native-room-y','4','--native-route-x','480','--native-route-y','119']
        else:options+=['--expect-no-signs']
        m.run_owned(m.parse_args(options),lease)
        result,inputs=r.result(args.name)
        assert baseline==r.baseline() and scripts==runner_inputs() and compiler==n.compiler_inputs()
        assert build==audited_host();n.verify_probe(receipt,baseline,scripts,compiler)
        for path,digest in baseline.items():
            if path not in ('application.xml','mods/loader-manifest.txt'):
                assert inputs[path]==(HOST if path=='pfe.swf' else digest),path
        assert inputs[PROBE_PATH]==probe['probeSHA256'] and inputs[CS_PATH]==FORMAL_CS
        policy=r.read(r.E/args.name/'process-policy.json')
        assert policy['performanceEligible'] is False and 'Unit.step player-only' in policy['diagnosticOnly']
        assert not policy.get('runFailure') and not policy.get('memoryAbort')
        r.save(r.E/args.name/'probe-build.json',probe)
        r.save(r.E/args.name/'runner-inputs.json',dict(options=options,baseline=baseline,hostBuild=build,
            probeBuildPath=str(receipt),runnerInputs=scripts,compilerInputs=compiler))
        summary=summarize(result,args.name,args.mode,build);summary['probeBuildPath']=str(receipt)
        r.save(r.E/args.name/'player-step-profile-summary.json',summary)
        r.save(OUT/(args.name+'-summary.json'),summary)
        print(json.dumps(dict(name=args.name,mode=args.mode,diagnosticOnly=True,performanceEligible=False,
            deployed=False,probeBuildPath=str(receipt),samples=[{key:row[key] for key in
            ('name','frames','totalScript','playerShots','enemyShots','profilePerFrame','playerTotalMsPerFrame')}
            for row in summary['samples']])),flush=True)
        lease.outcome='passed';lease.note='Player-only Unit.step attribution; no performance acceptance or deployment'


if __name__=='__main__':main()
