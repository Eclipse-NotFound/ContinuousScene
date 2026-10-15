"""Bound large-scene impact work by the actual native decal artwork.

Applied after prepare.py's Grafon extension and native decal translation.  The
normal room path stays unchanged. Large scenes preserve the native world alpha
box instead of re-clamping that box at every chunk edge. Runtime mark
entry [3] is a transient Rectangle: ScenePersistence deliberately saves only
[kind, args, stamp], so older terrain saves need no migration.
"""


def _once(source: str, old: str, new: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"decal patch anchor expected once, found {count}: {old[:96]}")
    return source.replace(old, new)


_HELPERS = r"""      // Match the two native decal frame choices without consuming more RNG.
      // Include child filters before applying the native scale/rotation matrix.
      private function sceneDecalBounds(args:Array, stamp:Array) : Rectangle
      {
         var result:Rectangle = null;
         try
         {
            var transform:Matrix = new Matrix();
            if(Number(args[4]) != 1) transform.scale(Number(args[4]),Number(args[4]));
            if(Number(args[5]) != 0) transform.rotate(Number(args[5]));
            transform.tx = Number(args[2]); transform.ty = Number(args[3]);
            for(var index:int = 0; index < 2; ++index)
            {
               var factory:Class = args[index] as Class;
               if(factory == null) continue;
               var art:MovieClip = new factory();
               if(art.totalFrames > 1)
                  art.gotoAndStop(Math.floor(Number(stamp[index]) * art.totalFrames + 1));
               var local:Rectangle = this.sceneDecalArtBounds(art);
               if(!local.isEmpty())
               {
                  var bounds:Rectangle = this.sceneDecalTransformBounds(local,transform);
                  result = result == null ? bounds : result.union(bounds);
               }
               if(index == 1)
               {
                  // Native decal uses degrees for this measurement, although
                  // its draw Matrix.rotate uses radians. Preserve both rules.
                  art.scaleX = art.scaleY = Number(args[4]);
                  art.rotation = Number(args[5]);
                  var width:int = Math.round(art.width / 2 + 2) * 2;
                  var height:int = Math.round(art.height / 2 + 2) * 2;
                  var alpha:Rectangle = this.sceneDecalAlphaBounds(Number(args[2]),Number(args[3]),width,height);
                  result = result == null ? alpha : result.union(alpha);
               }
            }
            if(result == null) return new Rectangle();
            // Bitmap draw antialiasing and the native alpha-preservation rim.
            var padding:Number = 4 + Math.abs(Number(args[4])) * 2;
            result.inflate(padding,padding);
            if(!isFinite(result.x) || !isFinite(result.y) || !isFinite(result.width) || !isFinite(result.height))
               throw new Error("Non-finite decal bounds");
            return result;
         }
         catch(error:Error)
         {
            // Unknown artwork/filter bounds must never erase a large impact.
            // Render conservatively; the native decal retains its own behavior.
            return new Rectangle(-this.sceneGutter,-this.sceneGutter,
               this.loc.limX + this.sceneGutter * 2,this.loc.limY + this.sceneGutter * 2);
         }
      }

      private function sceneDecalAlphaBounds(x:Number, y:Number, width:int, height:int) : Rectangle
      {
         // Native destination Point truncates toward zero. Clamp in world
         // coordinates FIRST: clamping each chunk's local point moves the
         // opposite edge and wrongly preserves alpha outside the native box.
         return new Rectangle(int(Math.max(x - width / 2,0)),int(Math.max(y - height / 2,0)),width,height);
      }

      private function sceneDecalSourcePixel(value:Number) : int
      {
         // AIR copyChannel rounds source Rectangle endpoints to nearest-even,
         // unlike its truncating destination Point. Preserve the resulting
         // one-pixel source/destination offset at fractional world positions.
         var lower:Number = Math.floor(value);
         var fraction:Number = value - lower;
         return int(fraction < 0.5 ? lower : fraction > 0.5 ? lower + 1 : lower % 2 == 0 ? lower : lower + 1);
      }

      private function sceneDecalPaint(art:MovieClip, x:Number, y:Number, width:int, height:int, blend:String) : void
      {
         var destination:Rectangle = this.sceneDecalAlphaBounds(x,y,width,height);
         var dx:int = this.sceneDecalSourcePixel(Math.max(x - width / 2,0)) - destination.x;
         var dy:int = this.sceneDecalSourcePixel(Math.max(y - height / 2,0)) - destination.y;
         var area:Rectangle = destination.intersection(new Rectangle(this.sceneX,this.sceneY,this.frontBmp.width,this.frontBmp.height));
         area.offset(-this.sceneX,-this.sceneY);
         var alpha:BitmapData = null;
         try
         {
            if(!area.isEmpty())
            {
               alpha = new BitmapData(int(area.width),int(area.height),false,0);
               var sample:Rectangle = area.clone(); sample.offset(dx,dy);
               // The native cut has already run on this buffer. Never read a
               // neighbour: during replay it can be at a different mark. A
               // fractional sample beyond this buffer clips as native does;
               // only its outermost hidden gutter pixel can lack that source.
               alpha.copyChannel(this.frontBmp,sample,new Point(0,0),BitmapDataChannel.ALPHA,BitmapDataChannel.GREEN);
            }
            this.frontBmp.draw(art,this.m,blend == "normal" ? World.w.loc.cTransform : null,blend,null,true);
            if(alpha != null)
               this.frontBmp.copyChannel(alpha,alpha.rect,area.topLeft,BitmapDataChannel.GREEN,BitmapDataChannel.ALPHA);
         }
         finally
         {
            if(alpha != null) alpha.dispose();
         }
      }

      private function sceneDecalArtBounds(art:flash.display.DisplayObject) : Rectangle
      {
         var bounds:Rectangle = art.getBounds(art);
         var container:flash.display.DisplayObjectContainer = art as flash.display.DisplayObjectContainer;
         if(container != null)
         {
            for(var index:int = 0; index < container.numChildren; ++index)
            {
               var child:flash.display.DisplayObject = container.getChildAt(index);
               var childBounds:Rectangle = this.sceneDecalArtBounds(child);
               if(childBounds.isEmpty()) continue;
               childBounds = this.sceneDecalTransformBounds(childBounds,child.transform.matrix);
               bounds = bounds.isEmpty() ? childBounds : bounds.union(childBounds);
            }
         }
         if(!bounds.isEmpty())
            for each(var filter:flash.filters.BitmapFilter in art.filters)
               bounds = this.frontBmp.generateFilterRect(bounds,filter);
         return bounds;
      }

      private function sceneDecalTransformBounds(bounds:Rectangle, transform:Matrix) : Rectangle
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
    source = _once(source, "      private function sceneApply(kind:String, args:Array) : void",
                   _HELPERS + "      private function sceneApply(kind:String, args:Array) : void")
    source = _once(source,
                   '         var stamp:Array = kind == "decal" ? [Math.random(),Math.random()] : null;\n'
                   '         if(kind == "decal" || kind == "paint" || kind == "gwall") this.sceneMarks.push([kind,args,stamp]);',
                   '         this.sceneLastDirtyCount = 0;\n'
                   '         if(kind == "decal" && args[0] == null && args[1] == null) return;\n'
                   '         var stamp:Array = kind == "decal" ? [Math.random(),Math.random()] : null;')
    source = _once(source,
                   '         if(kind == "decal") affected = new Rectangle(Number(args[2])-512,Number(args[3])-512,1024,1024);',
                   '         if(kind == "decal") affected = this.sceneDecalBounds(args,stamp);')
    source = _once(source,
                   '         this.sceneLastDirtyCount = 0;\n         this.sceneRasterizing = true;',
                   '         if(kind == "decal" || kind == "paint" || kind == "gwall") this.sceneMarks.push([kind,args,stamp,affected]);\n'
                   '         this.sceneRasterizing = true;')
    source = _once(source,
                   '               this.sceneStamp = item[2];\n               var action:Function = this[item[0]]; action.apply(this,item[1]);',
                   '               this.sceneStamp = item[2];\n'
                   '               if(item[0] == "decal")\n'
                   '               {\n'
                   '                  // Old saves contain three values. Cache bounds only in memory.\n'
                   '                  if(item.length < 4 || !(item[3] is Rectangle)) item[3] = this.sceneDecalBounds(item[1],item[2]);\n'
                   '                  if(!Rectangle(item[3]).intersects(new Rectangle(this.sceneX,this.sceneY,this.rectX,this.rectY))) continue;\n'
                   '               }\n'
                   '               var action:Function = this[item[0]]; action.apply(this,item[1]);')
    # Dispatcher/replay now use exact artwork bounds. The old native-body center
    # test would silently discard oversized decals on distant affected chunks.
    source = _once(source,
                   '         if(this.sceneLarge && (param3 < -512 || param4 < -512 || param3 > this.rectX + 512 || param4 > this.rectY + 512)) return;\n',
                   '')
    # Keep the original small-room body intact. This branch runs after its cut,
    # frame selection, native width/height measurement and matrix setup. It
    # changes only how the alpha-preservation box maps onto a scene buffer.
    anchor = '            _loc11_ = Math.round(_loc9_.height / 2 + 2) * 2;\n'
    source = _once(source, anchor, anchor +
                   '            if(this.sceneLarge)\n'
                   '            {\n'
                   '               this.sceneDecalPaint(_loc9_,param3 + this.sceneX,param4 + this.sceneY,int(_loc10_),int(_loc11_),param7);\n'
                   '               return;\n'
                   '            }\n')
    return source
