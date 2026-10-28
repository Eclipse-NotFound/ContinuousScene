"""Read only the current Unit.run bytecode; never patch or execute game code."""
from pathlib import Path
import importlib.util,sys,hashlib,json
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
support=HERE.parent/'camera-environment-paired-binary-20261028'
sys.path.insert(0,str(support))
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
b=load('boundary_raw_support',support/'build.py')
core=load('boundary_opcode_decoder',HERE.parents[1]/'native-crop-audit.py')
swf=b.RawSWF(HERE.parents[4]/'pfe.swf')
assert swf.sha256==b.BASE_SHA
index=next(i for i,t in enumerate(swf.tags) if t[0]==82)
prefix,data=swf.abc(index);abc=b.RawABC(data)
target=abc.named['fe.unit.Unit::0:1:run'];body=abc.bodies[target];code=abc.code(target)
rows,addresses=core.decode(code)
def name(i):return abc.simple(i) if i and abc.multinames[i][0] in (7,13,9,14,15,16) else '<runtime>'
print(json.dumps(dict(target=target,codeSHA256=b.digest(code),body=str(body),getTile=[i for i in range(len(abc.multinames)) if name(i)=='getTile'])))
for i,row in enumerate(rows):
    if row[2]==0x66 and any(k=='n' and name(v)=='space' for k,v in row[3]):
        print('SPACE at',row[0])
        for r in rows[max(0,i-2):i+22]:
            print(r,[(v,name(v)) for k,v in r[3] if k=='n'])
