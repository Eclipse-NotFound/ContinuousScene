"""Two local clamp replacements on the exact installed method; no new bindings."""
from pathlib import Path
import hashlib,importlib.util,json,sys,xml.etree.ElementTree as ET,zlib
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;B=HERE.parents[1]
BASE=B/'generated/scene-compat-20261024/tint/product'
HOST='A796827173AF7D6FAB9885FB66ECC62182AB5335918A30C7CCE4C44914A238B7'
XML='1D2642C7D55D1F97121738E6AE84996A140EBFEFF686E6706C88CEF82A7338DA'
TARGET='fe.graph.Grafon::0:1:sceneNativeEnvironment'
sp=importlib.util.spec_from_file_location('environment_clamp_retainer',B/'bullet-segments-audit.py')
engine=importlib.util.module_from_spec(sp);sp.loader.exec_module(engine);core=engine.core;sha=engine.sha
def original():
    assert sha(BASE/'pfe.swf')==HOST and sha(BASE/'pfe.xml')==XML
    tree=ET.parse(BASE/'pfe.xml');a=core.ABC(tree.findall('.//abc')[0]);body=a.bodies[a.named[TARGET]]
    assert body.get('method_info')=='3253' and body.get('max_regs')=='9' and body.get('max_stack')=='6'
    assert not list(body.find('exceptions')) and not list(body.find('traits/traits'))
    data=bytes.fromhex(body.get('codeBytes'));assert len(data)==205
    assert a.qualified(4720)=='Math' and a.simple(5071)=='max'
    assert a.string(5107)==':'
    rows,_=core.decode(data)
    for start,end,local in [(73,83,0xd2),(100,110,0xd3)]:
        picked=[(op,args) for a,b,op,args in rows if start<=a<end]
        assert picked==[(0x60,[('n',4720)]),(0x24,[('b',0)]),(local,[]),(0x46,[('n',5071),('u',2)])]
    return tree,a,body,data,rows
def patched():
    tree,a,body,data,rows=original()
    replacements={73:(83,bytes.fromhex('d224000c060000240010010000d2')),
                  100:(110,bytes.fromhex('d324000c060000240010010000d3'))}
    def pos(old):
        assert not any(start<old<end for start,(end,code) in replacements.items())
        return old+sum(len(code)-(end-start) for start,(end,code) in replacements.items() if old>=end)
    result=bytearray();survivors=[]
    for start,end,op,args in rows:
        if start in replacements:
            result.extend(replacements[start][1]);continue
        if any(lo<start<hi for lo,(hi,code) in replacements.items()):continue
        assert len(result)==pos(start)
        part=bytearray(data[start:end]);targets=[v for k,v in args if k=='target']
        assert op!=0x1b
        if targets:
            assert len(targets)==1 and core.OPS[op]=='j' and end-start==4
            part[1:4]=(pos(targets[0])-pos(end)).to_bytes(3,'little',signed=True)
        result.extend(part);survivors.append((start,end,op,args))
    result=bytes(result);new,addresses=core.decode(result)
    assert len(result)==213
    assert all(v in addresses for row in new for k,v in row[3] if k=='target')
    for start,end,op,args in survivors:
        found=next(v for v in new if v[0]==pos(start))
        assert found[1]==pos(end) and found[2]==op
        assert found[3]==[(k,pos(v)) if k=='target' else (k,v) for k,v in args]
    assert result[pos(73):pos(73)+14]==replacements[73][1]
    assert result[pos(100):pos(100)+14]==replacements[100][1]
    return result
def stage():
    tree,a,body,data,rows=original();body.set('codeBytes',patched().hex())
    out=HERE/'retained.xml';assert not out.exists();tree.write(out,encoding='utf-8',xml_declaration=True)
    return dict(base=HOST,baseXML=XML,target=TARGET,oldCodeSHA256=hashlib.sha256(data).hexdigest().upper(),
        newCodeSHA256=hashlib.sha256(patched()).hexdigest().upper(),oldBytes=205,newBytes=213,
        oldOffsets=[[73,83],[100,110]],newConstants=0,newFields=0,newMethods=0,allOtherInstructionsPreserved=True)
def audit(xml,swf):
    old=ET.parse(BASE/'pfe.xml').findall('.//abc');new=ET.parse(xml).findall('.//abc')
    assert len(old)==len(new)==2
    changed=[];preserved=0;classes=0
    for one,two in zip(old,new):
        a,b=core.ABC(one),core.ABC(two)
        assert a.named==b.named and a.class_by_name==b.class_by_name and set(a.bodies)==set(b.bodies)
        for idx,body in a.bodies.items():
            other=b.bodies[idx];name=a.names_by_method.get(idx)
            if name==TARGET:
                assert bytes.fromhex(other.get('codeBytes'))==patched()
                assert dict(other.attrib,codeBytes=body.get('codeBytes'))==dict(body.attrib)
                assert not list(other.find('exceptions')) and not list(other.find('traits/traits'))
                other.set('codeBytes',body.get('codeBytes'));changed.append(name)
            else:preserved+=1
        assert core.xml_value(one,{'bytes','fileOffset'})==core.xml_value(two,{'bytes','fileOffset'})
        classes+=len(a.class_by_name)
    assert changed==[TARGET] and preserved==5770 and classes==1016
    assert engine.support.swf_envelope(BASE/'pfe.swf')==engine.support.swf_envelope(swf)
    return dict(passed=True,changed=changed,unchangedBodies=preserved,unchangedClasses=classes,
        originalConstantPool=True,originalPrivateIdentities=True,originalRawAssets=True,
        candidateSHA256=sha(swf),candidateXMLSHA256=sha(xml),baseSHA256=HOST,deployed=False)
def splice():
    audit(HERE/'serialized.xml',BASE/'pfe.swf')
    signature,header,old=engine.raw_swf(BASE/'pfe.swf');ds,dh,donor=engine.raw_swf(HERE/'serialized.swf')
    assert signature==ds and header==dh and len(old)==len(donor) and [t[0] for t in old]==[t[0] for t in donor]
    abc=[i for i,t in enumerate(old) if t[0] in (72,82)];assert len(abc)==2
    for i in abc:assert engine.abc_prefix(old[i])==engine.abc_prefix(donor[i])
    tags=[(donor[i] if i==abc[0] else old[i])[2] for i in range(len(old))]
    body=header+b''.join(tags);out=HERE/'pfe.swf';assert not out.exists()
    out.write_bytes(signature+(len(body)+8).to_bytes(4,'little')+(zlib.compress(body,9) if signature[:3]==b'CWS' else body))
    fs,fh,final=engine.raw_swf(out);assert fs==signature and fh==header and [t[2] for t in final]==tags
    assert engine.support.swf_envelope(BASE/'pfe.swf')==engine.support.swf_envelope(out)
    return dict(base=HOST,candidate=sha(out),onlyABCTagChanged=abc[0],preservedRawTags=len(old)-1)
if __name__=='__main__':
    action=sys.argv[1]
    if action=='stage':result=stage()
    elif action=='splice':result=splice()
    elif action=='audit':result=audit(HERE/'pfe.xml',HERE/'pfe.swf')
    else:raise ValueError('stage/splice/audit required')
    out=HERE/(action+'-proof.json');assert not out.exists();out.write_text(json.dumps(result,indent=2),'utf-8')
    print(json.dumps(dict(step=action,passed=True,receiptSHA256=sha(out))),flush=True)
