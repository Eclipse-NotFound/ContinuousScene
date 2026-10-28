      // Candidate only. Installed by prepare-sats-viewport.py into a separate
      // source tree; the production renderer does not include this file yet.
      public const sceneSatsVersion:String = "sats-viewport-1";
      private var sceneSatsViewKey:String = "";

      private function sceneClearSats() : void
      {
         this.sceneSatsViewKey = "";
         for each(var entry:Object in this.sceneChunks)
         {
            var bitmap:Bitmap = entry.sats as Bitmap;
            if(bitmap == null) continue;
            if(bitmap.parent) bitmap.parent.removeChild(bitmap);
            if(bitmap.bitmapData) bitmap.bitmapData.dispose();
            bitmap.bitmapData = null;
            entry.sats = null;
         }
      }

      private function sceneSats() : void
      {
         // Reopening SATS takes a new snapshot, including changes since the
         // last selection. Keep drawSats/onSats and native targeting separate.
         this.sceneClearSats();
         this.sceneCaptureSatsView();
      }

      private function sceneCaptureSatsView() : void
      {
         var camera:* = World.w.cam;
         var scale:Number = camera.scaleV > 0 ? camera.scaleV : 1;
         // Always use the real viewport, even when diagnostic raster culling
         // is disabled. Include camera shake and a margin for the native blur.
         var view:Rectangle = new Rectangle((-camera.vx-camera.quakeX)/scale,
            (-camera.vy-camera.quakeY)/scale,camera.screenX/scale,camera.screenY/scale);
         view.inflate(8,8);
         var minX:int = Math.max(0,Math.floor(view.left/this.sceneSide));
         var minY:int = Math.max(0,Math.floor(view.top/this.sceneSide));
         var maxX:int = Math.min(Math.ceil(this.loc.limX/this.sceneSide)-1,Math.ceil(view.right/this.sceneSide)-1);
         var maxY:int = Math.min(Math.ceil(this.loc.limY/this.sceneSide)-1,Math.ceil(view.bottom/this.sceneSide)-1);
         var key:String = minX+":"+minY+":"+maxX+":"+maxY+":"+this.sceneResident;
         var entry:Object;
         var x:int;
         var y:int;
         if(key == this.sceneSatsViewKey)
         {
            // A chunk may be replaced without changing the resident count.
            // Check visible entries so its new pixels do not leave a hole.
            var missing:Boolean = false;
            for(x = minX; x <= maxX && !missing; ++x) for(y = minY; y <= maxY; ++y)
            {
               entry = this.sceneChunks[x+":"+y];
               if(entry != null && !entry.sats) {missing=true;break;}
            }
            if(!missing) return;
         }

         // Camera.calc continues during SATS (look, zoom, resize and shake).
         // Retain existing frozen pixels and capture newly exposed chunks only.
         // Detach old copies to bound the native visSats blur surface; retain
         // their bitmap data for a pan back to an already captured area.
         for each(entry in this.sceneChunks)
         {
            if(!entry.sats) continue;
            var needed:Boolean = entry.cx >= minX && entry.cx <= maxX
               && entry.cy >= minY && entry.cy <= maxY;
            if(needed && !entry.sats.parent) this.visSats.addChild(entry.sats);
            else if(!needed && entry.sats.parent) entry.sats.parent.removeChild(entry.sats);
         }

         var shown:Boolean = this.visSats.visible;
         var actors:Sprite = this.visObjs[2] as Sprite;
         var actorsShown:Boolean = actors.visible;
         this.visSats.visible = false; // Never include a previous SATS copy.
         try
         {
            // Native onSats(true) hides this live layer AFTER the opening
            // snapshot. Restore it temporarily for later camera exposures.
            if(shown) actors.visible = true;
            // Keep the original raster origin and canvas size for exact native
            // alpha/gradient rounding. Larger captures changed edge pixels.
            var batch:int = 1;
            for(x = minX; x <= maxX; x += batch)
               for(y = minY; y <= maxY; y += batch)
                  this.sceneCaptureSatsBatch(x,y,Math.min(maxX,x+batch-1),Math.min(maxY,y+batch-1));
            this.sceneSatsViewKey = key;
         }
         finally { actors.visible = actorsShown; this.visSats.visible = shown; }
      }

      private function sceneCaptureSatsBatch(minX:int,minY:int,maxX:int,maxY:int) : void
      {
         var pending:Array = [];
         var area:Rectangle = null;
         var entry:Object;
         var bounds:Rectangle;
         var x:int;
         var y:int;
         for(x = minX; x <= maxX; ++x) for(y = minY; y <= maxY; ++y)
         {
            entry = this.sceneChunks[x+":"+y];
            // Never synchronously generate distant geometry for a screenshot.
            // Camera.calc calls Grafon.sceneTick to ensure visible cells first.
            if(entry == null || entry.sats) continue;
            pending.push(entry);
            bounds = new Rectangle(x*this.sceneSide,y*this.sceneSide,this.sceneSide,this.sceneSide);
            area = area == null ? bounds : area.union(bounds);
         }
         if(pending.length == 0) return;

         var hidden:Array = [];
         var data:BitmapData = null;
         var cell:BitmapData = null;
         var raster:Bitmap;
         try
         {
            // Restore only the native and WallBlend layers needed by this
            // capture. All original visibility flags are restored on failure.
            for(x = minX; x <= maxX; ++x) for(y = minY; y <= maxY; ++y)
            {
               entry = this.sceneChunks[x+":"+y];
               if(entry == null) continue;
               for each(raster in entry.bitmaps)
                  if(!raster.visible) {hidden.push(raster);raster.visible=true;}
            }
            for each(var parent:Sprite in [this.visFront,this.visBack])
               for(var i:int = 0; i < parent.numChildren; ++i)
               {
                  raster = parent.getChildAt(i) as Bitmap;
                  if(raster != null && !raster.visible
                     && (raster.name == "WallBlendSceneFront" || raster.name == "WallBlendSceneBack")
                     && raster.getBounds(this.visual).intersects(area))
                  {hidden.push(raster);raster.visible=true;}
               }
            data = new BitmapData(int(area.width),int(area.height),true,0);
            data.draw(this.visual,new Matrix(1,0,0,1,-area.x,-area.y));
            for each(entry in pending)
            {
               // Batches deliberately contain exactly one native cell. Pass
               // through that raster directly, without allocating/copying it.
               cell = data; data = null;
               var bitmap:Bitmap = new Bitmap(cell,"auto",true);
               bitmap.x = entry.cx*this.sceneSide; bitmap.y = entry.cy*this.sceneSide;
               this.visSats.addChild(bitmap);
               entry.sats = bitmap;
               cell = null; // Ownership passes to sceneClearSats/sceneDrop.
            }
         }
         finally
         {
            if(cell) cell.dispose();
            if(data) data.dispose();
            for each(raster in hidden) raster.visible = false;
         }
      }
