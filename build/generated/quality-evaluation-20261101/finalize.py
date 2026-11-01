"""Stage only this investigation, preserving pre-existing state and WIP bytes."""
from pathlib import Path
import hashlib, io, json, subprocess, sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
REPO=ROOT/'mods/ContinuousScene'
sys.path.insert(0,str(ROOT/'mods/ModLoader/tools'))
from test_registry import Registry, ACTIVE

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest().upper()
def git(*args,data=None):
    return subprocess.run(['git','-C',str(REPO),*args],input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout

def main():
    resume=sys.argv[1:]==['--resume-own-state']
    assert not sys.argv[1:] or resume
    summary=json.loads((HERE/'summary.json').read_text('utf-8'))
    archive=json.loads((HERE/'archive.json').read_text('utf-8'))
    report='knowledge/experiments/quality-and-dense-enemies-20261101.md'
    paths=list(archive)+['.gitattributes',report]
    paths += [p.relative_to(REPO).as_posix() for p in HERE.iterdir() if p.is_file()]
    staged_names=set(git('diff','--cached','--name-only').decode().splitlines())
    own_paths=set(paths)|{'state/MEMORY.md','state/journal.md'}
    assert not staged_names or (resume and staged_names<=own_paths), 'Preserve existing index'
    assert summary['formalUnchanged'] and summary['foreignSourceUnchanged']
    assert sha(ROOT/'pfe.swf')==summary['host']
    assert all(sha(ROOT/k)==v for k,v in summary['formalMods'].items())
    assert sha(ROOT/'application.xml')==summary['formalDescriptor']['SHA256']
    assert sha(Path(summary['sharedFact']['path']))==summary['sharedFact']['SHA256']
    assert all(sha(REPO/k)==v for k,v in archive.items())
    active=[r for r in Registry().status() if r['state'] in ACTIVE and '01a13816' in r['owner']]
    assert not active,active
    foreign={'src/tests/SceneRenderChecks.as':sha(REPO/'src/tests/SceneRenderChecks.as')}
    for name in git('ls-files','--others','--exclude-standard','--','knowledge/experiments').decode('utf-8').splitlines():
        if name!=report:foreign[name]=sha(REPO/name)
    preserved={}
    for rel,note in [('state/MEMORY.md','memory-note.md'),('state/journal.md','journal-note.md')]:
        addition=(HERE/note).read_text('utf-8').strip()
        assert addition.startswith('<!-- quality-and-dense-20261101 -->')
        path=REPO/rel;old=path.read_bytes()
        def insertion(raw):
            eol=b'\r\n' if b'\r\n' in raw else b'\n'
            pos=raw.index(b'\n')+1 if rel.endswith('MEMORY.md') else 0
            payload=eol+addition.replace('\n',eol.decode()).encode('utf-8')+eol+eol
            return pos,payload
        if b'<!-- quality-and-dense-20261101 -->' in old:
            assert resume and old.count(b'<!-- quality-and-dense-20261101 -->')==1
            pos,payload=insertion(old)
            assert old[pos:pos+len(payload)]==payload
            old=old[:pos]+old[pos+len(payload):]
        def insert(raw):
            pos,payload=insertion(raw)
            return raw[:pos]+payload+raw[pos:]
        if path.read_bytes()!=insert(old):path.write_bytes(insert(old))
        preserved[rel]={'beforeSHA256':hashlib.sha256(old).hexdigest().upper(),'afterSHA256':sha(path),'preexistingBytesRetained':True}
        staged=insert(git('show','HEAD:'+rel))
        if rel in staged_names:assert git('show',':'+rel)==staged,rel
        blob=git('hash-object','-w','--stdin',data=staged).decode().strip()
        git('update-index','--cacheinfo','100644,'+blob+','+rel)
    families=sorted(set(Path(k).parts[2] for k in archive if k.startswith('build/generated/')))
    families.append(HERE.name)
    runs=sorted(set(Path(k).parts[3] for k in archive if k.startswith('knowledge/experiments/evidence/')))
    lines=['','# 2026-11-01 visual-tradeoff diagnostics: keep exact frozen bytes.']
    lines+=['build/generated/'+name+'/** -text whitespace=cr-at-eol' for name in families]
    lines+=['build/generated/'+name+'/compiler.log whitespace=cr-at-eol,-blank-at-eof' for name in families]
    lines+=['knowledge/experiments/evidence/'+name+'/** -text whitespace=cr-at-eol,-blank-at-eof' for name in runs]
    lines+=['knowledge/experiments/evidence/'+name+'/stderr.log whitespace=cr-at-eol,-blank-at-eof,-blank-at-eol' for name in runs]
    attributes=REPO/'.gitattributes'
    attribute_block=('\n'.join(lines)+'\n').encode('utf-8')
    # Two generated blank lines are part of the frozen compiler inputs; preserve their hashes.
    exceptions=''.join('build/generated/'+name+'/ContinuousSceneMotionMod.as whitespace=cr-at-eol,-blank-at-eol\n' for name in ('camera-temporal-present-v28-20261101','camera-temporal-target-v30-20261101')).encode('utf-8')
    if attribute_block in attributes.read_bytes():
        assert resume and (attributes.read_bytes().endswith(attribute_block) or attributes.read_bytes().endswith(attribute_block+exceptions))
    else:
        attributes.write_bytes(attributes.read_bytes()+attribute_block)
    if not attributes.read_bytes().endswith(exceptions):attributes.write_bytes(attributes.read_bytes()+exceptions)
    for rel,h in foreign.items():assert sha(REPO/rel)==h,rel
    git('add','-f','--pathspec-from-file=-','--pathspec-file-nul',data=b'\0'.join(p.encode('utf-8') for p in paths)+b'\0')
    objects=io.BytesIO(git('cat-file','--batch',data=''.join(':'+rel+'\n' for rel in archive).encode('utf-8')))
    for rel,h in archive.items():
        object_id,kind,size=objects.readline().strip().split()
        assert kind==b'blob',rel
        assert hashlib.sha256(objects.read(int(size))).hexdigest().upper()==h,rel
        assert objects.read(1)==b'\n',rel
    assert objects.read()==b''
    git('diff','--cached','--check')
    receipt=dict(ownActiveRegistryEntries=0,formalUnchanged=True,foreignFiles=foreign,
                 preservedState=preserved,frozenStagedFiles=len(archive),frozenBytesExact=True,
                 descriptorUnchanged=True,sharedFactSHA256=summary['sharedFact']['SHA256'],
                 performanceTargetAchieved=False,productionDeployment=None)
    with (HERE/'final-checks.json').open('x',encoding='utf-8') as f:json.dump(receipt,f,ensure_ascii=False,indent=2)
    git('add','-f','--',(HERE/'final-checks.json').relative_to(REPO).as_posix())
    print(json.dumps({k:v for k,v in receipt.items() if k not in ('foreignFiles','preservedState')}))

if __name__=='__main__':main()
