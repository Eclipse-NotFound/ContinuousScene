"""Exact-byte, registered deployment of the verified sight/threat changes.

Does not replace CS0.9.0, maps, the editor, or any other mod. Display experiments
are deliberately excluded. All inputs are rechecked before mutation.
"""
from pathlib import Path
from datetime import datetime
import argparse,hashlib,importlib.util,json,os,re,shutil,uuid
B=Path(__file__).resolve().parent;MOD=B.parent;ROOT=MOD.parent.parent
E=MOD/'knowledge/experiments/evidence'
RECEIPT=MOD/'state/performance-deployment-20261020.json'
TARGETS={
 'pfe.swf':('generated/fog-typed/pfe.swf','81C1BFB552AA8EFBB20CCF15CB404AB5D879F58515B466FF788A079F5F0EC015','BEFCF0509E11FAC9FEF7AFB834708B8B93752A14AE3D5CD72B42AA6D42F9B82A'),
 'mods/TDFC/release/TDFCMod.swf':('generated/tdfc-threat/TDFCMod.swf','03243196C99D6C4F1A2BE081598DBAE9B5D89A414BCD48E1F860232BCFDDE1E5','7ACD45193109267DBBF875240528048AD6F1D09FA3B8B36BAA6F98EBB5FDDCE5')}
def load(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
enemy=load('enemy',B/'enemy-speed.py');motion=enemy.motion
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def read(p):return json.loads(p.read_text('utf-8-sig'))
def save(p,value):p.write_text(json.dumps(value,ensure_ascii=False,indent=2),'utf-8')
def replace(src,dst):
 tmp=dst.with_name(dst.name+'.'+uuid.uuid4().hex+'.tmp')
 try:
  shutil.copy2(src,tmp);assert sha(tmp)==sha(src);os.replace(tmp,dst)
 finally:tmp.unlink(missing_ok=True)
def result(name):
 folder=E/name;r=read(folder/'storage/result.json');policy=read(folder/'process-policy.json')
 assert r['ok'] and not r.get('error'),name
 assert not policy['otherAirProcessIds'] and not policy.get('memoryAbort'),name
 assert all(x['ok'] for x in r['assertions']),name
 loader=read(folder/'loader-check.json')
 assert len(loader['sessions'])==1 and len(loader['loaded'])==15 and all(loader['loaded'].values()),name
 log=(folder/'storage/tdfc.log').read_text('utf-8-sig')
 assert not re.search(r'\[(?:error|ui-error)\]',log),('TDFC runtime error',name)
 return r,{k.replace('\\','/'):v for k,v in read(folder/'inputs.json').items()}
def baseline():
 paths=[ROOT/'pfe.swf',ROOT/'application.xml',ROOT/'mods/loader-manifest.txt']
 for line in (ROOT/'mods/loader-manifest.txt').read_text('utf-8-sig').splitlines():
  row=line.split('|')
  if len(row)!=5 or row[2]!='1':continue
  folder=ROOT/'mods'/row[0];paths.append(folder/'release'/(row[1]+'.swf'))
  for sub in ('release','config'):paths.extend(p for p in (folder/sub).rglob('*') if p.is_file() and p.suffix!='.swf')
  if row[0]=='LightAndDarkness':paths.append(folder/'atmosphere.json')
 return {p.relative_to(ROOT).as_posix():sha(p) for p in paths}
def preflight(prefix):
 assert '<content>pfe.swf</content>' in (ROOT/'application.xml').read_text('utf-8-sig')
 for target,(source,before,after) in TARGETS.items():
  assert sha(ROOT/target)==before,('Changed production',target)
  assert sha(B/source)==after,('Changed candidate',source)
 assert read(B/'generated/fog-typed/provenance.json')['version']=='fog-typed-20261020'
 assert read(B/'generated/fog-typed/strict-audit.json')['passed']
 values=baseline();checks=[]
 for suffix in ('normal','scene','native'):
  name=prefix+'-'+suffix;r,inputs=result(name)
  for path,current in values.items():
   if path in ('application.xml','mods/loader-manifest.txt'):continue # unique test descriptor / appended probe
   assert inputs.get(path)==(TARGETS[path][2] if path in TARGETS else current),('Dependency drift',name,path)
  if suffix!='native':
   assert len(r['samples'])==4 and all(len(s['frames'])==300 and s['empty']==0 for s in r['samples'])
  assert 'version v0.6.4-scene2' in (E/name/'storage/tdfc.log').read_text('utf-8-sig')
  checks.append({'name':name,'checks':len(r['assertions'])})
 for name in ('enemy-speed-20261020-typed-mane-pixels','enemy-speed-20261020-typed-plant-pixels','enemy-speed-20261020-components-r6-threat'):
  r,inputs=result(name);checks.append({'name':name,'checks':len(r['assertions'])})
  target='mods/TDFC/release/TDFCMod.swf' if name.endswith('threat') else 'pfe.swf'
  assert inputs[target]==TARGETS[target][2]
 return values,checks

def verified_probe(prefix):
 # Preserve the exact probe used for the completed candidate regression.
 # Subsequent diagnostic edits must not silently change the installed smoke.
 source=enemy.OUT/'ContinuousSceneProbe.swf'
 expected=read(E/(prefix+'-native')/'inputs.json')
 expected={k.replace('\\','/'):v for k,v in expected.items()}
 digest=expected['mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf']
 frozen=B/'generated'/'enemy-core-verified-probe.swf'
 if not frozen.exists():
  assert sha(source)==digest,'Tested probe changed before freezing'
  shutil.copy2(source,frozen)
 assert sha(frozen)==digest,'Frozen smoke probe changed'
 return frozen
def rollback(receipt):
 backup=Path(receipt['backup'])
 for target,(_,before,after) in TARGETS.items():
  assert sha(backup/target)==before
  assert sha(ROOT/target) in (before,after),('Concurrent change',target)
 for target,(_,before,after) in TARGETS.items():
  if sha(ROOT/target)==after:replace(backup/target,ROOT/target)
 receipt['status']='rolled-back';save(RECEIPT,receipt)
def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['check','deploy','rollback']);p.add_argument('--evidence',default='enemy-speed-20261020-core-candidate-r1');a=p.parse_args()
 if a.mode=='check':print(json.dumps(preflight(a.evidence)[1]));return
 with motion.Registration(owner='ContinuousScene / exact-byte performance deployment / 01a13816-367b-7261-8e11-ca9152565dd9',purpose=a.mode+' sight/threat candidates',run_dir=motion.RUNTIME,evidence=RECEIPT,wait=600) as lease:
  assert not motion.air_pids(),'AIR present; untouched'
  if a.mode=='rollback':rollback(read(RECEIPT));return
  assert not RECEIPT.exists(),'Existing receipt must be reviewed'
  values,checks=preflight(a.evidence);probe=verified_probe(a.evidence)
  backup=B/'backups'/('enemy-perf-'+datetime.now().strftime('%Y%m%d-%H%M%S'));backup.mkdir(parents=True,exist_ok=False)
  for target,(_,before,_) in TARGETS.items():
   dest=backup/target;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/target,dest);assert sha(dest)==before
  receipt={'version':'fog-typed-20261020 / TDFC0.6.4-scene2','status':'backed-up','time':datetime.now().astimezone().isoformat(),'backup':str(backup),'targets':TARGETS,'baseline':values,'checks':checks}
  save(RECEIPT,receipt)
  try:
   for path,digest in values.items():assert sha(ROOT/path)==digest,path
   for target,(source,_,after) in TARGETS.items():replace(B/source,ROOT/target);assert sha(ROOT/target)==after
   receipt['status']='installed-awaiting-smoke';save(RECEIPT,receipt)
   motion.prepare()
   shutil.copy2(probe,motion.RUNTIME/'mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf')
   smoke='enemy-speed-20261020-installed-native'
   motion.run_owned(motion.parse_args(['--name',smoke,'--suite','native','--high-qos']),lease)
   r,inputs=result(smoke)
   for path,before in values.items():
    expected=TARGETS[path][2] if path in TARGETS else before
    assert sha(ROOT/path)==expected,('Production dependency changed',path)
    if path not in ('application.xml','mods/loader-manifest.txt'):
     assert inputs[path]==expected,('Smoke dependency mismatch',path)
   receipt.update(status='verified',smoke={'name':smoke,'checks':len(r['assertions'])});save(RECEIPT,receipt)
  except BaseException:
   rollback(receipt);raise
  print(json.dumps({'status':receipt['status'],'backup':str(backup),'checks':sum(c['checks'] for c in checks)},ensure_ascii=False))
if __name__=='__main__':main()
