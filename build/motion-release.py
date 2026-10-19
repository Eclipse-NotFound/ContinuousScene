"""Exact-byte local deployment for the verified motion candidate only."""
from pathlib import Path
from datetime import datetime
import hashlib, importlib.util, json, os, shutil, sys, uuid

B=Path(__file__).resolve().parent;MOD=B.parent;ROOT=MOD.parent.parent
EVIDENCE=MOD/'knowledge/experiments/evidence'
RECEIPT=MOD/'state/deployment-v082.json'
TARGETS={
    'pfe.swf':('generated/motion-direction-rays/pfe.swf','02BFABE6A3B4881DFA1227515E71F2A8EA863D4B1B468FBE1D8008AEBA7D9240','81C1BFB552AA8EFBB20CCF15CB404AB5D879F58515B466FF788A079F5F0EC015'),
    'mods/ContinuousScene/release/ContinuousSceneMod.swf':('generated/motion-frozen-v082/ContinuousSceneMod.swf','241E48EA217D47932B6014B4AB213473E5FCF471E533CCB8F2CD91C4E15B02EA','CD65CEC6C763EF18B345BCC1208BAAA4911E02BDB1F557FE316EBBABFF9BD856'),
    'mods/WallBlend/release/WallBlendMod.swf':('generated/wb-motion-source/WallBlendMod.swf','0BD209A1763D1C08BCEEAA6415DC768AB3D18AD99BAD377B4D8C188EBD48DE5A','14112DA06214BCA51C6875D2527E73246DCB4C985CAADDA719EB4F77F1C0920D')}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest().upper()
def read(path):return json.loads(path.read_text('utf-8-sig'))
def save(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2),'utf-8')
def quiet():
    spec=importlib.util.spec_from_file_location('motion_test',B/'motion-test.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    assert not module.air_pids(),'AIR is running; leave it untouched'
def replace(source,target):
    temporary=target.with_name(target.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        shutil.copy2(source,temporary);assert sha(source)==sha(temporary)
        os.replace(temporary,target)
    finally:temporary.unlink(missing_ok=True)

def evidence(name):
    folder=EVIDENCE/name;r=read(folder/'storage/result.json');p=read(folder/'process-policy.json')
    assert r['ok'] and not r.get('error'),name
    assert not p['otherAirProcessIds'] and not p.get('memoryAbort'),name
    if name.endswith(('direction-benchmark','direction-cross')):
        assert p['performanceEligible'] and len(r['samples'])==4,name
        assert all(len(s['frames'])==300 and s['empty']==0 for s in r['samples']),name
    loader=read(folder/'loader-check.json')
    assert len(loader['sessions'])==1 and len(loader['loaded'])==15 and all(loader['loaded'].values()),name
    inputs={key.replace('\\','/'):value for key,value in read(folder/'inputs.json').items()}
    for relative,(_,_,after) in TARGETS.items():assert inputs[relative]==after,(name,relative)
    return {'name':name,'assertions':len(r['assertions'])},inputs

def preflight():
    quiet()
    for relative,(source,before,after) in TARGETS.items():
        assert sha(ROOT/relative)==before,('Production changed',relative)
        assert sha(B/source)==after,('Candidate changed',source)
    checks=[];allInputs=[]
    for name in ['direction-fog-mane','direction-fog-plant','direction-wall-pixels-r2',
                 'direction-benchmark','direction-cross','direction-native','direction-mechanics','direction-raster',
                 'direction-visual','direction-experience','lights-native','lights-scene']:
        check,inputs=evidence('motion-20261020-'+name);checks.append(check);allInputs.append(inputs)
    baseline={}
    for line in (ROOT/'mods/loader-manifest.txt').read_text('utf-8-sig').splitlines():
        fields=line.split('|')
        if len(fields)!=5 or fields[2]!='1':continue
        folder=ROOT/'mods'/fields[0]
        files=[folder/'release'/(fields[1]+'.swf')]
        for sub in ['release','config']:
            files.extend(p for p in (folder/sub).rglob('*') if p.is_file() and p.suffix!='.swf')
        if fields[0]=='LightAndDarkness':files.append(folder/'atmosphere.json')
        for path in files:
            relative=path.relative_to(ROOT).as_posix();digest=sha(path);baseline[relative]=digest
            expected=TARGETS[relative][2] if relative in TARGETS else digest
            for inputs in allInputs:assert inputs.get(relative)==expected,('Evidence dependency drift',relative)
    for rel in ['pfe.swf','application.xml','mods/loader-manifest.txt']:baseline[rel]=sha(ROOT/rel)
    audit=read(B/'generated/motion-direction-rays/combined.audit.json')
    assert audit['passed'] and audit['sourceHostSHA256']==TARGETS['pfe.swf'][1] and audit['finalHostSHA256']==TARGETS['pfe.swf'][2]
    return checks,baseline

def install():
    assert not RECEIPT.exists(),'Review the existing receipt before any new deployment'
    checks,baseline=preflight()
    backup=B/'backups'/('motion-v082-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
    backup.mkdir(parents=True,exist_ok=False)
    for relative,(_,before,_) in TARGETS.items():
        destination=backup/relative;destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/relative,destination);assert sha(destination)==before
    receipt={'version':'0.8.2','status':'backed-up','time':datetime.now().astimezone().isoformat(),
        'backup':str(backup),'targets':TARGETS,'baseline':baseline,'checks':checks}
    save(RECEIPT,receipt)
    try:
        for relative,digest in baseline.items():assert sha(ROOT/relative)==digest,relative
        for relative,(source,_,after) in TARGETS.items():replace(B/source,ROOT/relative);assert sha(ROOT/relative)==after
        receipt['status']='installed-awaiting-smoke';save(RECEIPT,receipt)
    except BaseException:
        for relative,(_,before,after) in TARGETS.items():
            current=sha(ROOT/relative)
            if current==after:replace(backup/relative,ROOT/relative)
            else:assert current==before,('Concurrent target change',relative)
        receipt['status']='rolled-back';save(RECEIPT,receipt);raise
    print(json.dumps({'status':receipt['status'],'checks':sum(c['assertions'] for c in checks),'backup':str(backup)}))

def rollback():
    quiet();r=read(RECEIPT);backup=Path(r['backup'])
    for relative,(_,before,after) in TARGETS.items():
        assert sha(ROOT/relative)==after and sha(backup/relative)==before,relative
    for relative in TARGETS:replace(backup/relative,ROOT/relative)
    r['status']='rolled-back';save(RECEIPT,r)

def verify():
    check,inputs=evidence('motion-20261020-installed-native')
    for relative,(_,_,after) in TARGETS.items():assert sha(ROOT/relative)==after
    r=read(RECEIPT)
    for relative,before in r['baseline'].items():
        if relative not in TARGETS:assert sha(ROOT/relative)==before,relative
    r['smoke']=check;r['status']='verified';save(RECEIPT,r);print('Verified installed bytes and native gameplay smoke')

if __name__=='__main__':
    {'check':lambda:print(json.dumps(preflight()[0])),'install':install,'rollback':rollback,'verify':verify}[sys.argv[1]]()
