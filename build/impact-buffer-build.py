"""Historical buffer experiment: no stable gain; pre-try cleanup gap. Not a release."""
from pathlib import Path
import importlib.util, json, shutil, subprocess, sys
B=Path(__file__).resolve().parent;ROOT=B.parents[2]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
e=load('buffer_enemy',B/'enemy-speed.py')
BASE=B/'generated/sats-viewport-20261021-combined'
OUT=B/'generated/impact-buffer-20261021'
EXPECTED='7D423BD7B7DD7D2B997E692BD1E22EF520879CD42387C14653C116C15385BCD4'
def main():
    with e.motion.Registration(owner='ContinuousScene / impact buffer build / 01a13816',purpose='Reuse native-origin impact buffer, candidate only',run_dir=OUT,evidence=OUT/'build.json',wait=300) as record:
        assert e.digest(ROOT/'pfe.swf')==e.digest(BASE/'pfe.swf')==EXPECTED
        s=(BASE/'source/fe/graph/Grafon.as').read_text('utf-8-sig')
        s=e.once(s,'      public var sceneCompactImpacts:Boolean = true;','''      public var sceneCompactImpacts:Boolean = true;
      public const sceneImpactVersion:String = "impact-buffer-1";
      public var sceneImpactBufferEnabled:Boolean = true;
      private var sceneImpactBuffer:BitmapData = null;
      private var sceneImpactBufferBusy:Boolean = false;''')
        a,z=e.parser._body(s,'sceneApplyCompactDecal');body=s[a+1:z]
        body=e.once(body,'         var temporary:BitmapData = new BitmapData(int(local.right),int(local.bottom),true,0);','''         var reuse:Boolean = this.sceneImpactBufferEnabled && !this.sceneImpactBufferBusy;
         var temporary:BitmapData;
         if(reuse)
         {
            // Preserve the raster origin. A fixed native-sized scratch can
            // retain its renderer resources across impacts. Pixels outside
            // local remain transparent, as with the old cropped allocation.
            if(this.sceneImpactBuffer == null || this.sceneImpactBuffer.width != previous.width || this.sceneImpactBuffer.height != previous.height)
            {
               if(this.sceneImpactBuffer != null) this.sceneImpactBuffer.dispose();
               this.sceneImpactBuffer = new BitmapData(previous.width,previous.height,true,0);
            }
            temporary = this.sceneImpactBuffer;
            temporary.fillRect(temporary.rect,0);
            this.sceneImpactBufferBusy = true;
         }
         else temporary = new BitmapData(int(local.right),int(local.bottom),true,0);''')
        body=e.once(body,'this.rectX = width; this.rectY = height; temporary.dispose();','this.rectX = width; this.rectY = height;\n            if(reuse) this.sceneImpactBufferBusy = false; else temporary.dispose();')
        s=s[:a+1]+body+s[z:]
        a,z=e.parser._body(s,'sceneClear')
        s=s[:a+1]+'''
         if(this.sceneImpactBuffer != null) this.sceneImpactBuffer.dispose();
         this.sceneImpactBuffer = null; this.sceneImpactBufferBusy = false;
'''+s[a+1:]
        p=OUT/'source/fe/graph/Grafon.as';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,'utf-8')
        ff=lambda *args:subprocess.run([str(e.JAVA),'-Xmx1400m','-jar',str(e.TOOLS/'ffdec/ffdec-cli.jar'),*map(str,args)],check=True)
        ff('-importScript',ROOT/'pfe.swf',OUT/'pfe.swf',OUT/'source')
        ff('-swf2xml',OUT/'pfe.swf',OUT/'pfe.xml')
        audit=OUT/'audit-base';audit.mkdir(exist_ok=True)
        shutil.copy2(BASE/'pfe.swf',audit/'pfe.swf');shutil.copy2(BASE/'pfe.xml',audit/'host.xml')
        subprocess.run([sys.executable,str(B/'renderer-audit.py'),str(OUT/'pfe.swf'),str(audit)],check=True)
        (OUT/'build.json').write_text(json.dumps({'version':'impact-buffer-1','base':EXPECTED,'candidate':e.digest(OUT/'pfe.swf'),'source':e.digest(p),'tested':False},indent=2),'utf-8')
        record.outcome='passed';record.note='Compiled and audited, runtime pending'
if __name__=='__main__':main()
