"""Port the reviewed turret method onto the exact visibility-corrected host.

Only the one method is relocated. The previously measured whole donor SWF is
not deployed, and no other classes or method bodies are accepted as changes.
"""
from pathlib import Path
import hashlib, importlib.util, json, re, shutil, subprocess, sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
sys.path[:0]=[str(ROOT/'mods/ModLoader/tools'),str(ROOT/'mods/ContinuousScene/build')]
from test_registry import Registration
from pcode_plan import abc_methods
HOST=ROOT/'pfe_before_unitvis_20261101-004531.swf'
HOST_SHA='9D8662F6CF80E0AD20741EC2A4E7BEAD68446269EBB0ADB641C876DB68698B1D'
OLD=HERE.parent/'camera-turret-animate-20261031'
BASE_XML=HERE.parent/'camera-unit-vis-20261101/base.xml'
JAVA=Path('D:/Program Files/Adobe Animate 2024/jre/bin/java.exe')
FF=ROOT/'mods/Sandevistan/build/tools/ffdec/ffdec-cli.jar'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()
def main():
    assert sha(HOST)==HOST_SHA
    if (HERE/'candidate.swf').exists():raise FileExistsError('candidate exists')
    with Registration(owner='ContinuousScene / camera GC guard / 01a13816',purpose='Port one turret method for camera-tail comparison',resource='game',run_dir=HERE,evidence=HERE,wait=900) as lease:
        methods=abc_methods(BASE_XML)
        prior=abc_methods(OLD/'base.xml')
        key='fe.unit.UnitTurret::0:1:animate'
        assert methods[key][1].attrib['codeBytes']==prior[key][1].attrib['codeBytes']
        patch=OLD/'fe.unit.UnitTurret-animate.pcode'
        assert patch.is_file()
        shutil.copy2(patch,HERE/patch.name)
        shutil.copy2(OLD/'source/fe/unit/UnitTurret.as',HERE/'UnitTurret-donor.as')
        (HERE/'replace.txt').write_text('fe.unit.UnitTurret\n'+str(HERE/patch.name)+'\n'+str(methods[key][0])+'\n','utf-8')
        def ff(label,*args):
            command=[str(JAVA),'-Xmx1024m','-jar',str(FF),*map(str,args)]
            with (HERE/(label+'.log')).open('xb') as log:
                lease.before_launch('Owned FFDec '+label)
                child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                lease.child(child.pid)
                try:code=child.wait(240)
                finally:
                    if child.poll() is None:child.kill();child.wait(15)
                    lease.child_stopped()
                if code:raise RuntimeError('FFDec '+label+' failed')
        ff('replace','-replace',HOST,HERE/'candidate.swf',HERE/'replace.txt')
        ff('audit-export','-swf2xml',HERE/'candidate.swf',HERE/'candidate.xml')
        candidate=abc_methods(HERE/'candidate.xml')
        assert set(methods)==set(candidate)
        changed=[k for k in methods if (None if methods[k] is None else methods[k][1].attrib['codeBytes'])!=(None if candidate[k] is None else candidate[k][1].attrib['codeBytes'])]
        assert changed==[key],changed
        spec=importlib.util.spec_from_file_location('renderer_audit',ROOT/'mods/ContinuousScene/build/renderer-audit.py')
        audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
        assert audit.classes(BASE_XML)==audit.classes(HERE/'candidate.xml')
        receipt={'base':str(HOST),'baseSHA256':HOST_SHA,'baseXmlSHA256':sha(BASE_XML),'donorMethodSHA256':sha(patch),'candidateSHA256':sha(HERE/'candidate.swf'),'changedMethods':changed,'classLayoutUnchanged':True,'deployed':False}
        (HERE/'build.json').write_text(json.dumps(receipt,indent=2),'utf-8')
        lease.outcome='passed';lease.note='Single-method candidate audited; runtime verification pending'
        print(json.dumps(receipt))
if __name__=='__main__':main()
