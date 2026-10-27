from pathlib import Path
import ast
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-live-parking-20261027'
VERSION='camera-live-parking-return-1'
def one(s,a,b):
    assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
def generated():
    result={}
    for name in ['tests/SceneFarParkingTrial.as','probe_patch.py','summary.py','README.md','run.py']:
        s=(BASE/name).read_text('utf-8-sig').replace('camera-live-parking-1',VERSION)
        if name.endswith('.as'):
            s=one(s,'                return verification;\n            } finally {if(a)a.dispose();if(b)b.dispose();if(c)c.dispose();report.pixelBuffersDisposed=3;}','            } finally {if(a)a.dispose();if(b)b.dispose();if(c)c.dispose();report.pixelBuffersDisposed=3;}\n            return verification;')
        if name=='probe_patch.py':
            s=one(s,"EXTRA_INPUTS=(HERE/'prepare.py',HERE/'summary.py')", "EXTRA_INPUTS=(HERE/'prepare.py',HERE/'summary.py',HERE.parent/'camera-live-parking-20261027/tests/SceneFarParkingTrial.as',HERE.parent/'camera-live-parking-20261027/probe_patch.py',HERE.parent/'camera-live-parking-20261027/summary.py',HERE.parent/'camera-live-parking-20261027/README.md',HERE.parent/'camera-live-parking-20261027/run.py')")
        if name=='README.md':s+='\n前驱只在编译阶段失败（AS3要求try/finally后显式return）；本变体仅移动返回语句，不改变实验行为。前驱证据保留。\n'
        result[name]=s
    return result
if __name__=='__main__':
    for name,s in generated().items():
        p=HERE/name;p.parent.mkdir(exist_ok=True)
        if p.suffix=='.py':ast.parse(s)
        if p.exists():assert p.read_text('utf-8-sig')==s
        else:p.write_text(s,'utf-8')
    print('Prepared AS3 explicit-return repair; failed compilation preserved')
