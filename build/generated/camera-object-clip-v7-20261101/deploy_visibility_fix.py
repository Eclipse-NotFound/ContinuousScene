"""Deploy only the independently verified reversion of the visibility override."""
from pathlib import Path
from datetime import datetime
import hashlib,json,os,shutil,uuid
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
before='CA94AF17ED56B273138789661BF725538E5CB7C161CF282AB8C4AA582F88B9B0'
after='9D8662F6CF80E0AD20741EC2A4E7BEAD68446269EBB0ADB641C876DB68698B1D'
candidate=ROOT/'pfe_before_unitvis_20261101-004531.swf'
target=ROOT/'pfe.swf'
proof=ROOT/'mods/ContinuousScene/knowledge/experiments/evidence/camera-object-clip-large-r1-20261101'
data=json.loads((proof/'storage/result.json').read_text('utf-8'))
inputs=json.loads((proof/'review-inputs.json').read_text('utf-8'))
assert data['ok'] and inputs['host']==after
assert data['nativeHiddenActor']=={'className':'UnitSpectre','before':False,'after':False}
assert all(x['ok'] for x in data['assertions'])
assert '<content>pfe.swf</content>' in (ROOT/'application.xml').read_text('utf-8-sig')
assert sha(candidate)==after and sha(target)==before,'Production changed; stop rather than overwrite'
receipt_path=HERE/'visibility-fix-deployment.json'
assert not receipt_path.exists()
token=datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]
backup=ROOT/('pfe_before_visibility_ownership_fix_'+token+'.swf')
assert not backup.exists()
shutil.copy2(target,backup)
assert sha(backup)==before
staged=ROOT/('.pfe-visibility-'+token+'.tmp')
shutil.copy2(candidate,staged)
assert sha(staged)==after and sha(target)==before
os.replace(staged,target)
assert sha(target)==after
receipt={'installedAt':datetime.now().isoformat(),'target':str(target),'before':before,'after':after,'backup':str(backup),'validation':str(proof),'sameValidatedBytes':True,'changedMethod':'fe.graph.Grafon.sceneTick','change':'Remove unconditional sceneUnit.vis.visible override; keep A2 gutter and budget48 changes','readback':sha(target)}
receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(receipt,ensure_ascii=False))
