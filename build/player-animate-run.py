"""Registered player-only UnitPlayer.animate attribution, on a strictly retained BEFC host.

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
OUT = B/'generated/player-animate-profile-20261022'
FORMAL_HOST = 'BEFCF0509E11FAC9FEF7AFB834708B8B93752A14AE3D5CD72B42AA6D42F9B82A'
FORMAL_CS = '7F1F2961C6E299D949423591F3C65C610C2EAEFA7FC72E8A583A402770D6B51F'
HOST = 'E498FCEF3DBFB7FA4E46FCD864817038D6A22C3A92BF0AE28C196116EFFEAC8C'
HOST_XML = 'AB496A7395471BA93D1066AE65AF41727CB1412FA71CD7ED2F974B2AECCE68DB'
AUDIT = 'D67FE3FCA6377AA576F5450B5E34F7E845146B7A214D377E1D9777FCEEDF4A75'
TARGET = 'fe.unit.UnitPlayer::0:1:animate'
GROUPS = ('bodyState','headRotation','filters','otherVisual','eyes')
EARLY = ('animOff','die','lurk','unlurk','res','lurked')
CS_PATH = 'mods/ContinuousScene/release/ContinuousSceneMod.swf'
PROBE_PATH = 'mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


n=load('player_animate_frozen_probe_helpers',B/'native-combat-baseline-run.py')
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
    assert build['version']=='player-animate-profile-1' and build['target']==TARGET
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
    assert audit['timerBinding']['callCount']==build['timerCalls']==23
    assert audit['timerBinding']['allCallsDirectQualified']
    assert audit['activationProof']['diagnosticLocals']==4
    assert audit['activationProof']['receiverEvidence']['staticSlotAccess'] is False
    assert audit['nativeProjectionProof']['nativeCanonicalInstructions']==2041
    assert audit['nativeProjectionProof']['originalCallAndBranchOrderPreserved']
    assert audit['wrapperSHA256']==r.sha(B/'player-animate-profile-audit.py')
    assert all(r.sha(Path(path))==digest for path,digest in build['sourceInputs'].items())
    return build


def check_stats(stats):
    assert stats['version']=='player-animate-profile-1'
    assert stats['diagnosticOnly'] is True and stats['performanceEligible'] is False
    keys=('calls','totalMs','totalMaxMs','normalCalls','errorCalls')+tuple(x+'Calls' for x in EARLY)+tuple(
        group+suffix for group in GROUPS for suffix in ('Ms','Calls','MaxMs'))
    for key in keys:
        value=stats[key]
        assert isinstance(value,(int,float)) and not isinstance(value,bool)
        assert math.isfinite(value) and value>=0 and value==int(value),(key,value)
    assert stats['calls']==stats['normalCalls']==300
    assert stats['errorCalls']==0 and all(stats[x+'Calls']==0 for x in EARLY)
    assert stats['totalMaxMs']<=stats['totalMs']
    for group in GROUPS:
        assert stats[group+'Calls']==300
        assert stats[group+'MaxMs']<=stats[group+'Ms']
    assert sum(stats[g+'Ms'] for g in GROUPS)<=stats['totalMs']


def check_timeline(report):
    assert report['version']=='player-same-frame-timeline-1'
    assert report['diagnosticOnly'] and report['performanceEligible'] is False and report['terminalOnly']
    cleanup=report['cleanup']
    assert cleanup['listenersRemoved'] is True,'Terminal timeline listeners leaked'
    count=cleanup['bitmapsDisposed']
    assert isinstance(count,int) and not isinstance(count,bool) and 0<=count<=4
    # In completed paths: two oracle captures plus one for each native goto.
    # An exception can occur between allocation and adding its case; preserve
    # that diagnostic without requiring a successful or conclusive outcome.
    if not report.get('error'):
        assert count==(len(report['cases'])+1 if report['cases'] else 0),'Terminal capture cleanup count differs'


def summarize(result,name,mode,build):
    # Reuse the exact native-platform, camera, seed, shot and 30-frame population
    # assertions. Their camera/population limitations remain in the full receipt.
    summary=n.summarize(result,name,mode)
    cfg=result['config']
    assert cfg['playerAnimateProfile'] and not cfg.get('emptyTerrain',False)
    assert not any(cfg.get(key,False) for key in ('worldProfile','locationProfile','guiWeaponProfile','activityTelemetry','playerStepProfile'))
    timeline=result['playerTimelineChecks'];check_timeline(timeline)
    summary.update(purpose='player-only native UnitPlayer.animate section attribution',performanceEligible=False,
        diagnosticOnly=True,performanceAcceptance=False,deployed=False,hostSHA256=HOST,continuousSceneSHA256=FORMAL_CS,
        profilerLimitations=build['limitations'],playerTimelineChecks=timeline)
    for source,row in zip(result['samples'],summary['samples']):
        stats=source['playerAnimateProfile'];check_stats(stats)
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
    with m.Registration(owner='ContinuousScene / player animate attribution / 01a13816',purpose=args.name,
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
            '--no-lighting','--no-wall','--player-animate-profile']
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
        assert policy['performanceEligible'] is False and 'UnitPlayer.animate inclusive' in policy['diagnosticOnly']
        assert not policy.get('runFailure') and not policy.get('memoryAbort')
        r.save(r.E/args.name/'probe-build.json',probe)
        r.save(r.E/args.name/'runner-inputs.json',dict(options=options,baseline=baseline,hostBuild=build,
            probeBuildPath=str(receipt),runnerInputs=scripts,compilerInputs=compiler))
        summary=summarize(result,args.name,args.mode,build);summary['probeBuildPath']=str(receipt)
        r.save(r.E/args.name/'player-animate-profile-summary.json',summary)
        r.save(OUT/(args.name+'-summary.json'),summary)
        print(json.dumps(dict(name=args.name,mode=args.mode,diagnosticOnly=True,performanceEligible=False,
            deployed=False,probeBuildPath=str(receipt),samples=[{key:row[key] for key in
            ('name','frames','totalScript','playerShots','enemyShots','profilePerFrame','playerTotalMsPerFrame')}
            for row in summary['samples']])),flush=True)
        lease.outcome='passed';lease.note='Player-only UnitPlayer.animate attribution; no performance acceptance or deployment'


if __name__=='__main__':main()
