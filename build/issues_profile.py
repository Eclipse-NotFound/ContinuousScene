"""Location timings in an isolated host. No production sources are changed."""
from pathlib import Path
import importlib.util
import hashlib
import json

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('profile_parser',ROOT/'profile-vision.py')
parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)

def replace(s,a,b):
    assert s.count(a)==1,(a,s.count(a))
    return s.replace(a,b)

def main():
    path=ROOT/'cache/v08-native/scripts/fe/loc/Location.as'
    source=path.read_text(encoding='utf-8-sig')
    source=replace(source,'   import flash.geom.ColorTransform;','   import flash.geom.ColorTransform;\n   import flash.utils.getTimer;\n   import flash.utils.getQualifiedClassName;')
    anchor='      public function Location('
    source=replace(source,anchor,'''      public var csIssueProfile:Object = {};
      public function csIssueRecord(label:String,ms:int):void {
         var row:Object=this.csIssueProfile[label];
         if(row==null)this.csIssueProfile[label]=row={calls:0,ms:0,max:0};
         ++row.calls;row.ms+=ms;row.max=Math.max(row.max,ms);
      }

'''+anchor)
    start,end=parser._body(source,'step');body=source[start+1:end]
    body=replace(body,'         this.gg.step();','         var csObjectStart:int=getTimer();\n         this.gg.step();\n         this.csIssueRecord("player.step",getTimer()-csObjectStart);')
    body=replace(body,'               obj.step();','               csObjectStart=getTimer();\n               obj.step();\n               this.csIssueRecord(getQualifiedClassName(obj),getTimer()-csObjectStart);')
    source=source[:start+1]+body+source[end:]
    for name in ['step','lighting','lighting2','getDist','rebuild','recalcWater']:
        start,end=parser._body(source,name);body=source[start+1:end]
        tail=parser._default_return(source,name,start)
        source=source[:start+1]+'\n         var csMethodStart:int=getTimer();\n         try {\n'+body+'\n         } finally {this.csIssueRecord("Location.'+name+'",getTimer()-csMethodStart);}\n'+tail+'\n      '+source[end:]
    out=ROOT/'generated/issues-profile/fe/loc/Location.as';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(source,encoding='utf-8')
    (out.parents[2]/'provenance.json').write_text(json.dumps({'isolatedOnly':True,'sourceSHA256':hashlib.sha256(path.read_bytes()).hexdigest()},indent=2),encoding='utf-8')
    print(out)

if __name__=='__main__':main()
