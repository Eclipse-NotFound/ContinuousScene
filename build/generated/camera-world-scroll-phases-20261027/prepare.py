from pathlib import Path
import importlib.util
import ast
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('world_scroll_phase_patch',HERE/'probe_patch.py')
patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)
def write(p,s):
    p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():assert p.read_text('utf-8-sig')==s,p
    else:p.write_text(s,'utf-8')
write(patch.HELPER,patch.helper_source())
s=(HERE.parent/'camera-world-scroll-cost-20261027/run.py').read_text('utf-8-sig')
for old,new in [
    ('camera-world-scroll-cost-1','camera-world-scroll-phases-1'),
    ("assert trial['testFrameRate']==120", "phase=trial['phaseObservation']\n    assert phase['listenerAdded']==phase['listenerRemoved']==1 and phase['snapshots']==480 and not phase['errors']\n    reposition_count=0\n    assert trial['testFrameRate']==120"),
    ("'windowVisible','terrain'):","'windowVisible','terrain','exitSnapshots','entryStates'):"),
    ('            assert value==expected',
     "            assert value==expected\n            seen=row['exitSnapshots'][j];entry=row['entryStates'][j]\n            assert seen['serial']==i*120+j+1 and seen['terrain']==expected and seen['vx']==vx and seen['vy']==vy\n            assert seen['worldVisible'] is True and seen['windowVisible'] is True\n            lo=row['sampleAtMs'][j-1] if j else row['startAtMs']\n            assert lo<=seen['atMs']<=row['sampleAtMs'][j]\n            native_entry=list(expected);native_entry[2:4]=[vx,vy]\n            assert entry==expected or entry==native_entry\n            reposition_count+=int(entry!=expected)"),
    ("assert intervals==trial['framesMs'] and stamps==trial['sampleAtMs']", "assert reposition_count==phase['nativeEntryRepositions']\n    assert intervals==trial['framesMs'] and stamps==trial['sampleAtMs']"),
    ("visualAccepted=trial['visualAccepted'],qualityFailures=trial['qualityFailures'],candidateAcceptance=False,",
     "visualAccepted=trial['visualAccepted'],qualityFailures=trial['qualityFailures'],candidateAcceptance=False,phaseObservation=phase,"),
]:
    assert old in s,old;s=s.replace(old,new)
ast.parse(s);write(HERE/'run.py',s)
print('Prepared read-only frame-end state proof plus bounded native entry overwrite check')
