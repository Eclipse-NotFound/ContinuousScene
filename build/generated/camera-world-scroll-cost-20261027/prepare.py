from pathlib import Path
import importlib.util
import ast
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('world_scroll_cost_patch',HERE/'probe_patch.py')
patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)
def write(p,s):
    p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():assert p.read_text('utf-8-sig')==s,p
    else:p.write_text(s,'utf-8')
write(patch.HELPER,patch.helper_source())
s=(HERE.parent/'camera-world-scroll-routewarm-20261027/run.py').read_text('utf-8-sig')
for old,new in [
    ('camera-world-scroll-routewarm-1','camera-world-scroll-cost-1'),
    ("trial['pixelsValid']","trial['observationsComplete']"),
    ("assert row['passed'] and len(row['conditions'])==1","assert row['observed'] and len(row['conditions'])==1"),
    ("enumerate(row['conditions'],2)","enumerate(row['conditions'],1)"),
    ("assert c['condition']==mode and c['changed']['maxRGB']<=2 and c['changed']['maxAlpha']==0",
     "assert c['condition']==mode and c['changed']['maxAlpha']==0\n            assert c['accepted'] is (c['changed']['maxRGB']<=2 and c['changed']['maxAlpha']==0)"),
    ("assert trial['testFrameRate']==120", "assert trial['qualityFailureIsMeasuredForAttributionOnly'] and trial['acceptanceLimitRGB']==2\n    failures=[c for row in trial['pixels'] for c in row['conditions'] if not c['accepted']]\n    assert trial['visualAccepted'] is (not failures) and len(trial['qualityFailures'])==len(failures)\n    assert trial['testFrameRate']==120"),
    ('(0,2,2,0)','(0,1,1,0)'),
    ("for name in ('native-moving','scroll-cached-moving')}","for name in ('native-moving','scroll-moving')}"),
    ('originalFrameRate=trial[\'originalFrameRate\'],testFrameRate=trial[\'testFrameRate\'],pixels=trial[\'pixels\'],cleanup=cleanup,',
     'originalFrameRate=trial[\'originalFrameRate\'],testFrameRate=trial[\'testFrameRate\'],pixels=trial[\'pixels\'],cleanup=cleanup,\n        visualAccepted=trial[\'visualAccepted\'],qualityFailures=trial[\'qualityFailures\'],candidateAcceptance=False,'),
    ('480 cached viewport-scrolling frames','480 attribution-only uncached scroll frames; visual rejection retained'),
    ('complete=True,arms=summary[\'arms\'],pairs=summary[\'pairs\']',
     'complete=True,visualAccepted=summary[\'visualAccepted\'],candidateAcceptance=False,arms=summary[\'arms\'],pairs=summary[\'pairs\']'),
]:
    assert old in s,old;s=s.replace(old,new)
ast.parse(s);write(HERE/'run.py',s)
print('Prepared attribution-only timing with separate explicit RGB2 visual acceptance')
