"""Bounded string-key cache in one exact host method; original bindings retained."""
from pathlib import Path
import hashlib,importlib.util,json,sys,xml.etree.ElementTree as ET,zlib
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;B=HERE.parents[1]
sp=importlib.util.spec_from_file_location('environment_original_body',HERE.parent/'camera-environment-clamp-20261027/audit.py')
prior=importlib.util.module_from_spec(sp);sp.loader.exec_module(prior)
BASE,HOST,XML,TARGET,engine,core,sha=prior.BASE,prior.HOST,prior.XML,prior.TARGET,prior.engine,prior.core,prior.sha
NAME='_csEnvironmentCellKeysV1';STRING=8161;QNAME=9705
def check_stack(code):
    rows,_=core.decode(code);by_start={r[0]:r for r in rows};pending=[(0,1)];depths={};maximum=1;ends=[]
    while pending:
        at,depth=pending.pop()
        if at==len(code):ends.append(depth);continue
        if at in depths:assert depths[at]==depth;continue
        depths[at]=depth;start,end,op,args=by_start[at]
        if op in [0x20,0x24,0x25,0x2c,0x60,0x62,0xd1,0xd2,0xd3]:needed,delta=0,1
        elif op==0x63:needed,delta=1,-1
        elif op in [0x73,0x85,0x86]:needed,delta=1,0
        elif op in [0xa0,0xa3]:needed,delta=2,-1
        elif op==0x66:needed,delta=(2,-1) if args[0][1]==8883 else (1,0)
        elif op==0x61:needed,delta=(3,-3) if args[0][1]==8883 else (2,-2)
        elif op==0x56:needed,delta=args[0][1],1-args[0][1]
        elif op==0x46:needed,delta=args[1][1]+1,-args[1][1]
        elif op in [0x13,0x14,0x15,0x17,0x1a]:needed,delta=2,-2
        elif op==0x10:needed,delta=0,0
        else:raise AssertionError(('unreviewed cache opcode',hex(op)))
        assert depth>=needed;after=depth+delta;maximum=max(maximum,after)
        targets=[v for k,v in args if k=='target']
        pending.extend((v,after) for v in targets)
        if op!=0x10:pending.append((end,after))
    assert ends and set(ends)=={2} and len(depths)==len(rows) and maximum<=8
    return dict(entryDepth=1,exitDepth=2,maximumDepth=maximum,allInstructionsReachable=True,mergeDepthsConsistent=True)
def add_name(node):
    a=core.ABC(node);assert len(a.cp['constant_string'])==STRING and len(a.cp['constant_multiname'])==QNAME
    assert all((e.text or '')!=NAME for e in a.cp['constant_string'])
    ns=a.cp['constant_namespace'][1];assert ns.get('kind')=='22' and a.string(int(ns.get('name_index')))==''
    ET.SubElement(node.find('constants/constant_string'),'item').text=NAME
    ET.SubElement(node.find('constants/constant_multiname'),'item',dict(type='Multiname',kind='7',name_index=str(STRING),namespace_index='1',namespace_set_index='0',qname_index='0'))
def key_code():
    _,a,_,data,_=prior.original()
    assert a.qualified(26)=='Array' and a.qualified(10)=='String'
    code=bytearray();labels={};branches=[]
    def u(n):
        out=bytearray()
        while n>=128:out.append((n&127)|128);n>>=7
        out.append(n);return out
    def emit(op,*args):
        code.append(op)
        for n in args:code.extend(u(n))
    def label(name):assert name not in labels;labels[name]=len(code)
    def jump(op,name):branches.append((len(code),name));code.extend(bytes([op,0,0,0]))
    def get(n):emit(0x62,n)
    def put(n):emit(0x63,n)
    def prop(n):emit(0x66,n)
    def slot(obj,index):get(obj);emit(0x24,index);prop(8883)
    def compose():
        get(11);get(9);emit(0xa0);emit(0x2c,5107);emit(0xa0)
        get(12);get(10);emit(0xa0);emit(0xa0);emit(0x85);put(16)
    # Same original Math.max/divide/int sequences, now evaluated once per axis.
    code.extend(data[73:88]);put(9)
    code.extend(data[100:115]);put(10)
    code.extend(data[66:73]);put(11)
    code.extend(data[93:100]);put(12)
    for n in [9,10]:
        get(n);emit(0x24,0);jump(0x15,'fallback')
        get(n);emit(0x25,255);jump(0x17,'fallback')
    get(4);prop(QNAME);emit(0x86,26);put(13)
    get(13);emit(0x20);jump(0x13,'initialize')
    slot(13,0);get(11);jump(0x1a,'initialize')
    slot(13,1);get(12);jump(0x1a,'initialize')
    slot(13,2);emit(0x86,26);put(14)
    get(14);emit(0x20);jump(0x14,'column')
    label('initialize');get(11);get(12);emit(0x56,0);emit(0x56,3);put(13)
    get(4);get(13);emit(0x61,QNAME);slot(13,2);emit(0x86,26);put(14)
    label('column');get(14);get(9);prop(8883);emit(0x86,26);put(15)
    get(15);emit(0x20);jump(0x14,'key')
    emit(0x56,0);put(15);get(14);get(9);get(15);emit(0x61,8883)
    label('key');get(15);get(10);prop(8883);emit(0x86,10);put(16)
    get(16);emit(0x20);jump(0x14,'ready')
    compose();get(15);get(10);get(16);emit(0x61,8883);jump(0x10,'ready')
    label('fallback');compose()
    label('ready');get(16)
    for start,name in branches:code[start+1:start+4]=(labels[name]-start-4).to_bytes(3,'little',signed=True)
    rows,addresses=core.decode(bytes(code))
    assert all(v in addresses for row in rows for k,v in row[3] if k=='target')
    assert sum(row[2]==0x46 and row[3]==[('n',5071),('u',2)] for row in rows)==2
    check_stack(bytes(code))
    return bytes(code)
def patched():
    _,_,_,data,rows=prior.original();replacement=key_code();delta=len(replacement)-51
    def pos(n):
        assert not 66<n<117
        return n+(delta if n>=117 else 0)
    out=bytearray();survivors=[]
    for start,end,op,args in rows:
        if start==66:out.extend(replacement);continue
        if 66<start<117:continue
        assert len(out)==pos(start) and op!=0x1b
        part=bytearray(data[start:end]);targets=[v for k,v in args if k=='target']
        if targets:
            assert len(targets)==1 and end-start==4
            part[1:4]=(pos(targets[0])-pos(end)).to_bytes(3,'little',signed=True)
        out.extend(part);survivors.append((start,end,op,args))
    decoded,addresses=core.decode(bytes(out))
    for start,end,op,args in survivors:
        got=next(row for row in decoded if row[0]==pos(start))
        assert got[1]==pos(end) and got[2]==op
        assert got[3]==[(k,pos(v)) if k=='target' else (k,v) for k,v in args]
    assert all(v in addresses for row in decoded for k,v in row[3] if k=='target')
    return bytes(out)
def stage():
    tree,a,body,data,_=prior.original();add_name(a.node)
    body.set('codeBytes',patched().hex());body.set('max_regs','17');body.set('max_stack','8')
    out=HERE/'retained.xml';assert not out.exists();tree.write(out,encoding='utf-8',xml_declaration=True)
    return dict(base=HOST,baseXML=XML,target=TARGET,oldCodeSHA256=hashlib.sha256(data).hexdigest().upper(),newCodeSHA256=hashlib.sha256(patched()).hexdigest().upper(),
        replacedRange=[66,117],newBytes=len(patched()),addedPublicPropertyName=NAME,addedStringIndex=STRING,addedQNameIndex=QNAME,newClassFields=0,
        originalMathMaxCallsPreserved=True,allOtherInstructionsPreserved=True,stackProof=check_stack(key_code()))
def audit(xml,swf):
    old=ET.parse(BASE/'pfe.xml').findall('.//abc');new=ET.parse(xml).findall('.//abc');assert len(old)==len(new)==2
    changed=[];preserved=0;classes=0
    for one,two in zip(old,new):
        a,b=core.ABC(one),core.ABC(two);assert a.named==b.named and a.class_by_name==b.class_by_name and set(a.bodies)==set(b.bodies)
        for idx,body in a.bodies.items():
            other=b.bodies[idx];name=a.names_by_method.get(idx)
            if name==TARGET:
                assert bytes.fromhex(other.get('codeBytes'))==patched() and other.get('max_regs')=='17' and other.get('max_stack')=='8'
                assert not list(other.find('exceptions')) and not list(other.find('traits/traits'))
                assert dict(other.attrib,codeBytes=body.get('codeBytes'),max_regs=body.get('max_regs'),max_stack=body.get('max_stack'))==dict(body.attrib)
                for k in ['codeBytes','max_regs','max_stack']:other.set(k,body.get(k))
                changed.append(name)
        if TARGET in a.named:
            for pool,index in [('constant_string',STRING),('constant_multiname',QNAME)]:
                assert len(b.cp[pool])==len(a.cp[pool])+1 and len(a.cp[pool])==index
            assert b.string(STRING)==NAME and b.qualified(QNAME)==NAME
            mn=b.cp['constant_multiname'][QNAME]
            assert dict(mn.attrib)==dict(type='Multiname',kind='7',name_index=str(STRING),namespace_index='1',namespace_set_index='0',qname_index='0')
            for pool in ['constant_string','constant_multiname']:
                parent=two.find('constants/'+pool);parent.remove(list(parent)[-1])
        preserved+=len(a.bodies)-(1 if TARGET in a.named else 0);classes+=len(a.class_by_name)
        assert core.xml_value(one,{'bytes','fileOffset'})==core.xml_value(two,{'bytes','fileOffset'})
    assert changed==[TARGET] and preserved==5770 and classes==1016
    assert engine.support.swf_envelope(BASE/'pfe.swf')==engine.support.swf_envelope(swf)
    return dict(passed=True,changed=changed,unchangedBodies=preserved,unchangedClasses=classes,originalConstantPoolPrefix=True,
        appendedNames=[NAME],originalPrivateIdentities=True,originalRawAssets=True,candidateSHA256=sha(swf),candidateXMLSHA256=sha(xml),baseSHA256=HOST,deployed=False)
def splice():
    audit(HERE/'serialized.xml',BASE/'pfe.swf')
    signature,header,old=engine.raw_swf(BASE/'pfe.swf');ds,dh,donor=engine.raw_swf(HERE/'serialized.swf')
    assert signature==ds and header==dh and len(old)==len(donor) and [t[0] for t in old]==[t[0] for t in donor]
    abc=[i for i,t in enumerate(old) if t[0] in (72,82)];assert len(abc)==2
    for i in abc:assert engine.abc_prefix(old[i])==engine.abc_prefix(donor[i])
    tags=[(donor[i] if i==abc[0] else old[i])[2] for i in range(len(old))];body=header+b''.join(tags);out=HERE/'pfe.swf';assert not out.exists()
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
