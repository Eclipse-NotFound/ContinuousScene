"""Native display-only tile crop, based on the restored BEFC host. No deployment."""
from pathlib import Path
import argparse, importlib.util, json, shutil, subprocess, sys
B=Path(__file__).resolve().parent;ROOT=B.parents[2]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
e=load('crop_build_enemy',B/'enemy-speed.py')
OUT=B/'generated/native-crop-20261021';BASE=B/'generated/fog-typed'
HOST='BEFCF0509E11FAC9FEF7AFB834708B8B93752A14AE3D5CD72B42AA6D42F9B82A'
SOURCE=B/'generated/motion-direction-rays/source/fe/graph/Grafon.as'
SOURCE_SHA='75157C9397AAC37163AB5CE6A8A872D7451CB723B35E87C6BF48EFE3969D38EB'

def prepare():
    assert e.digest(ROOT/'pfe.swf')==e.digest(BASE/'pfe.swf')==HOST
    assert e.digest(SOURCE)==SOURCE_SHA
    s=SOURCE.read_text('utf-8-sig')
    fragment=B.parent/'src/native/scene-crop-presentation.as.inc'
    s=e.once(s,'      public var sceneCompactImpacts:Boolean = true;',fragment.read_text('utf-8')+'\n      public var sceneCompactImpacts:Boolean = true;')
    s=e.once(s,'         for each(var nativeBuffer:BitmapData in entry.nativeBuffers) nativeBuffer.dispose();',
        '         this.sceneCropRelease(entry);\n         for each(var nativeBuffer:BitmapData in entry.nativeBuffers) nativeBuffer.dispose();')
    s=e.once(s,'         this.sceneChunks = {}; this.sceneResident = 0;',
        '         for each(var crop:BitmapData in this.sceneCropPool) crop.dispose();\n         this.sceneCropPool = [];\n         this.sceneChunks = {}; this.sceneResident = 0;')
    s=e.once(s,'         key += ":" + this.sceneResident;','         key += ":" + this.sceneResident + ":" + this.sceneCropPresentation;')
    s=e.once(s,'         this.sceneCullKey = key;\n         for each(var surface:Object in this.sceneChunks)',
        '''         this.sceneCullKey = key;
         // Release first so entering chunks can reuse the same pixel storage.
         for each(var leaving:Object in this.sceneChunks)
            if(!this.sceneCropPresentation || (view != null && !view.intersects(new Rectangle(leaving.cx * this.sceneSide,leaving.cy * this.sceneSide,this.sceneSide,this.sceneSide))))
               this.sceneCropRelease(leaving);
         for each(var surface:Object in this.sceneChunks)''')
    s=e.once(s,'            for each(var bitmap:Bitmap in surface.bitmaps)\n               if(bitmap.visible != visible) bitmap.visible = visible;',
        '            if(visible && this.sceneCropPresentation) this.sceneCropBind(surface);\n            for each(var bitmap:Bitmap in surface.bitmaps)\n               if(bitmap.visible != visible) bitmap.visible = visible;')
    s=e.once(s,'               ++entry.revision; ++this.sceneLastDirtyCount;',
        '               ++entry.revision; ++this.sceneLastDirtyCount;\n               this.sceneCropSync(entry,kind);')
    a,z=e.parser._body(s,'sceneFinishBatch');body=s[a+1:z]
    body+='\n         for each(var surface:Object in this.sceneChunks) this.sceneCropSync(surface);\n'
    s=s[:a+1]+body+s[z:]
    path=OUT/'source/fe/graph/Grafon.as';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(s,'utf-8')
    meta=dict(base=HOST,baseSource=SOURCE_SHA,source=e.digest(path),fragment=e.digest(fragment),
        changedMethods=['sceneClear','sceneDrop','sceneCullSurfaces','sceneApply','sceneFinishBatch'],
        addedMethods=['sceneCropBind','sceneCropSync','sceneCropRelease'],compiled=False,deployed=False)
    (OUT/'provenance.json').write_text(json.dumps(meta,indent=2),'utf-8');return meta

def build(probe=False):
    with e.motion.Registration(owner='ContinuousScene / native crop build / 01a13816',purpose='Display-only crop candidate and bytecode audit',run_dir=OUT,evidence=OUT/'build.json',wait=300) as record:
        assert not e.motion.air_pids(),'Other AIR present; untouched'
        meta=prepare()
        ff=lambda *args:subprocess.run([str(e.JAVA),'-Xmx1400m','-jar',str(e.TOOLS/'ffdec/ffdec-cli.jar'),*map(str,args)],check=True)
        ff('-importScript',ROOT/'pfe.swf',OUT/'pfe.swf',OUT/'source');ff('-swf2xml',OUT/'pfe.swf',OUT/'pfe.xml')
        audit=OUT/'audit-base';audit.mkdir(exist_ok=True)
        shutil.copy2(BASE/'pfe.swf',audit/'pfe.swf');shutil.copy2(BASE/'pfe.xml',audit/'host.xml')
        subprocess.run([sys.executable,str(B/'renderer-audit.py'),str(OUT/'pfe.swf'),str(audit)],check=True)
        subprocess.run([sys.executable,str(B/'native-crop-audit.py'),'--out',str(OUT/'semantic-audit.json')],check=True)
        if probe:e.compile_as(B.parent/'src','ContinuousSceneProbeDoc.as',OUT/'ContinuousSceneProbe.swf')
        meta.update(candidate=e.digest(OUT/'pfe.swf'),compiled=True)
        (OUT/'build.json').write_text(json.dumps(meta,indent=2),'utf-8')
        record.outcome='passed';record.note='Candidate compiled; rendering/performance tests pending'
        print(json.dumps(meta),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--build',action='store_true');p.add_argument('--probe',action='store_true');a=p.parse_args()
    if a.build:build(a.probe)
    else:print(json.dumps(prepare()))
