"""Finish the archive after preserving raw CR-CR-LF native trace logs."""
from pathlib import Path
import hashlib,json,subprocess,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4];REPO=ROOT/'mods/ContinuousScene'
sys.path.insert(0,str(ROOT/'mods/ModLoader/tools'))
from test_registry import Registry,ACTIVE
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def git(*args):return subprocess.run(['git','-C',str(REPO),*args],capture_output=True,check=True).stdout
def main():
    summary=json.loads((HERE/'summary.json').read_text('utf-8'))
    files={k.replace('\\','/'):v for k,v in json.loads((HERE/'archive.json').read_text('utf-8')).items()}
    attrs=REPO/'.gitattributes';raw=attrs.read_bytes();addition=[]
    for rel in files:
        if rel.endswith('/stderr.log'):
            line=rel+' whitespace=cr-at-eol,-blank-at-eof,-blank-at-eol'
            if line.encode() not in raw:addition.append(line)
    if addition:attrs.write_bytes(raw+('\n# Preserve native trace CR-CR-LF bytes.\n'+'\n'.join(addition)+'\n').encode())
    git('add','--','.gitattributes')
    git('add','-f','--',*[p.relative_to(REPO).as_posix() for p in HERE.iterdir() if p.is_file()])
    for rel,h in files.items():
        assert sha(REPO/rel)==h,rel
        assert hashlib.sha256(git('show',':'+rel)).hexdigest().upper()==h,rel
    preserved={}
    start=b'<!-- lossless-cut-survey-20261101 -->';end=b'<!-- /lossless-cut-survey-20261101 -->'
    def remove_note(data):
        assert data.count(start)==data.count(end)==1
        eol=b'\r\n' if b'\r\n' in data else b'\n'
        a=data.index(start)-len(eol);b=data.index(end)+len(end)+2*len(eol)
        assert data[a:a+len(eol)]==eol and data[b-2*len(eol):b]==eol*2
        return data[:a]+data[b:]
    for rel in ('state/MEMORY.md','state/journal.md'):
        staged=git('show',':'+rel);head=git('show','HEAD:'+rel)
        assert remove_note(staged)==head,rel
        work=(REPO/rel).read_bytes();before=remove_note(work)
        preserved[rel]={'reconstructedBeforeSHA256':hashlib.sha256(before).hexdigest().upper(),
                        'workingSHA256':sha(REPO/rel),'stagingContainsOnlyOwnAddition':True}
    assert sha(ROOT/'pfe.swf')==summary['host']
    assert all(sha(ROOT/k)==v for k,v in summary['formalMods'].items())
    assert sha(REPO/'src/tests/SceneRenderChecks.as')=='41DF71EE976EAD95CFFC1989CD9EF70A7C2FF0C24D541C4A3AD78A9F5B050983'
    active=[r for r in Registry().status() if r['state'] in ACTIVE and '01a13816' in r['owner']]
    assert not active,active
    git('diff','--cached','--check')
    result={'formalHost':summary['host'],'formalModCount':14,'formalUnchanged':True,
            'ownActiveRegistryEntries':0,'frozenStagedFiles':len(files),'frozenStagedBytesExact':True,
            'foreignTestSourceUnchanged':True,'preservedState':preserved,
            'whitespaceCheckPassed':True,'whitespaceException':'Only frozen native stderr CR-CR-LF and documented donor/compile log whitespace',
            'diagnosticIntervals':summary['totalIntervals'],'performanceTargetAchieved':False}
    with (HERE/'final-checks.json').open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    git('add','-f','--',(HERE/'final-checks.json').relative_to(REPO).as_posix())
    print(json.dumps({k:v for k,v in result.items() if k!='preservedState'},ensure_ascii=False))
if __name__=='__main__':main()
