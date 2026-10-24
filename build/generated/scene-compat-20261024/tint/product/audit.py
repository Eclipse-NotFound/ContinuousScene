"""Exact ABE2 two-body tint repair; no compilation or private rebinding."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
import zlib
import xml.etree.ElementTree as ET

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
B=HERE.parents[3]
BASE=B/'generated/vertical-camera-band-20261023'
HOST='ABE2B65EDF3D0E4E0FA8ECA76A60E577D40E47F20B9ACECEBEC7730849A2602A'
XML='EE33CE0282C1DFBA7BF7AE03D1E7646383DCCF79EA1252F9792A57344E1208CF'
TARGET='fe.graph.Grafon::0:1:sceneUpdateEntityColor'
COLOR='fe.graph.Grafon::0:1:sceneEntitySameColor'
TARGETS=[TARGET,COLOR]
POINT=561
# Input stack: Boolean(target.levit == 0). If false, replace it with
# target === World.w.gg. Original jumps to POINT bypass this new expression
# (notably target.vis == null), preserving native short-circuit protection.
INSERT=bytes.fromhex('2a110c000029d1603066a40a669202ac76')

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

engine=load('scene_tint_exact_retainer',B/'bullet-segments-audit.py')
core=engine.core
engine.CLASS='fe.graph.Grafon';engine.TARGET=TARGET;engine.OUT=HERE
engine.BASE_SWF=BASE/'pfe.swf';engine.BASE_XML=BASE/'pfe.xml';engine.BASE_HASH=HOST
sha=engine.sha
_original=None
_color=None

def original():
    global _original,_color
    if _original is None:
        assert sha(BASE/'pfe.swf')==HOST and sha(BASE/'pfe.xml')==XML
        tree=ET.parse(BASE/'pfe.xml');a=core.ABC(tree.findall('.//abc')[0])
        body=a.bodies[a.named[TARGET]]
        assert not list(body.find('exceptions')) and not list(body.find('traits/traits'))
        assert body.get('max_stack')=='8' and body.get('max_regs')=='16'
        for i,name,namespace in ((48,'World','fe'),(1316,'w',''),(274,'gg',''),(2217,'levit','')):
            mn=a.cp['constant_multiname'][i]
            assert mn.get('kind')=='7' and a.simple(i)==name
            ns=a.cp['constant_namespace'][int(mn.get('namespace_index'))]
            assert ns.get('kind')=='22' and a.string(int(ns.get('name_index')))==namespace
        _original=dict(body.attrib)
        _color=dict(a.bodies[a.named[COLOR]].attrib)
        assert _color['method_info']=='3246' and _color['max_regs']=='3' and _color['max_stack']=='2'
        assert a.qualified(7)=='flash.display.Sprite' and a.qualified(22)=='flash.geom.ColorTransform'
        assert a.simple(9064)=='isFinite' and a.simple(5429)=='transform' and a.simple(5430)=='colorTransform'
        mn=a.cp['constant_multiname'][9064]
        assert mn.get('kind')=='9' and mn.get('namespace_set_index')=='162'
        members=engine.set_members(a,162)
        assert len(members)==len(set(members)) and 1 in members
        ci=a.class_by_name['fe.graph.Grafon']
        for parent,container in ((a.instances[ci],'instance_traits/traits'),(a.statics[ci],'static_traits/traits')):
            assert all(a.simple(int(t.get('name_index')))!='isFinite' for t in parent.find(container))
        native=[]
        for name,index in a.named.items():
            if not name.startswith('fe.graph.Grafon::') or index not in a.bodies:continue
            candidate=a.bodies[index]
            if candidate.get('init_scope_depth')!='4' or candidate.get('max_scope_depth')!='5':continue
            decoded,_=core.decode(bytes.fromhex(candidate.get('codeBytes')))
            if any(row[2]==0x46 and row[3]==[('n',9064),('u',1)] for row in decoded):native.append(name)
        assert native, 'isFinite must reuse an actual native Grafon same-scope call'
        # This is an existing Grafon namespace-set lookup, not a public QName.
        # The candidate keeps the exact set and every existing private identity.
    return _original

def patched_code():
    data=bytes.fromhex(original()['codeBytes']);rows,_=core.decode(data)
    assert data[553:561]==bytes.fromhex('d166a9112400ab76')
    assert data[561:566]==bytes.fromhex('2a12050000')
    assert len(INSERT)==17
    result=bytearray()
    for start,end,op,args in rows:
        if start==POINT:result.extend(INSERT)
        assert op!=0x1b, 'Switch requires a separate review'
        part=bytearray(data[start:end])
        destinations=[v for k,v in args if k=='target']
        if destinations:
            assert len(destinations)==1 and core.OPS[op]=='j' and end-start==4
            destination=destinations[0]
            new_destination=destination+(len(INSERT) if destination>=POINT else 0)
            new_end=end+(len(INSERT) if start>=POINT else 0)
            part[1:4]=(new_destination-new_end).to_bytes(3,'little',signed=True)
        result.extend(part)
    result=bytes(result)
    decoded,_=core.decode(result)
    # Every original instruction/binding survives, with only branch addresses
    # relocated. In particular the null-visual edge skips all inserted reads.
    survivors=[row for row in decoded if not POINT<=row[0]<POINT+len(INSERT)]
    assert len(survivors)==len(rows)
    for old,new in zip(rows,survivors):
        assert old[2]==new[2]
        mapped=[(k,v+(len(INSERT) if v>=POINT else 0)) if k=='target' else (k,v) for k,v in old[3]]
        assert mapped==new[3]
    assert next(row for row in decoded if row[0]==548)[3]==[('target',578)]
    assert result[POINT:POINT+len(INSERT)]==INSERT
    return result

def color_code():
    original();data=bytes.fromhex(_color['codeBytes'])
    assert len(data)==155 and data[30:32]==b'\x27\x48' and data[154:]==b'\x48'
    # Keep the complete null guard and raw equality fast path. On false,
    # normalize only the expected color through AIR's actual DisplayObject
    # setter/getter, then execute an exact copy of the eight-component check.
    result=bytearray(data[:154]);labels={};branches=[]
    def u(value):
        out=bytearray()
        while value>=128:out.append((value&127)|128);value>>=7
        out.append(value);return out
    def emit(op,*args):
        result.append(op)
        for arg in args:result.extend(u(arg))
    def branch(op,label):
        start=len(result);result.extend(bytes([op,0,0,0]));branches.append((start,label))
    emit(0x2a);branch(0x11,'true');emit(0x29)
    for field in (5294,5296,5298,6175,5293,5295,5297,6714):
        emit(0x5d,9064);emit(0xd2);emit(0x66,field);emit(0x46,9064,1);branch(0x12,'false')
    emit(0x60,7);emit(0x42,0);emit(0x80,7);emit(0xd7)
    emit(0xd3);emit(0x66,5429);emit(0xd2);emit(0x61,5430)
    emit(0xd3);emit(0x66,5429);emit(0x66,5430);emit(0x80,22);emit(0xd6)
    repeat_start=len(result);result.extend(data[32:155])
    labels['true']=len(result);emit(0x48)
    labels['false']=len(result);emit(0x27);emit(0x48)
    for start,label in branches:result[start+1:start+4]=(labels[label]-start-4).to_bytes(3,'little',signed=True)
    rows,addresses=core.decode(bytes(result))
    assert result[:154]==data[:154] and result[repeat_start:repeat_start+123]==data[32:155]
    assert all(v in addresses for row in rows for k,v in row[3] if k=='target')
    return bytes(result)

def proof(abc,index):
    original();name=abc.names_by_method.get(index)
    assert name in TARGETS
    body=abc.bodies[index];old=_original if name==TARGET else _color
    assert int(old['method_info'])==index
    data=bytes.fromhex(body.get('codeBytes'));baseline=data==bytes.fromhex(old['codeBytes'])
    expected=patched_code() if name==TARGET else color_code()
    assert baseline or data==expected
    for key,value in old.items():
        if name==COLOR and not baseline and key=='max_regs':value='4'
        if key!='codeBytes':assert body.get(key)==value,(key,body.get(key),value)
    assert not list(body.find('exceptions')) and not list(body.find('traits/traits'))
    rows,addresses=core.decode(data);core.Compare.exceptions(body,abc,addresses)
    return rows

def operands(abc,index):
    return {v for row in proof(abc,index) for k,v in row[3] if k=='n'}

def no_diagnostic(abc,index):
    proof(abc,index)
    return dict(callCount=0,diagnosticCalls=False,callOffsets=[])

engine.body_operands=operands;engine.timer_binding=no_diagnostic

def audit(candidate_xml,candidate_swf):
    old_nodes=ET.parse(BASE/'pfe.xml').findall('.//abc')
    new_nodes=ET.parse(candidate_xml).findall('.//abc')
    assert len(old_nodes)==len(new_nodes)==2
    ignored={'bytes','fileOffset'};changed=[];preserved=0;classes=0
    for old,new in zip(old_nodes,new_nodes):
        a,b=core.ABC(old),core.ABC(new)
        assert a.named==b.named and a.class_by_name==b.class_by_name and set(a.bodies)==set(b.bodies)
        for index,body in a.bodies.items():
            name=a.names_by_method.get(index);other=b.bodies[index]
            if name in TARGETS:
                proof(a,index);proof(b,index)
                assert body.get('codeBytes')!=other.get('codeBytes')
                changed.append(name)
                # Reversing only these exact body attribute edits must restore
                # the complete ABC, including every pool and private identity.
                other.set('codeBytes',body.get('codeBytes'));other.set('max_regs',body.get('max_regs'))
            else:preserved+=1
        assert core.xml_value(old,ignored)==core.xml_value(new,ignored), 'Untargeted ABC metadata/body changed'
        classes+=len(a.class_by_name)
    assert changed==TARGETS and preserved==5769 and classes==1016
    assert engine.support.swf_envelope(BASE/'pfe.swf')==engine.support.swf_envelope(candidate_swf)
    result=dict(passed=True,auditTarget=TARGET,auditTargets=TARGETS,actualChangedBodies=changed,allowedChangedMethods=TARGETS,
        unchangedMethodBodies=preserved,unchangedClassLayouts=classes,addedFields=[],addedMethods=[],
        methodAndClassIndicesPreserved=True,originalConstantPoolPreserved=True,nonABCSWFEnvelopePreserved=True,
        baseSHA256=HOST,baseXMLSHA256=XML,candidateSHA256=sha(candidate_swf),candidateXMLSHA256=sha(candidate_xml),
        wrapperSHA256=sha(Path(__file__)),importedClassCopied=False,
        preservedOriginalLayout=True,constructorsPreserved=True,
        exactInsertedBytes=INSERT.hex(),insertionOffset=POINT,newMethods=0,newFields=0,
        originalBranchesPreserved=True,originalPrivateIdentitiesPreserved=True,
        version='scene-player-region-tint-2')
    return result

def splice():
    audit(HERE/'serialized.xml',BASE/'pfe.swf')
    signature,header,old=engine.raw_swf(BASE/'pfe.swf')
    ds,dh,donor=engine.raw_swf(HERE/'serialized.swf')
    assert signature==ds and header==dh and len(old)==len(donor)
    assert [t[0] for t in old]==[t[0] for t in donor]
    abc=[i for i,t in enumerate(old) if t[0] in (72,82)]
    assert len(abc)==2
    for i in abc:assert engine.abc_prefix(old[i])==engine.abc_prefix(donor[i])
    target=abc[0]
    tags=[(donor[i] if i==target else old[i])[2] for i in range(len(old))]
    body=header+b''.join(tags)
    output=HERE/'pfe.swf'
    output.write_bytes(signature+(len(body)+8).to_bytes(4,'little')+(zlib.compress(body,9) if signature[:3]==b'CWS' else body))
    fs,fh,final=engine.raw_swf(output)
    assert fs==signature and fh==header and [t[2] for t in final]==tags
    assert engine.support.swf_envelope(BASE/'pfe.swf')==engine.support.swf_envelope(output)
    return dict(passed=True,base=HOST,candidate=sha(output),preservedRawTags=len(old)-1,targets=TARGETS)

def stage(path):
    code=patched_code()
    tree=ET.parse(BASE/'pfe.xml');a=core.ABC(tree.findall('.//abc')[0])
    body=a.bodies[a.named[TARGET]];body.set('codeBytes',code.hex())
    other=a.bodies[a.named[COLOR]];other.set('codeBytes',color_code().hex());other.set('max_regs','4')
    proof(a,a.named[TARGET]);proof(a,a.named[COLOR]);tree.write(path,encoding='utf-8',xml_declaration=True)
    return dict(base=HOST,baseXML=XML,target=TARGET,oldCodeSHA256=hashlib.sha256(bytes.fromhex(original()['codeBytes'])).hexdigest().upper(),
        newCodeSHA256=hashlib.sha256(code).hexdigest().upper(),insertedBytes=INSERT.hex(),point=POINT,
        targets=TARGETS,sourceEquivalent='Player levit exemption + exact DisplayObject color normalization fallback',newConstants=0,newPrivateIdentities=0)

if __name__=='__main__':
    if sys.argv[1]=='stage':result=stage(HERE/'retained.xml')
    elif sys.argv[1]=='splice':result=splice()
    elif sys.argv[1]=='audit':result=audit(HERE/'pfe.xml',HERE/'pfe.swf')
    else:raise ValueError('stage/splice/audit required')
    path=HERE/({'stage':'predicate-proof.json','splice':'splice.json','audit':'semantic-audit.json'}[sys.argv[1]])
    path.write_text(json.dumps(result,indent=2),'utf-8')
    print(json.dumps({'passed':True,'step':sys.argv[1],'evidence':str(path),'sha256':sha(path)}),flush=True)
