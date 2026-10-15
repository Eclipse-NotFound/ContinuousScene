      // Region styles affect raster colors/backdrops, never logical room identity.
      private var sceneRegionData:Dictionary = new Dictionary(true);
      private var sceneRegionComposite:Array;
      private var sceneRegionPassActive:Boolean = false;
      public var sceneRegionPasses:int = 0;

      public function sceneSetRegions(value:Location, metadata:XML) : void
      {
         delete this.sceneRegionData[value];
         if(value.spaceX <= World.cellsX && value.spaceY <= World.cellsY) return;
         if(metadata == null || metadata.sceneRegions.region.length() == 0) return;
         var regions:Array = [];
         var world:Rectangle = new Rectangle(0,0,value.spaceX * Tile.tileX,value.spaceY * Tile.tileY);
         for each(var node:XML in metadata.sceneRegions.region)
         {
            var bounds:Rectangle = new Rectangle(Number(node.@x) * Tile.tileX,Number(node.@y) * Tile.tileY,
               Number(node.@width) * Tile.tileX,Number(node.@height) * Tile.tileY);
            if(!isFinite(bounds.x) || !isFinite(bounds.y) || !isFinite(bounds.width) || !isFinite(bounds.height)
               || bounds.width <= 0 || bounds.height <= 0 || !world.containsRect(bounds))
               throw new Error("ContinuousScene region is outside its map");
            for each(var prior:Object in regions)
               if(bounds.intersects(prior.bounds)) throw new Error("ContinuousScene regions overlap");
            var color:String = node.@color.length() ? String(node.@color) : value.color;
            var darkness:Number = node.@dark.length() ? Number(node.@dark) : value.darkness;
            if(!isFinite(darkness)) throw new Error("ContinuousScene region darkness is invalid");
            var style:Object = {bounds:bounds,
               backwall:node.@backwall.length() ? String(node.@backwall) : value.backwall,
               color:color,cTransform:value.colorFilter(color),darkness:int(darkness)};
            style.key = this.sceneRegionStyleKey(style);
            regions.push(style);
         }
         this.sceneRegionData[value] = regions;
         this.sceneSyncRegionLighting(value);
      }

      // Native allon/alloff affect the whole Location. Their redraw enters
      // sceneOpen before any regional pass temporarily owns Location's style.
      // Mutate existing styles so entity and overlay references remain valid.
      private function sceneSyncRegionLighting(value:Location) : void
      {
         if(value.lightOn == 0) return;
         var regions:Array = this.sceneRegionData[value];
         if(regions == null) return;
         for each(var style:Object in regions)
         {
            style.color = value.color;
            style.cTransform = value.cTransform;
            style.darkness = value.darkness;
            style.key = this.sceneRegionStyleKey(style);
         }
      }

      // Returned style references are read-only. Null means use the Location style.
      public function sceneRegionStyle(value:Location, worldX:Number, worldY:Number) : Object
      {
         var regions:Array = this.sceneRegionData[value];
         if(regions == null) return null;
         for each(var style:Object in regions)
            if(style.bounds.contains(worldX,worldY)) return style;
         return null;
      }

      // World-space clips allow overlays and later paint operations to use the
      // same exact split, including a 1000px room boundary inside a 320px chunk.
      public function sceneRegionSlices(value:Location, worldBounds:Rectangle) : Array
      {
         var result:Array = [];
         var regions:Array = this.sceneRegionData[value];
         if(regions == null) return result;
         for each(var style:Object in regions)
         {
            var clip:Rectangle = worldBounds.intersection(style.bounds);
            if(!clip.isEmpty()) result.push({bounds:clip,style:style});
         }
         return result;
      }

      private function sceneRegionStyleKey(style:Object) : String
      {
         return style.backwall + ":" + style.darkness + ":" + this.sceneRegionColorKey(style.cTransform);
      }

      private function sceneRegionColorKey(ct:ColorTransform) : String
      {
         return [
            ct == null ? 1 : ct.redMultiplier,ct == null ? 1 : ct.greenMultiplier,
            ct == null ? 1 : ct.blueMultiplier,ct == null ? 1 : ct.alphaMultiplier,
            ct == null ? 0 : ct.redOffset,ct == null ? 0 : ct.greenOffset,
            ct == null ? 0 : ct.blueOffset,ct == null ? 0 : ct.alphaOffset].join(":");
      }

      private function sceneRegionClearScratch() : void
      {
         if(this.sceneRegionComposite != null)
            for each(var data:BitmapData in this.sceneRegionComposite) data.dispose();
         this.sceneRegionComposite = null;
      }

      private function sceneRegionDrawPass(style:Object) : void
      {
         this.loc.backwall = style.backwall;
         this.loc.color = style.color;
         this.loc.cTransform = style.cTransform;
         this.loc.darkness = style.darkness;
         this.sceneMaskCursor = new Dictionary();
         ++this.sceneRegionPasses;
         var prior:Boolean = this.sceneRegionPassActive;
         this.sceneRegionPassActive = true;
         try { this.drawLoc(this.loc); }
         finally { this.sceneRegionPassActive = prior; }
      }

      private function sceneRegionEnsureScratch() : void
      {
         if(this.sceneRegionComposite != null && this.sceneRegionComposite[0].width == this.rectX
            && this.sceneRegionComposite[0].height == this.rectY) return;
         this.sceneRegionClearScratch(); this.sceneRegionComposite = [];
         for(var n:int = 0; n < 4; ++n)
            this.sceneRegionComposite.push(new BitmapData(this.rectX,this.rectY,true,0));
      }

      // Incremental impacts use the same fixed sceneStamp in every region.
      // Only affected pixels of the already resident chunk are copied; no
      // terrain rasterization, object recreation or extra RNG is performed.
      private function sceneApplyRegionAction(kind:String, args:Array, affected:Rectangle = null) : void
      {
         var action:Function = this[kind];
         if(this.sceneRegionPassActive || this.sceneRegionData[this.loc] == null
            || (kind != "decal" && kind != "drawWater")
            || (kind == "decal" && (args[1] == null || args[6] != "normal")))
         {
            action.apply(this,args); return;
         }
         var viewport:Rectangle = new Rectangle(this.sceneX,this.sceneY,this.rectX,this.rectY);
         if(affected == null)
            affected = kind == "decal" ? this.sceneDecalBounds(args,this.sceneStamp)
               : new Rectangle(args[0].X * Tile.tileX,args[0].Y * Tile.tileY,Tile.tileX,Tile.tileY * 2);
         var work:Rectangle = viewport.intersection(affected);
         if(work.isEmpty()) return;
         // BitmapData copy bounds must include antialiased edge pixels.
         work = new Rectangle(Math.floor(work.left),Math.floor(work.top),
            Math.ceil(work.right) - Math.floor(work.left),Math.ceil(work.bottom) - Math.floor(work.top));
         var original:ColorTransform = this.loc.cTransform;
         var originalKey:String = this.sceneRegionColorKey(original);
         var groups:Array = [];
         var byKey:Object = {};
         var styledArea:Number = 0;
         for each(var slice:Object in this.sceneRegionSlices(this.loc,work))
         {
            var key:String = this.sceneRegionColorKey(slice.style.cTransform);
            if(key == originalKey) continue;
            var group:Object = byKey[key];
            if(group == null)
            {
               group = {ct:slice.style.cTransform,clips:[],area:0};
               byKey[key] = group; groups.push(group);
            }
            group.clips.push(slice.bounds);
            group.area += slice.bounds.width * slice.bounds.height;
            styledArea += slice.bounds.width * slice.bounds.height;
         }
         if(groups.length == 0) { action.apply(this,args); return; }
         var target:BitmapData = kind == "decal" ? this.frontBmp : this.vodaBmp;
         var before:BitmapData;
         var output:BitmapData;
         var local:Rectangle = work.clone(); local.offset(-this.sceneX,-this.sceneY);
         var origin:Point = local.topLeft;
         var complete:Boolean = false;
         try
         {
            if(groups.length == 1 && groups[0].area == work.width * work.height)
            {
               this.loc.cTransform = groups[0].ct;
               action.apply(this,args); return;
            }
            this.sceneRegionEnsureScratch();
            before = this.sceneRegionComposite[0]; output = this.sceneRegionComposite[1];
            before.copyPixels(target,local,origin);
            var firstGroup:int = styledArea == work.width * work.height ? 1 : 0;
            this.loc.cTransform = firstGroup ? groups[0].ct : original;
            action.apply(this,args);
            output.copyPixels(target,local,origin);
            for(var gi:int = firstGroup; gi < groups.length; ++gi)
            {
               group = groups[gi];
               target.copyPixels(before,local,origin);
               this.loc.cTransform = group.ct;
               action.apply(this,args);
               for each(var worldClip:Rectangle in group.clips)
               {
                  var localClip:Rectangle = worldClip.clone(); localClip.offset(-this.sceneX,-this.sceneY);
                  output.copyPixels(target,localClip,localClip.topLeft);
               }
            }
            target.copyPixels(output,local,origin);
            complete = true;
         }
         finally
         {
            this.loc.cTransform = original;
            if(before != null && !complete) target.copyPixels(before,local,origin);
         }
      }

      private function sceneDrawRegionChunk() : void
      {
         var regions:Array = this.sceneRegionData[this.loc];
         if(regions == null || regions.length == 0)
         {
            this.drawLoc(this.loc); return;
         }
         var started:int = getTimer();
         var original:Object = {backwall:this.loc.backwall,color:this.loc.color,
            cTransform:this.loc.cTransform,darkness:this.loc.darkness};
         var originalKey:String = this.sceneRegionStyleKey(original);
         var viewport:Rectangle = new Rectangle(this.sceneX,this.sceneY,this.rectX,this.rectY);
         var inWorld:Rectangle = viewport.intersection(new Rectangle(0,0,
            this.loc.spaceX * Tile.tileX,this.loc.spaceY * Tile.tileY));
         var groups:Array = [];
         var byKey:Object = {};
         var styledArea:Number = 0;
         for each(var slice:Object in this.sceneRegionSlices(this.loc,viewport))
         {
            if(slice.style.key == originalKey) continue;
            var group:Object = byKey[slice.style.key];
            if(group == null)
            {
               group = {style:slice.style,clips:[],area:0};
               byKey[slice.style.key] = group; groups.push(group);
            }
            group.clips.push(slice.bounds);
            group.area += slice.bounds.width * slice.bounds.height;
            styledArea += slice.bounds.width * slice.bounds.height;
         }
         try
         {
            if(groups.length == 0)
            {
               this.sceneRegionDrawPass(original); return;
            }
            if(groups.length == 1 && groups[0].area == inWorld.width * inWorld.height)
            {
               this.sceneRegionDrawPass(groups[0].style); return;
            }
            // If styles cover this entire chunk, use the first as the base and
            // avoid an unused neutral pass. Otherwise preserve default gaps.
            var firstGroup:int = styledArea == inWorld.width * inWorld.height ? 1 : 0;
            this.sceneRegionDrawPass(firstGroup ? groups[0].style : original);
            var buffers:Array = [this.frontBmp,this.backBmp,this.backBmp2,this.vodaBmp];
            var n:int;
            var origin:Point = new Point(0,0);
            this.sceneRegionEnsureScratch();
            for(n = 0; n < 4; ++n)
               this.sceneRegionComposite[n].copyPixels(buffers[n],this.allRect,origin);
            for(var gi:int = firstGroup; gi < groups.length; ++gi)
            {
               group = groups[gi];
               this.sceneRegionDrawPass(group.style);
               for each(var worldClip:Rectangle in group.clips)
               {
                  var localClip:Rectangle = worldClip.clone();
                  localClip.offset(-this.sceneX,-this.sceneY);
                  var destination:Point = localClip.topLeft;
                  for(n = 0; n < 4; ++n)
                     this.sceneRegionComposite[n].copyPixels(buffers[n],localClip,destination);
               }
            }
            for(n = 0; n < 4; ++n)
               buffers[n].copyPixels(this.sceneRegionComposite[n],this.allRect,origin);
         }
         finally
         {
            this.loc.backwall = original.backwall;
            this.loc.color = original.color;
            this.loc.cTransform = original.cTransform;
            this.loc.darkness = original.darkness;
            this.sceneDrawMs = getTimer() - started;
            this.sceneMaxDrawMs = Math.max(this.sceneMaxDrawMs,this.sceneDrawMs);
         }
      }
