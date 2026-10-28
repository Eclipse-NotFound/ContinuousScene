"""Exact-method alicorn patch on the installed 2026-10-24 host; build only."""
from pathlib import Path
import hashlib, importlib.util, json, re, shutil, subprocess, sys
import xml.etree.ElementTree as ET
from pcode_plan import abc_methods

B=Path(__file__).resolve().parent; MOD=B.parent; ROOT=MOD.parents[1]
OUT=B/'generated/alicorn-alerts-20261028'
JAVA=Path('D:/Program Files/Adobe Animate 2024/jre/bin/java.exe')
TOOLS=ROOT/'mods/Sandevistan/build/tools'
EXPECTED='A796827173AF7D6FAB9885FB66ECC62182AB5335918A30C7CCE4C44914A238B7'
METHODS=['budilo','telepat','alarma','control','setNull']
CLS='fe.unit.UnitAlicorn'; REL=Path('fe/unit/UnitAlicorn')

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
parser=module('alicorn_parser',B/'profile-vision.py')
auditlib=module('alicorn_layout',B/'renderer-audit.py')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2),'utf-8')
def ff(label,*args):
    print(label,flush=True)
    with (OUT/(label+'.log')).open('wb') as f:
        subprocess.run([str(JAVA),'-Xmx768m','-jar',str(TOOLS/'ffdec/ffdec-cli.jar'),*map(str,args)],stdout=f,stderr=subprocess.STDOUT,check=True)
def once(s,a,b):
    assert s.count(a)==1,(a[:90],s.count(a));return s.replace(a,b,1)

GUARD='''         var sceneGraph:Object = World.w != null ? World.w.grafon : null;
         var sceneBounded:Boolean = loc != null && World.w != null && World.w.loc === loc
            && sceneGraph != null && sceneGraph.loc === loc
            && ("sceneLarge" in sceneGraph) && Boolean(sceneGraph["sceneLarge"]);
'''

def source():
    s=(OUT/'original/scripts'/REL.with_suffix('.as')).read_text('utf-8-sig')
    inc=(MOD/'src/patches/SceneAlicornAlerts.as.inc').read_text('utf-8-sig')
    for method in ['budilo','telepat']:
        a,z=parser._body(s,method);c,d=parser._body(inc,method)
        s=s[:a+1]+inc[c+1:d]+s[z:]
    for method in ['alarma','control','setNull']:
        a,z=parser._body(s,method);body=s[a+1:z]
        if method=='alarma':
            # Native damage calls alarma() with -1/-1; positive coordinates
            # identify an incoming warning, including other native enemy types.
            body=once(body,'            super.alarma(param1,param2);',
                '            if(sceneBounded && param1 >= 0 && param2 >= 0) sceneGraph["sceneNativeCall"]("alicornReceive",[this]);\n            super.alarma(param1,param2);')
        elif method=='control':
            # Observe the original calm decision, not target loss alone and not
            # stun. A telepathically assigned target may precede aiSpok's update.
            body=once(body,'            if(aiSpok == 0)\n            {',
                '            if(aiSpok == 0)\n            {\n               if(sceneBounded && celUnit == null && !stun && !levit) sceneGraph["sceneNativeCall"]("alicornClear",[this]);')
        else:
            body=once(body,'            aiState = aiSpok = 0;',
                '            aiState = aiSpok = 0;\n            if(sceneBounded) sceneGraph["sceneNativeCall"]("alicornClear",[this]);')
        s=s[:a+1]+'\n'+GUARD+body+s[z:]
    p=OUT/'source'/REL.with_suffix('.as');p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,'utf-8')

def method_code(text,name):
    h=re.search(r'\bfunction '+name+r'\(',text).end()
    a=re.search(r'\bmethod\s*\n',text[h:]).start()+h
    z=text.index('end ; method',a)+len('end ; method')
    return text[a:z]

def plan():
    orig=(OUT/'original-pcode/scripts'/REL.with_suffix('.pcode')).read_text('utf-8-sig')
    donor=(OUT/'donor-pcode/scripts'/REL.with_suffix('.pcode')).read_text('utf-8-sig')
    methods=abc_methods(OUT/'base.xml');args=[]
    for method in METHODS:
        old=method_code(orig,method);code=method_code(donor,method)
        assert not re.search(r'^\s*(newfunction|newclass|callstatic)\b',code,re.M),method
        # Class-private identities in any original instructions remain exact.
        members=lambda t:set(re.findall(r'QName\(PrivateNamespace\([^)]*\),"([^"]+)"\)',t))
        assert members(old)==members(code),(method,members(old),members(code))
        native=list(dict.fromkeys(re.findall(r'PrivateNamespace\([^)]*\)',old)))
        fresh=list(dict.fromkeys(re.findall(r'PrivateNamespace\([^)]*\)',code)))
        if not native:
            assert not members(code)
            for n in fresh:code=code.replace(','+n,'').replace(n+',','')
        else:
            assert len(native)==len(fresh),(method,native,fresh)
            for a,b in zip(fresh,native):code=code.replace(a,b)
        key=CLS+'::0:1:'+method;index,_=methods[key]
        p=OUT/(method+'.pcode');p.write_text(code+'\n','utf-8');args += [CLS,str(p),str(index)]
    (OUT/'replace.txt').write_text('\n'.join(args)+'\n','utf-8')

def audit():
    before=ET.parse(OUT/'base.xml');after=ET.parse(OUT/'pfe.xml')
    keys={CLS+'::0:1:'+n for n in METHODS};named=abc_methods(OUT/'base.xml')
    allowed={named[k][0] for k in keys}
    ba=before.findall('.//abc');aa=after.findall('.//abc');assert len(ba)==len(aa)
    preserved=0;changed=0
    for old_abc,new_abc in zip(ba,aa):
        cp=old_abc.find('constants');ss=[e.text or '' for e in cp.find('constant_string')];mn=list(cp.find('constant_multiname'))
        owns=any(ss[int(mn[int(n.attrib['name_index'])].attrib.get('name_index','0'))]=='UnitAlicorn' for n in old_abc.find('instance_info'))
        old=list(old_abc.find('bodies'));new=list(new_abc.find('bodies'));assert len(old)==len(new)
        for i,(a,b) in enumerate(zip(old,new)):
            if owns and i in allowed:assert a.attrib['codeBytes']!=b.attrib['codeBytes'],i;changed+=1
            else:assert auditlib.layout(a)==auditlib.layout(b),('unrelated body',i);preserved+=1
        for a in cp:
            b=new_abc.find('constants').find(a.tag);assert len(b)>=len(a)
            for i,node in enumerate(a):assert auditlib.layout(node)==auditlib.layout(b[i]) and node.text==b[i].text,(a.tag,i)
    assert changed==len(METHODS)
    assert auditlib.classes(OUT/'base.xml')==auditlib.classes(OUT/'pfe.xml')
    # Other SWF tags (including all resources) must remain byte-identical.
    import zlib,struct
    def tags(p):
        raw=p.read_bytes();data=zlib.decompress(raw[8:]) if raw[:3]==b'CWS' else raw[8:]
        offset=(5+4*(data[0]>>3)+7)//8+4;result=[]
        while offset<len(data):
            h=struct.unpack_from('<H',data,offset)[0];offset+=2;code=h>>6;n=h&63
            if n==63:n=struct.unpack_from('<I',data,offset)[0];offset+=4
            result.append((code,None if code==82 else data[offset:offset+n]));offset+=n
        return result
    assert tags(OUT/'base.swf')==tags(OUT/'pfe.swf')
    result={'ok':True,'base':sha(OUT/'base.swf'),'host':sha(OUT/'pfe.swf'),
            'methods':sorted(keys),'unchangedBodies':preserved,
            'allClassLayoutsPreserved':True,'oldConstantsPreserved':True,'otherTagsPreserved':True}
    save(OUT/'audit.json',result);print(json.dumps(result),flush=True)

def compile_as(source,entry,out):
    cfg=out.with_suffix('.config.xml')
    cfg.write_text(f'<flex-config><target-player>32.0</target-player><compiler><external-library-path><path-element>{TOOLS}/airsdk/frameworks/libs/air/airglobal.swc</path-element></external-library-path><source-path><path-element>{source}</path-element></source-path><debug>false</debug><optimize>true</optimize><theme/></compiler></flex-config>','utf-8')
    with out.with_suffix('.build.log').open('wb') as f:
        subprocess.run([str(JAVA),'-Xmx512m','-Dfile.encoding=UTF-8','-jar',str(TOOLS/'flexsdk/lib/mxmlc.jar'),f'+flexlib={TOOLS}/flexsdk/frameworks',f'-load-config={cfg}','-swf-version=32','-static-link-runtime-shared-libraries=true',f'-output={out}',str(source/entry)],stdout=f,stderr=subprocess.STDOUT,check=True)

def build():
    OUT.mkdir(parents=True,exist_ok=True)
    if not (OUT/'base.swf').exists():
        assert sha(ROOT/'pfe.swf')==EXPECTED,'Installed host changed: rebase explicitly'
        shutil.copy2(ROOT/'pfe.swf',OUT/'base.swf')
    assert sha(OUT/'base.swf')==EXPECTED
    if not (OUT/'base.xml').exists():ff('base-xml','-swf2xml',OUT/'base.swf',OUT/'base.xml')
    if not (OUT/'original/scripts'/REL.with_suffix('.as')).exists():ff('original-source','-selectclass',CLS,'-export','script',OUT/'original',OUT/'base.swf')
    if not (OUT/'original-pcode/scripts'/REL.with_suffix('.pcode')).exists():ff('original-pcode','-format','script:pcode','-selectclass',CLS,'-export','script',OUT/'original-pcode',OUT/'base.swf')
    source()
    ff('donor','-importScript',OUT/'base.swf',OUT/'donor.swf',OUT/'source')
    ff('donor-pcode','-format','script:pcode','-selectclass',CLS,'-export','script',OUT/'donor-pcode',OUT/'donor.swf')
    plan();ff('replace','-replace',OUT/'base.swf',OUT/'pfe.swf',OUT/'replace.txt')
    ff('final-xml','-swf2xml',OUT/'pfe.swf',OUT/'pfe.xml');audit()
    ff('readback','-selectclass',CLS,'-export','script',OUT/'readback',OUT/'pfe.swf')
    compile_as(MOD/'src','ContinuousSceneDoc.as',OUT/'ContinuousSceneMod.swf')
    save(OUT/'build.json',{'host':sha(OUT/'pfe.swf'),'mod':sha(OUT/'ContinuousSceneMod.swf'),
        'source':{str(p.relative_to(MOD)):sha(p) for p in (MOD/'src').rglob('*.as') if 'tests' not in p.parts},'version':'0.9.1'})
    print('Candidate build complete',flush=True)

if __name__=='__main__':build()
