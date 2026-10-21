"""Deploy only the exact tested native-art reuse host; preserve other mods."""
from pathlib import Path
from datetime import datetime
import argparse, importlib.util, json, shutil, statistics
B=Path(__file__).resolve().parent;MOD=B.parent;ROOT=MOD.parent.parent
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
release=load('impact_release_helpers',B/'enemy-release.py')
motion=release.motion;sha=release.sha;read=release.read;save=release.save;replace=release.replace
OUT=B/'generated/impact-native-20261021'
RECEIPT=MOD/'state/impact-deployment-20261021.json'
BEFORE='7D423BD7B7DD7D2B997E692BD1E22EF520879CD42387C14653C116C15385BCD4'
AFTER='5432A3B9B6820A94AE15AC0A97B13C4EDC534D3DC6DBED12063E0FE47677B71D'
EVIDENCE=['native-pixels-r1','native-pixels-r2','native-battle-r1','native-lifecycle','native-sats','native-normal']

def preflight():
    build=read(OUT/'build.json');audit=read(OUT/'pfe.audit.json');art=read(OUT/'art.audit.json')
    assert sha(ROOT/'pfe.swf')==BEFORE,'Production host changed; reconcile first'
    assert sha(OUT/'pfe.swf')==build['candidate']==audit['finalHostSHA256']==AFTER
    assert build['base']==audit['sourceHostSHA256']==BEFORE and build['version']=='impact-art-1'
    assert sha(OUT/'source/fe/graph/Grafon.as')==build['source']
    assert sha(MOD/'src/native/scene-impact-art.as.inc')==build['fragment']
    assert audit['passed'] and audit['originalConstantPoolPreserved']
    assert audit['unchangedNamedMethodsAndInitializers']==4672 and audit['unchangedClassLayouts']==1015
    assert art['passed'] and art['classCount']==18 and sha(OUT/'pfe.xml')==art['hostXMLSHA256']
    assert '<content>pfe.swf</content>' in (ROOT/'application.xml').read_text('utf-8-sig')
    baseline=release.baseline();checked=[];coverage=set();native=False;combat=False;normal=False;sats=False;probe=None;component=None
    for suffix in EVIDENCE:
        name='combat-20261021-'+suffix;r,inputs=release.result(name)
        policy=read(release.E/name/'process-policy.json')
        assert not policy.get('runFailure') and not policy.get('diagnosticOnly'),('Invalid or diagnostic evidence',name)
        for path,digest in baseline.items():
            if path in ('application.xml','mods/loader-manifest.txt'):continue
            assert inputs.get(path)==(AFTER if path=='pfe.swf' else digest),('Dependency drift',name,path)
        assertions={item['name']:item for item in r['assertions']};cfg=r.get('config',{})
        if cfg.get('impactCheck'):
            assert r['impact']['version']=='impact-art-1'
            assert len(r['impact']['cases'])==23
            assert all(c['pixelMismatches']==c['revisionMismatches']==0 and c['dirtyMatches'] for c in r['impact']['cases'])
            assert 'impact-native-single-frame-fixture' in assertions and 'decal-history-end-only' in assertions
            coverage.add((cfg['land'],bool(cfg['noLighting']),bool(cfg['noWall']),bool(cfg['vision'])))
            trials=r['impact']['benchmark']
            if len(trials)==8:
                assert [x['mode'] for x in trials]==['original','candidate','candidate','original','candidate','original','original','candidate']
                old=[x['ms'] for x in trials if x['mode']=='original'];new=[x['ms'] for x in trials if x['mode']=='candidate']
                assert statistics.mean(new)<statistics.mean(old) and statistics.median(new)<statistics.median(old)
                component={'scope':'100 same-state native decal calls; not whole-game FPS','originalMs':old,'candidateMs':new}
        elif cfg.get('satsCheck'):
            assert all('sats-pixels-'+str(i) in assertions for i in range(7))
            assert 'sats-v-opens-native-ui' in assertions and 'sats-v-closes-and-resumes' in assertions
            sats=True;probe=inputs['mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf']
        elif cfg.get('encounter'):
            assert len(r['samples'])==4 and all(len(row['frames'])==300 and row['empty']==0 for row in r['samples'])
            assert 'enemies-fired' in assertions
            assert read(release.E/name/'process-policy.json')['performanceEligible']
            if cfg.get('impactABBA'):
                assert [row['impactEnabled'] for row in r['samples']]==[False,True,True,False]
                combat=True
            elif cfg.get('benchmark')=='normal':normal=True
        elif r.get('mode')=='native-map':
            assert all(key in assertions for key in ('base-remains-native','ordinary-return-keeps-native-generation',
                'new-mission-refreshes-generation','native-save-load-preserves-random-return-rule',
                'native-save-load-regenerates-large-mode','disabled-native-room-size'))
            native=True
        checked.append({'name':name,'checks':len(r['assertions'])})
    assert ('random_mane',True,True,False) in coverage
    assert ('random_plant',False,False,True) in coverage
    assert component and native and combat and normal and sats
    source=B/'generated/impact-tests-20261021/ContinuousSceneProbe.swf'
    assert probe and sha(source)==probe,'Smoke probe differs from accepted SATS/gameplay tests'
    return baseline,checked,source,component

def rollback(receipt):
    backup=Path(receipt['backup'])/'pfe.swf'
    assert sha(backup)==BEFORE
    current=sha(ROOT/'pfe.swf');assert current in (BEFORE,AFTER),'Concurrent host change; no overwrite'
    if current==AFTER:replace(backup,ROOT/'pfe.swf')
    receipt['status']='rolled-back';save(RECEIPT,receipt)

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['check','deploy','rollback']);a=p.parse_args()
    if a.mode=='check':print(json.dumps(preflight()[1]));return
    with motion.Registration(owner='ContinuousScene / impact deployment / 01a13816',purpose=a.mode+' verified native-art reuse',run_dir=motion.RUNTIME,evidence=RECEIPT,wait=300) as lease:
        assert not motion.air_pids(),'Other AIR present; untouched'
        if a.mode=='rollback':rollback(read(RECEIPT));return
        assert not RECEIPT.exists(),'Existing receipt requires review'
        baseline,checked,probe,component=preflight()
        backup=B/'backups'/('impact-'+datetime.now().strftime('%Y%m%d-%H%M%S'));backup.mkdir(parents=True,exist_ok=False)
        shutil.copy2(ROOT/'pfe.swf',backup/'pfe.swf');assert sha(backup/'pfe.swf')==BEFORE
        receipt={'status':'backed-up','time':datetime.now().astimezone().isoformat(),'version':'impact-art-1',
            'backup':str(backup),'candidateSHA256':AFTER,'beforeSHA256':BEFORE,'baseline':baseline,
            'checks':checked,'component':component,'wholeGameImprovementProven':False}
        save(RECEIPT,receipt)
        try:
            for path,digest in baseline.items():assert sha(ROOT/path)==digest,path
            replace(OUT/'pfe.swf',ROOT/'pfe.swf');assert sha(ROOT/'pfe.swf')==AFTER
            receipt['status']='installed-awaiting-smoke';save(RECEIPT,receipt)
            motion.prepare();shutil.copy2(probe,motion.RUNTIME/'mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf')
            name='combat-20261021-installed'
            motion.run_owned(motion.parse_args(['--name',name,'--impact-check','--expect-no-signs','--vision','--land','random_plant','--high-qos','--window-width','2048','--window-height','1123']),lease)
            r,inputs=release.result(name)
            policy=read(release.E/name/'process-policy.json')
            assert not policy.get('runFailure') and not policy.get('diagnosticOnly')
            assert r['impact']['version']=='impact-art-1' and len(r['assertions'])>=136
            for path,digest in baseline.items():
                expected=AFTER if path=='pfe.swf' else digest
                assert sha(ROOT/path)==expected,('Production drift',path)
                if path not in ('application.xml','mods/loader-manifest.txt'):assert inputs[path]==expected,path
            receipt.update(status='verified',smoke={'name':name,'checks':len(r['assertions'])});save(RECEIPT,receipt)
        except BaseException:
            rollback(receipt);raise
        lease.outcome='passed';lease.note='Exact tested host installed; independent installed-file pixel regression passed'
        print(json.dumps({'status':receipt['status'],'backup':str(backup),'candidate':AFTER}))
if __name__=='__main__':main()
