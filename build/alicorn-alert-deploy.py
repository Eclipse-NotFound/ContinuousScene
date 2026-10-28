"""Install exactly the verified pair, with concurrent-input checks and owned rollback."""
import importlib, json, os, shutil, uuid
from datetime import datetime,timezone
b=importlib.import_module('alicorn-alerts')

def main():
    proof=json.loads((b.OUT/'latest-test.json').read_text('utf-8'))
    assert proof['ok'] and proof['checks']==31
    audit=json.loads((b.OUT/'audit.json').read_text('utf-8'));assert audit['ok'] and audit['host']==proof['host']
    items=[('pfe.swf',b.OUT/'pfe.swf',b.EXPECTED,proof['host']),
           ('mods/ContinuousScene/release/ContinuousSceneMod.swf',b.OUT/'ContinuousSceneMod.swf',
            '7F1F2961C6E299D949423591F3C65C610C2EAEFA7FC72E8A583A402770D6B51F',proof['mod'])]
    for rel,candidate,old,new in items:
        assert b.sha(b.ROOT/rel)==old,('Concurrent installed update',rel)
        assert b.sha(candidate)==new,('Candidate changed after verification',rel)
    # The selected test dependencies must still match installed dependencies.
    inputs={key.replace('\\','/'):value for key,value in json.loads((b.Path(proof['evidence'])/'inputs.json').read_text('utf-8')).items()}
    assert b.sha(b.ROOT/'mods/ModLoader/release/ModLoaderMod.swf')==inputs['mods/ModLoader/release/ModLoaderMod.swf']
    untouched={str(p.relative_to(b.ROOT)):b.sha(p) for p in (b.ROOT/'mods').glob('*/release/*.swf') if p!=b.ROOT/items[1][0]}
    for rel in ('application.xml','mods/loader-manifest.txt','Editor.swf','Editor/Enhancements/EditorTools.swf','Editor/Enhancements/NativeScene.swf'):
        untouched[rel]=b.sha(b.ROOT/rel)
    token=datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]
    backup=b.MOD/'build/backups'/('alicorn-'+token);backup.mkdir(parents=True)
    staged=[];installed=[]
    for rel,candidate,old,new in items:
        target=b.ROOT/rel;copy=backup/rel;copy.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(target,copy);assert b.sha(copy)==old
        temp=target.with_name(target.name+'.alicorn-'+token+'.tmp');assert not temp.exists()
        shutil.copy2(candidate,temp);assert b.sha(temp)==new;staged.append(temp)
    try:
        for (rel,candidate,old,new),temp in zip(items,staged):
            target=b.ROOT/rel;assert b.sha(target)==old,('Concurrent update before replace',rel)
            os.replace(temp,target);installed.append((target,backup/rel,new))
            assert b.sha(target)==new
        for rel,digest in untouched.items():assert b.sha(b.ROOT/rel)==digest,('Unrelated input drift',rel)
    except BaseException:
        for target,copy,new in reversed(installed):
            if b.sha(target)==new:
                temp=target.with_name(target.name+'.rollback-'+token);shutil.copy2(copy,temp);os.replace(temp,target)
        raise
    receipt={'installedAt':datetime.now(timezone.utc).isoformat(),'version':'0.9.1',
        'host':proof['host'],'mod':proof['mod'],'priorHost':b.EXPECTED,'backup':str(backup),
        'verification':proof,'auditSHA256':b.sha(b.OUT/'audit.json'),
        'unchangedRuntimeInputs':untouched,'installedReadbackPassed':True,
        'reuse':'Exact tested bytes; same runtime paths and unchanged ModLoader. Preferences are backward-compatible and player storage is untouched.'}
    b.save(b.MOD/'state/alicorn-alert-deployment-20261028.json',receipt)
    print(json.dumps({'installed':True,'host':proof['host'],'mod':proof['mod'],'backup':str(backup)},ensure_ascii=False))

if __name__=='__main__':main()
