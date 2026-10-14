"""Read FFDec exports, emit four method replacements for the standard FFDec CLI.

No binary writes. Private identities are recovered from the original class p-code.
"""
from pathlib import Path
import json
import re
import sys
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
GEN=HERE/'generated'
TARGETS=[('fe.loc.Location','Location'),('fe.inter.Camera','calc'),('fe.inter.Camera','setZoom'),('MainFE','onManifestLoaded')]

def abc_methods(path):
    tree=ET.parse(path)
    methods={}
    for abc in tree.findall('.//abc'):
        cp=abc.find('constants')
        ss=[e.text or '' for e in cp.find('constant_string')]
        ns=list(cp.find('constant_namespace'))
        mn=list(cp.find('constant_multiname'))
        def name(index,qualified=False):
            m=mn[int(index)]
            simple=ss[int(m.attrib.get('name_index','0'))]
            if not qualified: return simple
            space=ns[int(m.attrib.get('namespace_index','0'))]
            prefix=ss[int(space.attrib.get('name_index','0'))]
            return prefix+'.'+simple if prefix else simple
        bodies={int(e.attrib['method_info']):(i,e) for i,e in enumerate(abc.find('bodies'))}
        for ii,ci in zip(abc.find('instance_info'),abc.find('class_info')):
            cl=name(ii.attrib['name_index'],True)
            for key,index in [(cl+'::<init>',ii.attrib['iinit_index']),(cl+'::<static>',ci.attrib['cinit_index'])]:
                methods[key]=bodies.get(int(index))
            for scope,container in [(0,ii.find('instance_traits/traits')),(1,ci.find('static_traits/traits'))]:
                for tr in container:
                    if tr.attrib.get('type')=='TraitMethodGetterSetter':
                        key=cl+'::'+str(scope)+':'+tr.attrib['kindType']+':'+name(tr.attrib['name_index'])
                        methods[key]=bodies.get(int(tr.attrib['method_info']))
    return methods

def plan():
    methods=abc_methods(GEN/'host.xml')
    args=[]; manifest=[]
    audit=GEN/'audit'; audit.mkdir(exist_ok=True)
    for classname,method in TARGETS:
        relative=Path(*classname.split('.')).with_suffix('.pcode')
        source=(GEN/'donor-pcode/scripts'/relative).read_text(encoding='utf-8-sig')
        original=(GEN/'original-pcode/scripts'/relative).read_text(encoding='utf-8-sig')
        start=re.search(r'\bfunction '+method+r'\(',source).end()
        first=re.search(r'\bmethod\s*\n',source[start:]).start()+start
        last=source.index('end ; method',first)+len('end ; method')
        code=source[first:last]
        if re.search(r'^\s*(newfunction|newclass|callstatic)\b',code,re.M):
            raise RuntimeError('Method references require explicit relocation')
        # XML/property lookups include a class/file namespace set. No private slots
        # are accessed by these four changes; retain the original lookup identities.
        private_names=list(dict.fromkeys(re.findall(r'PrivateNamespace\([^)]*\)',original)))
        donor_names=list(dict.fromkeys(re.findall(r'PrivateNamespace\([^)]*\)',code)))
        if re.search(r'QName\(PrivateNamespace',code):
            raise RuntimeError('Direct private member access requires reviewed mapping')
        if donor_names:
            if not private_names:
                for a in donor_names:
                    code=code.replace(','+a,'').replace(a+',','')
            elif len(private_names)!=len(donor_names):
                raise RuntimeError(f'Namespace cardinality differs: {classname} {private_names} {donor_names}')
            # Both refer only to generic dynamic lookup sets here; use original order.
            else:
                for a,b in zip(donor_names,private_names): code=code.replace(a,b)
        key=classname+'::<init>' if method==classname.split('.')[-1] else classname+'::0:1:'+method
        index,_=methods[key]
        path=audit/(classname+'-'+method+'.pcode')
        path.write_text(code+'\n',encoding='utf-8')
        args.extend([classname,str(path),str(index)])
        manifest.append({'class':classname,'method':method,'bodyIndex':index,'file':str(path),'privateMappings':list(zip(donor_names,private_names))})
    (audit/'replace-args.txt').write_text('\n'.join(args)+'\n',encoding='utf-8')
    (audit/'replacement-plan.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(manifest,indent=2))

def audit():
    before=abc_methods(GEN/'original.xml'); after=abc_methods(GEN/'final.xml')
    allowed={'fe.loc.Location::<init>','fe.inter.Camera::0:1:calc','fe.inter.Camera::0:1:setZoom','MainFE::0:1:onManifestLoaded'}
    preserved=0
    for key in allowed:
        if key not in after or before[key][1].attrib.get('codeBytes') == after[key][1].attrib.get('codeBytes'):
            raise RuntimeError('Required method replacement did not happen: '+key)
    if 'fe.graph.Grafon::0:1:sceneTick' not in after:
        raise RuntimeError('Chunk renderer is missing')
    for key,value in before.items():
        if key.startswith('fe.graph.Grafon::') or key in allowed: continue
        other=after.get(key)
        if value is None:
            if other is not None: raise RuntimeError('Changed abstract body '+key)
        else:
            if other is None or value[1].attrib.get('codeBytes')!=other[1].attrib.get('codeBytes'):
                raise RuntimeError('Unrelated bytecode changed: '+key)
        preserved+=1
    result={'passed':True,'unchangedNamedMethodsAndInitializers':preserved,'originalCount':len(before),'requiredReplacements':sorted(allowed),'chunkRendererPresent':True}
    (GEN/'audit/bytecode-audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))

if __name__=='__main__':
    audit() if len(sys.argv)>1 and sys.argv[1]=='audit' else plan()
