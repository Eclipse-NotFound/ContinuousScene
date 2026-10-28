      // Preload in wider raster passes, then keep the existing small damage
      // surfaces. Gameplay never repaints a large batch for a single impact.
      private var sceneBatch:Boolean = false;
      private const sceneBatchCells:int = 3;
      private var scenePreloadWidth:int = 0;
      private var scenePreloadHeight:int = 0;

      private function scenePreloadAll() : void
      {
         if(this.scenePreloadRegions()) return;
         var columns:int = Math.ceil(this.loc.limX / this.sceneSide);
         var rows:int = Math.ceil(this.loc.limY / this.sceneSide);
         var size:int = this.sceneSide + 2 * this.sceneGutter;
         var parents:Array = [this.visFront,this.visBack,this.visBack2,this.visVoda];
         this.sceneBatch = true;
         this.sceneRasterizing = true;
         this.sceneRepaint = true;
         try
         {
            this.scenePrepare(this.loc);
            for(var bx:int = 0; bx < columns; bx += this.sceneBatchCells)
               for(var by:int = 0; by < rows; by += this.sceneBatchCells)
               {
                  this.sceneX = bx * this.sceneSide - this.sceneGutter;
                  this.sceneY = by * this.sceneSide - this.sceneGutter;
                  this.sceneDrawRegionChunk();
                  var buffers:Array = [this.frontBmp,this.backBmp,this.backBmp2,this.vodaBmp];
                  for(var cx:int = bx; cx < Math.min(columns,bx + this.sceneBatchCells); ++cx)
                     for(var cy:int = by; cy < Math.min(rows,by + this.sceneBatchCells); ++cy)
                     {
                        var key:String = cx + ":" + cy;
                        if(this.sceneChunks[key]) continue;
                        var nativeBuffers:Array = [];
                        var bitmaps:Array = [];
                        var source:Rectangle = new Rectangle((cx - bx) * this.sceneSide,
                           (cy - by) * this.sceneSide,size,size);
                        for(var n:int = 0; n < 4; ++n)
                        {
                           var data:BitmapData = new BitmapData(size,size,true,0);
                           data.copyPixels(buffers[n],source,new Point());
                           var bitmap:Bitmap = new Bitmap(data);
                           bitmap.scrollRect = new Rectangle(this.sceneGutter,this.sceneGutter,this.sceneSide,this.sceneSide);
                           bitmap.x = cx * this.sceneSide; bitmap.y = cy * this.sceneSide;
                           parents[n].addChild(bitmap); bitmaps.push(bitmap); nativeBuffers.push(data);
                        }
                        var x:int = cx * this.sceneSide - this.sceneGutter;
                        var y:int = cy * this.sceneSide - this.sceneGutter;
                        this.sceneChunks[key] = {cx:cx,cy:cy,bitmaps:bitmaps,sats:null,nativeBuffers:nativeBuffers,
                           revision:0,backobjs:this.sceneBackdropObjects(x,y,size,size),
                           x:x,y:y,side:this.sceneSide,gutter:this.sceneGutter};
                        ++this.sceneResident;
                     }
               }
         }
         catch(error:*)
         {
            this.sceneFinishBatch();
            throw error;
         }
         this.sceneFinishBatch();
      }

      private function sceneFinishBatch() : void
      {
         this.sceneBatch = false;
         this.scenePreloadWidth = this.scenePreloadHeight = 0;
         this.sceneX = this.sceneY = 0;
         this.sceneRepaint = false;
         // Keep rasterizing set while restoring the small scratch buffers.
         this.scenePrepare(this.loc);
         this.sceneRegionClearScratch();
         this.sceneRasterizing = false;
      }

      // A region has one native raster style. Draw it once, then distribute
      // its pixels to the existing small resident surfaces, including gutters.
      private function scenePreloadRegions() : Boolean
      {
         var regions:Array = this.sceneRegionData[this.loc];
         if(regions == null || regions.length == 0) return false;
         var area:Number = 0;
         for each(var style:Object in regions) area += style.bounds.width * style.bounds.height;
         if(area != this.loc.limX * this.loc.limY) return false;
         var original:Object = {backwall:this.loc.backwall,color:this.loc.color,cTransform:this.loc.cTransform,
            darkness:this.loc.darkness,backform:this.loc.backform,transpFon:this.loc.transpFon,
            tipWater:this.loc.tipWater,gas:this.loc.gas,homeStable:this.loc.homeStable};
         var columns:int = Math.ceil(this.loc.limX / this.sceneSide);
         var rows:int = Math.ceil(this.loc.limY / this.sceneSide);
         var size:int = this.sceneSide + 2 * this.sceneGutter;
         var parents:Array = [this.visFront,this.visBack,this.visBack2,this.visVoda];
         var n:int;
         this.sceneRasterizing = true; this.sceneRepaint = true;
         try
         {
            for(var cx:int = 0; cx < columns; ++cx) for(var cy:int = 0; cy < rows; ++cy)
            {
               var key:String = cx + ":" + cy;
               if(this.sceneChunks[key]) continue;
               var buffers:Array = [];
               var bitmaps:Array = [];
               for(n = 0; n < 4; ++n)
               {
                  var data:BitmapData = new BitmapData(size,size,true,0);
                  var bitmap:Bitmap = new Bitmap(data);
                  bitmap.scrollRect = new Rectangle(this.sceneGutter,this.sceneGutter,this.sceneSide,this.sceneSide);
                  bitmap.x = cx * this.sceneSide; bitmap.y = cy * this.sceneSide;
                  parents[n].addChild(bitmap); bitmaps.push(bitmap); buffers.push(data);
               }
               var x:int = cx * this.sceneSide - this.sceneGutter;
               var y:int = cy * this.sceneSide - this.sceneGutter;
               this.sceneChunks[key] = {cx:cx,cy:cy,bitmaps:bitmaps,sats:null,nativeBuffers:buffers,revision:0,
                  backobjs:this.sceneBackdropObjects(x,y,size,size),x:x,y:y,side:this.sceneSide,gutter:this.sceneGutter};
               ++this.sceneResident;
            }
            for each(style in regions)
            {
               var clip:Rectangle = style.bounds.clone();
               if(clip.left == 0) clip.left = -this.sceneGutter;
               if(clip.top == 0) clip.top = -this.sceneGutter;
               if(clip.right == this.loc.limX) clip.right = columns * this.sceneSide + this.sceneGutter;
               if(clip.bottom == this.loc.limY) clip.bottom = rows * this.sceneSide + this.sceneGutter;
               var draw:Rectangle = clip.clone(); draw.inflate(this.sceneGutter,this.sceneGutter);
               this.sceneX = draw.x; this.sceneY = draw.y;
               this.scenePreloadWidth = draw.width; this.scenePreloadHeight = draw.height;
               this.scenePrepare(this.loc);
               this.sceneRegionDrawPass(style);
               buffers = [this.frontBmp,this.backBmp,this.backBmp2,this.vodaBmp];
               for each(var surface:Object in this.sceneChunks)
               {
                  var worldClip:Rectangle = clip.intersection(new Rectangle(surface.x,surface.y,size,size));
                  if(worldClip.isEmpty()) continue;
                  var source:Rectangle = worldClip.clone(); source.offset(-this.sceneX,-this.sceneY);
                  var point:Point = new Point(worldClip.x-surface.x,worldClip.y-surface.y);
                  for(n = 0; n < 4; ++n) surface.nativeBuffers[n].copyPixels(buffers[n],source,point);
               }
            }
         }
         catch(error:*)
         {
            for(var field:String in original) this.loc[field] = original[field];
            this.sceneFinishBatch(); throw error;
         }
         for(field in original) this.loc[field] = original[field];
         this.sceneFinishBatch();
         return true;
      }
