"""Index native backdrop artwork once per complete large-scene redraw.

Apply after GrafonChunks and prepare.py's ordinary drawLoc edits. Bounds use the
current BackObj frame after setLight(), never a previous lighting configuration.
The original painter order and all native layer/blend operations are preserved.
"""


def _once(source: str, old: str, new: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"backdrop patch anchor expected once, found {count}: {old[:96]}")
    return source.replace(old, new, 1)


_HELPERS = r"""      private var sceneBackdropLocation:Location;
      private var sceneBackdropBuckets:Object = {};
      private var sceneBackdropBounds:Dictionary = new Dictionary(true);
      public var sceneBackdropTotal:int = 0;
      public var sceneBackdropReferences:int = 0;
      public var sceneBackdropFallbacks:int = 0;

      // Returned arrays are read-only views; consumers must not sort or splice.
      // Exact render-surface requests are O(1). Other rectangles use cached
      // bounds and preserve the native order without creating artwork clones.
      public function sceneBackdropObjects(x:Number, y:Number, width:Number, height:Number) : Array
      {
         if(!this.sceneLarge || this.sceneBackdropLocation !== this.loc)
            return this.loc.backobjs;
         var cx:int = int(Math.round((x + this.sceneGutter) / this.sceneSide));
         var cy:int = int(Math.round((y + this.sceneGutter) / this.sceneSide));
         if(x == cx * this.sceneSide - this.sceneGutter && y == cy * this.sceneSide - this.sceneGutter &&
            width == this.sceneSide + this.sceneGutter * 2 && height == width)
         {
            var bucket:Array = this.sceneBackdropBuckets[cx + ":" + cy];
            return bucket == null ? [] : bucket;
         }
         var region:Rectangle = new Rectangle(x,y,width,height);
         var result:Array = [];
         for each(var backdrop:BackObj in this.loc.backobjs)
         {
            var bounds:Rectangle = this.sceneBackdropBounds[backdrop];
            if(bounds != null && bounds.intersects(region)) result.push(backdrop);
         }
         return result;
      }

      private function sceneIndexBackdrops() : void
      {
         this.sceneBackdropBuckets = {};
         this.sceneBackdropBounds = new Dictionary(true);
         this.sceneBackdropTotal = this.loc.backobjs.length;
         this.sceneBackdropReferences = this.sceneBackdropFallbacks = 0;
         var columns:int = int(Math.ceil(this.loc.limX / this.sceneSide));
         var rows:int = int(Math.ceil(this.loc.limY / this.sceneSide));
         for each(var backdrop:BackObj in this.loc.backobjs)
         {
            var bounds:Rectangle = this.sceneBackdropObjectBounds(backdrop);
            this.sceneBackdropBounds[backdrop] = bounds;
            if(bounds.isEmpty()) continue;
            // Each bucket includes its native 40px neighbour gutter.
            var minX:int = Math.max(0,Math.floor((bounds.left - this.sceneGutter) / this.sceneSide));
            var minY:int = Math.max(0,Math.floor((bounds.top - this.sceneGutter) / this.sceneSide));
            var maxX:int = Math.min(columns - 1,Math.floor((bounds.right + this.sceneGutter) / this.sceneSide));
            var maxY:int = Math.min(rows - 1,Math.floor((bounds.bottom + this.sceneGutter) / this.sceneSide));
            for(var cx:int = minX; cx <= maxX; ++cx)
               for(var cy:int = minY; cy <= maxY; ++cy)
               {
                  var region:Rectangle = new Rectangle(cx * this.sceneSide - this.sceneGutter,
                     cy * this.sceneSide - this.sceneGutter,this.sceneSide + this.sceneGutter * 2,this.sceneSide + this.sceneGutter * 2);
                  if(!bounds.intersects(region)) continue;
                  var key:String = cx + ":" + cy;
                  var bucket:Array = this.sceneBackdropBuckets[key];
                  if(bucket == null) this.sceneBackdropBuckets[key] = bucket = [];
                  bucket.push(backdrop); ++this.sceneBackdropReferences;
               }
         }
         this.sceneBackdropLocation = this.loc;
      }

      private function sceneBackdropObjectBounds(backdrop:BackObj) : Rectangle
      {
         try
         {
            var transform:Matrix = new Matrix();
            transform.scale(backdrop.scX,backdrop.scY);
            transform.tx = backdrop.X; transform.ty = backdrop.Y;
            var result:Rectangle = null;
            for each(var art:flash.display.DisplayObject in [backdrop.vis,backdrop.erase,backdrop.light])
            {
               if(art == null) continue;
               var local:Rectangle = this.sceneBackdropArtBounds(art);
               if(local.isEmpty()) continue;
               var bounds:Rectangle = this.sceneBackdropTransformBounds(local,transform);
               result = result == null ? bounds : result.union(bounds);
            }
            if(result == null) return new Rectangle();
            // Smooth bitmap sampling and sub-pixel registration at chunk edges.
            var padding:Number = 4 + 2 * Math.max(Math.abs(backdrop.scX),Math.abs(backdrop.scY));
            result.inflate(padding,padding);
            if(!isFinite(result.x) || !isFinite(result.y) || !isFinite(result.width) || !isFinite(result.height))
               throw new Error("Non-finite backdrop bounds");
            return result;
         }
         catch(error:Error)
         {
            ++this.sceneBackdropFallbacks;
            // Unknown artwork must stay visible; pay its old cost conservatively.
            return new Rectangle(-this.sceneGutter,-this.sceneGutter,
               this.loc.limX + this.sceneGutter * 2,this.loc.limY + this.sceneGutter * 2);
         }
      }

      private function sceneBackdropArtBounds(art:flash.display.DisplayObject) : Rectangle
      {
         var bounds:Rectangle = art.getBounds(art);
         var container:flash.display.DisplayObjectContainer = art as flash.display.DisplayObjectContainer;
         if(container != null)
            for(var index:int = 0; index < container.numChildren; ++index)
            {
               var child:flash.display.DisplayObject = container.getChildAt(index);
               var childBounds:Rectangle = this.sceneBackdropArtBounds(child);
               if(childBounds.isEmpty()) continue;
               childBounds = this.sceneBackdropTransformBounds(childBounds,child.transform.matrix);
               bounds = bounds.isEmpty() ? childBounds : bounds.union(childBounds);
            }
         if(!bounds.isEmpty())
            for each(var filter:flash.filters.BitmapFilter in art.filters)
               bounds = bounds.union(this.frontBmp.generateFilterRect(bounds,filter));
         return bounds;
      }

      private function sceneBackdropTransformBounds(bounds:Rectangle, transform:Matrix) : Rectangle
      {
         var a:Point = transform.transformPoint(new Point(bounds.left,bounds.top));
         var b:Point = transform.transformPoint(new Point(bounds.right,bounds.top));
         var c:Point = transform.transformPoint(new Point(bounds.left,bounds.bottom));
         var d:Point = transform.transformPoint(new Point(bounds.right,bounds.bottom));
         var left:Number = Math.min(a.x,b.x,c.x,d.x);
         var top:Number = Math.min(a.y,b.y,c.y,d.y);
         return new Rectangle(left,top,Math.max(a.x,b.x,c.x,d.x)-left,Math.max(a.y,b.y,c.y,d.y)-top);
      }

"""


def apply_grafon(source: str) -> str:
    source = _once(source, "      private function sceneOpen(value:Location) : void",
                   _HELPERS + "      private function sceneOpen(value:Location) : void")
    source = _once(source,
                   "         this.sceneChunks = {}; this.sceneResident = 0;",
                   "         this.sceneChunks = {}; this.sceneResident = 0;\n"
                   "         this.sceneBackdropLocation = null; this.sceneBackdropBuckets = {};\n"
                   "         this.sceneBackdropBounds = new Dictionary(true);\n"
                   "         this.sceneBackdropTotal = this.sceneBackdropReferences = this.sceneBackdropFallbacks = 0;")
    source = _once(source,
                   "         this.setLight();\n         var px:Number =",
                   "         this.setLight();\n         this.sceneIndexBackdrops();\n         var px:Number =")
    source = _once(source,
                   "for each(bo in this.loc.backobjs)",
                   "for each(bo in this.sceneBackdropObjects(this.sceneX,this.sceneY,this.rectX,this.rectY))")
    source = _once(source,
                   "bitmaps:bitmaps,sats:null,nativeBuffers:nativeBuffers,revision:0,",
                   "bitmaps:bitmaps,sats:null,nativeBuffers:nativeBuffers,revision:0,\n"
                   "            backobjs:this.sceneBackdropObjects(this.sceneX,this.sceneY,this.rectX,this.rectY),")
    return source
