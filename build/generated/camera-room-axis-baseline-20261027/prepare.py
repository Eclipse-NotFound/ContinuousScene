"""Keep current package pins and isolation; compare only native room representations."""
from pathlib import Path
import importlib.util
import ast
HERE=Path(__file__).resolve().parent
def load(name,p):
    spec=importlib.util.spec_from_file_location(name,p)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def save(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():assert path.read_text('utf-8-sig')==text,path
    else:path.write_text(text,'utf-8')
patch=load('room_axis_patch',HERE/'probe_patch.py')
save(patch.HELPER,patch.helper_source())
source=(HERE.parent/'camera-terrain-layers-20261025/run.py').read_text('utf-8-sig')
start=source.index('def summarize(raw):')
end=source.index('\ndef main():',start)
source=source[:start]+patch.base.SUMMARY+'\n'+source[end:]
start=source.index('def options(name):')
end=source.index('\ndef metric(',start)
source=source[:start]+'''def options(name,mode):
    values=reference.options(name)+['--draw-control','tilecrop','--presentation-check']
    for flag,value in [('--benchmark',mode),('--window-width','1296'),('--window-height','759')]:
        index=values.index(flag);values[index+1]=value
    if mode=='normal':
        values=[v for v in values if v!='--expect-no-signs']
        values+=['--native-room-x','2','--native-room-y','4','--native-route-x','480','--native-route-y','119']
    return values

'''+source[end:]
edits=[
    ("VERSION = 'camera-terrain-layers-1'","VERSION = 'camera-room-axis-baseline-1'"),
    ("HERE/'lineage.py'","HERE.parent/'camera-terrain-layers-20261025/lineage.py'"),
    ("HERE/'prepare_runner.py'","HERE/'prepare.py'"),
    ("parser.add_argument('--name',required=True);","parser.add_argument('--mode',required=True,choices=['normal','scene']);parser.add_argument('--name',required=True);"),
    ("options=options(args.name)","options=options(args.name,args.mode)"),
    ("    trial,cleanup=raw['cameraRaster'],raw['cameraRasterCleanup']",
     """    trial,cleanup=raw['cameraRaster'],raw['cameraRasterCleanup']
    assert cfg['benchmark'] in ('normal','scene') and raw['world']['layoutSeed']==20261019
    assert trial['roomAxis']['continuous'] is (cfg['benchmark']=='scene')
    assert trial['stage']['width']==1280 and trial['stage']['height']==720"""),
    ("        rows=rows,arms=arms,pairs=paired,elapsedMs=sum(intervals),zeroNativeRasterWork=True,",
     "        roomAxis=trial['roomAxis'],world=raw['world'],viewport=raw['viewport'],rows=rows,arms=arms,pairs=paired,elapsedMs=sum(intervals),zeroNativeRasterWork=True,"),
    ("camera terrain layers / 01a13816","camera room axes / 01a13816")
    ,('960 moving camera terrain-layer controls; diagnostic only, no deployment','960 native camera axis frames for matched room mode; diagnostic only, no deployment')
]
for old,new in edits:
    n=source.count(old)
    assert n==(3 if old=="HERE/'lineage.py'" else 1),(old,n)
    source=source.replace(old,new)
ast.parse(source);save(HERE/'run.py',source)
print('Prepared matched native-only 1280x720 camera baseline, same frozen input package for both modes.')

