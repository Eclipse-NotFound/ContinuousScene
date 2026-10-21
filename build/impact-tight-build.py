"""Experimental tight impact canvas. Exact-pixel gate required; never deploy."""
from pathlib import Path
import importlib.util, json, shutil, subprocess, sys
B=Path(__file__).resolve().parent;ROOT=B.parents[2]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
e=load('tight_enemy',B/'enemy-speed.py')
BASE=B/'generated/sats-viewport-20261021-combined';OUT=B/'generated/impact-tight-20261021'
EXPECTED='7D423BD7B7DD7D2B997E692BD1E22EF520879CD42387C14653C116C15385BCD4'
def main():
    with e.motion.Registration(owner='ContinuousScene / impact tight build / 01a13816',purpose='Experimental tight canvas; pixel gate required',run_dir=OUT,evidence=OUT/'build.json',wait=300) as record:
        assert e.digest(ROOT/'pfe.swf')==e.digest(BASE/'pfe.swf')==EXPECTED
        s=(BASE/'source/fe/graph/Grafon.as').read_text('utf-8-sig')
        s=e.once(s,'      public var sceneCompactImpacts:Boolean = true;','''      public var sceneCompactImpacts:Boolean = true;
      public const sceneImpactVersion:String = "impact-tight-1";
      public var sceneImpactTightEnabled:Boolean = true;''')
        a,z=e.parser._body(s,'sceneApplyCompactDecal');body=s[a+1:z]
        body=e.once(body,'         var temporary:BitmapData = new BitmapData(int(local.right),int(local.bottom),true,0);','''         var shiftX:int = this.sceneImpactTightEnabled ? int(local.x) : 0;
         var shiftY:int = this.sceneImpactTightEnabled ? int(local.y) : 0;
         var output:Rectangle = local.clone(); output.offset(-shiftX,-shiftY);
         var temporary:BitmapData = new BitmapData(int(local.right)-shiftX,int(local.bottom)-shiftY,true,0);''')
        body=e.once(body,'temporary.copyPixels(previous,local,local.topLeft);','temporary.copyPixels(previous,local,output.topLeft);')
        body=e.once(body,'            this.frontBmp = temporary;','            this.frontBmp = temporary; this.sceneX = ox + shiftX; this.sceneY = oy + shiftY;')
        body=e.once(body,'previous.copyPixels(temporary,local,local.topLeft);','previous.copyPixels(temporary,output,local.topLeft);')
        s=s[:a+1]+body+s[z:]
        p=OUT/'source/fe/graph/Grafon.as';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,'utf-8')
        ff=lambda *args:subprocess.run([str(e.JAVA),'-Xmx1400m','-jar',str(e.TOOLS/'ffdec/ffdec-cli.jar'),*map(str,args)],check=True)
        ff('-importScript',ROOT/'pfe.swf',OUT/'pfe.swf',OUT/'source');ff('-swf2xml',OUT/'pfe.swf',OUT/'pfe.xml')
        audit=OUT/'audit-base';audit.mkdir(exist_ok=True)
        shutil.copy2(BASE/'pfe.swf',audit/'pfe.swf');shutil.copy2(BASE/'pfe.xml',audit/'host.xml')
        subprocess.run([sys.executable,str(B/'renderer-audit.py'),str(OUT/'pfe.swf'),str(audit)],check=True)
        (OUT/'build.json').write_text(json.dumps({'version':'impact-tight-1','base':EXPECTED,'candidate':e.digest(OUT/'pfe.swf'),'source':e.digest(p),'tested':False},indent=2),'utf-8')
        record.outcome='passed';record.note='Experimental build audited; pixel gate pending'
if __name__=='__main__':main()
