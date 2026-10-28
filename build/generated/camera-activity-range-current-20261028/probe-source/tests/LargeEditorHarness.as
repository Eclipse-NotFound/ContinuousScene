package {
 import flash.display.*;import flash.events.*;import flash.filesystem.*;import flash.net.*;import flash.system.*;import flash.utils.*;import flash.geom.*;import flash.desktop.NativeApplication;import flash.text.TextField;
 public class LargeEditorHarness extends Sprite {
  private var loader:Loader=new Loader(),timer:Timer=new Timer(400),h:*,v:*,sample:XML,start:int=getTimer(),phase:int=0;
  private var report:Object={checks:[],errors:[],timings:[]},complete:Boolean=false;
  public function LargeEditorHarness(){
   var conf:SharedObject=SharedObject.getLocal("EditorConf");conf.data.language="zh";conf.flush();
   loader.contentLoaderInfo.uncaughtErrorEvents.addEventListener(UncaughtErrorEvent.UNCAUGHT_ERROR,function(e:UncaughtErrorEvent):void{e.preventDefault();finish(String(e.error)+(e.error is Error?e.error.getStackTrace():""));});
   loader.load(new URLRequest("Editor.swf"),new LoaderContext(false,new ApplicationDomain(ApplicationDomain.currentDomain)));addChild(loader);
   timer.addEventListener(TimerEvent.TIMER,tick);timer.start();
  }
  private function read(f:String):XML{var s:FileStream=new FileStream();s.open(File.applicationDirectory.resolvePath(f),FileMode.READ);var x:XML=new XML(s.readUTFBytes(s.bytesAvailable));s.close();return x;}
  private function put(name:String,value:String):void{var s:FileStream=new FileStream();s.open(File.applicationStorageDirectory.resolvePath(name),FileMode.WRITE);s.writeUTFBytes(value);s.close();}
  private function check(n:String,b:Boolean,d:*=null):void{report.checks.push({name:n,ok:b,detail:d});}
  private function capture(n:String):void {
   // A hidden AIR window does not dispatch the normal render validation pass for fl.controls.
   for each(var list:* in [v.objList0,v.objList1,v.objList2,v.roomsList])list.validateNow();
   var b:BitmapData=new BitmapData(1800,950,false,0xffffff);b.draw(loader);var s:FileStream=new FileStream();s.open(File.applicationStorageDirectory.resolvePath(n+".png"),FileMode.WRITE);s.writeBytes(b.encode(b.rect,new PNGEncoderOptions()));s.close();b.dispose();
  }
  private function pointer(type:String,x:Number,y:Number):void {var c:Object=h.LargeContext();var local:Point=v.actObl.globalToLocal(v.localToGlobal(new Point(c.x+(x*20+4-c.panX)*c.zoom,c.y+(y*20+4-c.panY)*c.zoom)));v.actObl.dispatchEvent(new MouseEvent(type,true,false,local.x,local.y));}
  private function tick(e:Event):void{try{
   if(getTimer()-start>240000)throw new Error("editor timeout phase "+phase);
   report.timings.push({phase:phase,ms:getTimer()-start});put("progress.json",JSON.stringify(report.timings));
   if(phase==0){
    if(!loader.content)return;v=loader.content["ved"];h=v["singleSceneHost"];if(!h||!h.ToolsContext().active||!v["largeMapTools"])return;
    check("ordinary-size",h.LargeContext().width==48&&h.LargeContext().height==25);
    report.ui={canvas:[v.setka.x,v.setka.y],button:[v.getChildByName("SingleSceneEditorEntry").x,v.getChildByName("SingleSceneEditorEntry").y]};
    for(var li:int=0;li<v.languagesList.dataProvider.length;li++)if(v.languagesList.dataProvider.getItemAt(li).id=="zh"){v.languagesList.selectedIndex=li;v.languagesList.dispatchEvent(new Event(Event.CHANGE));break;}
    var blank:XML=SingleSceneDocument.blank(96,50);h.LargeOpen(blank);check("new-blank-opens",h.LargeSnapshot().room.a.length()==50&&h.LargeSnapshot().room.obj.(@id=="player").length()==1);
    sample=read("mods/ContinuousScene/maps/factory-rd.xml");SingleSceneDocument.validate(sample);
    h.LargeOpen(sample);phase=1;
   }else if(phase==1){
    var doc:XML=h.LargeSnapshot(),r:XML=doc.room[0];
    check("full-dimensions",r.@sceneWidth==192&&r.@sceneHeight==50);
    check("all-rows",r.a.length()==50);check("all-objects",r.obj.length()==sample.room.obj.length(),[r.obj.length(),sample.room.obj.length()]);
    check("all-backgrounds",r.back.length()==sample.room.back.length());check("environment-regions",r.sceneRegions.toXMLString()==sample.room.sceneRegions.toXMLString());
    var diffs:Array=[];
    for(var y:int=0;y<50;y++)if(String(r.a[y]).replace(/_/g,"")!=String(sample.room.a[y]).replace(/_/g,""))diffs.push(y);
    check("all-terrain-rows-roundtrip",diffs.length==0,diffs);
    h.LargeView(2800,400,0.75);phase=2;
   }else if(phase==2){
    capture("editor-far-region");
    // Use the native material picker and a dragged canvas rectangle beyond the first room.
    var material:DisplayObject;
    for(var mi:int=0;mi<v.panelFront.numChildren;mi++){var candidate:*=v.panelFront.getChildAt(mi);if("id" in candidate&&candidate.id=="N"){material=candidate;break;}}
    check("terrain-tool-exists",material!=null);if(!material)throw new Error("No native N material");material.dispatchEvent(new MouseEvent(MouseEvent.CLICK));
    pointer(MouseEvent.MOUSE_DOWN,171,36);pointer(MouseEvent.MOUSE_MOVE,173,38);pointer(MouseEvent.MOUSE_UP,173,38);
    doc=h.LargeSnapshot();var painted:int=0;for(var py:int=36;py<=38;py++)for(var px:int=171;px<=173;px++)if(String(doc.room.a[py]).split('.')[px].charAt(0)=="N")painted++;
    check("drag-paints-far-terrain",painted==9,painted);
    // Select the real object-list entry, then dispatch its ordinary canvas mouse events.
    var list:*=v.objList0;var found:Boolean=false;
    for(var i:int=0;i<list.dataProvider.length;i++)if(list.dataProvider.getItemAt(i).id=="box"){list.selectedIndex=i;found=true;break;}
    check("box-tool-exists",found);list.dispatchEvent(new Event(Event.CHANGE));
    var c:Object=h.LargeContext(),vx:Number=c.x+(167*20+4-c.panX)*c.zoom,vy:Number=c.y+(40*20+4-c.panY)*c.zoom;
    var local:Point=v.actObl.globalToLocal(v.localToGlobal(new Point(vx,vy)));
    for each(var type:String in [MouseEvent.MOUSE_MOVE,MouseEvent.MOUSE_DOWN,MouseEvent.MOUSE_UP])v.actObl.dispatchEvent(new MouseEvent(type,true,false,local.x,local.y));
    doc=h.LargeSnapshot();r=doc.room[0];var matches:XMLList=r.obj.(@id=="box"&&@x=="167"&&@y=="40");
    check("mouse-places-far-object",matches.length()==1,{count:matches.length(),c:c});
    // Edit that object's attributes through the existing property text field.
    v.SelObj.text='<obj id="box" x="168" y="40" code="authored-far-box"/>';check("property-update",h.updSelObj());
    var saved:XML=v.largeMapTools.document();put("roundtrip.xml",saved.toXMLString());h.LargeOpen(saved);
    doc=h.LargeSnapshot();check("reopen-far-object",doc.room.obj.(@code=="authored-far-box"&&@x=="168").length()==1);
    v.largeMapTools.publish();check("published-active",File.applicationDirectory.resolvePath("mods/ContinuousScene/maps/active.xml").exists);
    v.largeMapTools.publish();check("republish-keeps-backup",File.applicationDirectory.resolvePath("mods/ContinuousScene/maps/backups").getDirectoryListing().length==1);
    h.LargeGrow(200,60);doc=h.LargeSnapshot();check("grow-preserves-objects",doc.room.obj.length()==saved.room.obj.length());check("grow-size",doc.room.a.length()==60&&String(doc.room.a[59]).split(".").length==200);
    var rejected:Boolean=false;try{h.LargeGrow(48,25);}catch(err:Error){rejected=true;}check("shrink-refused",rejected);
    var bad:XML=saved.copy();bad.room.@sceneWidth=513;rejected=false;try{SingleSceneDocument.validate(bad);}catch(err2:Error){rejected=true;}check("invalid-dimensions-refused",rejected);
    bad=saved.copy();bad.room.appendChild(<obj id="player" x="7" y="22"/>);rejected=false;try{SingleSceneDocument.validate(bad);}catch(err3:Error){rejected=true;}check("duplicate-spawn-refused",rejected);
    h.LargeOpen(saved);h.LargeView(0,0,0.25);v.largeMapTools.show();capture("editor-large-map-panel");phase=3;
   }else if(phase==3){
    var panel:DisplayObjectContainer=v.getChildAt(v.numChildren-1) as DisplayObjectContainer;
    for(var bi:int=0;bi<panel.numChildren;bi++){var bt:DisplayObjectContainer=panel.getChildAt(bi) as DisplayObjectContainer;if(bt&&bt.numChildren&&bt.getChildAt(0) is TextField&&TextField(bt.getChildAt(0)).text=="关闭"){bt.dispatchEvent(new MouseEvent(MouseEvent.CLICK));break;}}
    h.LargeView(2400,300,0.75);v.getChildByName("NativePreviewEntry").dispatchEvent(new MouseEvent(MouseEvent.CLICK));phase=4;
   }else if(phase==4){
    var pf:File=File.applicationDirectory.resolvePath("Editor/logs/prerender.json");if(!pf.exists)return;
    var fs:FileStream=new FileStream();fs.open(pf,FileMode.READ);var preview:Object=JSON.parse(fs.readUTFBytes(fs.bytesAvailable));fs.close();
    check("native-local-preview",preview.nativeRenderer&&String(preview.room).indexOf("局部")>=0,preview.room);check("preview-size",preview.renderSize[0]==1920&&preview.renderSize[1]==1000);
    capture("editor-preview");v.stage.dispatchEvent(new KeyboardEvent(KeyboardEvent.KEY_DOWN,true,false,0,27));phase=5;
   }else if(phase==5){
    h.LargeOpen(read("rooms.xml"));check("ordinary-reopened",h.LargeContext().width==48&&h.LargeContext().height==25);
    check("ordinary-no-large-metadata",h.LargeSnapshot().room.@sceneWidth.length()==0);finish();
   }
  }catch(error:Error){finish(error.message+"\n"+error.getStackTrace());}}
  private function finish(error:String=null):void{if(complete)return;complete=true;timer.stop();if(error)report.errors.push(error);report.ok=!error;for each(var c:Object in report.checks)if(!c.ok)report.ok=false;report.elapsed=getTimer()-start;put("editor-result.json",JSON.stringify(report,null,2));NativeApplication.nativeApplication.exit(report.ok?0:1);}
 }
}
