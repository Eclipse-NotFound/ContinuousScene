"""Add only EnableTelemetry tag 93 to an exact isolated A796 host copy.

The official Adobe add-opt-in format uses a two-byte zero reserved payload.
No code, asset, FileAttributes, frame dimensions, timing or other tag changes.
"""
import hashlib
import struct
from pathlib import Path

HOST='A796827173AF7D6FAB9885FB66ECC62182AB5335918A30C7CCE4C44914A238B7'
TAG=struct.pack('<HH',(93<<6)|2,0)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def instrument(source,destination):
    assert sha(source)==HOST and not destination.exists()
    raw=source.read_bytes();assert raw[:3]==b'FWS'
    assert len(raw)==struct.unpack_from('<I',raw,4)[0]
    pos=8+(5+4*(raw[8]>>3)+7)//8+4;tags=[]
    while pos<len(raw):
        start=pos;h=struct.unpack_from('<H',raw,pos)[0];pos+=2
        code,length=h>>6,h&63
        if length==63:length=struct.unpack_from('<I',raw,pos)[0];pos+=4
        pos+=length;assert pos<=len(raw);tags.append((code,start,pos))
        if code==0:break
    assert pos==len(raw) and tags[0][0]==69 and not any(t[0] in (92,93) for t in tags)
    where=tags[1][2] if tags[1][0]==77 else tags[0][2]
    changed=bytearray(raw[:where]+TAG+raw[where:]);struct.pack_into('<I',changed,4,len(changed))
    restored=bytearray(changed[:where]+changed[where+4:]);struct.pack_into('<I',restored,4,len(restored))
    assert bytes(restored)==raw
    destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open('xb') as f:f.write(changed)
    assert destination.read_bytes()==bytes(changed)
    return dict(originalSHA256=HOST,instrumentedSHA256=sha(destination),tagCode=93,tagPayload='0000',tagOffset=where,
                originalTags=len(tags),addedBytes=4,allOriginalBytesRestored=True,gameCodeChanged=False,deployed=False)
