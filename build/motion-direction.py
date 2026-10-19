"""Limit prefetch to the swept viewport while moving; retain completed chunks."""
from pathlib import Path
import hashlib, json, shutil, subprocess, sys

B=Path(__file__).resolve().parent
RAYS='--rays' in sys.argv
BASE=B/('generated/motion-fog-rays' if RAYS else 'generated/motion-fog-ceiling')
OUT=B/('generated/motion-direction-rays' if RAYS else 'generated/motion-direction')
SOURCE=B/'generated/motion-host-incremental/source/fe/graph/Grafon.as'
JAVA='D:/Program Files/Adobe Animate 2024/jre/bin/java.exe'
FF=B.parents[2]/'mods/Sandevistan/build/tools/ffdec/ffdec-cli.jar'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def once(text,old,new):
    assert text.count(old)==1,(old,text.count(old))
    return text.replace(old,new)
def ff(*args):subprocess.run([JAVA,'-Xmx1400m','-jar',str(FF),*map(str,args)],check=True)

def main():
    audit=json.loads((BASE/'pfe.audit.json').read_text('utf-8'))
    assert audit['passed'] and audit['finalHostSHA256']==sha(BASE/'pfe.swf')
    assert audit['sourceHostSHA256']=='4D9CEF1FC713E50666971DEFDAB3A313F7FB46E10A332A32367ED965027DB5FC'
    assert audit['patchedNativeMethods']==['fe.loc.Location::0:1:lighting']
    assert sha(SOURCE)=='E4425097AA3176452813402D771B0E125F92447C13256FB71A5D7ECF808AF6CF'
    source=SOURCE.read_text('utf-8')
    source=once(source,'Math.max(6,Math.min(24,Math.ceil(this.sceneWarmMean*demand*1.35+2)))',
        'Math.max(2,Math.min(24,Math.ceil(this.sceneWarmMean*demand*1.35+1)))')
    source=once(source,'''         for(x = Math.max(0,minX-2); x <= Math.min(Math.ceil(this.loc.limX/this.sceneSide)-1,maxX+2); ++x)
            for(y = Math.max(0,minY-2); y <= Math.min(Math.ceil(this.loc.limY/this.sceneSide)-1,maxY+2); ++y)''',
        '''         // While moving, prepare the current and upcoming viewport.
         // At rest fill the surrounding ring gradually at the small idle budget.
         var moving:Boolean=Math.abs(dx)>0.5 || Math.abs(dy)>0.5;
         var warmLeft:int=minX-(!moving || dx< -0.5?2:0);
         var warmRight:int=maxX+(!moving || dx>0.5?2:0);
         var warmTop:int=minY-(!moving || dy< -0.5?2:0);
         var warmBottom:int=maxY+(!moving || dy>0.5?2:0);
         for(x = Math.max(0,warmLeft); x <= Math.min(Math.ceil(this.loc.limX/this.sceneSide)-1,warmRight); ++x)
            for(y = Math.max(0,warmTop); y <= Math.min(Math.ceil(this.loc.limY/this.sceneSide)-1,warmBottom); ++y)''')
    dest=OUT/'source/fe/graph/Grafon.as';dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(source,'utf-8')
    if '--source-only' in sys.argv:return
    ff('-importScript',BASE/'pfe.swf',OUT/'pfe.swf',OUT/'source')
    ff('-swf2xml',OUT/'pfe.swf',OUT/'pfe.xml')
    auditBase=OUT/'audit-base';auditBase.mkdir(exist_ok=True)
    shutil.copy2(BASE/'pfe.swf',auditBase/'pfe.swf');shutil.copy2(BASE/'pfe.xml',auditBase/'host.xml')
    subprocess.run([sys.executable,str(B/'renderer-audit.py'),str(OUT/'pfe.swf'),str(auditBase)],check=True)

if __name__=='__main__':main()
