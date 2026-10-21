"""Reuse audited native art for one impact, preserving every raster origin."""
from pathlib import Path
import importlib.util, json, shutil, subprocess, sys
B=Path(__file__).resolve().parent;ROOT=B.parents[2]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
e=load('native_art_enemy',B/'enemy-speed.py')
BASE=B/'generated/sats-viewport-20261021-combined';OUT=B/'generated/impact-native-20261021'
EXPECTED='7D423BD7B7DD7D2B997E692BD1E22EF520879CD42387C14653C116C15385BCD4'
def main():
    with e.motion.Registration(owner='ContinuousScene / native impact build / 01a13816',purpose='Audited native impact artwork reuse; candidate',run_dir=OUT,evidence=OUT/'build.json',wait=300) as record:
        assert e.digest(ROOT/'pfe.swf')==e.digest(BASE/'pfe.swf')==EXPECTED
        s=(BASE/'source/fe/graph/Grafon.as').read_text('utf-8-sig')
        fragment=B.parent/'src/native/scene-impact-art.as.inc'
        s=e.once(s,'      public var sceneCompactImpacts:Boolean = true;','      public var sceneCompactImpacts:Boolean = true;\n'+fragment.read_text('utf-8'))
        a,z=e.parser._body(s,'sceneApply');body=s[a+1:z]
        body=e.once(body,'         var stamp:Array =','''         var priorArt:Array = this.sceneImpactArt;
         this.sceneImpactArt = kind == "decal" && this.sceneImpactArtEnabled ? [] : null;
         try
         {
         var stamp:Array =''')
        body+='\n         }\n         finally { this.sceneImpactArt = priorArt; }\n'
        s=s[:a+1]+body+s[z:]
        s=e.once(s,'var art:MovieClip = new factory();','var art:MovieClip = this.sceneImpactGetArt(factory,index);')
        s=e.once(s,'art.gotoAndStop(Math.floor(Number(stamp[index]) * art.totalFrames + 1));','this.sceneImpactSelectFrame(art,index,Number(stamp[index]));')
        s=e.once(s,'_loc8_ = new param1();','_loc8_ = this.sceneImpactArt != null ? this.sceneImpactGetArt(param1,0) : new param1();')
        s=e.once(s,'_loc9_ = new param2();','_loc9_ = this.sceneImpactArt != null ? this.sceneImpactGetArt(param2,1) : new param2();')
        for index,local in [(0,'_loc8_'),(1,'_loc9_')]:
            original=f'{local}.gotoAndStop(Math.floor((this.sceneStamp != null ? Number(this.sceneStamp[{index}]) : Math.random()) * {local}.totalFrames + 1));'
            s=e.once(s,original,f'this.sceneImpactSelectFrame({local},{index},this.sceneStamp != null ? Number(this.sceneStamp[{index}]) : Math.random());')
        p=OUT/'source/fe/graph/Grafon.as';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,'utf-8')
        ff=lambda *args:subprocess.run([str(e.JAVA),'-Xmx1400m','-jar',str(e.TOOLS/'ffdec/ffdec-cli.jar'),*map(str,args)],check=True)
        ff('-importScript',ROOT/'pfe.swf',OUT/'pfe.swf',OUT/'source');ff('-swf2xml',OUT/'pfe.swf',OUT/'pfe.xml')
        audit=OUT/'audit-base';audit.mkdir(exist_ok=True)
        shutil.copy2(BASE/'pfe.swf',audit/'pfe.swf');shutil.copy2(BASE/'pfe.xml',audit/'host.xml')
        subprocess.run([sys.executable,str(B/'renderer-audit.py'),str(OUT/'pfe.swf'),str(audit)],check=True)
        (OUT/'build.json').write_text(json.dumps({'version':'impact-art-1','base':EXPECTED,'candidate':e.digest(OUT/'pfe.swf'),'source':e.digest(p),'fragment':e.digest(fragment),'tested':False},indent=2),'utf-8')
        record.outcome='passed';record.note='Native reuse compiled and audited; runtime pending'
if __name__=='__main__':main()
