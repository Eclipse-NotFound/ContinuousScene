"""Install only the exact tested Grafon host, with guarded backup and smoke."""
from pathlib import Path
from datetime import datetime
import argparse, importlib.util, json, shutil
B=Path(__file__).resolve().parent;MOD=B.parent;ROOT=MOD.parent.parent
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
release=load('sats_release_helpers',B/'enemy-release.py')
motion=release.motion;sha=release.sha;read=release.read;save=release.save;replace=release.replace
OUT=B/'generated/sats-viewport-20261021-combined'
RECEIPT=MOD/'state/sats-deployment-20261021.json'
SPEC=B/'generated/sats-acceptance.json'
BEFORE='BEFCF0509E11FAC9FEF7AFB834708B8B93752A14AE3D5CD72B42AA6D42F9B82A'
def preflight():
    spec=read(SPEC);build=read(OUT/'build.json');audit=read(OUT/'pfe.audit.json')
    after=sha(OUT/'pfe.swf')
    assert sha(ROOT/'pfe.swf')==BEFORE,'Production host changed; reconcile first'
    assert after==spec['candidateSHA256']==build['candidateHostSHA256']==audit['finalHostSHA256']
    assert build['baseHostSHA256']==audit['sourceHostSHA256']==BEFORE
    assert build['version']=='sats-viewport-1' and audit['passed'] and audit['originalConstantPoolPreserved']
    assert audit['unchangedNamedMethodsAndInitializers']==4672 and audit['unchangedClassLayouts']==1015
    assert '<content>pfe.swf</content>' in (ROOT/'application.xml').read_text('utf-8-sig')
    baseline=release.baseline();checked=[];coverage=set();native=False;movement=False;probe=None
    for name in spec['evidence']:
        result,inputs=release.result(name)
        for path,digest in baseline.items():
            if path in ('application.xml','mods/loader-manifest.txt'):continue
            assert inputs.get(path)==(after if path=='pfe.swf' else digest),('Dependency drift',name,path)
        assertions={item['name']:item for item in result['assertions']}
        cfg=result.get('config',{})
        if cfg.get('satsCheck'):
            assert all('sats-pixels-'+str(i) in assertions for i in range(7))
            assert 'sats-v-opens-native-ui' in assertions and 'sats-v-closes-and-resumes' in assertions
            assert 'decal-history-end-only' in assertions
            coverage.add((cfg['land'],bool(cfg['noLighting']),bool(cfg['noWall']),bool(cfg['vision'])))
            probe=inputs['mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf']
        elif cfg.get('encounter') and cfg.get('benchmark')=='scene':
            assert all(len(row['frames'])==300 and row['empty']==0 for row in result['samples'])
            assert len(result['samples'])==4 and 'enemies-fired' in assertions
            policy=read(release.E/name/'process-policy.json');assert policy['performanceEligible']
            movement=True
        elif result.get('mode')=='native-map':
            assert len(result['assertions'])>=51
            assert all(key in assertions for key in ('base-remains-native','ordinary-return-keeps-native-generation',
                'new-mission-refreshes-generation','native-save-load-preserves-random-return-rule',
                'native-save-load-regenerates-large-mode','disabled-native-room-size'))
            native=True
        checked.append({'name':name,'checks':len(result['assertions'])})
    assert ('random_mane',True,True,False) in coverage
    assert ('random_plant',False,False,True) in coverage
    assert native and movement,('Missing lifecycle/combat evidence',native,movement)
    source=B/'generated/sats-tests-20261021/ContinuousSceneProbe.swf'
    assert probe and sha(source)==probe,'Smoke probe differs from accepted tests'
    return baseline,checked,after,source
def rollback(receipt):
    before=Path(receipt['backup'])/'pfe.swf'
    assert sha(before)==BEFORE
    current=sha(ROOT/'pfe.swf')
    assert current in (BEFORE,receipt['candidateSHA256']),'Concurrent host change; no overwrite'
    if current!=BEFORE:replace(before,ROOT/'pfe.swf')
    receipt['status']='rolled-back';save(RECEIPT,receipt)
def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['check','deploy','rollback']);a=p.parse_args()
    if a.mode=='check':print(json.dumps(preflight()[1]));return
    with motion.Registration(owner='ContinuousScene / SATS deployment / 01a13816',purpose=a.mode+' exact tested SATS host',run_dir=motion.RUNTIME,evidence=RECEIPT,wait=300) as lease:
        assert not motion.air_pids(),'Other AIR running; untouched'
        if a.mode=='rollback':rollback(read(RECEIPT));return
        assert not RECEIPT.exists(),'Existing receipt requires review'
        baseline,checked,after,probe=preflight()
        backup=B/'backups'/('sats-'+datetime.now().strftime('%Y%m%d-%H%M%S'));backup.mkdir(parents=True,exist_ok=False)
        shutil.copy2(ROOT/'pfe.swf',backup/'pfe.swf');assert sha(backup/'pfe.swf')==BEFORE
        receipt={'status':'backed-up','time':datetime.now().astimezone().isoformat(),'version':'sats-viewport-1',
                 'backup':str(backup),'candidateSHA256':after,'beforeSHA256':BEFORE,'baseline':baseline,'checks':checked}
        save(RECEIPT,receipt)
        try:
            for path,digest in baseline.items():assert sha(ROOT/path)==digest,path
            replace(OUT/'pfe.swf',ROOT/'pfe.swf');assert sha(ROOT/'pfe.swf')==after
            receipt['status']='installed-awaiting-smoke';save(RECEIPT,receipt)
            motion.prepare();shutil.copy2(probe,motion.RUNTIME/'mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf')
            name='sats-20261021-installed'
            motion.run_owned(motion.parse_args(['--name',name,'--sats-check','--expect-no-signs','--vision','--land','random_plant','--high-qos','--window-width','2048','--window-height','1123']),lease)
            result,inputs=release.result(name)
            for path,digest in baseline.items():
                expected=after if path=='pfe.swf' else digest
                assert sha(ROOT/path)==expected,('Production drift',path)
                if path not in ('application.xml','mods/loader-manifest.txt'):assert inputs[path]==expected,path
            receipt.update(status='verified',smoke={'name':name,'checks':len(result['assertions'])});save(RECEIPT,receipt)
        except BaseException:
            rollback(receipt);raise
        lease.outcome='passed';lease.note='Installed exact tested host; independent installed-file SATS/decal smoke passed'
        print(json.dumps({'status':receipt['status'],'backup':str(backup),'candidate':after}))
if __name__=='__main__':main()
