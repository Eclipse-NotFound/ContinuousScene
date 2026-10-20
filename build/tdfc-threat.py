"""Narrow scene compatibility optimization from the frozen deployed TDFC line."""
from pathlib import Path
import hashlib,importlib.util,json,shutil,subprocess
B=Path(__file__).resolve().parent
OUT=B/'generated/tdfc-threat'
def load(name,p):
    s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def prepare():
    original=B/'generated/tdfc-scene-compat'
    OUT.mkdir(parents=True,exist_ok=True)
    for p in original.rglob('*.as'):
        dest=OUT/p.relative_to(original);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
    p=OUT/'GameBridge.as';s=p.read_text('utf-8-sig')
    s=s.replace('import flash.utils.getQualifiedClassName;','import flash.utils.getQualifiedClassName;\n import flash.utils.Dictionary;',1)
    assert s.count('public static function threat(')==1
    parser=load('body_parser',B/'profile-vision.py')
    a,z=parser._body(s,'threat');body=s[a+1:z]
    old=body.replace('cls(o)','getQualifiedClassName(o).split("::").pop()')
    body=body.replace('var c:String=cls(o); var v:Number=num(o,"vel");','var c:String=sceneClass(o); var v:Number=(c=="Bullet" || c=="SmartBullet")?num(o,"vel"):0;')
    s=s[:a+1]+'\n   if(!sceneThreatFast)return sceneThreatReference(s,loc);\n'+body+s[z:]
    marker='  public static function threat('
    additions='''  public static const sceneThreatVersion:String="0.6.4-scene2";
  public static var sceneThreatFast:Boolean=true;
  private static var sceneClasses:Dictionary=new Dictionary(true);
  private static function sceneClass(o:Object):String {
   var cached:String=sceneClasses[o];
   if(cached!=null)return cached;
   cached=cls(o);sceneClasses[o]=cached;return cached;
  }
  public static function sceneThreatReference(s:Object,loc:*):Object {
'''+old+'''\n  }
'''
    s=s.replace(marker,additions+marker,1);p.write_text(s,'utf-8')
    p=OUT/'TdfcRuntime.as';s=p.read_text('utf-8-sig').replace('v0.6.4-scene1 distant-enemy scheduling available','v0.6.4-scene2 distant-enemy scheduling and cached threat classification')
    s=s.replace(' import flash.display.DisplayObjectContainer;',' import flash.display.DisplayObjectContainer;\n import flash.display.MovieClip;\n import flash.desktop.NativeApplication;',1)
    s=s.replace('   if(!host || !host.stage)', '''   if(host && NativeApplication.nativeApplication.applicationID.indexOf("pfe-modsettings-continuous-motion-")==0) {
    var sceneTest:MovieClip=new MovieClip();sceneTest.name="ContinuousSceneTdfcThreat";sceneTest.visible=false;sceneTest.api=GameBridge;host.addChild(sceneTest);
   }
   if(!host || !host.stage)''',1)
    p.write_text(s,'utf-8')
    p=OUT/'Config.as';s=p.read_text('utf-8-sig').replace('VER:String="0.6.4"','VER:String="0.6.4-scene2"');p.write_text(s,'utf-8')
    changed=[]
    for p in original.rglob('*.as'):
        if p.read_bytes()!=(OUT/p.relative_to(original)).read_bytes():changed.append(p.relative_to(original).as_posix())
    assert sorted(changed)==['Config.as','GameBridge.as','TdfcRuntime.as'],changed
    (OUT/'source-origin.json').write_text(json.dumps({'base':'fb73655 plus deployed scene1 bridge','installedSHA256':'03243196C99D6C4F1A2BE081598DBAE9B5D89A414BCD48E1F860232BCFDDE1E5','changedSources':changed},indent=2),'utf-8')
def build():
    enemy=load('enemy',B/'enemy-speed.py')
    assert enemy.digest(enemy.ROOT/'mods/TDFC/release/TDFCMod.swf')==enemy.TDFC_HASH
    prepare();enemy.compile_as(OUT,'TDFCMod.as',OUT/'TDFCMod.swf')
    print(hashlib.sha256((OUT/'TDFCMod.swf').read_bytes()).hexdigest().upper())
if __name__=='__main__':prepare()
