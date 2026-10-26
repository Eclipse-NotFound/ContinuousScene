"""Numerically inspect retained original PNGs without editing image contents."""
from pathlib import Path
import hashlib
import json
from PIL import Image
import numpy as np
HERE=Path(__file__).resolve().parent
FOLDER=HERE.parents[2]/'knowledge/experiments/evidence/camera-stage3d-wholeworld-observed-20261027-r1/storage/stage3d-pixels'
def main():
    left,right=FOLDER/'native-0.png',FOLDER/'candidate-0.png'
    a=np.asarray(Image.open(left).convert('RGBA')).astype(np.int16)
    b=np.asarray(Image.open(right).convert('RGBA')).astype(np.int16)
    assert a.shape==b.shape
    d=np.max(np.abs(a[:,:,:3]-b[:,:,:3]),axis=2);rows=[]
    for t in (1,2,3,5,10,30,60,100):
        y,x=np.where(d>=t)
        rows.append(dict(threshold=t,count=len(x),bounds=None if len(x)==0 else [int(x.min()),int(y.min()),int(x.max()),int(y.max())]))
    result=dict(inputs={str(p):hashlib.sha256(p.read_bytes()).hexdigest().upper() for p in (left,right)},thresholds=rows,
        maxRGB=int(d.max()),maxAlpha=int(np.abs(a[:,:,3]-b[:,:,3]).max()),visualAccepted=False,
        interpretation='Full native/candidate images visually inspected; no obvious terrain omission. RGB>=3 localized around glowing object edges. Blend mechanism not established.')
    dest=HERE/'pixel-review.json';assert not dest.exists()
    dest.write_text(json.dumps(result,indent=2),'utf-8');print(json.dumps(result['thresholds']))
if __name__=='__main__':main()
