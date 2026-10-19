"""Frozen native-entry wall regression. Uses launcher selection and hidden AIR desktop."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime

HERE = Path(__file__).resolve().parent
MOD = HERE.parent.parent
ROOT = MOD.parent.parent
OUT = MOD / 'build/generated/boundary-wall-20261019'
RUNTIME = OUT / 'runtime'
JAVA = Path('D:/Program Files/Adobe Animate 2024/jre/bin/java.exe')
TOOLS = ROOT / 'mods/Sandevistan/build/tools'
LAUNCHER = ROOT / 'mods/ModLoader/RemainsModLauncher.exe'
SOURCE_REV = '3882d90'
TARGET = Path('mods/ContinuousScene/release/ContinuousSceneMod.swf')
RECEIPT = MOD/'state/deployment-v081.json'
BASELINE_CS = 'B5E8110E11FE2DF8A748B223DFFA6E0EC42E4F61A931D4D4E065CC199EFA2F1B'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')


def command(args, **kw):
    try:
        return subprocess.run([str(a) for a in args], check=True, **kw)
    except subprocess.CalledProcessError as exc:
        if exc.stderr: print(exc.stderr.decode('gb18030', errors='replace'))
        raise


def inventory():
    data = command([LAUNCHER, '--list', '--json', '--no-ui'], capture_output=True).stdout
    return json.loads(data.decode('utf-8-sig', errors='replace'))


def compile_swf(doc, source, output):
    cfg = OUT / 'compiler.xml'
    extra = f'<path-element>{MOD}/src</path-element>' if source == HERE else ''
    cfg.write_text(f'''<flex-config xmlns="http://www.adobe.com/2006/flex-config">
<target-player>32.0</target-player><compiler><external-library-path><path-element>{TOOLS}/airsdk/frameworks/libs/air/airglobal.swc</path-element></external-library-path>
<source-path><path-element>{source}</path-element>{extra}</source-path><debug>false</debug><optimize>true</optimize></compiler></flex-config>''', encoding='utf-8')
    output.parent.mkdir(parents=True, exist_ok=True)
    command([JAVA, '-Xmx512m', '-Dsun.io.useCanonCaches=false', '-Djava.util.Arrays.useLegacyMergeSort=true', '-jar', TOOLS/'flexsdk/lib/mxmlc.jar',
             f'+flexlib={TOOLS}/flexsdk/frameworks', f'-load-config={cfg}', '-swf-version=32', '-use-network=false', '-static-link-runtime-shared-libraries=true', f'-output={output}', source/doc])


def descriptor(appid):
    (RUNTIME/'application.xml').write_text(f'''<?xml version="1.0" encoding="utf-8"?>
<application xmlns="http://ns.adobe.com/air/application/30.0"><id>{appid}</id><versionNumber>0.1.0</versionNumber>
<filename>BoundaryWallTest</filename><initialWindow><content>pfe.swf</content><visible>false</visible><width>1280</width><height>800</height><renderMode>direct</renderMode></initialWindow><supportedProfiles>extendedDesktop</supportedProfiles></application>''', encoding='utf-8')


def prepare():
    if (OUT/'baseline.json').exists():
        raise RuntimeError('Baseline already frozen')
    if sha(ROOT/TARGET) != BASELINE_CS:
        raise RuntimeError('This historical builder only supports the frozen 0.8.0 source; preserve newer releases')
    inv = inventory()
    if inv['gameVersion'] != '1.02' or inv['descriptor'] != 'application.xml':
        raise RuntimeError('Unexpected game descriptor')
    RUNTIME.mkdir(parents=True, exist_ok=True)
    for pattern in ('texture*.swf', 'sprite*.swf', 'sound*.swf', 'text_*.xml', 'lang.xml', 'pfe.swf'):
        for path in ROOT.glob(pattern): shutil.copy2(path, RUNTIME/path.name)
    for folder in ('Rooms', 'Music', 'Texture'):
        if (ROOT/folder).exists(): shutil.copytree(ROOT/folder, RUNTIME/folder, dirs_exist_ok=True)
    baseline = {}
    for row in inv['mods']:
        if not row['enabled']: continue
        source = ROOT/'mods'/row['directory']
        target = RUNTIME/'mods'/row['directory']
        for folder in ('release', 'config'):
            if (source/folder).exists(): shutil.copytree(source/folder, target/folder, dirs_exist_ok=True)
        if (source/'atmosphere.json').exists(): shutil.copy2(source/'atmosphere.json', target/'atmosphere.json')
        swf = source/'release'/(row['entry']+'.swf')
        baseline[str(swf.relative_to(ROOT))] = sha(swf)
    for rel in ('pfe.swf','mods/loader-manifest.txt','mods/ContinuousScene/release/scene.xml'):
        baseline[rel] = sha(ROOT/rel)
    for name in ('supported-mods.txt',):
        shutil.copy2(ROOT/'mods/ModLoader'/name, RUNTIME/'mods/ModLoader'/name)
    shutil.copy2(ROOT/'mods/loader-manifest.txt', RUNTIME/'mods/loader-manifest.txt')
    shutil.copy2(ROOT/'mods/ContinuousScene/release/ContinuousSceneMod.swf', OUT/'baseline.swf')
    descriptor('pfe-cs-boundary-prepare-'+uuid.uuid4().hex[:8])
    compile_swf('BoundaryWallProbeDoc.as', HERE, RUNTIME/'mods/BoundaryWallProbe/release/BoundaryWallProbeMod.swf')
    command([LAUNCHER, '--root', RUNTIME, '--only', ','.join(inv['selected']+['BoundaryWallProbeMod']), '--no-ui', '--report', OUT/'selection.json'], capture_output=True)
    save(OUT/'baseline.json', baseline)
    save(OUT/'inventory.json', inv)
    print('Frozen', len(baseline), 'baseline files', flush=True)


def candidate():
    source = OUT/'candidate-source'
    source.mkdir(exist_ok=True)
    for name in ('ContinuousSceneDoc.as','ContinuousSceneMod.as','NativeSceneAdapter.as','NativeSceneActivity.as'):
        content = command(['git','-C',MOD,'show',f'{SOURCE_REV}:src/{name}'],capture_output=True).stdout.decode('utf-8')
        if name=='ContinuousSceneMod.as':
            assert content.count('VERSION:String="0.8.0"')==1
            content=content.replace('VERSION:String="0.8.0"','VERSION:String="0.8.1"')
        if name=='NativeSceneAdapter.as':
            anchor='var space:Array=[],Tile:Class=getDefinitionByName("fe.loc.Tile") as Class,tile:*;'
            assert content.count(anchor)==1
            content=content.replace(anchor,'state.boundaryRestored=NativeSceneWalls.restore(land,regions);\n            '+anchor)
        (source/name).write_text(content,encoding='utf-8')
    shutil.copy2(MOD/'src/NativeSceneWalls.as',source/'NativeSceneWalls.as')
    compile_swf('ContinuousSceneDoc.as',source,OUT/'candidate.swf')
    save(OUT/'candidate-source.json',{p.name:sha(p) for p in source.glob('*.as')})
    print('Candidate',sha(OUT/'candidate.swf'))


def run(args):
    if not args.name or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name):
        raise RuntimeError('A new lowercase evidence name is required')
    evidence=MOD/'knowledge/experiments/evidence'/args.name
    evidence.mkdir(parents=True,exist_ok=False)
    choice=OUT/('candidate.swf' if args.variant=='candidate' else 'baseline.swf')
    if args.variant=='installed': choice=ROOT/'mods/ContinuousScene/release/ContinuousSceneMod.swf'
    shutil.copy2(choice,RUNTIME/'mods/ContinuousScene/release/ContinuousSceneMod.swf')
    appid='pfe-cs-boundary-'+uuid.uuid4().hex
    descriptor(appid)
    save(RUNTIME/'boundary-test.json',{'map':args.map,'enabled':not args.disabled})
    save(evidence/'hashes.json',{str(p.relative_to(RUNTIME)):sha(p) for p in RUNTIME.rglob('*.swf')})
    sys.path.insert(0,str(ROOT/'mods/ModLoader/tools'))
    from air_test_process import HiddenProcess
    started=time.time()
    with (evidence/'stdout.log').open('wb') as stdout, (evidence/'stderr.log').open('wb') as stderr:
        process=HiddenProcess([str(ROOT/'adl64.exe'),'-runtime',str(ROOT/'runtimes/air/win64'),str(RUNTIME/'application.xml')],cwd=RUNTIME,stdout=stdout,stderr=stderr)
        try:
            print('Owned hidden AIR',process.pid,flush=True)
            code=process.wait(210)
        finally:
            if process.poll() is None: process.kill();process.wait(15)
            process.close()
            descriptor_path=RUNTIME/'application.xml'
            if descriptor_path.exists() and f'<id>{appid}</id>' in descriptor_path.read_text(encoding='utf-8'):
                descriptor_path.unlink()
    store=Path(os.environ['APPDATA'])/appid/'Local Store'
    for p in store.glob('*'):
        if p.is_file() and p.suffix.lower() in ('.json','.log','.png'): shutil.copy2(p,evidence/p.name)
    save(evidence/'run.json',{'appid':appid,'exitCode':code,'seconds':time.time()-started,'hiddenDesktop':True,'variant':args.variant,'purpose':'functional-only'})
    result=json.loads((evidence/'boundary-result.json').read_text(encoding='utf-8-sig'))
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
    return 0 if result['ok'] else 1


def preflight(installed_hash=None):
    baseline=json.loads((OUT/'baseline.json').read_text(encoding='utf-8'))
    for rel,digest in baseline.items():
        expected=installed_hash if Path(rel)==TARGET and installed_hash else digest
        if sha(ROOT/rel)!=expected: raise RuntimeError('Production changed: '+rel)
    # Preserve configs and room templates too, not just compiled modules.
    for base in [RUNTIME/'Rooms']+[RUNTIME/'mods'/row['directory']/folder for row in json.loads((OUT/'inventory.json').read_text(encoding='utf-8'))['mods'] if row['enabled'] for folder in ('release','config')]:
        if not base.exists(): continue
        for path in base.rglob('*'):
            if path.is_file() and path.suffix.lower() in ('.xml','.json','.txt'):
                rel=path.relative_to(RUNTIME)
                if sha(path)!=sha(ROOT/rel): raise RuntimeError('Config or room changed: '+str(rel))
    atmosphere=Path('mods/LightAndDarkness/atmosphere.json')
    if sha(RUNTIME/atmosphere)!=sha(ROOT/atmosphere): raise RuntimeError('LAD atmosphere changed')
    return baseline


def rollback():
    receipt=json.loads(RECEIPT.read_text(encoding='utf-8'))
    target=ROOT/TARGET;backup=Path(receipt['backup'])
    if receipt['version']!='0.8.1' or sha(target)!=receipt['after'] or sha(backup)!=receipt['before']:
        raise RuntimeError('Refusing to overwrite newer files or use an altered backup')
    replace_file(backup,target)
    receipt['status']='rolled-back';save(RECEIPT,receipt)
    print('Rolled back only ContinuousSceneMod.swf')


def replace_file(source,target):
    temp=target.with_name(target.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        shutil.copy2(source,temp)
        if sha(source)!=sha(temp): raise RuntimeError('Replacement copy differs')
        os.replace(temp,target)
    finally:
        if temp.exists(): temp.unlink()


def install():
    if RECEIPT.exists(): raise RuntimeError('Installation receipt already exists; review it first')
    baseline=preflight();after=sha(OUT/'candidate.swf')
    if baseline[str(TARGET)] != BASELINE_CS:
        raise RuntimeError('Baseline module does not match the frozen source revision')
    checks=[]
    for name,enabled,map_id in [('boundary-candidate-mane-20261019',True,'random_mane'),('boundary-candidate-plant-20261019',True,'random_plant'),('boundary-disabled-mane-20261019',False,'random_mane')]:
        evidence=MOD/'knowledge/experiments/evidence'/name
        result=json.loads((evidence/'boundary-result.json').read_text(encoding='utf-8-sig'))
        hashes=json.loads((evidence/'hashes.json').read_text(encoding='utf-8'))
        if not result['ok'] or result['version']!='0.8.1' or result['enabled']!=enabled or result['map']!=map_id:
            raise RuntimeError('Runtime evidence is not green: '+name)
        for rel,digest in baseline.items():
            if Path(rel).suffix.lower()!='.swf': continue
            expected=after if Path(rel)==TARGET else digest
            if hashes.get(str(Path(rel)))!=expected: raise RuntimeError('Evidence dependency mismatch: '+rel)
        checks.append({'evidence':name,'assertions':len(result['checks'])})
    if sha(MOD/'src/NativeSceneWalls.as')!=sha(OUT/'candidate-source/NativeSceneWalls.as'):
        raise RuntimeError('Wall implementation changed after candidate compilation')
    backup=MOD/'build/backups'/('boundary-v081-'+datetime.now().strftime('%Y%m%d-%H%M%S'))/'ContinuousSceneMod.swf'
    backup.parent.mkdir(parents=True,exist_ok=False)
    shutil.copy2(ROOT/TARGET,backup)
    before=sha(backup)
    if before!=baseline[str(TARGET)]: raise RuntimeError('Backup differs from approved baseline')
    receipt={'version':'0.8.1','status':'backed-up','time':datetime.now().astimezone().isoformat(),'target':str(TARGET),'before':before,'after':after,'backup':str(backup),'checks':checks,'baseline':baseline,'sourceRevision':SOURCE_REV}
    save(RECEIPT,receipt)
    preflight()
    try:
        replace_file(OUT/'candidate.swf',ROOT/TARGET)
        preflight(after)
        receipt['status']='installed-awaiting-smoke';save(RECEIPT,receipt)
        smoke='boundary-installed-mane-20261019'
        if run(argparse.Namespace(name=smoke,variant='installed',map='random_mane',disabled=False)):
            raise RuntimeError('Installed functionality failed')
        preflight(after)
        receipt['status']='verified';receipt['smoke']=smoke;save(RECEIPT,receipt)
        print('Installed and verified ContinuousScene 0.8.1:',after,flush=True)
    except Exception:
        if sha(ROOT/TARGET)==after:
            replace_file(backup,ROOT/TARGET)
            receipt['status']='rolled-back-after-failure';save(RECEIPT,receipt)
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['prepare','probe','candidate','run','install','rollback','check'])
    parser.add_argument('--variant',choices=['baseline','candidate','installed'],default='baseline')
    parser.add_argument('--map',choices=['random_mane','random_plant'],default='random_mane')
    parser.add_argument('--name')
    parser.add_argument('--disabled',action='store_true')
    args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    if args.action=='prepare': prepare()
    elif args.action=='candidate': candidate()
    elif args.action=='probe': compile_swf('BoundaryWallProbeDoc.as',HERE,RUNTIME/'mods/BoundaryWallProbe/release/BoundaryWallProbeMod.swf')
    elif args.action=='install': install()
    elif args.action=='rollback': rollback()
    elif args.action=='check': preflight();print('Production inputs match the tested baseline')
    else: sys.exit(run(args))
