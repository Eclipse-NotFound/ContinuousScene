      // Logical objects never move between chunks. Only raster layers are cached.
      public var sceneX:int = 0;
      public var sceneY:int = 0;
      public var sceneLarge:Boolean = false;
      public var sceneRedraws:int = 0;
      public var sceneDrawMs:int = 0;
      public var sceneMaxDrawMs:int = 0;
      public var sceneResident:int = 0;
      public var sceneEvictions:int = 0;
      public var sceneMisses:int = 0;
      public var scenePreload:Boolean = false;
      public var sceneLastDirtyCount:int = 0;
      public function sceneSurfaces() : Array
      {
         var result:Array = [];
         for each(var entry:Object in this.sceneChunks) result.push(entry);
         return result;
      }
      private var sceneRepaint:Boolean = false;
      private var sceneRasterizing:Boolean = false;
      private var sceneHistory:Dictionary = new Dictionary(true);
      private var sceneMarks:Array = [];
      private var sceneStamp:Array;
      private var sceneChunks:Object = {};
      private var sceneScratch:Array;
      private var sceneSide:int = 320;
      private var sceneGutter:int = 40;
      private var sceneMaskPool:Dictionary = new Dictionary();
      private var sceneMaskCursor:Dictionary = new Dictionary();

      private function sceneMask(factory:Class) : MovieClip
      {
         if(!this.sceneLarge) return new factory();
         var list:Array = this.sceneMaskPool[factory];
         if(list == null) this.sceneMaskPool[factory] = list = [];
         var index:int = int(this.sceneMaskCursor[factory]);
         this.sceneMaskCursor[factory] = index + 1;
         if(index == list.length) list.push(new factory());
         var result:MovieClip = list[index];
         result.scaleX = result.scaleY = 1;
         return result;
      }

      private function sceneMatrix(value:Matrix = null) : Matrix
      {
         var result:Matrix = value == null ? new Matrix() : value.clone();
         result.tx -= this.sceneX; result.ty -= this.sceneY;
         return result;
      }

      private function scenePrepare(value:Location) : void
      {
         if(!this.sceneRasterizing)
         {
            this.sceneClear(); this.sceneLarge = false;
            this.sceneX = this.sceneY = 0;
         }
         var width:int = this.sceneLarge ? this.sceneSide + this.sceneGutter * 2 : 1920;
         var height:int = this.sceneLarge ? width : 1000;
         if(width != this.rectX || height != this.rectY)
         {
            this.frontBmp.dispose(); this.backBmp.dispose(); this.backBmp2.dispose();
            this.vodaBmp.dispose(); this.satsBmp.dispose(); this.colorBmp.dispose(); this.shadBmp.dispose();
            this.rectX = width; this.rectY = height;
            this.allRect = new Rectangle(0,0,width,height);
            this.frontBmp = new BitmapData(width,height,true,0);
            this.backBmp = new BitmapData(width,height,true,0);
            this.backBmp2 = new BitmapData(width,height,true,0);
            this.vodaBmp = new BitmapData(width,height,true,0);
            this.satsBmp = new BitmapData(width,height,true,0);
            this.colorBmp = new BitmapData(width,height,true,0);
            this.shadBmp = new BitmapData(width,height,true,0);
            this.frontBitmap.bitmapData = this.frontBmp;
            this.backBitmap.bitmapData = this.backBmp;
            this.backBitmap2.bitmapData = this.backBmp2;
            this.vodaBitmap.bitmapData = this.vodaBmp;
            this.satsBitmap.bitmapData = this.satsBmp;
         }
         this.sceneScratch = [this.frontBmp,this.backBmp,this.backBmp2,this.vodaBmp];
         this.frontBitmap.visible = this.backBitmap.visible = this.backBitmap2.visible = this.vodaBitmap.visible = this.satsBitmap.visible = !this.sceneLarge;
         this.kusokX = value.spaceX; this.kusokY = value.spaceY;
         if(this.lightX != value.spaceX + 1 || this.lightY != value.spaceY + 3)
         {
            this.lightBmp.dispose();
            this.lightX = value.spaceX + 1; this.lightY = value.spaceY + 3;
            this.lightRect = new Rectangle(0,0,this.lightX,this.lightY);
            this.lightBmp = new BitmapData(this.lightX,this.lightY,true,4278190080);
            this.lightBitmap.bitmapData = this.lightBmp;
         }
      }

      private function sceneClear() : void
      {
         for each(var entry:Object in this.sceneChunks) this.sceneDrop(entry);
         this.sceneChunks = {}; this.sceneResident = 0;
         this.sceneMaskPool = new Dictionary(); this.sceneMaskCursor = new Dictionary();
      }

      private function sceneDrop(entry:Object) : void
      {
         for each(var nativeBuffer:BitmapData in entry.nativeBuffers) nativeBuffer.dispose();
         for each(var bitmap:Bitmap in entry.bitmaps)
         {
            if(bitmap.parent) bitmap.parent.removeChild(bitmap);
            bitmap.bitmapData = null; // The native buffer owns these same pixels.
         }
         if(entry.sats)
         {
            if(entry.sats.parent) entry.sats.parent.removeChild(entry.sats);
            entry.sats.bitmapData.dispose();
         }
         --this.sceneResident; ++this.sceneEvictions;
      }

      private function sceneOpen(value:Location) : void
      {
         this.sceneClear();
         this.loc = value; value.grafon = this; this.sceneLarge = true;
         if(this.sceneHistory[value] == null) this.sceneHistory[value] = [];
         this.sceneMarks = this.sceneHistory[value];
         this.sceneRasterizing = true; this.scenePrepare(value); this.sceneRasterizing = false;
         this.lightBmp.fillRect(this.lightRect,4278190080);
         this.setLight();
         var px:Number = value.spawnPoints.length ? (value.spawnPoints[0].x + 1) * 40 : value.gg.X;
         var py:Number = value.spawnPoints.length ? (value.spawnPoints[0].y + 1) * 40 : value.gg.Y;
         var left:Number = Math.max(0,Math.min(value.limX - World.w.swfStage.stageWidth, px - World.w.swfStage.stageWidth / 2));
         var top:Number = Math.max(0,Math.min(value.limY - World.w.swfStage.stageHeight, py - World.w.swfStage.stageHeight / 2 + 100));
         this.sceneEnsure(left,top,World.w.swfStage.stageWidth,World.w.swfStage.stageHeight,true);
         this.drawAllObjs();
      }

      private function sceneRender(cx:int, cy:int) : void
      {
         var key:String = cx + ":" + cy;
         if(this.sceneChunks[key]) return;
         this.sceneX = cx * this.sceneSide - this.sceneGutter;
         this.sceneY = cy * this.sceneSide - this.sceneGutter;
         this.sceneRasterizing = true; this.sceneRepaint = true;
         this.sceneMaskCursor = new Dictionary();
         try { this.drawLoc(this.loc); }
         finally { this.sceneRepaint = false; this.sceneRasterizing = false; }
         var parents:Array = [this.visFront,this.visBack,this.visBack2,this.visVoda];
         var buffers:Array = [this.frontBmp,this.backBmp,this.backBmp2,this.vodaBmp];
         var bitmaps:Array = [];
         var nativeBuffers:Array = [];
         for(var n:int = 0; n < 4; ++n)
         {
            // Keep one pixel store, including the neighbour gutter needed by damage
            // and WallBlend. scrollRect crops without a second 320px bitmap copy.
            var data:BitmapData = buffers[n].clone();
            var bitmap:Bitmap = new Bitmap(data);
            bitmap.scrollRect = new Rectangle(this.sceneGutter,this.sceneGutter,this.sceneSide,this.sceneSide);
            bitmap.x = cx * this.sceneSide; bitmap.y = cy * this.sceneSide;
            parents[n].addChild(bitmap); bitmaps.push(bitmap);
            nativeBuffers.push(data);
         }
         this.sceneChunks[key] = {cx:cx,cy:cy,bitmaps:bitmaps,sats:null,nativeBuffers:nativeBuffers,revision:0,
            x:cx * this.sceneSide - this.sceneGutter,y:cy * this.sceneSide - this.sceneGutter,side:this.sceneSide,gutter:this.sceneGutter}; ++this.sceneResident;
         this.sceneX = this.sceneY = 0;
      }

      private function sceneEnsure(left:Number, top:Number, width:Number, height:Number, initial:Boolean = false) : void
      {
         if(this.scenePreload)
         {
            left = top = 0; width = this.loc.limX - 1; height = this.loc.limY - 1;
         }
         var minX:int = Math.max(0,int(Math.floor(left / this.sceneSide)));
         var minY:int = Math.max(0,int(Math.floor(top / this.sceneSide)));
         var maxX:int = Math.min(Math.ceil(this.loc.limX / this.sceneSide) - 1,int(Math.floor((left + width) / this.sceneSide)));
         var maxY:int = Math.min(Math.ceil(this.loc.limY / this.sceneSide) - 1,int(Math.floor((top + height) / this.sceneSide)));
         var cx:int;
         var cy:int;
         var key:String;
         for(cx = minX; cx <= maxX; ++cx)
            for(cy = minY; cy <= maxY; ++cy)
               if(!this.sceneChunks[cx + ":" + cy])
               {
                  if(!initial) ++this.sceneMisses;
                  this.sceneRender(cx,cy);
               }
         // Prepare one chunk per frame, before it enters the camera.
         var made:Boolean = false;
         for(cx = Math.max(0,minX - 1); cx <= Math.min(Math.ceil(this.loc.limX / this.sceneSide) - 1,maxX + 1); ++cx)
            for(cy = Math.max(0,minY - 1); cy <= Math.min(Math.ceil(this.loc.limY / this.sceneSide) - 1,maxY + 1); ++cy)
               if((initial || !made) && !this.sceneChunks[cx + ":" + cy])
               {
                  this.sceneRender(cx,cy); made = true;
               }
         for(key in this.sceneChunks)
         {
            var entry:Object = this.sceneChunks[key];
            if(entry.cx < minX - 1 || entry.cx > maxX + 1 || entry.cy < minY - 1 || entry.cy > maxY + 1)
            {
               this.sceneDrop(entry); delete this.sceneChunks[key];
            }
         }
      }

      public function sceneTick() : void
      {
         if(!this.sceneLarge || this.loc == null) return;
         this.sceneEnsure(-World.w.cam.vx,-World.w.cam.vy,World.w.cam.screenX,World.w.cam.screenY);
         World.w.cam.setZoom(0);
      }

      private function sceneApply(kind:String, args:Array) : void
      {
         var stamp:Array = kind == "decal" ? [Math.random(),Math.random()] : null;
         if(kind == "decal" || kind == "paint" || kind == "gwall") this.sceneMarks.push([kind,args,stamp]);
         var ox:int = this.sceneX;
         var oy:int = this.sceneY;
         var affected:Rectangle;
         if(kind == "decal") affected = new Rectangle(Number(args[2])-512,Number(args[3])-512,1024,1024);
         else if(kind == "paint") affected = new Rectangle(Math.min(args[0],args[2])-50,Math.min(args[1],args[3])-50,
            Math.abs(args[2]-args[0])+100,Math.abs(args[3]-args[1])+100);
         else if(kind == "gwall") affected = new Rectangle(int(args[0])*40,int(args[1])*40,40,40);
         else if(kind == "drawWater") affected = new Rectangle(args[0].X*40,args[0].Y*40,40,80);
         this.sceneLastDirtyCount = 0;
         this.sceneRasterizing = true;
         this.sceneStamp = stamp;
         try
         {
            for each(var entry:Object in this.sceneChunks)
            {
               // Only raster surfaces intersecting the actual operation become dirty.
               // Logical tiles, units and projectiles remain live everywhere.
               if(affected && !affected.intersects(new Rectangle(entry.x,entry.y,this.rectX,this.rectY))) continue;
               this.frontBmp = entry.nativeBuffers[0]; this.backBmp = entry.nativeBuffers[1];
               this.backBmp2 = entry.nativeBuffers[2]; this.vodaBmp = entry.nativeBuffers[3];
               this.sceneX = entry.x; this.sceneY = entry.y;
               var action:Function = this[kind]; action.apply(this,args);
               ++entry.revision; ++this.sceneLastDirtyCount;
            }
         }
         finally
         {
            this.frontBmp = this.sceneScratch[0]; this.backBmp = this.sceneScratch[1];
            this.backBmp2 = this.sceneScratch[2]; this.vodaBmp = this.sceneScratch[3];
            this.sceneX = ox; this.sceneY = oy; this.sceneRasterizing = false; this.sceneStamp = null;
         }
      }

      private function sceneRestoreMarks() : void
      {
         if(!this.sceneLarge) return;
         try
         {
            for each(var item:Array in this.sceneMarks)
            {
               this.sceneStamp = item[2];
               var action:Function = this[item[0]]; action.apply(this,item[1]);
            }
         }
         finally { this.sceneStamp = null; }
      }

      private function sceneSats() : void
      {
         for each(var entry:Object in this.sceneChunks)
         {
            if(entry.sats)
            {
               if(entry.sats.parent) entry.sats.parent.removeChild(entry.sats);
               entry.sats.bitmapData.dispose();
            }
            var data:BitmapData = new BitmapData(this.sceneSide,this.sceneSide,true,0);
            data.draw(this.visual,new Matrix(1,0,0,1,-entry.cx * this.sceneSide,-entry.cy * this.sceneSide));
            var bitmap:Bitmap = new Bitmap(data,"auto",true);
            bitmap.x = entry.cx * this.sceneSide; bitmap.y = entry.cy * this.sceneSide;
            this.visSats.addChild(bitmap); entry.sats = bitmap;
         }
      }
