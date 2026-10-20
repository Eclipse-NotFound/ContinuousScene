"""Deploy only the three tested authoring artifacts; never replace the game host."""
from pathlib import Path
import argparse,importlib.util,json,shutil,os,datetime
spec=importlib.util.spec_from_file_location('builder',Path(__file__).with_name('large-map.py'));b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
ROOT,MOD,OUT=b.ROOT,b.MOD,b.OUT
RECEIPT=MOD/'state/deployment-v090.json'
TARGETS={'Editor.swf':'Editor.swf','Editor/Enhancements/EditorTools.swf':'EditorTools.swf','mods/ContinuousScene/release/ContinuousSceneMod.swf':'ContinuousSceneMod.swf'}
def data(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def evidence(folder,kind):
    p=Path(folder).resolve();r=data(p/'storage'/f'{kind}-result.json');assert r['ok'] and all(c['ok'] for c in r['checks']),p
    inputs={k.replace('\\','/'):v for k,v in data(p/'inputs.json').items()}
    if kind=='game':
        loader=data(p/'loader-check.json');assert len(loader['sessions'])==1 and all(loader['loaded'].values())
    assert data(p/'sample.json')['sha256']==b.sha(MOD/'maps/factory-rd.xml'),'sample changed'
    return {'path':str(p),'checks':len(r['checks']),'inputs':inputs,'resultSha256':b.sha(p/'storage'/f'{kind}-result.json')}
def replace(src,dst):
    temp=dst.with_name(dst.name+'.authoring-writing');assert not temp.exists(),temp
    shutil.copy2(src,temp);os.replace(temp,dst)
def audit(editor,game,installed=False):
    e=evidence(editor,'editor');g=evidence(game,'game')
    expected={p:b.sha(ROOT/p if installed else OUT/n) for p,n in TARGETS.items()}
    for p,h in expected.items():
        assert g['inputs'][p]==h,('game artifact differs',p)
        if p in e['inputs']:assert e['inputs'][p]==h,('editor artifact differs',p)
    for p,h in g['inputs'].items():
        if p in TARGETS or p.startswith('mods/SingleSceneProbe/'):continue
        assert b.sha(ROOT/p)==h,('dependency changed; retest without replacing it',p)
    assert b.sha(ROOT/'Editor/Enhancements/NativeScene.swf')==e['inputs']['Editor/Enhancements/NativeScene.swf']
    return e,g,expected
def deploy(editor,game):
    assert not RECEIPT.exists(),'Existing receipt: inspect before a new deployment'
    e,g,after=audit(editor,game);base=data(OUT/'baseline.json')
    before={p:b.sha(ROOT/p) for p in TARGETS}
    assert all(before[p]==base[p] for p in TARGETS),'Installed target changed; merge before deployment'
    backup=MOD/'build/backups'/('authoring-v090-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'));backup.mkdir(parents=True,exist_ok=False)
    for p,n in TARGETS.items():shutil.copy2(ROOT/p,backup/n);assert b.sha(backup/n)==before[p]
    active=MOD/'maps/active.xml'
    receipt={'status':'backed-up','time':datetime.datetime.now().isoformat(),'backup':str(backup),'before':before,'after':after,'editor':e,'game':g,'sampleSha256':b.sha(MOD/'maps/factory-rd.xml'),'activeCreated':not active.exists(),'activeBefore':b.sha(active) if active.exists() else None,'replaced':[]}
    b.save(RECEIPT,receipt)
    try:
        for p,n in TARGETS.items():
            assert b.sha(ROOT/p)==before[p] and b.sha(OUT/n)==after[p],'Concurrent target/candidate change'
            replace(OUT/n,ROOT/p);receipt['replaced'].append(p);b.save(RECEIPT,receipt);assert b.sha(ROOT/p)==after[p]
        if receipt['activeCreated']:
            with active.open('xb') as f:f.write((MOD/'maps/factory-rd.xml').read_bytes())
        receipt['status']='installed-pending-smoke';b.save(RECEIPT,receipt)
    except Exception:
        rollback();raise
    print(RECEIPT)
def verify(editor,game):
    receipt=data(RECEIPT);assert receipt['status']=='installed-pending-smoke'
    e,g,after=audit(editor,game,True);assert after==receipt['after']
    if receipt['activeCreated']:assert b.sha(MOD/'maps/active.xml')==receipt['sampleSha256'],'Applied map changed'
    receipt.update(status='verified',verifiedAt=datetime.datetime.now().isoformat(),installedEditor=e,installedGame=g);b.save(RECEIPT,receipt);print('Verified',e['checks']+g['checks'],'installed checks')
def rollback():
    receipt=data(RECEIPT);backup=Path(receipt['backup']);active=MOD/'maps/active.xml'
    for p in receipt['replaced']:
        assert b.sha(ROOT/p)==receipt['after'][p],('Refuse to overwrite a later version',p)
        assert b.sha(backup/TARGETS[p])==receipt['before'][p]
    if receipt['activeCreated'] and active.exists():assert b.sha(active)==receipt['sampleSha256'],'Refuse to remove an edited map'
    for p in receipt['replaced']:replace(backup/TARGETS[p],ROOT/p);assert b.sha(ROOT/p)==receipt['before'][p]
    if receipt['activeCreated'] and active.exists():
        assert active.resolve().parent==(MOD/'maps').resolve();active.unlink()
    receipt['status']='rolled-back';b.save(RECEIPT,receipt);print('Rolled back this deployment only')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['audit','deploy','verify','rollback']);p.add_argument('--editor');p.add_argument('--game');a=p.parse_args()
    if a.action=='rollback':rollback()
    else:
        assert a.editor and a.game,'Both completed test evidence paths are required'
        globals()[a.action](a.editor,a.game)
