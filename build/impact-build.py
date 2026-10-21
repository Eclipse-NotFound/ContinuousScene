"""Historical clip experiment: pixels passed, no stable speedup. Not a release."""
from pathlib import Path
import importlib.util, json, shutil, subprocess, sys
B=Path(__file__).resolve().parent;ROOT=B.parents[2]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
e=load('impact_enemy',B/'enemy-speed.py')
BASE=B/'generated/sats-viewport-20261021-combined'
OUT=B/'generated/impact-clip-20261021'
EXPECTED='7D423BD7B7DD7D2B997E692BD1E22EF520879CD42387C14653C116C15385BCD4'
def main():
    with e.motion.Registration(owner='ContinuousScene / impact build / 01a13816',purpose='Clip impact raster work, candidate only',run_dir=OUT,evidence=OUT/'build.json',wait=300) as record:
        assert e.digest(ROOT/'pfe.swf')==e.digest(BASE/'pfe.swf')==EXPECTED
        s=(BASE/'source/fe/graph/Grafon.as').read_text('utf-8-sig')
        s=e.once(s,'      public var sceneCompactImpacts:Boolean = true;','''      public var sceneCompactImpacts:Boolean = true;
      public const sceneImpactVersion:String = "impact-clip-1";
      public var sceneDecalClipEnabled:Boolean = true;
      private var sceneDecalClip:Rectangle = null;''')
        a,z=e.parser._body(s,'sceneApplyCompactDecal');body=s[a+1:z]
        body=e.once(body,'         var local:Rectangle = area.clone(); local.offset(-ox,-oy);','''         var local:Rectangle = area.clone(); local.offset(-ox,-oy);
         var priorClip:Rectangle = this.sceneDecalClip;''')
        body=e.once(body,'            this.frontBmp = temporary;','''            this.frontBmp = temporary;
            // The copied output is exactly this rectangle. Clip native draw
            // work to it while retaining the original bitmap/raster origin.
            this.sceneDecalClip = this.sceneDecalClipEnabled ? local : null;''')
        body=e.once(body,'            this.frontBmp = previous;','            this.sceneDecalClip = priorClip;\n            this.frontBmp = previous;')
        s=s[:a+1]+body+s[z:]
        s=e.once(s,'this.frontBmp.draw(art,this.m,blend == "normal" ? World.w.loc.cTransform : null,blend,null,true);','this.frontBmp.draw(art,this.m,blend == "normal" ? World.w.loc.cTransform : null,blend,this.sceneDecalClip,true);')
        s=e.once(s,'this.frontBmp.draw(_loc8_,this.m,null,"erase",null,true);','this.frontBmp.draw(_loc8_,this.m,null,"erase",this.sceneDecalClip,true);')
        p=OUT/'source/fe/graph/Grafon.as';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,'utf-8')
        ff=lambda *args:subprocess.run([str(e.JAVA),'-Xmx1400m','-jar',str(e.TOOLS/'ffdec/ffdec-cli.jar'),*map(str,args)],check=True)
        ff('-importScript',ROOT/'pfe.swf',OUT/'pfe.swf',OUT/'source')
        ff('-swf2xml',OUT/'pfe.swf',OUT/'pfe.xml')
        audit=OUT/'audit-base';audit.mkdir(exist_ok=True)
        shutil.copy2(BASE/'pfe.swf',audit/'pfe.swf');shutil.copy2(BASE/'pfe.xml',audit/'host.xml')
        subprocess.run([sys.executable,str(B/'renderer-audit.py'),str(OUT/'pfe.swf'),str(audit)],check=True)
        (OUT/'build.json').write_text(json.dumps({'version':'impact-clip-1','base':EXPECTED,'candidate':e.digest(OUT/'pfe.swf'),'source':e.digest(p),'tested':False},indent=2),'utf-8')
        record.outcome='passed';record.note='Compiled and audited, runtime pending'
if __name__=='__main__':main()
