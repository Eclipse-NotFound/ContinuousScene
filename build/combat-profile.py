"""Profile the installed SATS host in isolation; never deploy diagnostics."""
from pathlib import Path
import importlib.util, hashlib, json, subprocess, argparse
B=Path(__file__).resolve().parent
ROOT=B.parents[2]
OUT=B/'generated/combat-profile-20261021'
BASE=B/'generated/sats-viewport-20261021-combined'
EXPECTED='7D423BD7B7DD7D2B997E692BD1E22EF520879CD42387C14653C116C15385BCD4'
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
e=load('combat_enemy',B/'enemy-speed.py')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def main():
    global OUT
    parser=argparse.ArgumentParser();parser.add_argument('--deep',action='store_true');args=parser.parse_args()
    if args.deep:OUT=B/'generated/combat-profile-deep-20261021'
    with e.motion.Registration(owner='ContinuousScene / combat profile / 01a13816',purpose='Diagnostic host build, no deployment',run_dir=OUT,evidence=OUT/'provenance.json',resource='game',wait=300) as record:
        assert sha(ROOT/'pfe.swf')==sha(BASE/'pfe.swf')==EXPECTED
        s=(B/'generated/fog-typed/source/fe/loc/Location.as').read_text('utf-8-sig')
        s=e.once(s,'   import flash.geom.ColorTransform;','   import flash.geom.ColorTransform;\n   import flash.utils.getTimer;\n   import flash.utils.getQualifiedClassName;')
        s=e.once(s,'      public function Location(','''      public var csMotionNative:Object={};
      public function csMotionRecord(key:String,ms:int):void {var r:Object=csMotionNative[key];if(!r)csMotionNative[key]=r={calls:0,ms:0,max:0};++r.calls;r.ms+=ms;r.max=Math.max(r.max,ms);}
      public function Location(''')
        a,z=e.parser._body(s,'step');body=s[a+1:z]
        body=e.once(body,'         this.gg.step();','         var csObjStart:int=getTimer();this.gg.step();this.csMotionRecord("player",getTimer()-csObjStart);csObjStart=getTimer();')
        body=e.once(body,'         if(this.prob)','         this.csMotionRecord("activity",getTimer()-csObjStart);\n         if(this.prob)')
        body=e.once(body,'obj.step();','csObjStart=getTimer();obj.step();this.csMotionRecord(getQualifiedClassName(obj),getTimer()-csObjStart);')
        s=s[:a+1]+body+s[z:]
        for name in ['step','lighting','lighting2','rebuild','recalcWater','hitTile']:s=e.wrap(s,name,'Location.'+name,'this.csMotionRecord')
        p=OUT/'source/fe/loc/Location.as';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,'utf-8')
        s=(BASE/'source/fe/graph/Grafon.as').read_text('utf-8-sig')
        s=e.once(s,'      public function Grafon(','''      public var sceneMotionProfile:Object={};
      private function csMotionRecord(key:String,ms:int):void {var r:Object=sceneMotionProfile[key];if(!r)sceneMotionProfile[key]=r={calls:0,ms:0,max:0};++r.calls;r.ms+=ms;r.max=Math.max(r.max,ms);}
      public function Grafon(''')
        a,z=e.parser._body(s,'decal');body=s[a+1:z]
        body=e.once(body,'this.sceneApply("decal",[param1,param2,param3,param4,param5,param6,param7]);','var csDecalStart:int=getTimer();this.sceneApply("decal",[param1,param2,param3,param4,param5,param6,param7]);this.csMotionRecord("sceneApply.decal",getTimer()-csDecalStart);')
        s=s[:a+1]+body+s[z:]
        for name in ['sceneTick','sceneNativeEnvironment']:s=e.wrap(s,name,name,'this.csMotionRecord')
        if args.deep:
            s=e.once(s,'if(kind == "decal") affected = this.sceneDecalBounds(args,stamp);','if(kind == "decal") {var csBoundsStart:int=getTimer();affected = this.sceneDecalBounds(args,stamp);this.csMotionRecord("decal.bounds",getTimer()-csBoundsStart);}')
            a,z=e.parser._body(s,'decal');body=s[a+1:z]
            body=e.once(body,'         param3 -= this.sceneX;','         var csArtStart:int=getTimer();\n         param3 -= this.sceneX;')
            body=e.once(body,'            this.frontBmp.draw(_loc8_,this.m,null,"erase",null,true);','''            this.csMotionRecord("decal.cutArt",getTimer()-csArtStart);csArtStart=getTimer();
            this.frontBmp.draw(_loc8_,this.m,null,"erase",null,true);
            this.csMotionRecord("decal.cutDraw",getTimer()-csArtStart);csArtStart=getTimer();''')
            body=e.once(body,'               this.sceneDecalPaint(_loc9_,','               this.csMotionRecord("decal.paintArt",getTimer()-csArtStart);\n               this.sceneDecalPaint(_loc9_,')
            s=s[:a+1]+body+s[z:]
            a,z=e.parser._body(s,'sceneDecalPaint');body=s[a+1:z]
            body='\n         var csPaintStart:int=getTimer();'+body
            line='            this.frontBmp.draw(art,this.m,blend == "normal" ? World.w.loc.cTransform : null,blend,null,true);'
            body=e.once(body,line,'            this.csMotionRecord("decal.alphaRead",getTimer()-csPaintStart);csPaintStart=getTimer();\n'+line+'\n            this.csMotionRecord("decal.paintDraw",getTimer()-csPaintStart);csPaintStart=getTimer();')
            body=e.once(body,'            if(alpha != null) alpha.dispose();','            if(alpha != null) alpha.dispose();\n            this.csMotionRecord("decal.alphaWrite",getTimer()-csPaintStart);')
            s=s[:a+1]+body+s[z:]
        p=OUT/'source/fe/graph/Grafon.as';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,'utf-8')
        subprocess.run([str(e.JAVA),'-Xmx1400m','-jar',str(e.TOOLS/'ffdec/ffdec-cli.jar'),'-importScript',str(ROOT/'pfe.swf'),str(OUT/'pfe.swf'),str(OUT/'source')],check=True)
        (OUT/'provenance.json').write_text(json.dumps({'diagnosticOnly':True,'base':EXPECTED,'host':sha(OUT/'pfe.swf'),'sources':{str(p.relative_to(OUT)):sha(p) for p in (OUT/'source').rglob('*.as')}},indent=2),'utf-8')
        record.outcome='passed';record.note='Diagnostic-only compilation, runtime pending'
if __name__=='__main__':main()
