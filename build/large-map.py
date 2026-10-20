"""Single-scene authoring candidates. Never rebuilds or replaces the game host."""
from pathlib import Path
import argparse, hashlib, json, shutil, subprocess, sys, os, time, uuid,struct,zlib
import xml.etree.ElementTree as ET

MOD=Path(__file__).resolve().parents[1];ROOT=MOD.parents[1]
OUT=MOD/'build/large-map';JAVA=Path('D:/Program Files/Adobe Animate 2024/jre/bin/java.exe')
TOOLS=ROOT/'mods/Sandevistan/build/tools';PY=Path(sys.executable)
sys.path.insert(0,str(ROOT/'mods/ModLoader/tools'))
from test_registry import Registration
from air_test_process import HiddenProcess
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
def save(p,data):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
def call(args,log):
    with log.open('wb') as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True)
def change(s,a,b):
    assert s.count(a)==1,(a[:110],s.count(a));return s.replace(a,b,1)
def method(s,name,new):
    start=s.index('      public function '+name+'(');brace=s.index('{',start);depth=1;i=brace+1
    while depth:
        if s[i]=='{':depth+=1
        elif s[i]=='}':depth-=1
        i+=1
    return s[:brace+1]+'\n'+new+'\n      '+s[i-1:]
def compile(doc,source,output):
    cfg=output.with_suffix('.config.xml')
    cfg.write_text(f'''<flex-config><target-player>32.0</target-player><compiler><library-path><path-element>{TOOLS}/airsdk/frameworks/libs/air/airglobal.swc</path-element></library-path><source-path><path-element>{source}</path-element><path-element>{MOD}/src</path-element></source-path><debug>false</debug><optimize>true</optimize></compiler></flex-config>''',encoding='utf-8')
    call([JAVA,'-Xmx768m','-jar',TOOLS/'flexsdk/lib/mxmlc.jar',f'+flexlib={TOOLS}/flexsdk/frameworks',f'-load-config={cfg}','-theme=','-swf-version=32','-static-link-runtime-shared-libraries=true',f'-output={output}',source/doc],output.with_suffix('.build.log'))
def prepare():
    targets=['Editor.swf','Editor/Enhancements/EditorTools.swf','Editor/Enhancements/NativeScene.swf','pfe.swf','mods/ContinuousScene/release/ContinuousSceneMod.swf']
    base=OUT/'baseline.json'
    if not base.exists():save(base,{p:sha(ROOT/p) for p in targets})
    baseline=json.loads(base.read_text())
    original=OUT/'baseline/Editor.swf'
    if not original.exists():
        assert sha(ROOT/'Editor.swf')==baseline['Editor.swf'],'Original editor baseline required'
        original.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/'Editor.swf',original)
    assert sha(original)==baseline['Editor.swf'],'Frozen editor baseline changed'
    frozen=OUT/'baseline/helper-src'
    if not frozen.exists():
        assert sha(ROOT/'Editor/Enhancements/EditorTools.swf')==baseline['Editor/Enhancements/EditorTools.swf'],'Original helper baseline required'
        shutil.copytree(ROOT/'Editor/Enhancements/src',frozen)
        save(OUT/'baseline/helper-sha256.json',{str(p.relative_to(frozen)):sha(p) for p in frozen.rglob('*.as')})
    assert json.loads((OUT/'baseline/helper-sha256.json').read_text())=={str(p.relative_to(frozen)):sha(p) for p in frozen.rglob('*.as')}
    # Candidate derives from the installed editor, retaining localization and previous bridge.
    ed=(OUT/'baseline/scripts/Editor.as').read_text(encoding='utf-8-sig')
    ed=change(ed,'      public function ToolsContext() : Object',(MOD/'src/editor/LargeEditorBridge.as.inc').read_text(encoding='utf-8')+'\n      public function ToolsContext() : Object')
    ed=change(ed,'"view":this.ed,','"view":this.ed,\n            "viewport":this.LargeContext(),')
    ed=change(ed,'         this.LoadEditorTools();','         this.ed["singleSceneHost"]=this;\n         this.LoadEditorTools();')
    ed=change(ed,'         var s:XML = param1;','''         var s:XML = param1;
         this.largeMeta=s?s.copy():null;
         this.LargeAllocate(s && s.@sceneWidth.length()?int(s.@sceneWidth):48,s && s.@sceneHeight.length()?int(s.@sceneHeight):25);
         this.LargeView(0,0,1);''')
    ed=change(ed,'               this.space[i][j].upd();','               if(this.space[i][j].parent) this.space[i][j].upd();')
    ed=change(ed,'         this.ed.viewVid.gotoAndStop(this.v_vid ? 1 : 2);','         this.ed.viewVid.gotoAndStop(this.v_vid ? 1 : 2);\n         this.LargeRefreshOverview();')
    ed=change(ed,'         this.isDraw = false;\n         this.ed.ramka.visible = false;','         this.isDraw = false;\n         this.ed.ramka.visible = false;\n         this.LargeRefreshOverview();')
    ed=change(ed,'         return r;','''         if(this.largeMeta) {
            for each(var attr:XML in this.largeMeta.attributes()) {
               var key:String=String(attr.name());
               if(key!="name" && key!="x" && key!="y" && key!="z") r.@[key]=attr;
            }
            for each(var extra:XML in this.largeMeta.children())
               if(["a","obj","back","options","doors"].indexOf(String(extra.name()))<0) r.appendChild(extra.copy());
         }
         if(this.largeMeta && this.largeMeta.@sceneWidth.length()) {
            r.@sceneWidth=this.spacex;r.@sceneHeight=this.spacey;r.@x=0;r.@y=0;delete r.@z;delete r.doors;
         }
         return r;''')
    ed=change(ed,'         this.mapBitmap.visible = !this.rndMode;','         this.mapBitmap.visible = !this.rndMode && !(this.largeMeta && this.largeMeta.@sceneWidth.length());')
    ed=change(ed,'         if(this.rndMode)\n         {\n            return;\n         }','         if(this.rndMode || (this.largeMeta && this.largeMeta.@sceneWidth.length()))\n         {\n            return;\n         }')
    for prop in ('begx = this.endx','endx'):
        old=f'         this.{prop} = Math.floor((param1 - this.ed.setka.x) / this.raz);'
        ed=change(ed,old,f'         var point:flash.geom.Point=this.LargePoint(param1,param2);\n         this.{prop} = Math.floor(point.x / this.raz);')
    ed=ed.replace('Math.floor((param2 - this.ed.setka.y) / this.raz)','Math.floor(point.y / this.raz)')
    ed=change(ed,'         this.begx = this.endx = Math.floor(point.x / this.raz);','         this.largeDown=false;\n         this.begx = this.endx = Math.floor(point.x / this.raz);')
    ed=change(ed,'            this.mActive = true;\n            if(param3)','            this.largeDown=true;\n            this.mActive = true;\n            if(param3)')
    ed=change(ed,'      public function mup(param1:Boolean, param2:Boolean = false) : *\n      {','''      public function mup(param1:Boolean, param2:Boolean = false) : *
      {
         if(!this.largeDown) return;
         this.largeDown=false;''')
    ed=change(ed,'         if(this.begx > this.endx)','''         this.begx=Math.max(0,Math.min(this.spacex-1,this.begx));this.endx=Math.max(0,Math.min(this.spacex-1,this.endx));
         this.begy=Math.max(0,Math.min(this.spacey-1,this.begy));this.endy=Math.max(0,Math.min(this.spacey-1,this.endy));
         if(this.begx > this.endx)''')
    ed=ed.replace('this.endx * this.raz + this.ed.setka.x','(this.endx * this.raz-this.largePanX)*this.largeZoom + this.ed.setka.x')
    ed=ed.replace('this.endy * this.raz + this.ed.setka.y','(this.endy * this.raz-this.largePanY)*this.largeZoom + this.ed.setka.y')
    ed=change(ed,'            this.ed.vobj.x =','            this.ed.vobj.scaleX=this.ed.vobj.scaleY=this.largeZoom;\n            this.ed.vobj.x =')
    ed=method(ed,'setRamka','''         var x0:Number=Math.max(0,(Math.min(this.begx,this.endx)*20-this.largePanX)*this.largeZoom);
         var y0:Number=Math.max(0,(Math.min(this.begy,this.endy)*20-this.largePanY)*this.largeZoom);
         var x1:Number=Math.min(960,((Math.max(this.begx,this.endx)+1)*20-this.largePanX)*this.largeZoom);
         var y1:Number=Math.min(500,((Math.max(this.begy,this.endy)+1)*20-this.largePanY)*this.largeZoom);
         this.ed.ramka.x=this.ed.setka.x+x0;this.ed.ramka.y=this.ed.setka.y+y0;
         this.ed.ramka.scaleX=Math.max(0,x1-x0)/100;this.ed.ramka.scaleY=Math.max(0,y1-y0)/100;''')
    dest=OUT/'editor-patch';dest.mkdir(exist_ok=True);(dest/'Editor.as').write_text(ed,encoding='utf-8')
    helper=OUT/'helper-src';shutil.copytree(frozen,helper,dirs_exist_ok=True)
    shutil.copy2(MOD/'src/editor/LargeMapEditor.as',helper/'LargeMapEditor.as')
    s=(helper/'EditorTools.as').read_text(encoding='utf-8-sig')
    s=change(s,'            labels=new MapLabels(host);','            labels=new MapLabels(host);\n            new LargeMapEditor(host);')
    s=change(s,'            timer.start();','            timer.start();\n            view.addEventListener("largeViewportChanged",viewportChanged);')
    s=change(s,'        private function artChanged(event:Event):void', '        private function viewportChanged(event:Event):void { labels.viewportChanged(); }\n        private function artChanged(event:Event):void')
    s=change(s,'            timer.stop();','            timer.stop();\n            view.removeEventListener("largeViewportChanged",viewportChanged);')
    s=change(s,'            button.x=view.butCheck.x','            button.name="NativePreviewEntry";\n            button.x=view.butCheck.x')
    (helper/'EditorTools.as').write_text(s,encoding='utf-8')
    s=(helper/'PreviewPanel.as').read_text(encoding='utf-8-sig')
    s=change(s,'try { snapshot=host.ToolsSnapshot(); }','''try { snapshot=host.ToolsSnapshot();
                if(XML(snapshot.room).@sceneWidth.length()) {
                    var vc:Object=host.LargeContext();
                    snapshot.room=SingleSceneDocument.window(XML(snapshot.room),int((vc.panX+480/vc.zoom)/20)-24,int((vc.panY+250/vc.zoom)/20)-12);
                }
            }''')
    (helper/'PreviewPanel.as').write_text(s,encoding='utf-8')
    s=(helper/'MapLabels.as').read_text(encoding='utf-8-sig')
    s=change(s,'        public function invalidate():void', '        public function viewportChanged():void { layer.visible=false;dirty=true; }\n        public function invalidate():void')
    s=change(s,'var tokens:Array=[context.room,','var tokens:Array=[context.viewport.panX,context.viewport.panY,context.viewport.zoom,context.room,')
    s=change(s,'layer.visible=context.ids && context.active;','layer.visible=context.ids && context.active && context.viewport.zoom>=0.75;')
    # Label layout uses screen coordinates, bounded by the edit viewport at every zoom.
    s=change(s,'            layer.transform.matrix=view.world.transform.matrix.clone();','            layer.transform.matrix=new Matrix(1,0,0,1,view.world.x,view.world.y);')
    s=change(s,'                inv.invert(); m.concat(inv);','                m.tx=0;m.ty=0;')
    s=change(s,'                var tf:TextField=field(String(object.vis.tid.text));','''                var vx:Number=(Number(object.X)*20-context.viewport.panX)*context.viewport.zoom;
                var vy:Number=(Number(object.Y)*20-context.viewport.panY)*context.viewport.zoom;
                if(vx<0||vy<0||vx>955||vy>495) continue;
                var tf:TextField=field(String(object.vis.tid.text));''')
    s=change(s,'x:Number(object.X)*20,y:Number(object.Y)*20,','x:vx,y:vy,')
    (helper/'MapLabels.as').write_text(s,encoding='utf-8')
    save(OUT/'source-manifest.json',{str(p.relative_to(ROOT)):sha(p) for p in [*dest.rglob('*.as'),*helper.rglob('*.as'),*MOD.joinpath('src').glob('*.as')]})
    print('Prepared current editor + viewport + metadata preservation')
def build():
    prepare()
    call([JAVA,'-Xmx1536m','-jar',TOOLS/'ffdec/ffdec-cli.jar','-importScript',OUT/'baseline/Editor.swf',OUT/'Editor.swf',OUT/'editor-patch'],OUT/'editor-build.log')
    compile('EditorTools.as',OUT/'helper-src',OUT/'EditorTools.swf')
    compile('ContinuousSceneDoc.as',MOD/'src',OUT/'ContinuousSceneMod.swf')
    audit_editor()
    print('Compiled editor, helper and ContinuousScene')

def tags(path):
    data=path.read_bytes();body=zlib.decompress(data[8:]) if data[:3]==b'CWS' else data[8:]
    pos=(5+4*(body[0]>>3)+7)//8+4;header=body[:pos];out=[]
    while pos<len(body):
        start=pos;v=struct.unpack_from('<H',body,pos)[0];pos+=2;size=v&63
        if size==63:size=struct.unpack_from('<I',body,pos)[0];pos+=4
        out.append((v>>6,body[pos:pos+size],body[start:pos+size]));pos+=size
    return data[:8],header,out
def audit_editor():
    a,head,old=tags(OUT/'baseline/Editor.swf');_,head2,new=tags(OUT/'Editor.swf')
    assert head==head2 and len(old)==len(new)
    changed=[];output=[]
    for i,(x,y) in enumerate(zip(old,new)):
        assert x[0]==y[0]
        if x[1]!=y[1]:changed.append({'index':i,'type':x[0]})
        output.append(y[2] if x[0]==82 else x[2])
    assert sum(x['type']==82 for x in changed)==1,changed
    body=head+b''.join(output)
    (OUT/'Editor.swf').write_bytes(b'CWS'+a[3:4]+struct.pack('<I',len(body)+8)+zlib.compress(body))
    _,_,final=tags(OUT/'Editor.swf')
    assert all(x[1]==y[1] for x,y in zip(old,final) if x[0]!=82)
    save(OUT/'editor-tag-audit.json',{'changedTagsBeforeAssetPreservation':changed,'nonCodeTagsPreserved':sum(t[0]!=82 for t in old),'sha256':sha(OUT/'Editor.swf')})

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','build']);args=parser.parse_args()
    globals()[args.action]()
