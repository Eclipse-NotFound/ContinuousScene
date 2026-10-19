"""Isolated timing host built from the current v08 candidate sources."""
from pathlib import Path
import importlib.util
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('profile_parser',ROOT/'profile-vision.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
for relative,origin,names in [
 ('fe/loc/Location.as','generated/v08-objects/source/fe/loc/Location.as',['step','lighting','lighting2','getDist','rebuild','recalcWater']),
 ('fe/graph/Grafon.as','generated/v08-renderer-only/fe/graph/Grafon.as',['sceneApply','sceneWarmOne','drawLoc'])]:
    s=(ROOT/origin).read_text(encoding='utf-8-sig')
    if 'import flash.utils.getTimer;' not in s:
        s=s.replace('   import ', '   import flash.utils.getTimer;\n   import flash.utils.getQualifiedClassName;\n   import ',1)
    elif 'import flash.utils.getQualifiedClassName;' not in s:
        s=s.replace('   import ', '   import flash.utils.getQualifiedClassName;\n   import ',1)
    cls=Path(relative).stem
    anchor='      public function '+cls+'('
    assert s.count(anchor)==1
    s=s.replace(anchor,'''      public var csIssueProfile:Object = {};
      public function csIssueRecord(label:String,ms:int):void {
         var row:Object=this.csIssueProfile[label];
         if(row==null)this.csIssueProfile[label]=row={calls:0,ms:0,max:0};
         ++row.calls;row.ms+=ms;row.max=Math.max(row.max,ms);
      }
'''+anchor)
    if cls=='Location':
        start,end=p._body(s,'step');body=s[start+1:end]
        body=body.replace('this.gg.step();','var csObjStart:int=getTimer(); this.gg.step(); this.csIssueRecord("player.step",getTimer()-csObjStart);')
        assert body.count('obj.step();')==1
        body=body.replace('obj.step();','{csObjStart=getTimer(); obj.step(); this.csIssueRecord(getQualifiedClassName(obj),getTimer()-csObjStart);}')
        s=s[:start+1]+body+s[end:]
    if cls=='Grafon':
        s=s.replace('if(kind == "decal") affected = this.sceneDecalBounds(args,stamp);','if(kind == "decal") {var csBoundsStart:int=getTimer(); affected = this.sceneDecalBounds(args,stamp); this.csIssueRecord("bounds",getTimer()-csBoundsStart);}')
        s=s.replace('this.sceneApplyRegionAction(kind,args,affected);','var csRegionStart:int=getTimer(); this.sceneApplyRegionAction(kind,args,affected); this.csIssueRecord("regionAction",getTimer()-csRegionStart);')
    for name in names:
        if ('function '+name+'(') not in s:continue
        start,end=p._body(s,name);body=s[start+1:end]
        tail=p._default_return(s,name,start)
        s=s[:start+1]+'\nvar csProfileStart:int=getTimer(); try {\n'+body+'\n} finally {this.csIssueRecord("'+cls+'.'+name+'",getTimer()-csProfileStart);}\n'+tail+'\n'+s[end:]
    dest=ROOT/'generated/issues-combat-profile'/relative;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(s,encoding='utf-8')
print('Prepared isolated current-candidate combat timing sources')
import subprocess,sys
subprocess.run([sys.executable,str(ROOT/'issues_player_profile.py')],check=True)
unit=(ROOT/'generated/issues-player-profile/fe/unit/Unit.as').read_text(encoding='utf-8')
unit=unit.replace('   import flash.utils.getTimer;','   import flash.utils.getTimer;\n   import flash.utils.getQualifiedClassName;',1)
anchor='this.childObjs[i].step();'
assert unit.count(anchor)==1
unit=unit.replace(anchor,'var csChildStart:int=getTimer(); '+anchor+' if(this.player)csPlayerRecord("child."+getQualifiedClassName(this.childObjs[i]),getTimer()-csChildStart);')
dest=ROOT/'generated/issues-combat-profile/fe/unit/Unit.as';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(unit,encoding='utf-8')
