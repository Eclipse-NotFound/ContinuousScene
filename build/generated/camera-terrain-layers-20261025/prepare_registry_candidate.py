"""Prepare and verify a source-only proposed change; no shared tool writes."""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
SOURCE=ROOT/'ModLoader/tools/test_registry.py'
TARGET=HERE/'test_registry.proposed.py'
original=SOURCE.read_text('utf-8-sig')
assert original.count('import sqlite3\n')==1
helpers=(HERE/'registry-fallback-candidate.py').read_text('utf-8-sig')
a=helpers.index("PREFIX='cim-microseconds:'")
b=helpers.index("if __name__=='__main__':")
helpers=helpers[a:b].replace("PREFIX='cim-microseconds:'","CIM_TOKEN_PREFIX='cim-microseconds:'").replace('PREFIX+', 'CIM_TOKEN_PREFIX+').replace('len(PREFIX)', 'len(CIM_TOKEN_PREFIX)').replace('startswith(PREFIX)', 'startswith(CIM_TOKEN_PREFIX)')
anchor='def process_token(pid):'
out=original.replace('import sqlite3\n','import sqlite3\nimport subprocess\n',1).replace(anchor,helpers+'\n'+anchor,1)
old='        return None if ctypes.get_last_error() == 87 else "unknown"'
assert out.count(old)==1
out=out.replace(old,'''        error = ctypes.get_last_error()
        if error == 87:
            return None
        # A reused protected system PID can deny OpenProcess. Supplement its
        # creation identity without treating CIM failures or absence as exit.
        return cim_token(pid) if error == 5 else "unknown"''',1)
old='return token is None or (token != "unknown" and process["token"] != "unknown" and token != process["token"])'
assert out.count(old)==1
out=out.replace(old,'return token is None or different_identity(process["token"], token)',1)
ast.parse(out)
if TARGET.exists():assert TARGET.read_text('utf-8-sig')==out
else:TARGET.write_text(out,'utf-8')
# These assertions also protect the unchanged reservation / recover operations.
for name in ('Registry','Registration','main'):
    before=next(n for n in ast.parse(original).body if getattr(n,'name',None)==name)
    after=next(n for n in ast.parse(out).body if getattr(n,'name',None)==name)
    assert ast.dump(before)==ast.dump(after),name
spec=importlib.util.spec_from_file_location('registry_source_candidate',TARGET)
candidate=importlib.util.module_from_spec(spec);spec.loader.exec_module(candidate)
live=candidate.process_token(63256)
old={'pid':63256,'token':'134374159796693439'}
assert candidate.different_identity(old['token'],live)
assert not candidate.different_identity(live,live)
assert not candidate.different_identity(old['token'],'unknown')
assert not candidate.different_identity('unknown',live)
summary=dict(sourceSHA256=hashlib.sha256(SOURCE.read_bytes()).hexdigest().upper(),
    candidateSHA256=hashlib.sha256(TARGET.read_bytes()).hexdigest().upper(),
    currentToken=live,recordedToken=old['token'],differentIdentity=True,
    registryMethodsUnchanged=True,sharedSourceUnchanged=True,installed=False)
(HERE/'registry-candidate-check.json').write_text(json.dumps(summary,indent=2),'utf-8')
print(json.dumps(summary))
