"""Experimental reuse of artwork within one impact, not across frames."""
from pathlib import Path
import importlib.util, json, shutil, subprocess, sys
B=Path(__file__).resolve().parent;ROOT=B.parents[2]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
e=load('art_enemy',B/'enemy-speed.py')
BASE=B/'generated/sats-viewport-20261021-combined';OUT=B/'generated/impact-art-20261021'
EXPECTED='7D423BD7B7DD7D2B997E692BD1E22EF520879CD42387C14653C116C15385BCD4'
def main():
    with e.motion.Registration(owner='ContinuousScene / impact art build / 01a13816',purpose='Experimental same-impact artwork reuse; no deployment',run_dir=OUT,evidence=OUT/'build.json',wait=300) as record:
        assert e.digest(ROOT/'pfe.swf')==e.digest(BASE/'pfe.swf')==EXPECTED
        s=(BASE/'source/fe/graph/Grafon.as').read_text('utf-8-sig')
        s=e.once(s,'      public var sceneCompactImpacts:Boolean = true;','''      public var sceneCompactImpacts:Boolean = true;
      public const sceneImpactVersion:String = "impact-art-experiment-1";
      public var sceneImpactArtEnabled:Boolean = true;
      private var sceneImpactArt:Array = null;

      private function sceneImpactGetArt(factory:Class, index:int) : MovieClip
      {
         if(!this.sceneImpactArtEnabled || this.sceneImpactArt == null) return new factory();
         var art:MovieClip = this.sceneImpactArt[index] as MovieClip;
         if(art == null) { art = new factory(); this.sceneImpactArt[index] = art; }
         art.scaleX = art.scaleY = 1; art.rotation = 0;
         return art;
      }''')
        a,z=e.parser._body(s,'sceneApply');body=s[a+1:z]
        body=e.once(body,'         var stamp:Array =','''         var priorArt:Array = this.sceneImpactArt;
         this.sceneImpactArt = kind == "decal" ? [] : null;
         try
         {
         var stamp:Array =''')
        body+='\n         }\n         finally { this.sceneImpactArt = priorArt; }\n'
        s=s[:a+1]+body+s[z:]
        # The same factory and fixed frame are used in every region/chunk.
        # Unknown constructor/frame-script semantics must be excluded before release.
        s=e.once(s,'var art:MovieClip = new factory();','var art:MovieClip = this.sceneImpactGetArt(factory,index);')
        s=e.once(s,'_loc8_ = new param1();','_loc8_ = this.sceneImpactGetArt(param1,0);')
        s=e.once(s,'_loc9_ = new param2();','_loc9_ = this.sceneImpactGetArt(param2,1);')
        p=OUT/'source/fe/graph/Grafon.as';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,'utf-8')
        ff=lambda *args:subprocess.run([str(e.JAVA),'-Xmx1400m','-jar',str(e.TOOLS/'ffdec/ffdec-cli.jar'),*map(str,args)],check=True)
        ff('-importScript',ROOT/'pfe.swf',OUT/'pfe.swf',OUT/'source');ff('-swf2xml',OUT/'pfe.swf',OUT/'pfe.xml')
        audit=OUT/'audit-base';audit.mkdir(exist_ok=True)
        shutil.copy2(BASE/'pfe.swf',audit/'pfe.swf');shutil.copy2(BASE/'pfe.xml',audit/'host.xml')
        subprocess.run([sys.executable,str(B/'renderer-audit.py'),str(OUT/'pfe.swf'),str(audit)],check=True)
        (OUT/'build.json').write_text(json.dumps({'version':'impact-art-experiment-1','experimentalOnly':True,'base':EXPECTED,'candidate':e.digest(OUT/'pfe.swf'),'source':e.digest(p),'tested':False},indent=2),'utf-8')
        record.outcome='passed';record.note='Experimental build audited; pixels and performance pending'
if __name__=='__main__':main()
