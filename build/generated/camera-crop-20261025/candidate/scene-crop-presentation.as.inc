      // Candidate only. Call Allowed before the cull-key return; include it in
      // that key. Recycle all newly invisible entries before binding visibles.
      public const sceneCropVersion:String = "native-crop-guard-1";
      public var sceneCropPresentation:Boolean = true;
      public var sceneCropCopies:int = 0;
      public var sceneCropAllocations:int = 0;
      public var sceneCropRestoreErrors:int = 0;
      public var sceneCropFailures:int = 0;
      public var sceneCropLastError:String = "";
      private var sceneCropPool:Array = [];
      private var sceneCropDisabled:Boolean = false;
      private var sceneCropDepth:int = 0;

      private function sceneCropAllowed() : Boolean
      {
         if(!this.sceneCropPresentation || this.sceneCropDisabled || this.sceneCropDepth != 0 || !this.sceneLarge || this.sceneSide != 320) return false;
         var camera:* = World.w.cam;
         if(camera == null || Number(camera.scaleV) != 1 || camera.quakeX != 0 || camera.quakeY != 0 || this.visSats == null || this.visSats.visible) return false;
         for each(var root:Sprite in [this.visFront,this.visBack,this.visBack2,this.visVoda])
         {
            if(root == null || root.stage == null || root.stage !== World.w.main.stage) return false;
            // Unverified effect/clip combinations stay native. Alpha is not a
            // gate: the native water layer intentionally uses alpha 0.6.
            for(var ancestor:flash.display.DisplayObject = root; ancestor != null; ancestor = ancestor.parent)
               if(ancestor.transform.matrix3D != null || ancestor.filters.length != 0 || ancestor.blendMode != "normal" || ancestor.mask != null || ancestor.scrollRect != null) return false;
            var matrix:Matrix = root.transform.concatenatedMatrix;
            if(matrix == null || matrix.a != 1 || matrix.d != 1 || matrix.b != 0 || matrix.c != 0 ||
               !isFinite(matrix.tx) || !isFinite(matrix.ty) || matrix.tx != Math.floor(matrix.tx) || matrix.ty != Math.floor(matrix.ty)) return false;
         }
         return true;
      }

      private function sceneCropSetVisible(entry:Object, visible:Boolean, allowed:Boolean) : void
      {
         for each(var bitmap:Bitmap in entry.bitmaps) if(bitmap.visible != visible) bitmap.visible = visible;
         if(!visible) { this.sceneCropRelease(entry); return; }
         // Keep visible copies dormant across fractional-shake/zoom transitions.
         if(!allowed || this.sceneCropDisabled || this.sceneCropDepth != 0) { this.sceneCropRestore(entry); return; }
         if(!this.sceneCropBind(entry)) return;
         if(entry.cropRevision !== entry.revision) entry.cropDirty = 15;
         this.sceneCropCopy(entry);
         if(this.sceneCropDisabled || entry.cropPixels == null) return;
         // Mark ownership before the first setter so partial publication also
         // restores every original layer if a later setter throws.
         entry.cropBound = true;
         try
         {
            for(var i:int = 0; i < 4; ++i)
            {
               bitmap = entry.bitmaps[i];
               this.sceneCropSwap(bitmap,entry.cropPixels[i]);
               if(bitmap.scrollRect != null) bitmap.scrollRect = null;
            }
         }
         catch(bindError:Error) { this.sceneCropFailed(bindError.message); }
      }

      private function sceneCropBind(entry:Object) : Boolean
      {
         if(entry.cropPixels != null) return true;
         if(entry.side != 320 || entry.gutter != 40 || entry.bitmaps.length != 4 || entry.nativeBuffers.length != 4)
         { this.sceneCropFailed("Unsupported native tile shape"); return false; }
         var states:Array = [];
         for(var i:int = 0; i < 4; ++i)
         {
            var bitmap:Bitmap = entry.bitmaps[i]; var clip:Rectangle = bitmap.scrollRect;
            var matrix:Matrix = bitmap.transform.matrix;
            if(bitmap.bitmapData !== entry.nativeBuffers[i] || clip == null || clip.x != entry.gutter || clip.y != entry.gutter ||
               clip.width != entry.side || clip.height != entry.side || matrix == null || matrix.a != 1 || matrix.d != 1 || matrix.b != 0 || matrix.c != 0 ||
               !isFinite(matrix.tx) || !isFinite(matrix.ty) || matrix.tx != Math.floor(matrix.tx) || matrix.ty != Math.floor(matrix.ty))
            { this.sceneCropFailed("Unexpected native tile binding or geometry"); return false; }
            states.push({bitmap:bitmap,data:bitmap.bitmapData,clip:clip});
         }
         entry.cropState = states; entry.cropPixels = []; entry.cropBound = false;
         entry.cropSource = new Rectangle(entry.gutter,entry.gutter,entry.side,entry.side);
         entry.cropOrigin = new Point(); entry.cropDirty = 15; entry.cropRevision = -1;
         for(i = 0; i < 4; ++i)
         {
            var data:BitmapData = this.sceneCropPool.length ? this.sceneCropPool.pop() : null;
            if(data != null && (data.width != entry.side || data.height != entry.side)) { data.dispose(); data = null; }
            if(data == null)
            {
               // Catch only this candidate's allocation, never native drawing.
               try { data = new BitmapData(entry.side,entry.side,true,0); ++this.sceneCropAllocations; }
               catch(allocationError:Error) { this.sceneCropFailed(allocationError.message); return false; }
            }
            entry.cropPixels.push(data);
         }
         return true;
      }

      private function sceneCropSync(entry:Object, kind:String = null) : void
      {
         if(entry.cropPixels == null) return;
         entry.cropDirty |= kind == "decal" || kind == "gwall" ? 1 : kind == "paint" ? 2 : kind == "drawWater" ? 8 : 15;
         // Batch writes do not necessarily increment revision. null explicitly
         // dirties all four; dormant copies synchronize only when rebound.
         if(entry.cropBound) this.sceneCropCopy(entry);
      }

      private function sceneCropCopy(entry:Object) : void
      {
         try
         {
            for(var i:int = 0; i < 4; ++i) if((entry.cropDirty & (1 << i)) != 0)
            {
               entry.cropPixels[i].copyPixels(entry.nativeBuffers[i],entry.cropSource,entry.cropOrigin);
               ++this.sceneCropCopies; entry.cropDirty &= ~(1 << i);
            }
            entry.cropRevision = entry.revision;
         }
         catch(copyError:Error) { this.sceneCropFailed(copyError.message); }
      }

      private function sceneCropRestore(entry:Object) : void
      {
         if(entry.cropPixels == null || !entry.cropBound) return;
         for(var i:int = 0; i < entry.cropState.length; ++i)
         {
            // Continue through every owned layer if an external owner has
            // already destroyed a buffer; never mask the original draw error.
            try
            {
               var state:Object = entry.cropState[i]; var bitmap:Bitmap = state.bitmap;
               this.sceneCropSwap(bitmap,state.data);
               if(!this.sceneCropSameRect(bitmap.scrollRect,state.clip)) bitmap.scrollRect = state.clip;
            }
            catch(restoreError:Error) { ++this.sceneCropRestoreErrors; this.sceneCropDisabled = true; }
         }
         entry.cropBound = false;
      }

      private function sceneCropSameRect(a:Rectangle, b:Rectangle) : Boolean
      { return a == null ? b == null : b != null && a.x == b.x && a.y == b.y && a.width == b.width && a.height == b.height; }

      private function sceneCropSwap(bitmap:Bitmap, data:BitmapData) : void
      {
         if(bitmap.bitmapData === data) return;
         // Keep current settings, including updates by other modules since bind.
         var smooth:Boolean = bitmap.smoothing; var snapping:String = bitmap.pixelSnapping;
         try { bitmap.bitmapData = data; }
         finally
         {
            if(bitmap.smoothing != smooth) bitmap.smoothing = smooth;
            if(bitmap.pixelSnapping != snapping) bitmap.pixelSnapping = snapping;
         }
      }

      private function sceneCropRelease(entry:Object) : void
      {
         if(entry.cropPixels == null) return;
         this.sceneCropRestore(entry);
         for(var i:int = 0; i < entry.cropPixels.length; ++i)
         {
            var data:BitmapData = entry.cropPixels[i];
            // A failed restore must never dispose pixels still displayed.
            if(entry.cropState[i].bitmap.bitmapData === data) continue;
            if(this.sceneCropPool.length < 64) this.sceneCropPool.push(data); else data.dispose();
         }
         entry.cropPixels = null; entry.cropState = null; entry.cropSource = null; entry.cropOrigin = null;
      }

      private function sceneCropAbort() : void
      {
         this.sceneCropDisabled = true; this.sceneCullKey = "";
         for each(var entry:Object in this.sceneChunks)
            try { this.sceneCropRelease(entry); } catch(releaseError:Error) { ++this.sceneCropRestoreErrors; }
         while(this.sceneCropPool.length)
            try { BitmapData(this.sceneCropPool.pop()).dispose(); } catch(disposeError:Error) { ++this.sceneCropRestoreErrors; }
      }

      private function sceneCropFailed(message:String) : void
      { ++this.sceneCropFailures; this.sceneCropLastError = message; this.sceneCropAbort(); }

      private function sceneCropClear() : void
      { this.sceneCropAbort(); this.sceneCropDisabled = false; this.sceneCropDepth = 0; }

      private function sceneCropSuspend() : void
      {
         ++this.sceneCropDepth; this.sceneCullKey = "";
         if(this.sceneCropDepth == 1) for each(var entry:Object in this.sceneChunks) this.sceneCropRestore(entry);
      }

      private function sceneCropResume() : void
      {
         if(this.sceneCropDepth > 0) --this.sceneCropDepth;
         // Do not allocate/copy in sceneSats' finally: preserve its exceptions.
         // The next normal sceneTick rebinds still-resident visible copies.
         this.sceneCullKey = "";
      }
