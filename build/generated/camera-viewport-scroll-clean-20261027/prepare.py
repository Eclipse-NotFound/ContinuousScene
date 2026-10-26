"""Only eliminate no-op renderer writes; preserve every native eligibility check."""
from pathlib import Path
import ast
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'camera-viewport-scroll-pixels-20261026'
def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():assert path.read_bytes()==data,path
    else:path.write_bytes(data)
source=(OLD/'SceneTilePresentation.as').read_text('utf-8-sig')
edits=[
    ('                data.lock();','''                var changedPixels:Boolean=full || dx!=0 || dy!=0 || dirty.length>0;
                if(changedPixels)data.lock();'''),
    ('                } finally {data.unlock();}','                } finally {if(changedPixels)data.unlock();}'),
    ('                group.node.x=nextX;group.node.y=nextY;group.node.visible=true;',
     '''                if(group.node.x!=nextX)group.node.x=nextX;
                if(group.node.y!=nextY)group.node.y=nextY;
                if(!group.node.visible)group.node.visible=true;'''),
    ('            for(var hidden:Object in records)Bitmap(hidden).alpha=0;',
     '            for(var hidden:Object in records)if(Bitmap(hidden).alpha!=0)Bitmap(hidden).alpha=0;'),
    ('            for each(var group:Object in groups)group.node.visible=false;',
     '            for each(var group:Object in groups)if(group.node.visible)group.node.visible=false;'),
    ('            for(var key:Object in records)Bitmap(key).alpha=records[key].alpha;',
     '            for(var key:Object in records)if(Bitmap(key).alpha!=records[key].alpha)Bitmap(key).alpha=records[key].alpha;')
]
for before,after in edits:
    assert source.count(before)==1,(before,source.count(before));source=source.replace(before,after,1)
# Prove all other source bytes remain unchanged after reversible substitutions.
reversed_source=source
for before,after in reversed(edits):
    assert reversed_source.count(after)==1
    reversed_source=reversed_source.replace(after,before,1)
assert reversed_source==(OLD/'SceneTilePresentation.as').read_text('utf-8-sig')
save(HERE/'SceneTilePresentation.as',source.encode('utf-8'))
patch=(OLD/'probe_patch.py').read_text('utf-8-sig')
patch=patch.replace("PATCH_SOURCE=HERE.parent/'camera-viewport-scroll-20261026/probe_patch.py'",
                    "PATCH_SOURCE=HERE.parent/'camera-viewport-scroll-pixels-20261026/probe_patch.py'",1)
begin=patch.index('    edits=[')
end=patch.index('    for old,new in edits:',begin)
patch=patch[:begin]+'''    edits=[('version:"camera-viewport-scroll-pixels-1"','version:"camera-viewport-scroll-clean-1"')]
'''+patch[end:]
patch=patch.replace('    assert PRESENTER.read_bytes()==base.PRESENTER.read_bytes()\n','',1)
patch=patch.replace('Retain the failed renderer exactly; save the pixel triplet for diagnosis.',
                    'No-op update removal, with prior eligibility checks and retained pixel triplets.')
ast.parse(patch);save(HERE/'probe_patch.py',patch.encode('utf-8'))
import importlib.util
spec=importlib.util.spec_from_file_location('viewport_clean_patch',HERE/'probe_patch.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
save(module.HELPER,module.helper_source().encode('utf-8'))
runner=(OLD/'run.py').read_text('utf-8-sig').replace('camera-viewport-scroll-pixels-1','camera-viewport-scroll-clean-1')
ast.parse(runner);save(HERE/'run.py',runner.encode('utf-8'))
print('Prepared six reversible no-op changes; all eligibility and pixel thresholds retained.')

