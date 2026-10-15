"""Read FFDec exports and emit reviewed method replacements for FFDec CLI.

No binary writes. Private identities are recovered from the original class p-code.
"""
from pathlib import Path
import json
import hashlib
import re
import sys
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
GEN=HERE/'generated'
TARGETS=[('fe.loc.Location','Location'),('fe.inter.Camera','calc'),('fe.inter.Camera','setZoom'),('fe.loc.Game','save'),('fe.loc.Land','createMap'),('fe.unit.Unit','setVisPos'),('fe.loc.Box','addVisual'),('fe.loc.Box','runVis'),('fe.unit.UnitPlayer','actions'),('fe.unit.UnitPlayer','crackAction')]

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
            # These two native methods already access one private member each.
            # Retain that exact name and the original class-private identity;
            # never authorize arbitrary private access from a new donor.
            approved={('fe.unit.UnitPlayer','actions'):{'changeWeaponNow'},
                      ('fe.unit.UnitPlayer','crackAction'):{'actionReady'}}
            names=set(re.findall(r'QName\(PrivateNamespace\([^)]*\),"([^"]+)"\)',code))
            os=original.index('function '+method+'(')
            oe=original.index('end ; method',os)
            prior=set(re.findall(r'QName\(PrivateNamespace\([^)]*\),"([^"]+)"\)',original[os:oe]))
            if names != approved.get((classname,method)) or names != prior:
                raise RuntimeError('Unreviewed direct private member access')
            # crackAction contains only a class-private call; it has no generic
            # lookup namespace set and therefore no file-private namespace.
            # Match the namespace from the same native private member, rather
            # than demanding all namespaces of the entire original class.
            if len(donor_names)==1:
                member=next(iter(names))
                native_ns=set(re.findall(r'QName\((PrivateNamespace\([^)]*\)),"'+re.escape(member)+r'"\)',original[os:oe]))
                if len(native_ns)!=1:
                    raise RuntimeError('Ambiguous native private member identity')
                private_names=list(native_ns)
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
    allowed={c+'::<init>' if m==c.split('.')[-1] else c+'::0:1:'+m for c,m in TARGETS}
    preserved=0
    unchanged_required=[]
    for key in allowed:
        if key not in before or key not in after or before[key] is None or after[key] is None:
            raise RuntimeError('Required concrete method is missing: '+key)
        # Map1 already contains CS 0.4. For example Game.save can legitimately
        # be byte-identical after applying the same scene persistence call.
        if before[key][1].attrib.get('codeBytes') == after[key][1].attrib.get('codeBytes'):
            unchanged_required.append(key)
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
    # A method-body transplant cannot create Map1's added instance/static
    # slots. Require the published Land layout to survive unchanged as well.
    def land_layout(path):
        tree=ET.parse(path)
        for abc in tree.findall('.//abc'):
            constants=abc.find('constants')
            strings=[node.text or '' for node in constants.find('constant_string')]
            namespaces=list(constants.find('constant_namespace'))
            names=list(constants.find('constant_multiname'))
            for instance,static in zip(abc.find('instance_info'),abc.find('class_info')):
                name=names[int(instance.attrib['name_index'])]
                namespace=namespaces[int(name.attrib.get('namespace_index','0'))]
                if strings[int(name.attrib.get('name_index','0'))]=='Land' and strings[int(namespace.attrib.get('name_index','0'))]=='fe.loc':
                    slots=[]
                    for scope,container in [('instance',instance.find('instance_traits/traits')),('static',static.find('static_traits/traits'))]:
                        for trait in container:
                            trait_name=names[int(trait.attrib['name_index'])]
                            slots.append((scope,strings[int(trait_name.attrib.get('name_index','0'))]))
                    if ('instance','rconnectLayoutSeed') not in slots or ('static','rconnectSeedSource') not in slots:
                        raise RuntimeError('Published RConnect Map1 Land seed traits missing')
                    # Grafon replacement renumbers method table entries and
                    # moves file offsets. The named-body audit above already
                    # verifies Land's constructor/static/method identities and
                    # code; retain all actual slot/type/visibility metadata.
                    relocated={'bytes','fileOffset','iinit_index','cinit_index','method_info'}
                    def layout(node):
                        return (node.tag,tuple(sorted((k,v) for k,v in node.attrib.items() if k not in relocated)),tuple(layout(child) for child in node))
                    return layout(instance),layout(static)
        raise RuntimeError('Published Land class is missing')
    if land_layout(GEN/'original.xml')!=land_layout(GEN/'final.xml'):
        raise RuntimeError('Published RConnect Map1 Land class layout changed')
    source_host=HERE.parents[2]/'mods/RConnect/build/m52/a22-map-only-03/native/pfe.swf'
    result={'passed':True,'unchangedNamedMethodsAndInitializers':preserved,'originalCount':len(before),'requiredReplacements':sorted(allowed),'unchangedRequired':sorted(unchanged_required),'chunkRendererPresent':True,'rconnectLandLayoutPreserved':True,
            'sourceHostSHA256':hashlib.sha256(source_host.read_bytes()).hexdigest().upper(),
            'finalHostSHA256':hashlib.sha256((HERE/'runtime/pfe.swf').read_bytes()).hexdigest().upper()}
    (GEN/'audit/bytecode-audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))

if __name__=='__main__':
    audit() if len(sys.argv)>1 and sys.argv[1]=='audit' else plan()
