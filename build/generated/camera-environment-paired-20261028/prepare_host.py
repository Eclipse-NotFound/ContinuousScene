"""Prepare a diagnostic selector around the exact original and cached key blocks."""
from pathlib import Path
import ast,importlib.util
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-environment-keycache-20261027'

def one(s,a,b):
    assert s.count(a)==1,(a[:100],s.count(a))
    return s.replace(a,b,1)

def audit_source():
    s=(BASE/'audit.py').read_text('utf-8-sig')
    s=one(s,"NAME='_csEnvironmentCellKeysV1';STRING=8161;QNAME=9705",
        "NAME='_csEnvironmentCellKeysV1';STRING=8161;QNAME=9705\nSWITCH='_csUseEnvironmentKeyCacheV1';SWITCH_STRING=8162;SWITCH_QNAME=9706")
    s=one(s,'0x20,0x24,0x25,0x2c,','0x20,0x24,0x25,0x26,0x2c,')
    marker="    ET.SubElement(node.find('constants/constant_multiname'),'item',dict(type='Multiname',kind='7',name_index=str(STRING),namespace_index='1',namespace_set_index='0',qname_index='0'))"
    s=one(s,marker,marker+"\n    ET.SubElement(node.find('constants/constant_string'),'item').text=SWITCH\n    ET.SubElement(node.find('constants/constant_multiname'),'item',dict(type='Multiname',kind='7',name_index=str(SWITCH_STRING),namespace_index='1',namespace_set_index='0',qname_index='0'))")
    s=one(s,'def key_code():','def cached_key_code():')
    s=one(s,'def patched():','''def key_code():
    # The shared branch is present in both measured modes; all original key
    # instructions remain contiguous and byte-identical in the baseline branch.
    _,_,_,data,rows=prior.original()
    native=data[66:117];cached=cached_key_code()
    assert not [arg for start,end,op,args in rows if 66<=start<117 for arg in args if arg[0]=='target']
    def u(n):
        out=bytearray()
        while n>=128:out.append((n&127)|128);n>>=7
        out.append(n);return bytes(out)
    head=bytes([0x62,4,0x66])+u(SWITCH_QNAME)+bytes([0x26,0x1a])
    # ifstrictne skips the cached block and its final unconditional jump.
    head+=(len(cached)+4).to_bytes(3,'little',signed=True)
    result=head+cached+bytes([0x10])+len(native).to_bytes(3,'little',signed=True)+native
    check_stack(result)
    return result

def patched():''')
    s=one(s,"addedPublicPropertyName=NAME,addedStringIndex=STRING,addedQNameIndex=QNAME,newClassFields=0,",
        "addedPublicPropertyNames=[NAME,SWITCH],addedStringIndices=[STRING,SWITCH_STRING],addedQNameIndices=[QNAME,SWITCH_QNAME],newClassFields=0,diagnosticOnly=True,")
    s=one(s,"assert len(b.cp[pool])==len(a.cp[pool])+1 and len(a.cp[pool])==index",
        "assert len(b.cp[pool])==len(a.cp[pool])+2 and len(a.cp[pool])==index")
    s=one(s,"            assert b.string(STRING)==NAME and b.qualified(QNAME)==NAME",
        "            assert b.string(STRING)==NAME and b.qualified(QNAME)==NAME\n            assert b.string(SWITCH_STRING)==SWITCH and b.qualified(SWITCH_QNAME)==SWITCH\n            assert dict(b.cp['constant_multiname'][SWITCH_QNAME].attrib)==dict(type='Multiname',kind='7',name_index=str(SWITCH_STRING),namespace_index='1',namespace_set_index='0',qname_index='0')")
    s=one(s,"parent=two.find('constants/'+pool);parent.remove(list(parent)[-1])",
        "parent=two.find('constants/'+pool);parent.remove(list(parent)[-1]);parent.remove(list(parent)[-1])")
    s=one(s,'appendedNames=[NAME],','appendedNames=[NAME,SWITCH],diagnosticOnly=True,')
    return s

def build_source():
    s=(BASE/'build.py').read_text('utf-8-sig')
    s=one(s,'import importlib.util,json,subprocess,sys','import argparse,importlib.util,json,subprocess,sys')
    s=one(s,"HERE.parent/'camera-visible-allocation-stacks-20261027/run.py'","HERE.parent/'camera-native-once-20261028/run.py'")
    s=one(s,"    paths.extend([e.JAVA,e.TOOLS/'ffdec/ffdec-cli.jar'])", """    parser=argparse.ArgumentParser();parser.add_argument('--wait-ready-seconds',type=int,default=0);args=parser.parse_args()
    readiness=fixture.wait_ready(args.wait_ready_seconds)
    if readiness is not None and not readiness['ready']:return
    paths.extend([e.JAVA,e.TOOLS/'ffdec/ffdec-cli.jar'])""")
    s=one(s,"paths.extend([e.JAVA,e.TOOLS/'ffdec/ffdec-cli.jar'])",
        "paths.extend([HERE/'prepare_host.py',HERE.parent/'camera-environment-keycache-20261027/audit.py',HERE.parent/'camera-environment-keycache-20261027/build.py',e.JAVA,e.TOOLS/'ffdec/ffdec-cli.jar'])")
    s=one(s,"version='scene-environment-keycache-1'","version='scene-environment-paired-diagnostic-1'")
    s=one(s,"deployed=False,runtimeVerified=False)","deployed=False,runtimeVerified=False,diagnosticOnly=True,readinessReceipt=readiness)")
    return s

def prepare():
    for name,value in [('audit.py',audit_source()),('build.py',build_source())]:
        ast.parse(value);path=HERE/name
        if path.exists():assert path.read_text('utf-8-sig')==value,name
        else:path.write_text(value,'utf-8')

if __name__=='__main__':
    prepare();print('Prepared diagnostic method selector; no compilation or game launch')
