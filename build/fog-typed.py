"""Candidate: type native sight-loop temporaries and reuse the current tile.

Keep arithmetic, ray endpoints, visibility and pixel writes in their original
order. Transplant only Location.lighting into the verified installed host.
"""
from pathlib import Path
import hashlib, importlib.util, json, shutil, subprocess, sys
import objects_native_patch as methods

B=Path(__file__).resolve().parent
OUT=B/'generated/fog-typed'
ROOT=B.parents[2]
JAVA='D:/Program Files/Adobe Animate 2024/jre/bin/java.exe'
FF=ROOT/'mods/Sandevistan/build/tools/ffdec/ffdec-cli.jar'
BASE=B/'generated/motion-direction-rays'
spec=importlib.util.spec_from_file_location('parser',B/'profile-vision.py')
parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)
def ff(*args):subprocess.run([JAVA,'-Xmx1400m','-jar',str(FF),*map(str,args)],check=True)
def once(s,a,b):
    assert s.count(a)==1,(a,s.count(a))
    return s.replace(a,b)
def prepare():
    source=(B/'generated/motion-fog-rays/source/fe/loc/Location.as').read_text('utf-8-sig')
    a,z=parser._body(source,'lighting');original=source[a+1:z];body=original
    for old,new in [('var _loc8_:* = undefined;','var _loc8_:int = 0;'),
                    ('var _loc11_:* = undefined;','var _loc11_:Number = NaN;'),
                    ('var _loc12_:* = undefined;','var _loc12_:Number = NaN;'),
                    ('var _loc16_:* = undefined;','var _loc16_:int = 0;'),
                    ('var _loc7_:* = firstX;','var _loc7_:int = firstX;')]:body=once(body,old,new)
    body=once(body,'         var raySpace:Array=this.space;','         var raySpace:Array=this.space;\n         var currentColumn:Array;\n         var currentTile:Tile;')
    body=once(body,'            _loc8_ = firstY;','            currentColumn=raySpace[_loc7_] as Array;\n            _loc8_ = firstY;')
    body=once(body,'               _loc5_ = Number(this.space[_loc7_][_loc8_].visi);','               currentTile=currentColumn[_loc8_] as Tile;\n               _loc5_ = currentTile.visi;')
    body=body.replace('this.space[_loc7_][_loc8_]','currentTile')
    # Same-instance A/B control, default enabled. This leaves the exact previous
    # algorithm available to the isolated probe without modifying world state.
    import re
    previous=re.sub(r'\b_loc(\d+)_',r'old_loc\1_',original)
    for name in ['bounded','control','interiorRay','raySpace','firstX','firstY','lastX','lastY']:
        previous=re.sub(r'\b'+name+r'\b','old_'+name,previous)
    body='''
         var typedControl:Object=World.w.main.getChildByName("ContinuousSceneCarrier");
         if(typedControl!=null && typedControl["nativeAPI"]!=null && typedControl["nativeAPI"]["fogTypedEnabled"]===false) {
'''+previous+'\nreturn;\n}\n'+body
    out=OUT/'source/fe/loc/Location.as';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(source[:a+1]+body+source[z:],'utf-8')
def build():
    expected='81C1BFB552AA8EFBB20CCF15CB404AB5D879F58515B466FF788A079F5F0EC015'
    assert hashlib.sha256((ROOT/'pfe.swf').read_bytes()).hexdigest().upper()==expected
    assert hashlib.sha256((BASE/'pfe.swf').read_bytes()).hexdigest().upper()==expected
    prepare();ff('-importScript',ROOT/'pfe.swf',OUT/'donor.swf',OUT/'source')
    for name,p in [('original',ROOT/'pfe.swf'),('donor',OUT/'donor.swf')]:
        ff('-format','script:pcode','-selectclass','fe.loc.Location','-export','script',OUT/(name+'-pcode'),p)
    shutil.copy2(BASE/'pfe.xml',OUT/'base.xml');methods.GEN=OUT
    path,index,key=methods.plan_method('fe.loc.Location','lighting')
    (OUT/'replace.txt').write_text('\n'.join(['fe.loc.Location',str(path),str(index)])+'\n','utf-8')
    ff('-replace',ROOT/'pfe.swf',OUT/'pfe.swf',OUT/'replace.txt')
    ff('-swf2xml',OUT/'pfe.swf',OUT/'pfe.xml')
    (OUT/'methods.json').write_text(json.dumps([key]),'utf-8')
    audit=OUT/'audit-base';audit.mkdir(exist_ok=True)
    shutil.copy2(ROOT/'pfe.swf',audit/'pfe.swf');shutil.copy2(BASE/'pfe.xml',audit/'host.xml')
    subprocess.run([sys.executable,str(B/'renderer-audit.py'),str(OUT/'pfe.swf'),str(audit),str(OUT/'methods.json')],check=True)
    strict_audit()
    (OUT/'provenance.json').write_text(json.dumps({'version':'fog-typed-20261020','base':expected,'sha256':hashlib.sha256((OUT/'pfe.swf').read_bytes()).hexdigest().upper(),'methods':[key]},indent=2),'utf-8')
def strict_audit():
    from pcode_plan import abc_methods
    spec=importlib.util.spec_from_file_location('audit',B/'renderer-audit.py')
    audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
    before,after=abc_methods(BASE/'pfe.xml'),abc_methods(OUT/'pfe.xml')
    changed=[]
    assert set(before)==set(after),'Method set changed'
    for key,value in before.items():
        other=after[key]
        assert (value is None)==(other is None),key
        if value is not None and value[1].attrib['codeBytes']!=other[1].attrib['codeBytes']:changed.append(key)
    assert changed==['fe.loc.Location::0:1:lighting'],changed
    old,new=audit.classes(BASE/'pfe.xml'),audit.classes(OUT/'pfe.xml')
    assert old==new,'Class layout changed'
    result={'passed':True,'changedMethods':changed,'unchangedMethodsIncludingGrafon':len(before)-1,'allClassLayouts':len(old)}
    (OUT/'strict-audit.json').write_text(json.dumps(result,indent=2),'utf-8');print(json.dumps(result))

if __name__=='__main__':
    if '--audit' in sys.argv:strict_audit()
    elif '--build' in sys.argv:build()
    else:prepare()
