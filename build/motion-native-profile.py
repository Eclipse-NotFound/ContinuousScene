"""Diagnostic-only Location profiler built on the frozen motion host."""
from pathlib import Path
import hashlib, importlib.util, json, subprocess

B=Path(__file__).resolve().parent
OUT=B/'generated/motion-native-profile'
HOST=B/'generated/motion-host-incremental/pfe.swf'
JAVA='D:/Program Files/Adobe Animate 2024/jre/bin/java.exe'
FF=B.parents[2]/'mods/Sandevistan/build/tools/ffdec/ffdec-cli.jar'
spec=importlib.util.spec_from_file_location('profile_parser',B/'profile-vision.py')
parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)

def ff(*args):
    subprocess.run([JAVA,'-Xmx1400m','-jar',str(FF),*map(str,args)],check=True)

def once(source,old,new):
    assert source.count(old)==1,(old,source.count(old))
    return source.replace(old,new)

def main():
    assert hashlib.sha256(HOST.read_bytes()).hexdigest().upper()=='4D9CEF1FC713E50666971DEFDAB3A313F7FB46E10A332A32367ED965027DB5FC'
    OUT.mkdir(parents=True,exist_ok=True)
    path=OUT/'original/scripts/fe/loc/Location.as'
    if not path.exists():ff('-selectclass','fe.loc.Location','-export','script',OUT/'original',HOST)
    source=path.read_text('utf-8-sig')
    source=once(source,'   import flash.geom.ColorTransform;',
                '   import flash.geom.ColorTransform;\n   import flash.utils.getTimer;\n   import flash.utils.getQualifiedClassName;')
    source=once(source,'      public function Location(','''      public var csMotionNative:Object = {};
      public function csMotionRecord(key:String,ms:int):void {
         var row:Object=this.csMotionNative[key];
         if(row==null)this.csMotionNative[key]=row={calls:0,ms:0,max:0};
         ++row.calls;row.ms+=ms;row.max=Math.max(row.max,ms);
      }
      public function Location(''')
    a,z=parser._body(source,'step');body=source[a+1:z]
    body=once(body,'         this.gg.step();',
        '         var csObjectStart:int=getTimer();\n         this.gg.step();\n         this.csMotionRecord("player",getTimer()-csObjectStart);\n         csObjectStart=getTimer();')
    # Compiler-generated local variable numbering is deliberately not assumed.
    anchor='         if(this.prob)'
    body=once(body,anchor,'         this.csMotionRecord("activity",getTimer()-csObjectStart);\n'+anchor)
    body=once(body,'obj.step();','csObjectStart=getTimer();\n                  obj.step();\n                  this.csMotionRecord(getQualifiedClassName(obj),getTimer()-csObjectStart);')
    source=source[:a+1]+body+source[z:]
    for name in ['step','lighting','lighting2','rebuild','recalcWater']:
        a,z=parser._body(source,name);body=source[a+1:z]
        source=source[:a+1]+'\nvar csStart:int=getTimer();try {\n'+body+'\n} finally {this.csMotionRecord("Location.'+name+'",getTimer()-csStart);}\n'+parser._default_return(source,name,a)+'\n'+source[z:]
    target=OUT/'source/fe/loc/Location.as';target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(source,'utf-8')
    grafon=(B/'generated/motion-host-incremental/source/fe/graph/Grafon.as').read_text('utf-8-sig')
    grafon=once(grafon,'      public function Grafon(','''      public var sceneMotionProfile:Object={};
      private function csMotionRecord(key:String,ms:int):void {
         var row:Object=this.sceneMotionProfile[key];
         if(row==null)this.sceneMotionProfile[key]=row={calls:0,ms:0,max:0};
         ++row.calls;row.ms+=ms;row.max=Math.max(row.max,ms);
      }
      public function Grafon(''')
    for name in ['sceneTick','sceneNativeEnvironment','sceneUpdateEntityColor','sceneAdvanceWarm','sceneCullSurfaces']:
        a,z=parser._body(grafon,name);body=grafon[a+1:z]
        grafon=grafon[:a+1]+'\nvar csStart:int=getTimer();try {\n'+body+'\n} finally {this.csMotionRecord("'+name+'",getTimer()-csStart);}\n'+parser._default_return(grafon,name,a)+'\n'+grafon[z:]
    target=OUT/'source/fe/graph/Grafon.as';target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(grafon,'utf-8')
    ff('-importScript',HOST,OUT/'pfe.swf',OUT/'source')
    (OUT/'provenance.json').write_text(json.dumps({'diagnosticOnly':True,
        'sourceHost':str(HOST),'sourceSHA256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'outputSHA256':hashlib.sha256((OUT/'pfe.swf').read_bytes()).hexdigest()},indent=2),'utf-8')

if __name__=='__main__':main()
