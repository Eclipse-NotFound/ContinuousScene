"""Attribute installed RV costs in an isolated application, retaining its source."""
from pathlib import Path
import importlib.util, hashlib, json, shutil
ROOT=Path(__file__).resolve().parent
MOD=ROOT.parents[1]/'RealisticVision'
BASE=MOD/'build/wall-performance-output/candidate/src'
OUT=ROOT/'generated/issues-rv-profile'
spec=importlib.util.spec_from_file_location('parser',ROOT/'profile-vision.py')
parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)
s=(BASE/'RealisticVisionMod.as').read_text(encoding='utf-8-sig')
assert hashlib.sha256((BASE/'RealisticVisionMod.as').read_bytes()).hexdigest()=='62085fefc016119b3eeb7c5520e2a8d8d0f6215b92fdd7efbaa8c5a922c5ef81'
shutil.copytree(BASE,OUT,dirs_exist_ok=True)
s=s.replace('   import flash.display.Bitmap;', '   import flash.display.Bitmap;\n   import flash.display.MovieClip;',1)
names=['onFrameInner','prepareOcclusion','computeFov','applyVision','fillFogCache','updateWallSurface','hideEnemies','applyMask','scanArms','refreshWallField']
for name in names:
    start,end=parser._body(s,name);body=s[start+1:end]
    s=s[:start+1]+'\nvar csBegin:int=getTimer();try{\n'+body+'\n}finally{csRecord("'+name+'",getTimer()-csBegin);}\n'+parser._default_return(s,name,start)+'\n      '+s[end:]
pos=s.index('{',s.index('public class RealisticVisionMod'))+1
s=s[:pos]+'''
      private var csProfile:Object={};
      private function csRecord(name:String,ms:int):void {
         var row:Object=csProfile[name];if(!row)csProfile[name]=row={calls:0,ms:0,max:0};
         ++row.calls;row.ms+=ms;row.max=Math.max(row.max,ms);
      }
      private function csPublish(main:*):void {
         var carrier:MovieClip=new MovieClip();carrier.name="CSIssuesVision";
         var self:RealisticVisionMod=this;
         carrier["snapshot"]=function():Object{self.csProfile.wall=self.wallSurface.csProfile;return self.csProfile;};
         carrier["reset"]=function():void{self.csProfile={};self.wallSurface.csProfile={};};
         main.addChild(carrier);
      }
'''+s[pos:]
start,_=parser._body(s,'startup');s=s[:start+1]+'\nthis.csPublish(main);\n'+s[start+1:]
(OUT/'RealisticVisionMod.as').write_text(s,encoding='utf-8')
w=(BASE/'RVWallSurface.as').read_text(encoding='utf-8-sig')
w=w.replace('   import flash.display.Bitmap;', '   import flash.utils.getTimer;\n   import flash.display.Bitmap;',1)
pos=w.index('{',w.index('public class RVWallSurface'))+1
w=w[:pos]+'''\n      public var csProfile:Object={};
      private function csRecord(name:String,ms:int):void {
         var row:Object=csProfile[name];if(!row)csProfile[name]=row={calls:0,ms:0,max:0};
         ++row.calls;row.ms+=ms;row.max=Math.max(row.max,ms);
      }\n'''+w[pos:]
for name in ['update','updateContour','buildContourClip','rebuildFaces','rebuildSamples','rebuildSupport','foregroundSources','copyForeground']:
    start,end=parser._body(w,name);body=w[start+1:end]
    w=w[:start+1]+'\nvar csBegin:int=getTimer();try{\n'+body+'\n}finally{csRecord("'+name+'",getTimer()-csBegin);}\n'+parser._default_return(w,name,start)+'\n      '+w[end:]
(OUT/'RVWallSurface.as').write_text(w,encoding='utf-8')
(OUT/'profile.json').write_text(json.dumps({'isolatedOnly':True,'methods':names}),encoding='utf-8')
print(OUT)
