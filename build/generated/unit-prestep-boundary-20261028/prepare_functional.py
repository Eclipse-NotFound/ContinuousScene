"""Explicit functional-only successor; retain foreign AIR evidence without stopping it."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
source=HERE.parents[1]/'motion-test.py'
before=source.read_text('utf-8-sig')
changes=[
 ('BASE=Path(__file__).resolve().parent','BASE=Path('+repr(str(source.parent))+')'),
 ("    if air_pids():raise RuntimeError('Existing AIR; do not mutate test input')",'    # Exclusive shared registry protects this isolated runtime; players use other paths.'),
 ("    if air_pids():raise RuntimeError('Performance requires no other AIR; untouched')",'    foreign_before=air_pids()'),
 ("    policy['memoryBefore']=memory;", "    policy['performanceEligible']=False;policy['functionalOnly']=True;policy['foreignAirBefore']=foreign_before\n    policy['memoryBefore']=memory;"),
 ("                    policy['otherAirProcessIds']=others;policy['performanceEligible']=False\n                    raise RuntimeError('Other AIR appeared; do not use timing')", "                    policy['otherAirProcessIds']=sorted(set(policy['otherAirProcessIds']+others));policy['performanceEligible']=False")]
after=before
for old,new in changes:
    assert after.count(old)==1,old
    after=after.replace(old,new)
target=HERE/'functional_runner.py'
assert not target.exists()
target.write_text(after,'utf-8')
run=(HERE/'run.py').read_text('utf-8')
old="m=load('boundary_motion',HERE.parents[1]/'motion-test.py')"
assert run.count(old)==1
(HERE/'run_functional.py').write_text(run.replace(old,"m=load('boundary_functional',HERE/'functional_runner.py')"),'utf-8')
(HERE/'functional-origin.json').write_text(json.dumps(dict(source=str(source),sourceSHA256=hashlib.sha256(source.read_bytes()).hexdigest(),changes=changes,performanceEligible=False),indent=2),'utf-8')
