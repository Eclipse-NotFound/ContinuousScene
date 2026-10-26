"""Inspect the exact installed camera body and the prior retained source lineage."""
from pathlib import Path
import hashlib
import importlib.util
import json
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
B=HERE.parents[1]
GAME=B.parents[2]
BASE=B/'generated/scene-compat-20261024/tint/product'
HOST='A796827173AF7D6FAB9885FB66ECC62182AB5335918A30C7CCE4C44914A238B7'
XML='1D2642C7D55D1F97121738E6AE84996A140EBFEFF686E6706C88CEF82A7338DA'
TARGET='fe.inter.Camera::0:1:calc'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()

def load():
    assert sha(BASE/'pfe.swf')==sha(GAME/'pfe.swf')==HOST
    assert sha(BASE/'pfe.xml')==XML
    spec=importlib.util.spec_from_file_location('scroll_native_exact_support',B/'bullet-segments-audit.py')
    engine=importlib.util.module_from_spec(spec);spec.loader.exec_module(engine)
    tree=ET.parse(BASE/'pfe.xml');abc=engine.core.ABC(tree.findall('.//abc')[0])
    body=abc.bodies[abc.named[TARGET]]
    previous=engine.core.ABC(ET.parse(B/'generated/vertical-camera-band-20261023/pfe.xml').findall('.//abc')[0])
    assert ET.tostring(body)==ET.tostring(previous.bodies[previous.named[TARGET]])
    return engine,tree,abc,body

if __name__=='__main__':
    engine,tree,abc,body=load()
    rows,_=engine.core.decode(bytes.fromhex(body.get('codeBytes')))
    setters=[]
    for i,row in enumerate(rows):
        if row[2]==0x61 and any(k=='n' and abc.simple(v) in ('x','y') for k,v in row[3]):
            setters.append(dict(index=i,rows=[dict(offset=r[0],end=r[1],op=hex(r[2]),args=[(k,v,abc.qualified(v) if k=='n' else '') for k,v in r[3]]) for r in rows[max(0,i-12):i+3]]))
    pool=[]
    for i,mn in enumerate(abc.cp['constant_multiname']):
        if i and abc.simple(i)=='scrollRect':pool.append(dict(index=i,node=mn.attrib,name=abc.multiname(i)))
    print(json.dumps(dict(body=body.attrib,setters=setters,scrollRect=pool),ensure_ascii=False))
