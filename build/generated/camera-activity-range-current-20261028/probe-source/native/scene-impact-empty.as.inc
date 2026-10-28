      // Experimental only; requires scene-impact-art.as.inc's audited Class
      // identity whitelist. Invoke immediately before the native erase draw:
      // if(this.sceneImpactEraseNeeded(_loc8_,param1)) <unchanged erase draw>;
      // Do not use this predicate for paint or skip the surrounding decal work.
      //
      // Existing sceneDecalTransformBounds transforms all four getBounds
      // corners. An affine image of a rectangle is enclosed by their AABB;
      // floor/ceil plus two destination pixels preserves the antialias rim.
      // Filtered, masked or unknown display trees always retain the old draw.
      //
      // Local source has no prior BitmapData.hitTest call to serve as an
      // oracle. The intended native overload is hitTest(Point(0,0),1,Rectangle):
      // true when the rectangle contains destination alpha >= 1. Before any
      // release, verify alpha 0/1/255 and all retained pixels against the old
      // draw; this fragment is neither compiled nor runtime-validated.
      public var sceneImpactEmptyEnabled:Boolean = true;
      public var sceneImpactEmptyChecks:int = 0;
      public var sceneImpactEmptySkips:int = 0;

      private function sceneImpactEraseNeeded(art:MovieClip, factory:Class) : Boolean
      {
         if(!this.sceneImpactEmptyEnabled || !this.sceneLarge || art == null
            || this.frontBmp == null || !this.sceneImpactCanReuse(factory)) return true;
         try
         {
            if(art.filters.length != 0 || art.mask != null || art.scrollRect != null
               || art.cacheAsBitmap || art.blendMode != "normal") return true;
            for(var index:int = 0; index < art.numChildren; ++index)
            {
               var child:flash.display.DisplayObject = art.getChildAt(index);
               if(!(child is flash.display.Shape) || child.filters.length != 0
                  || child.mask != null || child.scrollRect != null
                  || child.cacheAsBitmap || child.blendMode != "normal") return true;
            }
            var local:Rectangle = art.getBounds(art);
            if(local.isEmpty()) return true;
            var bounds:Rectangle = this.sceneDecalTransformBounds(local,this.m);
            if(!isFinite(bounds.left) || !isFinite(bounds.top)
               || !isFinite(bounds.right) || !isFinite(bounds.bottom)) return true;
            var left:Number = Math.max(0,Math.floor(bounds.left)-2);
            var top:Number = Math.max(0,Math.floor(bounds.top)-2);
            var right:Number = Math.min(this.frontBmp.width,Math.ceil(bounds.right)+2);
            var bottom:Number = Math.min(this.frontBmp.height,Math.ceil(bounds.bottom)+2);
            ++this.sceneImpactEmptyChecks;
            if(right <= left || bottom <= top)
            {
               ++this.sceneImpactEmptySkips;
               return false;
            }
            var area:Rectangle = new Rectangle(left,top,right-left,bottom-top);
            if(!this.frontBmp.hitTest(new Point(0,0),1,area))
            {
               ++this.sceneImpactEmptySkips;
               return false;
            }
         }
         catch(error:Error)
         {
            // Bounds/API uncertainty must never remove a native erase.
            return true;
         }
         return true;
      }
