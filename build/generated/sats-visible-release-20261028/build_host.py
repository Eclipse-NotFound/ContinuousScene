"""Prepare four exact host hooks for the separately compiled V3 SATS handler.

Default: in-memory audit only. --build writes exclusively to this directory.
No AIR, Java, source-class recompilation, deployment, or official configuration write.
"""
from pathlib import Path
import argparse,importlib.util,json,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
SUPPORT=HERE.parent/'camera-environment-paired-binary-20261028'
sys.path.insert(0,str(SUPPORT))
from raw_abc import RawABC,Reader,require,u30
from resources import ResourceGuard

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
b=load('sats_guard_raw_support',SUPPORT/'build.py')
core=load('sats_guard_decoder',HERE.parents[1]/'native-crop-audit.py')
BASE='B84F24280B3C676F4068E1CDC5A6EBEE89988F62BCF7A44D4DD71A4771360184'
FROZEN=HERE.parent/'sats-visible-final-20261028'
EXPECTED='A80ED32BEE50C612CB46EA1E581C8CA9C81072E0B9E6EE1A51E5BACEFBDCBA19'
FROZEN_AUDIT='1B62ED327FC490B8C9846ECD7322BA8D076444B84B43F8A237F503743B107965'
TARGETS={
    3231:('sceneSats','69BF23AA7AC530656672D08F1E561D944E1366845A980A07A6119E8DA671BBF9',2),
    3219:('sceneTick','DEFB11339BB22D7D55790C3E822B8451355EFA6101F6B0C17166711D3D69BF76',116),
    3282:('onSats','50C3A93BEACD1ED41B19F27122408535897F0DE595D8F3C635220BF7226CD092',30)}
CLEAR_NAME='fe.graph.Grafon::0:1:sceneClear'

def call(key,mode,value=False):
    # receiver, action string, [Grafon, mode], call sceneNativeCall(kind,args).
    return b'\xd0\x2c'+u30(key)+b'\xd0\x24'+bytes([mode])+b'\x56\x02'+bytes([0x46 if value else 0x4f])+u30(9048)+b'\x02'

def hook(method,key):
    if TARGETS[method][0]=='sceneClear':
        # Release owned SATS state before native sceneDrop disposes source cells.
        # Dedicated V3 action avoids an older V2 handler treating mode 3 as refresh.
        return call(key,3)
    if method==3231:
        # If handler absent/disabled it returns null/false; execute original body.
        return call(key,1,True)+b'\x12\x01\x00\x00\x47'
    action=call(key,0 if method==3219 else 2)
    test=b'\xd0\x66'+u30(1648)+b'\x66'+u30(3667) if method==3219 else b'\xd1'
    branch=0x12 if method==3219 else 0x11
    return test+bytes([branch])+len(action).to_bytes(3,'little',signed=True)+action

def patched_method(abc,method,key):
    name,pinned,at=TARGETS[method];code=abc.code(method);old=abc.bodies[method]
    require(abc.named['fe.graph.Grafon::0:1:'+name]==method and b.digest(code)==pinned,'Current method changed: '+name)
    rows,_=core.decode(code);addition=hook(method,key)
    require(at in {r[0] for r in rows},'Hook not on instruction boundary')
    if name in ('sceneSats','sceneClear'):require(code[:2]==b'\xd0\x30','Scope prologue changed')
    else:require(code[at:]==b'\x47','Expected terminal return')
    mapping={a:a+(len(addition) if a>at else 0) for a,_,_,_ in rows}
    mapping[len(code)]=len(code)+len(addition)
    out=bytearray()
    for start,end,op,args in rows:
        require(len(out)==mapping[start],'Instruction relocation drift')
        if start==at:out+=addition
        position=len(out)
        if op==0x1b:
            out.append(op)
            out+=(mapping[args[0][1]]-position).to_bytes(3,'little',signed=True)
            out+=u30(len(args)-2)
            for _,dest in args[1:]:out+=(mapping[dest]-position).to_bytes(3,'little',signed=True)
        elif any(k=='target' for k,v in args):
            require(len(args)==1 and end-start==4,'Unknown branch format')
            out.append(op);out+=(mapping[args[0][1]]-(position+4)).to_bytes(3,'little',signed=True)
        else:out+=code[start:end]
    decoded,_=core.decode(bytes(out))
    kept=[r for r in decoded if not at<=r[0]<at+len(addition)]
    require(len(kept)==len(rows),'Original instructions lost')
    for prior,current in zip(rows,kept):
        start,end,op,args=prior
        start_new=mapping[start]+(len(addition) if start==at else 0)
        require(current==(start_new,start_new+end-start,op,[(k,mapping[v] if k=='target' else v) for k,v in args]),
                'Old instruction changed beyond branch relocation')
    tail=Reader(abc.data[old.tail_start:old.end]);count=tail.count();relocated=u30(count)
    for _ in range(count):
        lo,hi,target,kind,var=(tail.integer() for __ in range(5))
        relocated+=b''.join(u30(v) for v in (mapping[lo],mapping[hi],mapping[target],kind,var))
    relocated+=bytes(tail.data[tail.pos:])
    frame=b''.join(u30(v) for v in (method,max(old.stack,4),old.registers,old.scope,old.max_scope,len(out)))
    body=frame+out+relocated
    return body,dict(method=method,name=name,oldCodeSHA256=pinned,newCodeSHA256=b.digest(out),
        oldBytes=len(code),newBytes=len(out),originalInstructionCount=len(rows),
        unchangedOriginalInstructions=True,exceptionOffsetsRelocated=count,
        unchangedTraits=True,maxStack=max(old.stack,4),hookBytes=addition.hex())

def main():
    p=argparse.ArgumentParser();p.add_argument('--build',action='store_true');args=p.parse_args()
    require(HERE.name=='sats-visible-release-20261028','Unexpected candidate directory')
    outputs=[HERE/'pfe.swf',HERE/'host-audit.json']
    if args.build:require(not any(p.exists() for p in outputs),'Preserve existing candidate evidence')
    guard=ResourceGuard()
    try:
        files=[Path(__file__),HERE/'SatsVisibleGuard.as',FROZEN/'host-audit.json',SUPPORT/'build.py',SUPPORT/'raw_abc.py',SUPPORT/'resources.py',HERE.parents[1]/'native-crop-audit.py']
        inputs={str(p):b.sha(p) for p in files}
        require(b.sha(FROZEN/'host-audit.json')==FROZEN_AUDIT,'Frozen V3 audit changed')
        frozen_audit=json.loads((FROZEN/'host-audit.json').read_text('utf-8-sig'))
        require(frozen_audit['passed'] and frozen_audit['candidate']==EXPECTED,'Unexpected frozen V3 host')
        swf=b.RawSWF(ROOT/'pfe.swf');require(swf.sha256==BASE,'Official host changed')
        index=next(i for i,t in enumerate(swf.tags) if t[0]==82);abc=RawABC(swf.abc(index)[1])
        require(abc.simple(9048)=='sceneNativeCall' and abc.simple(1648)=='visSats' and abc.simple(3667)=='visible','Hook bindings changed')
        require(b.digest(abc.code(1159))=='7E3C3C53F08578B9283224D142C5572044F027918A48B7E3C250C63C959D99F2','Boundary fix missing')
        clear_method=abc.named[CLEAR_NAME]
        require(clear_method not in TARGETS,'sceneClear collides with existing target')
        require(abc.bodies[clear_method].exceptions==0,'Review sceneClear exception scope before adding an entry hook')
        # Method identity comes from the exact B84F input; never guess an index.
        # Record its old body digest in the same audit as the three pinned hooks.
        TARGETS[clear_method]=('sceneClear',b.digest(abc.code(clear_method)),2)
        pool=abc.pools['string'];key=pool.count;literal=b'satsVisibleV3'
        require(literal not in abc.strings,'V3 action already installed')
        edits=[(pool.count_start,pool.entries_start,u30(key+1),'string-count'),(pool.end,pool.end,u30(len(literal))+literal,'string-append')]
        methods=[]
        for method in TARGETS:
            body,proof=patched_method(abc,method,key);old=abc.bodies[method]
            edits.append((old.start,old.end,body,'method-'+str(method)));methods.append(proof)
        require(methods==frozen_audit['methods'],'Four native hooks differ from frozen V3')
        changed,inverse=b.edit_bytes(abc.data,edits);restored,_=b.edit_bytes(changed,inverse)
        require(restored==abc.data,'Exact whole ABC inverse failed')
        after=RawABC(changed)
        require(after.strings[:-1]==abc.strings and after.strings[-1]==literal,'Existing strings changed')
        require(after.named==abc.named and after.class_by_name==abc.class_by_name and after.multinames==abc.multinames,'Identities changed')
        preserved=0
        for method,old in abc.bodies.items():
            if method in TARGETS:continue
            new=after.bodies[method]
            require(abc.data[old.start:old.end]==after.data[new.start:new.end],'Unrelated method changed')
            preserved+=1
        require(abc.data[abc.method_start:abc.method_end]==after.data[after.method_start:after.method_end],'Method signatures changed')
        for left,right in zip(abc.instances+abc.classes,after.instances+after.classes):require(abc.raw(left)==after.raw(right),'Class layout changed')
        proof=dict(passed=True,base=BASE,methods=methods,sourceInputs=inputs,handlerAction='satsVisibleV3',
            addedStringIndex=key,unchangedOtherMainBodies=preserved,unchangedClasses=abc.class_count,
            exactInverseRestoresABC=True,unitBoundaryFixPreserved=True,loaderPreserved=True,
            runtimeVerified=False,performanceEligible=False,requiresExplicitHandlerInstall=True,
            sceneClearHookBeforeNativeDrop=True,closeMode=2,sceneClearMode=3,
            note='Without V3 handler original SATS path remains; V2 trial evidence does not validate the new scene-clear lifecycle or product carrier.')
        if args.build:
            b.write_candidate(outputs[0],swf,index,changed);actual=b.RawSWF(outputs[0])
            require(actual.sha256==EXPECTED,'V3 host must remain byte-identical to frozen A80ED32B')
            require(len(actual.tags)==len(swf.tags) and actual.signature==swf.signature,'SWF envelope changed')
            require(actual.body[:actual.frame_end]==swf.body[:swf.frame_end],'Frame header changed')
            for i in range(len(swf.tags)):
                if i!=index:require(actual.raw_tag(i)==swf.raw_tag(i),'Unrelated SWF tag changed')
                else:require(actual.abc(i)[0]==swf.abc(i)[0] and actual.abc(i)[1]==changed,'ABC readback differs')
            proof['candidate']=actual.sha256;proof['preservedRawTags']=len(swf.tags)-1
            proof['identicalFrozenHost']=EXPECTED
        require(inputs=={str(p):b.sha(p) for p in files} and b.sha(ROOT/'pfe.swf')==BASE,'Inputs changed during operation')
        guard.sample('finished');proof['resources']=guard.receipt()
        if args.build:b.json_write(outputs[1],proof)
        print(json.dumps({k:v for k,v in proof.items() if k not in ('sourceInputs','resources')}))
    finally:guard.close()

if __name__=='__main__':main()
