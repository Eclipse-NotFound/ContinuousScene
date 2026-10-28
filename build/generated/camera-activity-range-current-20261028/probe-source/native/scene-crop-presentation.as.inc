      // Display-only crop. Native gutters remain authoritative for drawing,
      // WallBlend, lights and replay. Keep the original Bitmap objects/layers.
      public const sceneCropVersion:String = "native-crop-1";
      public var sceneCropPresentation:Boolean = true;
      public var sceneCropCopies:int = 0;
      public var sceneCropAllocations:int = 0;
      private var sceneCropPool:Array = [];

      private function sceneCropBind(entry:Object) : void
      {
         if(entry.cropPixels != null) return;
         var pixels:Array = [];
         var source:Rectangle = new Rectangle(entry.gutter,entry.gutter,entry.side,entry.side);
         var origin:Point = new Point();
         try
         {
            // Allocate/copy every layer before publishing any of them.
            for(var i:int = 0; i < 4; ++i)
            {
               var data:BitmapData = this.sceneCropPool.length ? this.sceneCropPool.pop() : null;
               if(data != null && (data.width != entry.side || data.height != entry.side))
               { data.dispose(); data = null; }
               if(data == null)
               { data = new BitmapData(entry.side,entry.side,true,0); ++this.sceneCropAllocations; }
               pixels.push(data);
               data.copyPixels(entry.nativeBuffers[i],source,origin);
               ++this.sceneCropCopies;
            }
            entry.cropPixels = pixels; entry.cropSource = source; entry.cropOrigin = origin;
            for(i = 0; i < 4; ++i)
            {
               var bitmap:Bitmap = entry.bitmaps[i];
               var smooth:Boolean = bitmap.smoothing;
               bitmap.bitmapData = pixels[i]; bitmap.smoothing = smooth;
               bitmap.scrollRect = null;
            }
         }
         catch(error:Error)
         {
            // A failed display allocation must leave the native game usable.
            if(entry.cropPixels != null) this.sceneCropRelease(entry);
            else for each(data in pixels) data.dispose();
            this.sceneCropPresentation = false;
         }
      }

      private function sceneCropSync(entry:Object, kind:String = null) : void
      {
         if(entry.cropPixels == null) return;
         // One native operation writes one layer. Copy its complete inner
         // tile after all regional composition has finished, without relying
         // on approximate artwork bounds or a later ENTER_FRAME callback.
         var layer:int = kind == "decal" || kind == "gwall" ? 0 : kind == "paint" ? 1 : kind == "drawWater" ? 3 : -1;
         for(var i:int = 0; i < 4; ++i)
            if(layer < 0 || layer == i)
            {
               entry.cropPixels[i].copyPixels(entry.nativeBuffers[i],entry.cropSource,entry.cropOrigin);
               ++this.sceneCropCopies;
            }
      }

      private function sceneCropRelease(entry:Object) : void
      {
         if(entry.cropPixels == null) return;
         for(var i:int = 0; i < 4; ++i)
         {
            var bitmap:Bitmap = entry.bitmaps[i];
            var data:BitmapData = entry.cropPixels[i];
            var smooth:Boolean = bitmap.smoothing;
            bitmap.bitmapData = entry.nativeBuffers[i]; bitmap.smoothing = smooth;
            bitmap.scrollRect = entry.cropSource;
            if(this.sceneCropPool.length < 64) this.sceneCropPool.push(data);
            else data.dispose();
         }
         entry.cropPixels = null; entry.cropSource = null; entry.cropOrigin = null;
      }
