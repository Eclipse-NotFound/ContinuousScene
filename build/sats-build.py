"""Compile only the candidate Grafon into the current BEFC host; never deploy."""
from pathlib import Path
import hashlib, importlib.util, json, shutil, subprocess, sys
B=Path(__file__).resolve().parent
ROOT=B.parents[2]
OUT=B/'generated/sats-viewport-20261021-combined'
JAVA=Path('D:/Program Files/Adobe Animate 2024/jre/bin/java.exe')
FF=ROOT/'mods/Sandevistan/build/tools/ffdec/ffdec-cli.jar'
BASE=B/'generated/fog-typed'
sys.path.insert(0,str(ROOT/'mods/ModLoader/tools'))
from test_registry import Registration
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def ff(*args):subprocess.run([str(JAVA),'-Xmx1400m','-jar',str(FF),*map(str,args)],check=True)
def main():
    with Registration(owner='ContinuousScene / SATS build / 01a13816',purpose='Compile isolated Grafon and audit preserved host',run_dir=OUT,evidence=OUT/'build.json',resource='offline',wait=0) as record:
        subprocess.run([sys.executable,str(B/'prepare-sats-viewport.py'),'--mode','combined'],check=True)
        meta=json.loads((OUT/'provenance.json').read_text('utf-8'))
        assert sha(ROOT/'pfe.swf')==meta['baseHostSHA256']==sha(BASE/'pfe.swf')
        ff('-importScript',ROOT/'pfe.swf',OUT/'pfe.swf',OUT/'source')
        ff('-swf2xml',OUT/'pfe.swf',OUT/'pfe.xml')
        auditBase=OUT/'audit-base';auditBase.mkdir(exist_ok=True)
        shutil.copy2(BASE/'pfe.swf',auditBase/'pfe.swf');shutil.copy2(BASE/'pfe.xml',auditBase/'host.xml')
        subprocess.run([sys.executable,str(B/'renderer-audit.py'),str(OUT/'pfe.swf'),str(auditBase)],check=True)
        meta.update(status='compiled-awaiting-tests',compiled=True,candidateHostSHA256=sha(OUT/'pfe.swf'),version='sats-viewport-1')
        (OUT/'build.json').write_text(json.dumps(meta,indent=2),'utf-8')
        record.outcome='passed';record.note='Compilation and unchanged non-Grafon classes/methods/constants passed; runtime pending'
        print(json.dumps(meta))
if __name__=='__main__':main()
