package {
    import flash.display.*;
    import flash.events.*;
    import flash.filesystem.*;
    import flash.geom.*;
    import flash.text.*;
    import flash.utils.*;
    import flash.ui.Keyboard;
    import flash.net.FileFilter;

    public class LargeMapEditor {
        private var host:Object,view:MovieClip,panel:Sprite,status:TextField,wInput:TextField,hInput:TextField;
        private var openFile:File,saveFile:File,pending:XML;
        private var spaceHeld:Boolean=false,drag:Point,origin:Point;
        public function LargeMapEditor(h:Object) {
            host=h;view=h.ToolsContext().view;
            // Independent entry placed after the existing preview/review entries.
            var b:ToolButton=new ToolButton("大地图",100,30);b.name="SingleSceneEditorEntry";
            b.x=view.butCheck.x+view.butCheck.width+20+126+136;b.y=view.butCheck.y-8;
            view.addChild(b);b.addEventListener(MouseEvent.CLICK,function(e:Event):void {show();});
            view.stage.addEventListener(KeyboardEvent.KEY_DOWN,keyDown,false,1000);
            view.stage.addEventListener(KeyboardEvent.KEY_UP,keyUp,false,1000);
            view.stage.addEventListener(Event.DEACTIVATE,function(e:Event):void {spaceHeld=false;drag=null;});
            view.actObl.addEventListener(MouseEvent.MOUSE_DOWN,down,false,1000);
            view.actObl.addEventListener(MouseEvent.MOUSE_MOVE,move,false,1000);
            view.actObl.addEventListener(MouseEvent.MOUSE_UP,up,false,1000);
            view.stage.addEventListener(MouseEvent.MOUSE_UP,endDrag);
            view.actObl.addEventListener(MouseEvent.MOUSE_WHEEL,wheel,false,1000);
            view["largeMapTools"]=this;
        }
        private function text(value:String,x:Number,y:Number,width:Number,size:int=16):TextField {
            var t:TextField=new TextField();t.defaultTextFormat=new TextFormat("Microsoft YaHei UI",size,0xe5efeb);
            t.text=value;t.x=x;t.y=y;t.width=width;t.height=32;t.selectable=false;panel.addChild(t);return t;
        }
        private function button(value:String,x:Number,y:Number,width:Number,action:Function):void {
            var b:ToolButton=new ToolButton(value,width,32);b.x=x;b.y=y;panel.addChild(b);
            b.addEventListener(MouseEvent.CLICK,function(e:Event):void {try {action();}catch(error:Error) {status.text=error.message;}});
        }
        public function show():void {
            if(!panel) {
                panel=new Sprite();panel.x=300;panel.y=160;panel.graphics.beginFill(0x172a26,0.99);panel.graphics.lineStyle(2,0x75ad98);panel.graphics.drawRect(0,0,1050,510);panel.graphics.endFill();
                panel.addEventListener(MouseEvent.MOUSE_DOWN,function(e:MouseEvent):void {e.stopPropagation();});
                text("单一大地图",28,20,600,24);
                text("空格拖动画布 · 滚轮缩放 · 原有地形、物体与属性工具继续使用",28,65,1000);
                text("宽（格）",28,117,100);wInput=text("192",138,117,95);wInput.type=TextFieldType.INPUT;wInput.selectable=true;wInput.border=true;wInput.restrict="0-9";
                text("高（格）",260,117,100);hInput=text("75",370,117,95);hInput.type=TextFieldType.INPUT;hInput.selectable=true;hInput.border=true;hInput.restrict="0-9";
                button("扩展当前地图",500,115,160,function():void {host.LargeGrow(int(wInput.text),int(hInput.text));status.text="已扩展；原有内容保留。";});
                button("新建大地图…",680,115,160,function():void {confirmOpen(SingleSceneDocument.blank(int(wInput.text),int(hInput.text)));});
                button("载入 XML…",28,185,160,chooseOpen);
                button("研发部示例…",206,185,170,function():void {confirmOpen(read(File.applicationDirectory.resolvePath("mods/ContinuousScene/maps/factory-rd.xml")));});
                button("另存 XML…",394,185,160,chooseSave);
                button("应用到游戏",572,185,170,publish);
                button("适应全图",760,185,160,function():void {var c:Object=host.LargeContext();host.LargeView(0,0,Math.min(960/(c.width*20),500/(c.height*20)));close();});
                text("应用后：游戏信息页 →「大地图 · 编辑地图」。重新进入时读取最新文件。",28,251,995);
                text("预渲染显示编辑视野中心的 48×25 格；完整场景请在游戏中检验。",28,287,995);
                status=text("",28,337,990);status.height=90;status.wordWrap=true;status.multiline=true;
                button("关闭",880,450,130,close);
            }
            view.addChild(panel);var c:Object=host.LargeContext();wInput.text=String(c.width);hInput.text=String(c.height);
            status.text="支持 48–512 × 25–256 格。应用到游戏需要一个 player 出生点。新建或载入前请先保存当前作品。";
            panel.visible=true;
        }
        private function close():void {pending=null;if(panel){var c:DisplayObject=panel.getChildByName("confirmOpen");if(c)panel.removeChild(c);if(panel.parent)panel.parent.removeChild(panel);}}
        private function read(f:File):XML {if(f.size>16*1024*1024)throw new Error("地图文件超过 16 MB。");var s:FileStream=new FileStream();var result:XML;try {s.open(f,FileMode.READ);result=new XML(s.readUTFBytes(s.bytesAvailable));}finally{s.close();}return result;}
        private function confirmOpen(doc:XML):void {
            var room:XML=SingleSceneDocument.validate(doc,false);
            if(doc.name()=="room") {doc=<all><land serial="1"/></all>;doc.appendChild(room.copy());}
            pending=doc;
            status.text="载入「"+doc.room.@name+"」将替换当前编辑内容。请先另存；再次点击下方确认后继续。";
            var old:DisplayObject=panel.getChildByName("confirmOpen");if(old)panel.removeChild(old);
            var b:ToolButton=new ToolButton("确认替换当前编辑内容",260,32);b.name="confirmOpen";b.x=28;b.y=450;panel.addChild(b);
            b.addEventListener(MouseEvent.CLICK,function(e:Event):void {host.LargeOpen(pending);close();});
        }
        private function chooseOpen():void {
            openFile=File.applicationDirectory.resolvePath("Editor/Work");
            openFile.addEventListener(Event.SELECT,function(e:Event):void {try {confirmOpen(read(openFile));}catch(error:Error){status.text=error.message;}});
            openFile.browseForOpen("载入单一大地图 XML",[new FileFilter("大地图 XML","*.xml")]);
        }
        public function document():XML {var s:XML=host.LargeSnapshot();return SingleSceneDocument.pack(s.room[0],s.land[0]);}
        private function chooseSave():void {
            var doc:XML=document();saveFile=File.applicationDirectory.resolvePath("Editor/Work/large-map.xml");
            saveFile.addEventListener(Event.SELECT,function(e:Event):void {try {write(saveFile,doc);status.text="已保存："+saveFile.nativePath;}catch(error:Error){status.text=error.message;}});
            saveFile.browseForSave("另存完整大地图 XML");
        }
        private function write(f:File,doc:XML):void {
            f=new File(f.nativePath);f.parent.createDirectory();var s:FileStream=new FileStream();
            try {s.open(f,FileMode.WRITE);s.writeUTFBytes('<?xml version="1.0" encoding="utf-8"?>\n'+doc.toXMLString());}finally{s.close();}
        }
        public function publish():void {
            var doc:XML=document();var f:File=new File(File.applicationDirectory.resolvePath("mods/ContinuousScene/maps/active.xml").nativePath);
            if(f.exists) {var backup:File=new File(f.parent.resolvePath("backups").nativePath);backup.createDirectory();f.copyTo(backup.resolvePath("active-"+new Date().time+".xml"),false);}
            var temp:File=new File(f.parent.resolvePath("active-writing.tmp").nativePath);write(temp,doc);temp.moveTo(f,true);
            if(status)status.text="已应用。游戏信息页的「大地图 · 编辑地图」可进入；已在图内时先返回再进入。";
        }
        private function keyDown(e:KeyboardEvent):void {if(e.keyCode==Keyboard.SPACE && !(view.stage.focus is TextField)) spaceHeld=true;}
        private function keyUp(e:KeyboardEvent):void {if(e.keyCode==Keyboard.SPACE) spaceHeld=false;}
        private function down(e:MouseEvent):void {if(!spaceHeld)return;var c:Object=host.LargeContext();drag=new Point(view.mouseX,view.mouseY);origin=new Point(c.panX,c.panY);e.stopImmediatePropagation();}
        private function move(e:MouseEvent):void {if(!drag)return;var c:Object=host.LargeContext();host.LargeView(origin.x-(view.mouseX-drag.x)/c.zoom,origin.y-(view.mouseY-drag.y)/c.zoom,c.zoom);e.stopImmediatePropagation();}
        private function up(e:MouseEvent):void {if(drag){drag=null;e.stopImmediatePropagation();}}
        private function endDrag(e:MouseEvent):void {drag=null;}
        private function wheel(e:MouseEvent):void {
            var c:Object=host.LargeContext();if(!c.active)return;
            var z:Number=Math.max(0.0625,Math.min(2,c.zoom*(e.delta>0?1.25:0.8)));
            var mx:Number=view.mouseX-c.x,my:Number=view.mouseY-c.y;
            host.LargeView(c.panX+mx/c.zoom-mx/z,c.panY+my/c.zoom-my/z,z);e.stopImmediatePropagation();
        }
    }
}
