"""Coarse LAD timings in a frozen, isolated copy; never deploy this output."""
from pathlib import Path
import importlib.util, subprocess, json, hashlib
ROOT=Path(__file__).resolve().parent
LAD=ROOT.parents[1]/'LightAndDarkness'
OUT=ROOT/'generated/lad-profile-source'
spec=importlib.util.spec_from_file_location('body_parser',ROOT/'profile-vision.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
revision='a2d28af'
files=subprocess.check_output(['git','-C',str(LAD),'ls-tree','-r','--name-only',revision,'src'],text=True).splitlines()
manifest=[]
for name in files:
    data=subprocess.check_output(['git','-C',str(LAD),'show',revision+':'+name])
    destination=OUT/Path(name).relative_to('src');destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_bytes(data)
    manifest.append({'path':name,'sha256':hashlib.sha256(data).hexdigest()})
path=OUT/'lad/LadRuntime.as';source=path.read_text(encoding='utf-8-sig')
anchor='        public var enabled:Boolean=true;'
assert source.count(anchor)==1
source=source.replace(anchor,'''        public var csProfile:Object={};
        public function csRecord(name:String,elapsed:int):void {
            var row:Object=csProfile[name];
            if(!row)csProfile[name]=row={calls:0,ms:0,max:0};
            ++row.calls;row.ms+=elapsed;row.max=Math.max(row.max,elapsed);
        }
'''+anchor)
for name in ['syncLamps','render','simulationStep','updateRepair','onFrame']:
    start,end=p._body(source,name)
    body=source[start+1:end]
    source=source[:start+1]+'\nvar csStart:int=getTimer();try {\n'+body+'\n} finally {csRecord("'+name+'",getTimer()-csStart);}\n'+source[end:]
for old,new in [
    ('projectiles.advance();','var csAdvance:int=getTimer();projectiles.advance();csRecord("projectiles.advance",getTimer()-csAdvance);'),
    ('field.render(location,view,lights(view),','var csField:int=getTimer();field.render(location,view,lights(view),'),
    ('atmosphere.settings.darkZones?darkZones:null,atmosphere.settings.darkness);','atmosphere.settings.darkZones?darkZones:null,atmosphere.settings.darkness);csRecord("field.render",getTimer()-csField);'),
    ('LadLampCatalog.visual(lamp);','var csVisual:int=getTimer();LadLampCatalog.visual(lamp);csRecord("lamp.visual",getTimer()-csVisual);')
]:
    assert source.count(old)==1,old
    source=source.replace(old,new)
source=source.replace('v0.3.1 loaded','v0.3.1-profile loaded')
path.write_text(source,encoding='utf-8')
(OUT/'source-manifest.json').write_text(json.dumps({'revision':revision,'isolatedOnly':True,'files':manifest},indent=2),encoding='utf-8')
print(OUT)
