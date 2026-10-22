"""Prepare only the r3 sleeping-root probe helper; never compile, run AIR or deploy.

Reuses the exact r2 diagnostic CS binary. Only a frozen copy of the r2 helper is
changed, and every change has a reversible textual proof. Live src is not read.
"""
from pathlib import Path
import argparse
import ast
import difflib
import hashlib
import json
import re
import sys

sys.dont_write_bytecode=True
B=Path(__file__).resolve().parent
MOD,ROOT=B.parent,B.parent.parent.parent
R2=B/'generated/sleeping-root-20261022-r2'
OUT=B/'generated/sleeping-root-20261022-r3'
BASE_SHA='7F1F2961C6E299D949423591F3C65C610C2EAEFA7FC72E8A583A402770D6B51F'
HOST_SHA='BEFCF0509E11FAC9FEF7AFB834708B8B93752A14AE3D5CD72B42AA6D42F9B82A'
R2_NATIVE='76748C8EDF4B3320B330ED60A84AE6C179A63DE52B24C42DD82333501ADA0172'
R2_PROVENANCE='AF87F1EF61253FB6467A585077792A786A9EC35619E62787D225987B908B4629'
R2_BUILD='2BFF64E1C1F62D3594F26F47E35818CFF9B67D51FFF345D238693CE585C07225'
R2_HELPER='EC51EE9B9AB8BE14585DD279DF08B76E77E0B7E0082BB4F9E56DB2D5A6E787FC'
CLASSES=('UnitSlime','UnitBat','UnitBloat','UnitMonstrik','UnitAnt','UnitTurret','UnitVortex')
FILES=('ContinuousSceneDoc.as','ContinuousSceneMod.as','NativeSceneAdapter.as',
       'NativeSceneActivity.as','NativeSceneWalls.as','SingleSceneDocument.as')
HELPER='SceneSleepingRootPresentation.as'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()
def digest(data):return hashlib.sha256(data).hexdigest().upper()
def read(path):return json.loads(Path(path).read_text('utf-8-sig'))


def frozen_native_proof():
    assert sha(ROOT/'pfe.swf')==HOST_SHA
    assert sha(MOD/'release/ContinuousSceneMod.swf')==BASE_SHA
    paths={R2/'source-provenance.json':R2_PROVENANCE,R2/'build.json':R2_BUILD,
        R2/'ContinuousSceneMod.swf':R2_NATIVE,R2/'probe-helper'/HELPER:R2_HELPER}
    for p,expected in paths.items():assert sha(p)==expected,('r2 frozen input changed',str(p))
    proof,build=read(R2/'source-provenance.json'),read(R2/'build.json')
    assert proof['baseline']==build['baseline']==BASE_SHA and proof['host']==build['host']==HOST_SHA
    assert proof['reverseInsertionCheck'] and proof['sourceClosure']==list(FILES)
    assert proof['probeHelperSHA256']==R2_HELPER and build['sourceProvenanceSHA256']==R2_PROVENANCE
    assert build['candidateSHA256']==R2_NATIVE and not build['deployed'] and not build['airRun']
    manifest_path=B/'large-map/source-manifest.json';receipt_path=MOD/'state/deployment-v090.json'
    assert sha(manifest_path)==proof['productionSourceManifestSHA256']
    assert sha(receipt_path)==proof['productionReceiptSHA256']
    manifest,receipt=read(manifest_path),read(receipt_path)
    assert receipt['status']=='verified' and receipt['after']['mods/ContinuousScene/release/ContinuousSceneMod.swf']==BASE_SHA
    paths[manifest_path]=sha(manifest_path);paths[receipt_path]=sha(receipt_path)
    for directory in ('source','original-source'):
        assert {p.name for p in (R2/directory).glob('*.as')}==set(FILES)
    for name in FILES:
        before,after=R2/'original-source'/name,R2/'source'/name
        assert sha(before)==proof['before'][name]==manifest['mods\\ContinuousScene\\src\\'+name]
        assert sha(after)==proof['after'][name]
        reverse=after.read_bytes().decode('utf-8')
        for edit in reversed(proof['edits'].get(name,[])):
            assert reverse.count(edit['after'])==1
            reverse=reverse.replace(edit['after'],edit['before'],1)
        assert reverse.encode('utf-8')==before.read_bytes()
        paths[before]=sha(before);paths[after]=sha(after)
    native=next(x for x in build['builds'] if x['name']=='ContinuousSceneMod')
    assert Path(native['output']).resolve()==(R2/'ContinuousSceneMod.swf').resolve() and native['sha256']==R2_NATIVE
    for path,key in ((R2/'ContinuousSceneMod.xml','configSHA256'),(R2/'ContinuousSceneMod-compile.log','compilerLogSHA256')):
        assert sha(path)==native[key];paths[path]=sha(path)
    return {str(p):value for p,value in paths.items()}


def modify_helper(original):
    source=original.decode('utf-8');edits=[]
    def edit(old,new):
        nonlocal source
        assert source.count(old)==1,(old[:70],source.count(old))
        source=source.replace(old,new,1);edits.append(dict(before=old,after=new))
    edit('Moves sleeping exact UnitRaider / UnitSlaver roots off-stage.',
         'Moves sleeping exact Raider/Slaver and seven reviewed non-Pon roots off-stage.')
    old='''                // Slaver only changes parentId/kolTrs in its constructor. Do
                // not broaden to UnitPon or all Raider subclasses: Merc/Encl
                // own separate arm roots; other subclasses need review.
                if(unitClass!="fe.unit::UnitRaider" && unitClass!="fe.unit::UnitSlaver")'''
    new='''                // Exact original non-Pon classes share Unit vis/hpbar/child roots.
                // No subclass-wide allowance; Merc/Encl own separate arm roots.
                var reviewedNonPon:Boolean=''' + ' ||\n                    '.join('unitClass=="fe.unit::'+c+'"' for c in CLASSES)+''';
                if(unitClass!="fe.unit::UnitRaider" && unitClass!="fe.unit::UnitSlaver" && !reviewedNonPon)'''
    edit(old,new)
    edit('                if(!(u.childObjs is Array)){skip(u,"no-explicit-child-array");return;}',
         '''                // In these exact native classes null means no child collection only
                // when no current weapon exists. Preserve null; never replace it.
                if(!(u.childObjs is Array) && !(reviewedNonPon && u.childObjs===null && u.currentWeapon===null))
                    {skip(u,"no-explicit-child-array");return;}''')
    edit('            for each(var child:* in u.childObjs) {',
         '            if(u.childObjs!==null)for each(var child:* in u.childObjs) {')
    edit('                || u.childObjs!==record.childArray || u.childObjs.length!=record.children.length)',
         '''                || u.childObjs!==record.childArray
                || (record.childArray===null ? u.currentWeapon!==null : u.childObjs.length!=record.children.length))''')
    edit('version:"sleeping-root-pixels-2"','version:"sleeping-root-pixels-3"')
    edit('version:"sleeping-root-probe-2"','version:"sleeping-root-probe-3"')
    edit('allowedClasses:["fe.unit::UnitRaider","fe.unit::UnitSlaver"]',
         'allowedClasses:['+','.join('"fe.unit::'+c+'"' for c in ('UnitRaider','UnitSlaver')+CLASSES)+']')
    restored=source
    for item in reversed(edits):
        assert restored.count(item['after'])==1
        restored=restored.replace(item['after'],item['before'],1)
    assert restored.encode('utf-8')==original
    # Lexical balance is a source check, deliberately not advertised as AS3 compile.
    stripped=re.sub(r'''/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*' ''', '',source,flags=re.S|re.X)
    stack=[]
    for ch in stripped:
        if ch in '([{':stack.append(ch)
        elif ch in ')]}':assert stack and stack.pop()=={')':'(',']':'[','}':'{'}[ch]
    assert not stack
    assert not re.search(r'u\.childObjs\s*=(?!=)',source)
    assert source.count('if(u.childObjs!==null)for each')==1
    assert source.count('record.childArray===null ? u.currentWeapon!==null : u.childObjs.length!=record.children.length')==1
    return source.encode('utf-8'),edits


def reference_proof():
    ref=ROOT/'game-reference/decompiled/1.02/src102/scripts'
    evidence=[];inputs={}
    for name in CLASSES:
        p=ref/'fe/unit'/(name+'.as');source=p.read_text('utf-8-sig');inputs[str(p)]=sha(p)
        assert re.search(r'public class '+name+r' extends Unit\b',source)
        assert not re.search(r'function (addVisual|remVisual)\b|addChild\(|removeChild\(|addEventListener\(',source)
        assert not re.search(r'var \w+:(MovieClip|Sprite|Bitmap|DisplayObject)',source)
        evidence.append(dict(className='fe.unit::'+name,parent='fe.unit::Unit',
            nativeRootOverrides=False,ownDisplayObjectFields=False,referencePath=str(p),referenceSHA256=sha(p)))
    for name in ('fe/unit/Unit.as','fe/Obj.as','fe/Pt.as','fe/weapon/Weapon.as','fe/weapon/WPunch.as','hpBar.as'):
        p=ref/name;inputs[str(p)]=sha(p)
    for pattern in ('visual*Slime.as','visualBloodwing*.as','visualBloat[0-9]*.as','visualTurret*.as','visualVortex.as'):
        for p in ref.glob(pattern):
            source=p.read_text('utf-8-sig')
            assert 'extends MovieClip' in source and 'addEventListener' not in source
            inputs[str(p)]=sha(p)
    return dict(classes=evidence,inputs=inputs,
        knownNullChildren='Only these seven exact classes and currentWeapon===null; original null identity retained.',
        roots='Inherited Unit vis layer2, hpbar layer3, optional childObjs weapon roots; blit bitmap stays inside vis.',
        limitations=['Reference source is original 1.02, not a new production module compilation.',
            'Slime/Bat/Bloat/Vortex/Turret timelines still require existing safeTree checks; no blanket static claim.',
            'LAD captures ADDED globally for lastObj projectile identity; combination testing is still required.',
            'Original fl UI classes have stage-added/removed listeners; reviewed unit root classes are MovieClip wrappers.'])


def prepare():
    ast.parse(Path(__file__).read_text('utf-8'))
    assert not OUT.exists(),'Preserve existing r3 evidence; use --check'
    native=frozen_native_proof();original=(R2/'probe-helper'/HELPER).read_bytes()
    modified,edits=modify_helper(original);references=reference_proof()
    OUT.mkdir();(OUT/'probe-helper').mkdir()
    (OUT/'probe-helper'/HELPER).write_bytes(modified)
    (OUT/'helper.patch').write_text(''.join(difflib.unified_diff(original.decode('utf-8').splitlines(True),
        modified.decode('utf-8').splitlines(True),fromfile='r2/'+HELPER,tofile='r3/'+HELPER)),'utf-8')
    proof=dict(version='sleeping-root-helper-source-3',diagnosticOnly=True,performanceAcceptance=False,
        helperCompiled=False,airRun=False,deployed=False,builderSHA256=sha(Path(__file__)),
        baseline=BASE_SHA,host=HOST_SHA,nativeCandidatePath=str(R2/'ContinuousSceneMod.swf'),
        nativeCandidateSHA256=R2_NATIVE,reusesR2NativeBinary=True,nativeInputs=native,
        previousHelperSHA256=R2_HELPER,probeHelperSHA256=digest(modified),edits=edits,
        reverseInsertionCheck=True,preservedControls=['safeTree','viewport','root ownership','restore ordering','zero-clips wake'],
        exactAddedClasses=list(CLASSES),sourceReferences=references,
        sourceCheck='Python AST and helper lexical balance plus exact reversible diff; AS3 compile pending')
    (OUT/'source-provenance.json').write_text(json.dumps(proof,indent=2,ensure_ascii=False),'utf-8')
    assert native==frozen_native_proof()
    print(json.dumps(dict(prepared=True,compiled=False,output=str(OUT),helperSHA256=digest(modified),
        nativeCandidateSHA256=R2_NATIVE,provenanceSHA256=sha(OUT/'source-provenance.json'))))


def check():
    proof=read(OUT/'source-provenance.json')
    assert proof['version']=='sleeping-root-helper-source-3' and proof['builderSHA256']==sha(Path(__file__))
    assert proof['nativeInputs']==frozen_native_proof()
    modified,edits=modify_helper((R2/'probe-helper'/HELPER).read_bytes())
    assert edits==proof['edits'] and digest(modified)==proof['probeHelperSHA256']==sha(OUT/'probe-helper'/HELPER)
    assert references_equal(proof['sourceReferences'],reference_proof())
    print(json.dumps(dict(passed=True,staticOnly=True,helperCompiled=False,airRun=False,
        helperSHA256=proof['probeHelperSHA256'],nativeCandidateSHA256=R2_NATIVE)))


def references_equal(before,after):return before==after


if __name__=='__main__':
    if not __debug__:raise RuntimeError('Assertions required')
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true')
    args=parser.parse_args();(check if args.check else prepare)()
