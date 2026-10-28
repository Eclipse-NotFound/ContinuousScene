      private var largeMeta:XML;
      private var largePanX:Number=0;
      private var largePanY:Number=0;
      private var largeZoom:Number=1;
      private var largeDown:Boolean=false;
      private var largeGrid:MovieClip;
      private var largeReadout:TextField;
      private var largeOverview:Bitmap;

      public function LargeContext():Object {
         return {width:this.spacex,height:this.spacey,panX:this.largePanX,panY:this.largePanY,
            zoom:this.largeZoom,x:this.ed.setka.x,y:this.ed.setka.y,active:this.inited,
            large:this.largeMeta!=null && this.largeMeta.@sceneWidth.length()>0};
      }
      private function LargeAllocate(w:int,h:int):void {
         if(w==this.spacex && h==this.spacey && this.space.length) return;
         if(w<48||h<25||w>512||h>256) throw new Error("大地图尺寸超出范围。");
         while(this.ed.world.numChildren) this.ed.world.removeChildAt(0);
         while(this.ed.bworld.numChildren) this.ed.bworld.removeChildAt(0);
         var previous:Array=this.space;
         this.space=[];this.spacex=w;this.spacey=h;
         for(var x:int=0;x<w;x++) {
            this.space[x]=[];
            for(var y:int=0;y<h;y++) {
               var t:edTile=previous[x] && previous[x][y]?previous[x][y]:null;
               if(t==null) {
                  t=new edTile();var b:MovieClip=new edTileBack();
                  t.vis2=b;t.x=b.x=x*this.raz;t.y=b.y=y*this.raz;b.stop();b.alpha=0.5;
               }
               this.space[x][y]=t;
            }
         }
         this.LargeView(0,0,1);
      }
      public function LargeView(px:Number,py:Number,z:Number):void {
         this.largeZoom=Math.max(0.0625,Math.min(2,z));
         this.largePanX=Math.max(0,Math.min(this.spacex*20-960/this.largeZoom,px));
         this.largePanY=Math.max(0,Math.min(this.spacey*20-500/this.largeZoom,py));
         var rect:flash.geom.Rectangle=new flash.geom.Rectangle(this.largePanX,this.largePanY,960/this.largeZoom,500/this.largeZoom);
         for each(var part:MovieClip in [this.ed.bworld,this.ed.worldback,this.ed.world,this.ed.worldobj]) {
            part.x=this.ed.setka.x;part.y=this.ed.setka.y;part.scaleX=part.scaleY=this.largeZoom;part.scrollRect=rect;
         }
         // Keep only visible tile clips attached. The complete editable data stays resident.
         while(this.ed.world.numChildren) this.ed.world.removeChildAt(0);
         while(this.ed.bworld.numChildren) this.ed.bworld.removeChildAt(0);
         var x0:int=Math.max(0,int(rect.x/20));var y0:int=Math.max(0,int(rect.y/20));
         var x1:int=Math.min(this.spacex,Math.ceil(rect.right/20));var y1:int=Math.min(this.spacey,Math.ceil(rect.bottom/20));
         if(this.largeZoom<0.75) {
            if(largeOverview && largeOverview.bitmapData) largeOverview.bitmapData.dispose();
            var pixels:BitmapData=new BitmapData(this.spacex,this.spacey,false,16777215);
            for(var x:int=0;x<this.spacex;x++) for(var y:int=0;y<this.spacey;y++) {
               var code:String=this.space[x][y].enc();var first:String=code.charAt(0);
               var solid:Boolean=first!="" && first!="_" && first.charCodeAt(0)>64;
               var color:uint=solid && this.v_front?8094610:code.length>1 && this.v_back?13293514:16777215;
               pixels.setPixel(x,y,color);
            }
            if(this.v_obj) for each(var item:Object in this.objs) if(!item.isback) pixels.setPixel(int(item.X),int(item.Y),3385942);
            largeOverview=new Bitmap(pixels);largeOverview.scaleX=largeOverview.scaleY=20;this.ed.world.addChild(largeOverview);
         } else {
            if(largeOverview && largeOverview.bitmapData) {largeOverview.bitmapData.dispose();largeOverview=null;}
            for(x=x0;x<x1;x++) for(y=y0;y<y1;y++) {
               this.space[x][y].upd();this.ed.world.addChild(this.space[x][y]);this.ed.bworld.addChild(this.space[x][y].vis2);
            }
         }
         this.ed.worldobj.visible=this.v_obj && this.largeZoom>=0.75;
         this.ed.worldback.visible=this.v_backobj && this.largeZoom>=0.75;
         this.ed.world.visible=this.largeZoom<0.75?(this.v_front||this.v_back||this.v_obj):this.v_front;
         this.ed.ramka.visible=false;
         this.LargeGridUpdate();
         this.ed.dispatchEvent(new Event("largeViewportChanged"));
      }
      public function LargeRefreshOverview():void {
         if(this.inited && this.largeZoom<0.75) this.LargeView(this.largePanX,this.largePanY,this.largeZoom);
      }
      private function LargeGridUpdate():void {
         var visible:Boolean=this.largeMeta!=null && this.largeMeta.@sceneWidth.length()>0 || this.largeZoom!=1;
         this.ed.setka.visible=!visible;
         if(!largeGrid) {
            largeGrid=new MovieClip();largeGrid.mouseEnabled=false;largeGrid.mouseChildren=false;
            this.ed.addChildAt(largeGrid,this.ed.getChildIndex(this.ed.actObl));
            largeReadout=new TextField();largeReadout.defaultTextFormat=new TextFormat("Microsoft YaHei UI",13,3355443);
            largeReadout.width=960;largeReadout.height=26;largeReadout.mouseEnabled=false;this.ed.addChild(largeReadout);
         }
         largeGrid.visible=largeReadout.visible=visible;
         largeGrid.x=this.ed.setka.x;largeGrid.y=this.ed.setka.y;
         largeReadout.x=largeGrid.x;largeReadout.y=largeGrid.y+505;
         largeGrid.graphics.clear();if(!visible) return;
         var step:int=this.largeZoom<0.25?8:this.largeZoom<0.5?4:1;
         var size:Number=20*this.largeZoom*step;
         largeGrid.graphics.lineStyle(1,3355443,0.22);
         for(var x:Number=(-this.largePanX*this.largeZoom)%size;x<960;x+=size) if(x>=0) {largeGrid.graphics.moveTo(x,0);largeGrid.graphics.lineTo(x,500);}
         for(var y:Number=(-this.largePanY*this.largeZoom)%size;y<500;y+=size) if(y>=0) {largeGrid.graphics.moveTo(0,y);largeGrid.graphics.lineTo(960,y);}
         largeReadout.text=this.spacex+" × "+this.spacey+" 格　视野起点 ("+int(this.largePanX/20)+", "+int(this.largePanY/20)+")　缩放 "+int(this.largeZoom*100)+"%　"+(this.largeZoom<0.75?"概览：放大查看素材与标签":"空格拖动 · 滚轮缩放");
      }
      private function LargePoint(sx:Number,sy:Number):flash.geom.Point {
         var p:flash.geom.Point=this.ed.globalToLocal(new flash.geom.Point(sx,sy));
         return new flash.geom.Point((p.x-this.ed.setka.x)/this.largeZoom+this.largePanX,(p.y-this.ed.setka.y)/this.largeZoom+this.largePanY);
      }
      public function LargeOpen(doc:XML):void {
         // Caller validates before replacing the current document.
         this.selobj=null;this.showSelect();this.allroom=doc.copy();this.cmapZ=0;
         this.decodeAll();this.mActive=true;
      }
      public function LargeSnapshot():XML {
         if(!this.updSelObj()) throw new Error("物体或房间的 XML 属性无效。");
         var r:XML=this.encode();
         var result:XML=<all sceneFormat="1"/>;
         if(this.landXML) result.appendChild(this.landXML.copy());
         result.appendChild(r);return result;
      }
      public function LargeGrow(w:int,h:int):void {
         if(w<this.spacex||h<this.spacey) throw new Error("扩展地图不能裁剪已有内容；请使用新建来创建更小的地图。");
         if(w>512||h>256) throw new Error("最大尺寸为 512×256 格。");
         var doc:XML=this.LargeSnapshot();var r:XML=doc.room[0];
         var oldW:int=this.spacex;var oldH:int=this.spacey;
         for(var y:int=0;y<h;y++) {
            var row:Array=y<oldH?String(r.a[y]).split("."):[];
            while(row.length<w) row.push("_");
            if(y<oldH) r.a[y]=<a>{row.join(".")}</a>;else r.appendChild(<a>{row.join(".")}</a>);
         }
         r.@sceneWidth=w;r.@sceneHeight=h;this.LargeOpen(doc);
      }
