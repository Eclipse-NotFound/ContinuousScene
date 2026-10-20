"""Registered, private-desktop enemy/motion attribution from installed bytes.

Diagnostic outputs stay in build; never installs anything into the game.
"""
from pathlib import Path
import argparse, hashlib, importlib.util, json, shutil, subprocess

B=Path(__file__).resolve().parent
ROOT=B.parents[2]
OUT=B/'generated/enemy-speed'
JAVA=Path('D:/Program Files/Adobe Animate 2024/jre/bin/java.exe')
TOOLS=ROOT/'mods/Sandevistan/build/tools'
HOST_HASH='81C1BFB552AA8EFBB20CCF15CB404AB5D879F58515B466FF788A079F5F0EC015'
TDFC_HASH='03243196C99D6C4F1A2BE081598DBAE9B5D89A414BCD48E1F860232BCFDDE1E5'

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result
motion=module('motion',B/'motion-test.py')
parser=module('asparser',B/'profile-vision.py')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def once(s,a,b):
    assert s.count(a)==1,(a,s.count(a))
    return s.replace(a,b)
def wrap(s,name,key,record):
    a,z=parser._body(s,name)
    body='\nvar csMeasureStart:int=getTimer();try {\n'+s[a+1:z]+'\n} finally {'+record+'("'+key+'",getTimer()-csMeasureStart);}\n'+parser._default_return(s,name,a)+'\n'
    return s[:a+1]+body+s[z:]
def compile_as(src,entry,out):
    out.parent.mkdir(parents=True,exist_ok=True)
    config=out.with_suffix('.xml')
    config.write_text(f'''<flex-config><target-player>32.0</target-player><compiler>
<external-library-path><path-element>{TOOLS}/airsdk/frameworks/libs/air/airglobal.swc</path-element></external-library-path>
<source-path><path-element>{src}</path-element></source-path><debug>false</debug><optimize>true</optimize><theme/>
</compiler></flex-config>''','utf-8')
    subprocess.run([str(JAVA),'-Xmx512m','-Dfile.encoding=UTF-8','-jar',str(TOOLS/'flexsdk/lib/mxmlc.jar'),'+flexlib='+str(TOOLS/'flexsdk/frameworks'),'-load-config='+str(config),'-swf-version=32','-static-link-runtime-shared-libraries=true','-output='+str(out),str(src/entry)],check=True)

def profiles():
    assert digest(ROOT/'pfe.swf')==HOST_HASH,'Installed host changed; review before profiling'
    assert digest(ROOT/'mods/TDFC/release/TDFCMod.swf')==TDFC_HASH,'TDFC changed; review lineage'
    source=OUT/'tdfc';shutil.copytree(B/'generated/tdfc-scene-compat',source,dirs_exist_ok=True)
    # Frozen deployed lineage only. Do not build unpublished TDFC checkout.
    repo=ROOT/'mods/TDFC'
    for original_path in (B/'generated/tdfc-scene-compat').glob('*.as'):
        path=source/original_path.name
        if path.name=='TdfcRuntime.as':continue
        original=subprocess.check_output(['git','-C',str(repo),'show','fb73655:src/'+path.name])
        assert path.read_text('utf-8-sig').replace('\r\n','\n')==original.decode('utf-8-sig').replace('\r\n','\n'),path.name
    prof='''package {
 import flash.display.MovieClip;
 import flash.desktop.NativeApplication;
 public class CsEnemyProfile {
  private static var rows:Object={};
  public static function add(key:String,ms:int):void {var r:Object=rows[key];if(!r)rows[key]=r={calls:0,ms:0,max:0};++r.calls;r.ms+=ms;r.max=Math.max(r.max,ms);}
  public static function init(main:*):void {
   if(NativeApplication.nativeApplication.applicationID.indexOf("pfe-modsettings-continuous-")!=0)throw new Error("Isolated profiler only");
   var c:MovieClip=new MovieClip();c.name="ContinuousSceneTdfcProfile";c.visible=false;
   c.api={reset:function():void{rows={};},snapshot:function():Object{return rows;}};main.addChild(c);
  }
 }
}'''
    (source/'CsEnemyProfile.as').write_text(prof,'utf-8')
    methods={'TdfcRuntime':['onFrame'], 'GameBridge':['snapshot','sense','covers','walkable','threat'],
             'PerceptionModel':['observe','deliver','schedule'],'SquadMind':['frame','context'],
             'ActionExecutor':['assess','apply'],'TacticalMind':['decide']}
    for cls,names in methods.items():
        p=source/(cls+'.as');s=p.read_text('utf-8-sig')
        if 'import flash.utils.getTimer;' not in s:s=once(s,'package {','package {\n import flash.utils.getTimer;')
        if cls=='TdfcRuntime':s=once(s,'   if(host)return;host=main as DisplayObjectContainer;','   if(host)return;host=main as DisplayObjectContainer;CsEnemyProfile.init(main);')
        for name in names:s=wrap(s,name,cls+'.'+name,'CsEnemyProfile.add')
        p.write_text(s,'utf-8')
    compile_as(source,'TDFCMod.as',OUT/'TDFCMod.swf')
    source=OUT/'native/fe/loc/Location.as';source.parent.mkdir(parents=True,exist_ok=True)
    s=(B/'generated/motion-fog-rays/source/fe/loc/Location.as').read_text('utf-8-sig')
    if 'import flash.utils.getTimer;' not in s:s=once(s,'   import flash.geom.ColorTransform;','   import flash.geom.ColorTransform;\n   import flash.utils.getTimer;\n   import flash.utils.getQualifiedClassName;')
    s=once(s,'      public function Location(','''      public var csMotionNative:Object={};
      public function csMotionRecord(key:String,ms:int):void {var r:Object=csMotionNative[key];if(!r)csMotionNative[key]=r={calls:0,ms:0,max:0};++r.calls;r.ms+=ms;r.max=Math.max(r.max,ms);}
      public function Location(''')
    a,z=parser._body(s,'step');body=s[a+1:z]
    body=once(body,'         this.gg.step();','         var csObjStart:int=getTimer();this.gg.step();this.csMotionRecord("player",getTimer()-csObjStart);csObjStart=getTimer();')
    body=once(body,'         if(this.prob)','         this.csMotionRecord("activity",getTimer()-csObjStart);\n         if(this.prob)')
    body=once(body,'obj.step();','csObjStart=getTimer();obj.step();this.csMotionRecord(getQualifiedClassName(obj),getTimer()-csObjStart);')
    s=s[:a+1]+body+s[z:]
    for name in ['step','lighting','lighting2','rebuild','recalcWater','hitTile']:s=wrap(s,name,'Location.'+name,'this.csMotionRecord')
    source.write_text(s,'utf-8')
    s=(B/'generated/motion-direction-rays/source/fe/graph/Grafon.as').read_text('utf-8-sig')
    s=once(s,'      public function Grafon(','''      public var sceneMotionProfile:Object={};
      private function csMotionRecord(key:String,ms:int):void {var r:Object=sceneMotionProfile[key];if(!r)sceneMotionProfile[key]=r={calls:0,ms:0,max:0};++r.calls;r.ms+=ms;r.max=Math.max(r.max,ms);}
      public function Grafon(''')
    # FFDec produces invalid nested-finally scope stacks for sceneApply.
    # Time the public decal caller without changing the existing try/finally.
    a,z=parser._body(s,'decal');body=s[a+1:z]
    body=once(body,'this.sceneApply("decal",[param1,param2,param3,param4,param5,param6,param7]);',
        'var csDecalStart:int=getTimer();this.sceneApply("decal",[param1,param2,param3,param4,param5,param6,param7]);this.csMotionRecord("sceneApply.decal",getTimer()-csDecalStart);')
    s=s[:a+1]+body+s[z:]
    for name in ['sceneTick','sceneNativeEnvironment']:
        s=wrap(s,name,name,'this.csMotionRecord')
    gp=OUT/'native/fe/graph/Grafon.as';gp.parent.mkdir(parents=True,exist_ok=True);gp.write_text(s,'utf-8')
    subprocess.run([str(JAVA),'-Xmx1400m','-jar',str(TOOLS/'ffdec/ffdec-cli.jar'),'-importScript',str(ROOT/'pfe.swf'),str(OUT/'pfe.swf'),str(OUT/'native')],check=True)
    (OUT/'provenance.json').write_text(json.dumps({'diagnosticOnly':True,'host':HOST_HASH,'tdfc':TDFC_HASH,'outputs':{p.name:digest(p) for p in [OUT/'pfe.swf',OUT/'TDFCMod.swf']}},indent=2),'utf-8')

def main():
    p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--profile',action='store_true');p.add_argument('--stage',type=int,default=1);p.add_argument('--wait',type=int,default=300);p.add_argument('--reuse-build',action='store_true');p.add_argument('--no-encounter',action='store_true')
    p.add_argument('--speed',type=float,default=8);p.add_argument('--window-width',type=int,default=0);p.add_argument('--window-height',type=int,default=0);p.add_argument('--reuse-profile',action='store_true')
    p.add_argument('--host',type=Path);p.add_argument('--fog-perf',action='store_true')
    p.add_argument('--draw-control',choices=['world','fog','objects','tilecrop','fogpixels','atlas'])
    p.add_argument('--tdfc',type=Path)
    p.add_argument('--exclude-rconnect',action='store_true')
    p.add_argument('--render-perf',action='store_true')
    p.add_argument('--presentation-check',action='store_true')
    p.add_argument('--benchmark',choices=['normal','scene']);p.add_argument('--fixed-enemies',action='store_true')
    args=p.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    with motion.Registration(owner='ContinuousScene / enemy and high-speed motion / 01a13816-367b-7261-8e11-ca9152565dd9',purpose=args.name,run_dir=motion.RUNTIME,evidence=B.parent/'knowledge/experiments/evidence'/args.name,wait=args.wait) as record:
        if motion.air_pids():raise RuntimeError('Other AIR present; untouched')
        if not args.reuse_build:
            compile_as(B.parent/'src','ContinuousSceneProbeDoc.as',OUT/'ContinuousSceneProbe.swf')
            if args.profile and not args.reuse_profile:profiles()
        motion.prepare(['RConnectMod'] if args.exclude_rconnect else [])
        shutil.copy2(OUT/'ContinuousSceneProbe.swf',motion.RUNTIME/'mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf')
        if args.profile:
            shutil.copy2(OUT/'TDFCMod.swf',motion.RUNTIME/'mods/TDFC/release/TDFCMod.swf')
            shutil.copy2(OUT/'pfe.swf',motion.RUNTIME/'pfe.swf')
        if args.host:
            if args.profile:raise ValueError('Choose either diagnostic profile or candidate host')
            shutil.copy2(args.host,motion.RUNTIME/'pfe.swf')
        if args.tdfc:
            if args.profile:raise ValueError('Choose diagnostic or candidate TDFC')
            shutil.copy2(args.tdfc,motion.RUNTIME/'mods/TDFC/release/TDFCMod.swf')
        options=['--name',args.name,'--short','--no-lighting','--no-wall','--high-qos','--expect-no-signs','--stage',str(args.stage),'--speed',str(args.speed),'--window-width',str(args.window_width),'--window-height',str(args.window_height)]
        if not args.no_encounter:options+=['--encounter']
        if args.profile:options+=['--profile']
        if args.fog_perf:options+=['--fog-perf']
        if args.draw_control:options+=['--draw-control',args.draw_control]
        if args.render_perf:options+=['--render-perf']
        if args.presentation_check:options+=['--presentation-check']
        if args.benchmark:options+=['--benchmark',args.benchmark]
        if args.fixed_enemies:options+=['--fixed-enemies']
        motion.run_owned(motion.parse_args(options),record)

if __name__=='__main__':main()
