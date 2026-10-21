"""Isolated Unit.blit repeat-copy experiment on BEFC. Never deploys."""
from pathlib import Path
import importlib.util, json, subprocess, sys
B=Path(__file__).resolve().parent;OUT=B/'generated/unit-blit-20261022';BASE=B/'generated/fog-typed'
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
e=load('unit_blit_build_helpers',B/'enemy-speed.py')
HOST='BEFCF0509E11FAC9FEF7AFB834708B8B93752A14AE3D5CD72B42AA6D42F9B82A'

def main():
    OUT.mkdir(exist_ok=True)
    with e.motion.Registration(owner='ContinuousScene / unit bitmap reuse / 01a13816',purpose='One-method isolated candidate build and strict audit',run_dir=OUT,evidence=OUT/'build.json',wait=300) as lease:
        assert not e.motion.air_pids(),'Other AIR present; untouched'
        assert e.digest(e.ROOT/'pfe.swf')==e.digest(BASE/'pfe.swf')==HOST
        def ff(*args):subprocess.run([str(e.JAVA),'-Xmx1400m','-jar',str(e.TOOLS/'ffdec/ffdec-cli.jar'),*map(str,args)],check=True)
        ff('-selectclass','fe.unit.Unit','-export','script',OUT/'original',BASE/'pfe.swf')
        original=OUT/'original/scripts/fe/unit/Unit.as';s=original.read_text('utf-8-sig')
        a,z=e.parser._body(s,'blit');old=s[a+1:z]
        copy='         this.visData.copyPixels(this.blitData,this.blitRect,this.blitPoint);'
        assert old.count(copy)==1 and old.count('this.blitRect.')==2
        body=e.once(old,copy,'''         if(World.w.grafon.sceneLarge)
         {
            var csCarrier:Object = World.w.main.getChildByName("ContinuousSceneCarrier");
            var csAPI:Object = csCarrier == null ? null : csCarrier["nativeAPI"];
            if(csAPI != null && csAPI["unitBlitGate"] != null
               && csAPI["unitBlitGate"](this,this.blitData,this.visData,this.blitRect,this.blitPoint)) return;
         }
'''+copy)
        target=OUT/'source/fe/unit/Unit.as';target.parent.mkdir(parents=True,exist_ok=True)
        assert all(p==target for p in (OUT/'source').rglob('*.as'))
        target.write_text(s[:a+1]+body+s[z:],'utf-8')
        audit=B/'unit-blit-audit.py';assert audit.is_file()
        ff('-importScript',BASE/'pfe.swf',OUT/'compiled.swf',OUT/'source')
        ff('-swf2xml',OUT/'compiled.swf',OUT/'compiled.xml')
        def check(*args):subprocess.run([sys.executable,'-B',str(audit),*map(str,args)],check=True)
        check('--retain','--base',BASE/'pfe.xml','--candidate',OUT/'compiled.xml','--out',OUT/'retained.xml')
        ff('-xml2swf',OUT/'retained.xml',OUT/'serialized.swf')
        ff('-swf2xml',OUT/'serialized.swf',OUT/'serialized.xml')
        check('--splice-abc','--base',BASE/'pfe.xml','--candidate',OUT/'serialized.xml','--base-swf',BASE/'pfe.swf','--candidate-swf',OUT/'serialized.swf','--out',OUT/'pfe.swf')
        ff('-swf2xml',OUT/'pfe.swf',OUT/'pfe.xml')
        check('--base',BASE/'pfe.xml','--candidate',OUT/'pfe.xml','--base-swf',BASE/'pfe.swf','--candidate-swf',OUT/'pfe.swf','--out',OUT/'audit.json')
        meta=dict(base=HOST,originalSource=e.digest(original),source=e.digest(target),candidate=e.digest(OUT/'pfe.swf'),audit=e.digest(OUT/'audit.json'),deployed=False,experimental=True)
        (OUT/'build.json').write_text(json.dumps(meta,indent=2),'utf-8');print(json.dumps(meta),flush=True)
        lease.outcome='passed';lease.note='Isolated gate only; no production callback or deployment'
if __name__=='__main__':main()
