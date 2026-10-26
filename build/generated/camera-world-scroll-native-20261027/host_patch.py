"""Exact diagnostic Camera.calc edit. Only skip world x/y setters under scrollRect."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
import xml.etree.ElementTree as ET
import zlib

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('native_scroll_inspection',HERE/'inspect_host.py')
source=importlib.util.module_from_spec(spec);spec.loader.exec_module(source)
engine,_,_,_=source.load()
core=engine.core
BASE,HOST,XML,TARGET=source.BASE,source.HOST,source.XML,source.TARGET
sha=source.sha
POINTS={1936:3659,1975:3660}
SCROLL=8904

def u(value):
    result=bytearray()
    while value>=128:result.append((value&127)|128);value>>=7
    result.append(value);return result

def replacement(field):
    # Entry stack [worldVisual, coordinate]. The SATS setter already ran.
    # Keep original setproperty only for null scrollRect; both paths empty it.
    code=bytearray([0x2b,0x2a,0x66]);code.extend(u(SCROLL));code.append(0x20)
    branch=len(code);code.extend([0x14,0,0,0])
    code.append(0x2b);setter=len(code);code.append(0x61);code.extend(u(field))
    jump=len(code);code.extend([0x10,0,0,0]);skip=len(code);code.extend([0x29,0x29])
    code[branch+1:branch+4]=(skip-branch-4).to_bytes(3,'little',signed=True)
    code[jump+1:jump+4]=(len(code)-jump-4).to_bytes(3,'little',signed=True)
    return bytes(code),setter

def patched():
    _,_,a,body=source.load()
    assert body.get('max_stack')=='8' and body.get('max_regs')=='15'
    assert not list(body.find('exceptions')) and not list(body.find('traits/traits'))
    mn=a.cp['constant_multiname'][SCROLL]
    assert a.simple(SCROLL)=='scrollRect' and mn.get('kind')=='7' and mn.get('namespace_index')=='1'
    ns=a.cp['constant_namespace'][1]
    assert ns.get('kind')=='22' and a.string(int(ns.get('name_index'))) == ''
    data=bytes.fromhex(body.get('codeBytes'));rows,_=core.decode(data)
    inserts={p:replacement(n)[0] for p,n in POINTS.items()}
    def mapped(pos):return pos+sum(len(ins)-3 for p,ins in inserts.items() if p<pos)
    result=bytearray();survivors=[]
    for start,end,op,args in rows:
        assert op!=0x1b, 'Switch needs separate relocation proof'
        if start in POINTS:
            assert op==0x61 and args==[('n',POINTS[start])] and end-start==3
            assert a.simple(POINTS[start])==('x' if start==1936 else 'y')
            assert data[start-4:start]==bytes.fromhex('620e080e')
            result.extend(inserts[start]);continue
        assert len(result)==mapped(start)
        part=bytearray(data[start:end])
        targets=[v for k,v in args if k=='target']
        if targets:
            assert len(targets)==1 and end-start==4 and core.OPS[op]=='j'
            part[1:4]=(mapped(targets[0])-mapped(end)).to_bytes(3,'little',signed=True)
        survivors.append((mapped(start),op,[(k,mapped(v) if k=='target' else v) for k,v in args]))
        result.extend(part)
    result=bytes(result);decoded,_=core.decode(result)
    actual={row[0]:row for row in decoded}
    for address,op,args in survivors:
        assert actual[address][2:]==(op,args)
    for point,field in POINTS.items():
        ins,setter=replacement(field);start=mapped(point)
        assert result[start:start+len(ins)]==ins
        assert actual[start+setter][2:]==(0x61,[('n',field)])
    assert len(result)==len(data)+sum(len(v)-3 for v in inserts.values())
    return result,dict(originalBodySHA256=hashlib.sha256(data).hexdigest().upper(),
        candidateBodySHA256=hashlib.sha256(result).hexdigest().upper(),
        originalBytes=len(data),candidateBytes=len(result),
        originalInstructionsPreservedExceptTwoWorldSetters=True,
        originalBranchTargetsRelocatedExactly=True,
        setters=[dict(originalOffset=p,field=a.simple(n),replacementHex=inserts[p].hex()) for p,n in POINTS.items()],
        stackEntry=2,stackPeak=4,stackExit=0,originalMaxStack=8,
        newConstants=0,newRegisters=0,newClassMembers=0,
        nativeCameraCalculationsRetained=True,satsSettersRetained=True,sceneTickRetained=True)

def audit(xml,swf):
    code,proof=patched();old_nodes=ET.parse(BASE/'pfe.xml').findall('.//abc');new_nodes=ET.parse(xml).findall('.//abc')
    assert len(old_nodes)==len(new_nodes)==2
    changed=[];preserved=0;classes=0
    for old,new in zip(old_nodes,new_nodes):
        a,b=core.ABC(old),core.ABC(new)
        assert a.named==b.named and a.class_by_name==b.class_by_name and set(a.bodies)==set(b.bodies)
        for i,body in a.bodies.items():
            if a.names_by_method.get(i)==TARGET:
                other=b.bodies[i];assert bytes.fromhex(other.get('codeBytes'))==code
                other.set('codeBytes',body.get('codeBytes'));changed.append(TARGET)
            else:preserved+=1
        assert core.xml_value(old,{'bytes','fileOffset'})==core.xml_value(new,{'bytes','fileOffset'}), 'Untargeted ABC changed'
        classes+=len(a.class_by_name)
    assert changed==[TARGET] and preserved==5770 and classes==1016
    assert engine.support.swf_envelope(BASE/'pfe.swf')==engine.support.swf_envelope(swf)
    return dict(passed=True,changedMethods=changed,unchangedMethodBodies=preserved,unchangedClassLayouts=classes,
        constantPoolsAndPrivateIdentitiesPreserved=True,nonABCAssetsPreserved=True,
        candidateSHA256=sha(swf),candidateXMLSHA256=sha(xml),proof=proof)

def splice():
    audit(HERE/'serialized.xml',BASE/'pfe.swf')
    signature,header,old=engine.raw_swf(BASE/'pfe.swf')
    ds,dh,donor=engine.raw_swf(HERE/'serialized.swf')
    assert signature==ds and header==dh and [v[0] for v in old]==[v[0] for v in donor]
    abc=[i for i,v in enumerate(old) if v[0] in (72,82)];assert len(abc)==2
    for i in abc:assert engine.abc_prefix(old[i])==engine.abc_prefix(donor[i])
    tags=[(donor[i] if i==abc[0] else old[i])[2] for i in range(len(old))]
    content=header+b''.join(tags);output=HERE/'pfe.swf';assert not output.exists()
    output.write_bytes(signature+(len(content)+8).to_bytes(4,'little')+(zlib.compress(content,9) if signature[:3]==b'CWS' else content))
    fs,fh,final=engine.raw_swf(output)
    assert fs==signature and fh==header and [v[2] for v in final]==tags
    assert engine.support.swf_envelope(BASE/'pfe.swf')==engine.support.swf_envelope(output)
    return dict(passed=True,preservedRawTags=len(tags)-1,candidateSHA256=sha(output))

def stage():
    code,proof=patched();_,tree,a,body=source.load();body.set('codeBytes',code.hex())
    target=HERE/'retained.xml';assert not target.exists();tree.write(target,encoding='utf-8',xml_declaration=True)
    return dict(base=HOST,baseXML=XML,target=TARGET,proof=proof,diagnosticOnly=True,deployed=False)

if __name__=='__main__':
    action=sys.argv[1]
    result=stage() if action=='stage' else splice() if action=='splice' else audit(HERE/'pfe.xml',HERE/'pfe.swf') if action=='audit' else None
    assert result is not None
    output=HERE/(action+'-proof.json');assert not output.exists();output.write_text(json.dumps(result,indent=2),'utf-8')
    print(json.dumps(dict(action=action,passed=True,receipt=str(output))),flush=True)
