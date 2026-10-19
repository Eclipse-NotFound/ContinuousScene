"""Preserve native moving paths and original-room reward ownership."""
from pathlib import Path
import importlib.util, json, re, sys
from pcode_plan import abc_methods
ROOT=Path(__file__).resolve().parent
GEN=ROOT/'generated/v08-objects'
spec=importlib.util.spec_from_file_location('body_parser',ROOT/'profile-vision.py')
parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)
TARGETS=[('fe.serv.Interact','move'),('fe.loc.Bonus','take'),('fe.unit.Unit','die'),('fe.unit.Unit','setCel'),('fe.unit.UnitPlayer','animate'),('fe.loc.Location','step')]

def prepare():
    source=(ROOT/'cache/v08-objects/scripts/fe/serv/Interact.as').read_text(encoding='utf-8-sig')
    start,_=parser._body(source,'move')
    source=source[:start+1]+'''
         var sceneShift:Object=World.w.grafon.sceneNativeCall("moveOffset",[this]);
         if(sceneShift!=null) {
            this.begX+=sceneShift.x;this.endX+=sceneShift.x;this.endX2+=sceneShift.x;
            this.begY+=sceneShift.y;this.endY+=sceneShift.y;
         }
'''+source[start+1:]
    out=GEN/'source/fe/serv/Interact.as';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(source,encoding='utf-8')
    for cls in ['fe.loc.Bonus','fe.unit.Unit','fe.unit.UnitPlayer','fe.loc.Location']:
        relative=Path(*cls.split('.')).with_suffix('.as')
        source=(ROOT/'cache/v08-objects/scripts'/relative).read_text(encoding='utf-8-sig')
        if cls=='fe.loc.Bonus':
            start,end=parser._body(source,'take')
            body=source[start+1:end]
            for field in ['kolXp','maxXp','unXp','summXp','detecting']:
                body=body.replace('loc.'+field,'sceneReward.'+field)
            old='loc.takeXP(sceneReward.summXp,World.w.gg.X,World.w.gg.Y - 100,true);'
            assert body.count(old)==1
            body=body.replace(old,'if(!World.w.grafon.sceneNativeCall("takeXP",[this,sceneReward.summXp,World.w.gg.X,World.w.gg.Y-100])) '+old)
            source=source[:start+1]+'\n         var sceneReward:Object=World.w.grafon.sceneNativeCall("reward",[this]);\n         if(sceneReward==null)sceneReward=loc;\n'+body+source[end:]
        elif cls=='fe.unit.Unit':
            old='loc.takeXP(this.xp,X,Y,true);';assert source.count(old)==1
            source=source.replace(old,'if(!World.w.grafon.sceneNativeCall("takeXP",[this,this.xp,X,Y])) '+old)
            old='loc.detecting = true;';assert source.count(old)==1
            source=source.replace(old,'if(!World.w.grafon.sceneNativeCall("detecting",[this])) '+old)
        elif cls=='fe.loc.Location':
            start,end=parser._body(source,'step');body=source[start+1:end]
            old='this.gg.step();';assert body.count(old)==1
            body=body.replace(old,old+'\n         var sceneSleeping:Object=World.w.grafon.sceneLarge ? World.w.grafon.sceneNativeCall("activity",[this]) : null;')
            old='obj.step();';assert body.count(old)==1
            body=body.replace(old,'if(sceneSleeping==null || !sceneSleeping[obj]) obj.step();')
            source=source[:start+1]+body+source[end:]
        else:
            old='''                           if(vis.osn.body.currentFrame < 70)
                           {
                              vis.osn.body.gotoAndStop(_loc1_);
                           }'''
            assert source.count(old)==1
            source=source.replace(old,'''                           if(vis.osn.body.currentFrame < 70)
                           {
                              if(!World.w.grafon.sceneLarge || !World.w.grafon.sceneReuseIdleFrame || vis.osn.body.currentFrame!=_loc1_ || vis.osn.body.isPlaying)
                                 vis.osn.body.gotoAndStop(_loc1_);
                              else if(_loc1_==1)
                                 vis.osn.body.sleg1.mark.visible=false;
                           }''')
        out=GEN/'source'/relative;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(source,encoding='utf-8')

def plan():
    args=[];keys=[]
    for cls,method in TARGETS:
        path,index,key=plan_method(cls,method)
        args.extend([cls,str(path),str(index)]);keys.append(key)
    (GEN/'replace-args.txt').write_text('\n'.join(args)+'\n',encoding='utf-8')
    (GEN/'methods.json').write_text(json.dumps(keys),encoding='utf-8')
    print(json.dumps(keys))

def plan_method(cls,method):
    relative=Path(*cls.split('.')).with_suffix('.pcode')
    original=(GEN/'original-pcode/scripts'/relative).read_text(encoding='utf-8-sig')
    donor=(GEN/'donor-pcode/scripts'/relative).read_text(encoding='utf-8-sig')
    start=re.search(r'\bfunction '+method+r'\(',donor).end()
    first=re.search(r'\bmethod\s*\n',donor[start:]).start()+start
    last=donor.index('end ; method',first)+len('end ; method')
    code=donor[first:last]
    assert not re.search(r'^\s*(newfunction|newclass|callstatic)\b',code,re.M)
    old_start=re.search(r'\bfunction '+method+r'\(',original).end()
    old_end=original.index('end ; method',old_start)
    private_members=set(re.findall(r'QName\(PrivateNamespace\([^)]*\),"([^"]+)"\)',code))
    if private_members:
        prior=set(re.findall(r'QName\(PrivateNamespace\([^)]*\),"([^"]+)"\)',original[old_start:old_end]))
        allowed={('fe.unit.UnitPlayer','animate'):{'t_stay','t_walk'},
                 ('fe.loc.Location','step'):{'showSign','getDist','rebuild','recalcWater'}}
        assert private_members==prior==allowed.get((cls,method)),(cls,method,private_members,prior)
    old=list(dict.fromkeys(re.findall(r'PrivateNamespace\([^)]*\)',original[old_start:old_end])))
    new=list(dict.fromkeys(re.findall(r'PrivateNamespace\([^)]*\)',code)))
    if new:
        if not old:
            for name in new:code=code.replace(','+name,'').replace(name+',','')
        else:
            assert len(old)==len(new),(old,new)
            for a,b in zip(new,old):code=code.replace(a,b)
    key=cls+'::0:1:'+method
    index,_=abc_methods(GEN/'base.xml')[key]
    path=GEN/(cls+'-'+method+'.pcode');path.write_text(code+'\n',encoding='utf-8')
    return path,index,key

if __name__=='__main__':
    (plan if sys.argv[-1]=='plan' else prepare)()
