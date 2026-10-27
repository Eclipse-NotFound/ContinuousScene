package {
   import flash.display.Bitmap;
   import flash.display.BitmapData;
   import flash.display.BitmapDataChannel;
   import flash.display.DisplayObject;
   import flash.display.DisplayObjectContainer;
   import flash.display.Sprite;
   import flash.display.Shape;
   import flash.geom.ColorTransform;
   import flash.geom.Matrix;
   import flash.geom.Point;
   import flash.geom.Rectangle;

   /** Display-only fog replacement at explored wall boundaries. Native alpha
    * separates rock from air. Constant wall brightness is optional; contour
    * correction is always active. Logic light and unit masks remain untouched. */
   public class SceneLegacyRVWallSurface {
      public var nativeTerrainSources:Function;
      public function diagnosticSources(front:DisplayObjectContainer):Array {left=0;top=0;return foregroundSources(front);}
      private static const CELL:int = 40;
      private static const STEP:int = 5;
      private static const BRIGHT:Number = 12;
      private static const DEPTH:Number = 32;
      private static const FRINGE:Number = 10;
      private var owner:*;
      private var bounds:Rectangle;
      // Keep the actual sampled values instead of allocating and joining three
      // string signatures every frame. Dirty flags survive a callback throwing
      // halfway through a scan; partial cache writes must never hide a change.
      private var shapeDirty:Boolean = true;
      private var terrainDirty:Boolean = true;
      private var fieldShapeDirty:Boolean = true;
      private var lightDirty:Boolean = true;
      private var previousBright:Boolean;
      private var contourGeometryVersion:uint = 0;
      private var seen:Vector.<int> = new Vector.<int>();
      private var lights:Vector.<Number> = new Vector.<Number>();
      private var faces:Array = [];
      private var heights:Vector.<int>;
      private var cols:int;
      private var rows:int;
      private var left:int;
      private var top:int;
      private var field:BitmapData;
      private var floorField:BitmapData;
      private var wallField:BitmapData;
      private var fieldStamp:BitmapData;
      // Faces always lie on the 5px sampling grid. The same two kernels
      // are reused at every face, preserving the original rounding exactly.
      private var kernelOffsets:Array=[];
      private var kernelAlphas:Array=[];
      private var sampleStarts:Vector.<int>;
      private var samplePixels:Vector.<int>;
      private var sampleAlphas:Vector.<int>;
      private var sampleCells:Vector.<int>;
      private var floorValues:Vector.<uint>;
      private var baseLight:BitmapData;
      private var wallPixels:Sprite = new Sprite();
      private var baseOwner:Sprite;
      private var baseClip:Shape = new Shape();
      private var alphaMap:Array=[];
      private var zeroMap:Array=[];
      private var origin:Point = new Point();
      private var support:Array=[];
      private var supportComplement:Array=[];
      private var pieces:Array=[];
      private var terrainUpdates:int = 0;
      private var fieldUpdates:int = 0;
      private var wallFieldUpdates:int = 0;
      private var mode:int = -1;
      private var contourDirty:Boolean = true;
      private var contourPieces:Array = [];
      private var contourLayoutDirty:Boolean = true;
      private var contourFog:BitmapData;
      private var contourBitmap:Bitmap;
      private var airClip:Shape = new Shape();
      private var solidClip:Shape = new Shape();
      private var onClip:Shape = new Shape();
      private var airPixels:Sprite = new Sprite();
      private var contourUpdates:int = 0;
      private var contourSourceLayout:Array;
      private var contourSourceVersion:int=0;

      public function SceneLegacyRVWallSurface() {
         wallPixels.mouseEnabled=wallPixels.mouseChildren=false;
         for each(var sign:int in [1,-1]){
            var offsets:Vector.<int>=new Vector.<int>(),alphas:Vector.<int>=new Vector.<int>();
            var low:int=Math.floor(-(sign>0?FRINGE:DEPTH)/STEP),high:int=Math.ceil((sign>0?DEPTH:FRINGE)/STEP);
            for(var q:int=low;q<high;q++){
               var distance:Number=(q+0.5)*STEP*sign;
               if(distance < -FRINGE || distance>=DEPTH)continue;
               var alpha:int=distance<=BRIGHT?255:Math.round(255*(DEPTH-distance)/(DEPTH-BRIGHT));
               if(distance<0)alpha=Math.round(alpha*Math.min(1,(distance+FRINGE)/STEP));
               offsets.push(q);alphas.push(alpha);
            }
            kernelOffsets.push(offsets);kernelAlphas.push(alphas);
         }
         for(var i:int=0;i<256;i++){alphaMap[i]=uint(255-i)<<24;zeroMap[i]=0;}
      }

      public function update(parent:Sprite, base:Sprite, grafon:*, loc:*, view:Rectangle,
                             known:Function, light:Function, alwaysBright:Boolean):void {
         var requested:int=alwaysBright?1:0;
         if(mode!=requested){this.reset();mode=requested;}
         if(baseOwner!==base) {
            if(baseOwner!=null && (baseOwner.mask===baseClip||baseOwner.mask===onClip))baseOwner.mask=null;
            baseOwner=base;
         }
         var front:DisplayObjectContainer = null;
         try { front = grafon.visFront as DisplayObjectContainer; } catch(e:Error) {}
         if(front == null || !front.visible || view.width <= 0 || view.height <= 0) {
            wallPixels.visible=airPixels.visible=false;base.mask=null;
            if(baseClip.parent)baseClip.parent.removeChild(baseClip);
            if(onClip.parent)onClip.parent.removeChild(onClip);
            return;
         }
         if(wallPixels.parent != parent) parent.addChild(wallPixels);
         if(baseClip.parent != parent)parent.addChild(baseClip);
         parent.setChildIndex(wallPixels,parent.numChildren-1);
         wallPixels.visible = true;
         var oldHeights:Vector.<int>=heights;
         var oldLeft:int=left,oldTop:int=top,oldCols:int=cols,oldRows:int=rows;
         var terrainChanged:Boolean=terrainDirty || owner!==loc || (alwaysBright && bounds!=null && !bounds.equals(view));
         terrainDirty=terrainChanged;
         var reset:Boolean = owner !== loc || bounds == null || !bounds.equals(view);
         if(reset) {
            owner=loc; bounds=view.clone(); shapeDirty=fieldShapeDirty=lightDirty=true;
            left=int(view.x); top=int(view.y); cols=int(view.width); rows=int(view.height);
            if(field == null || field.width!=cols*CELL/STEP || field.height!=rows*CELL/STEP) {
               if(field != null) field.dispose();
               field=new BitmapData(cols*CELL/STEP,rows*CELL/STEP,true,0);
               if(floorField!=null){floorField.dispose();wallField.dispose();fieldStamp.dispose();}
               floorField=new BitmapData(field.width,field.height,false,0);
               wallField=new BitmapData(field.width,field.height,false,0);
               fieldStamp=new BitmapData(field.width,field.height,false,0);
            }
            if(alwaysBright && (baseLight==null || baseLight.width!=cols*CELL || baseLight.height!=rows*CELL)){
               if(baseLight!=null)baseLight.dispose();
               baseLight=new BitmapData(cols*CELL,rows*CELL,false,0xffffff);
            }
            wallPixels.x=left*CELL; wallPixels.y=top*CELL;
            heights=new Vector.<int>((cols+2)*(rows+2),true);
            // Keep patches in the same world location when the viewport origin
            // changes. Cached runs are local coordinates, so translate those too.
            var dx:int=(oldLeft-left)*CELL,dy:int=(oldTop-top)*CELL;
            if(!terrainChanged && (dx!=0 || dy!=0))for each(var movedPatch:Object in contourPieces){
               movedPatch.rect.offset(dx,dy);
               var movedRuns:Vector.<int>=movedPatch.runs as Vector.<int>;
               if(movedRuns!=null)for(var ri:int=0;ri<movedRuns.length;ri+=5){movedRuns[ri]+=dx;movedRuns[ri+1]+=dy;}
            }
            contourDirty=contourLayoutDirty=true;
         }
         // One-cell halo distinguishes exterior faces from joins, including two
         // touching half-height tiles. Geometry is checked even when FOV is static.
         var index:int=0;
         for(var y:int=top-1;y<=top+rows;y++) for(var x:int=left-1;x<=left+cols;x++) {
            var h:int=heightAt(loc,x,y);
            if(reset){
               if(oldHeights!=null && x>=oldLeft-1 && x<=oldLeft+oldCols && y>=oldTop-1 && y<=oldTop+oldRows
                  && oldHeights[x-oldLeft+1+(y-oldTop+1)*(oldCols+2)]!=h)terrainDirty=terrainChanged=true;
            }else if(heights[index]!=h)terrainDirty=terrainChanged=true;
            if(heights[index]!=h){shapeDirty=true;heights[index]=h;}
            index++;
         }
         if(shapeDirty) {
            if(terrainChanged)contourGeometryVersion++;
            // Drop obsolete runs before rebuilding geometry. Packed integers
            // avoid keeping thousands of rectangle objects alive in the cache.
            if(terrainChanged)for each(var stalePatch:Object in contourPieces)stalePatch.runs=null;
            fieldShapeDirty=true;
            rebuildFaces(loc);
            rebuildSamples();
            seen.length=lights.length=faces.length/5;
            shapeDirty=terrainDirty=false;
         }
         if(previousBright!=alwaysBright){lightDirty=true;previousBright=alwaysBright;}
         var count:int=0;
         for(var i:int=0;i<faces.length;i+=5) {
            var isKnown:int=known(faces[i+3],faces[i+4])?1:0;
            index=i/5;
            if(seen[index]!=isKnown){fieldShapeDirty=true;seen[index]=isKnown;}
            count+=isKnown;
            var value:Number=isKnown?Math.round(255*Math.max(0,Math.min(1,
               light(faces[i+3],faces[i+4],faces[i],faces[i+1],faces[i+2])))):0;
            var previous:Number=lights[index];
            // The former string signature treated NaN as equal to NaN.
            if(value!=previous && !(value!=value && previous!=previous)){
               lightDirty=true;lights[index]=value;
            }
         }
         var fieldChanged:Boolean=fieldShapeDirty;
         if(fieldChanged || lightDirty){
            // Bulk bitmap upload preserves the old integer max/rounding rules.
            // Geometry is stable across lighting changes; retain face samples.
            var n:int=field.width*field.height;
            // Clear only previously sampled cells; do not allocate a full
            // lighting vector on every changing frame.
            for(var c:int=0;c<sampleCells.length;c++)floorValues[sampleCells[c]]=0;
            var shapeValues:Vector.<uint>=fieldChanged?new Vector.<uint>(n,true):null;
            var wallValues:Vector.<uint>=fieldChanged&&alwaysBright?new Vector.<uint>(n,true):null;
            for(i=0;i<seen.length;i++)if(seen[i]){
               var intensity:int=lights[i];
               for(var q:int=sampleStarts[i];q<sampleStarts[i+1];q++){
                  var pixel:int=samplePixels[q],alpha:int=sampleAlphas[q];
                  var value8:int=Math.round(alpha*intensity/255);
                  if(value8>(floorValues[pixel]&255))floorValues[pixel]=uint(0xff000000)|uint(value8*0x010101);
                  if(fieldChanged && alpha>int(shapeValues[pixel]>>>24)){
                     shapeValues[pixel]=uint(alpha)<<24;
                     if(alwaysBright)wallValues[pixel]=uint(0xff000000)|uint(alpha*0x010101);
                  }
               }
            }
            floorField.setVector(floorField.rect,floorValues);
            if(fieldChanged){
               field.setVector(field.rect,shapeValues);
               if(alwaysBright)wallField.setVector(wallField.rect,wallValues);
               wallFieldUpdates++;
            }
            if(!alwaysBright)wallField.copyPixels(floorField,floorField.rect,origin);
            fieldUpdates++;
            fieldStamp.copyChannel(floorField,floorField.rect,origin,BitmapDataChannel.RED,BitmapDataChannel.RED);
            fieldStamp.copyChannel(wallField,wallField.rect,origin,BitmapDataChannel.GREEN,BitmapDataChannel.GREEN);
            if(fieldChanged){rebuildSupport();contourDirty=contourLayoutDirty=true;if(alwaysBright){rebuildPieces();rebuildClip(loc);}}
            fieldShapeDirty=lightDirty=false;
         }
         wallPixels.visible=count>0;
         airPixels.visible=wallPixels.visible;
         if(!wallPixels.visible){base.mask=null;if(baseClip.parent)baseClip.parent.removeChild(baseClip);if(onClip.parent)onClip.parent.removeChild(onClip);return;}
         if(!alwaysBright){updateContour(parent,base,front,loc,false);return;}
         var sources:Array=alwaysBright?foregroundSources(front):null,updated:Boolean=false;
         // Rasterize the unmodified fog once per update. Drawing it separately
         // for each small rectangle repeats the nested masks and blur work.
         base.mask=null;
         try {
         baseLight.fillRect(baseLight.rect,0xffffff);
         baseLight.draw(base,new Matrix(1,0,0,1,-left*CELL,-top*CELL),null,null,null,true);
         for each(var piece:Object in pieces){
            var scratch:BitmapData=piece.next,terrain:BitmapData=piece.previous;
            var pixelsChanged:Boolean=false;
            if(alwaysBright){
            scratch.fillRect(scratch.rect,0);
            if(sources!=null)copyForeground(sources,piece.rect,scratch);
            else {
               var matrix:Matrix=front.transform.matrix;
               matrix.tx-=left*CELL+piece.rect.x;matrix.ty-=top*CELL+piece.rect.y;
               scratch.draw(front,matrix,front.transform.colorTransform,null,scratch.rect,true);
            }
            var delta:Object=scratch.compare(terrain);
            pixelsChanged=!(delta is uint && uint(delta)==0);
            if(delta is BitmapData)BitmapData(delta).dispose();
            if(pixelsChanged){piece.previous=scratch;piece.next=terrain;updated=true;}
            }
            var shadeChanged:Boolean=false;
            if(piece.version!=fieldUpdates){
               piece.nextStamp.copyPixels(fieldStamp,piece.stampRect,origin);
               delta=piece.nextStamp.compare(piece.stamp);
               shadeChanged=!(delta is uint && uint(delta)==0);
               if(delta is BitmapData)BitmapData(delta).dispose();
               if(shadeChanged){var swap:BitmapData=piece.stamp;piece.stamp=piece.nextStamp;piece.nextStamp=swap;}
               piece.version=fieldUpdates;
            }
            // Local fields include a one-sample halo for bilinear filtering.
            // Unchanged wall patches reuse their target shading while the
            // original moving fog is still sampled every frame below.
            if(shadeChanged || pixelsChanged){
            var scale:Matrix=new Matrix(STEP,0,0,STEP,-piece.rect.x,-piece.rect.y);
            piece.floor.fillRect(piece.floor.rect,0);
            piece.floor.draw(floorField,scale,null,null,null,true);
            if(alwaysBright){
            if(pixelsChanged || piece.wallVersion!=wallFieldUpdates){
            piece.wall.fillRect(piece.wall.rect,0);
            piece.wall.draw(wallField,scale,null,null,null,true);
            piece.wall.copyChannel(piece.previous,piece.previous.rect,origin,BitmapDataChannel.ALPHA,BitmapDataChannel.ALPHA);
            piece.wallVersion=wallFieldUpdates;
            }
            // Grayscale stores brightness: native alpha linearly selects rock
            // or air, including semitransparent and overlapping foregrounds.
            piece.floor.draw(piece.wall);
            }
            }
            piece.nextBase.copyPixels(baseLight,piece.rect,origin);
            delta=piece.nextBase.compare(piece.base);
            var baseChanged:Boolean=!(delta is uint && uint(delta)==0);
            if(delta is BitmapData)BitmapData(delta).dispose();
            if(baseChanged){swap=piece.base;piece.base=piece.nextBase;piece.nextBase=swap;}
            if(!piece.outputValid || baseChanged || shadeChanged || pixelsChanged){
               piece.light.copyPixels(piece.base,piece.base.rect,origin);
               piece.light.draw(piece.floor,null,null,"lighten");
               piece.output.paletteMap(piece.light,piece.light.rect,origin,alphaMap,zeroMap,zeroMap,zeroMap);
               piece.outputValid=true;
            }
         }} finally {base.mask=baseClip;}
         if(updated)terrainUpdates++;
         updateContour(parent,base,front,loc,true);
      }

      private function heightAt(loc:*,x:int,y:int):int {
         if(x<0 || y<0 || x>=loc.spaceX || y>=loc.spaceY)return CELL;
         var t:*=loc.getTile(x,y);
         if(t.opac<1)return 0;
         var cut:int=0;
         if("zForm" in t)cut=int(t.zForm)*10;
         return Math.max(0,CELL-cut);
      }

      public function reset():void {
         if(baseOwner!=null && (baseOwner.mask===baseClip||baseOwner.mask===onClip))baseOwner.mask=null;baseOwner=null;
         if(baseClip.parent)baseClip.parent.removeChild(baseClip);baseClip.graphics.clear();
         if(wallPixels.parent)wallPixels.parent.removeChild(wallPixels);
         if(field!=null)field.dispose();field=null;
         if(baseLight!=null)baseLight.dispose();baseLight=null;
         if(floorField!=null){floorField.dispose();wallField.dispose();fieldStamp.dispose();}floorField=wallField=fieldStamp=null;
         for each(var piece:Object in pieces)disposePiece(piece);pieces=[];
         owner=null;bounds=null;terrainDirty=shapeDirty=fieldShapeDirty=lightDirty=true;
         faces=[];support=[];supportComplement=[];heights=null;seen.length=lights.length=0;
         sampleStarts=null;samplePixels=null;sampleAlphas=null;sampleCells=null;floorValues=null;
         if(airClip.parent)airClip.parent.removeChild(airClip);airClip.graphics.clear();wallPixels.mask=null;
         if(solidClip.parent)solidClip.parent.removeChild(solidClip);solidClip.graphics.clear();
         if(onClip.parent)onClip.parent.removeChild(onClip);onClip.graphics.clear();
         if(airPixels.parent)airPixels.parent.removeChild(airPixels);airPixels.mask=null;
         if(contourBitmap!=null){if(contourBitmap.parent)contourBitmap.parent.removeChild(contourBitmap);contourBitmap.bitmapData=null;contourBitmap=null;}
         for each(var patch:Object in contourPieces){patch.alpha.dispose();patch.next.dispose();patch.scratch.dispose();patch.pixels.dispose();}contourPieces=[];
         if(contourFog!=null)contourFog.dispose();contourFog=null;
         contourDirty=contourLayoutDirty=true;mode=-1;contourSourceLayout=null;contourSourceVersion++;
      }

      /** Default path leaves the original smooth wall field untouched on ALL
       * material pixels (including antialiased pixels). Only actual empty
       * cutouts inside collision cells receive the open-side fog. No screenshot
       * of the dynamic fog, full-resolution shading or pixelwise light merge. */
      private function updateContour(parent:Sprite,base:Sprite,front:DisplayObjectContainer,loc:*,bright:Boolean):void {
         if(contourFog==null||contourFog.width!=field.width||contourFog.height!=field.height){
            if(contourFog!=null)contourFog.dispose();contourFog=new BitmapData(field.width,field.height,true,0xff000000);
            if(contourBitmap==null){contourBitmap=new Bitmap(null,"auto",true);airPixels.addChild(contourBitmap);}
            contourBitmap.bitmapData=contourFog;contourBitmap.scaleX=contourBitmap.scaleY=STEP;
            contourDirty=true;
         }
         if(contourLayoutDirty){
            var old:Object={};
            for each(var patch:Object in contourPieces)old[patch.rect.toString()]=patch;
            contourPieces=[];
            for each(var area:Rectangle in support){
               var key:String=area.toString();patch=old[key];
               if(patch!=null)delete old[key];
               else patch={rect:area,alpha:new BitmapData(area.width,area.height,true,0),next:new BitmapData(area.width,area.height,true,0),scratch:new BitmapData(area.width,area.height,true,0),pixels:new BitmapData(area.width,area.height,true,0)};
               contourPieces.push(patch);
            }
            for each(patch in old){patch.alpha.dispose();patch.next.dispose();patch.scratch.dispose();patch.pixels.dispose();}
            contourLayoutDirty=false;
         }
         var sources:Array=foregroundSources(front);
         var sameSources:Boolean=sources!=null && contourSourceLayout!=null && sources.length==contourSourceLayout.length;
         if(sameSources)for(var si:int=0;si<sources.length;si++){
            var oldSource:Object=contourSourceLayout[si],newSource:Object=sources[si];
            if(oldSource.data!==newSource.data || oldSource.x!=newSource.x || oldSource.y!=newSource.y || !Rectangle(oldSource.rect).equals(newSource.rect)){sameSources=false;break;}
         }
         if(!sameSources){contourSourceVersion++;contourSourceLayout=sources;}
         for each(patch in contourPieces){
         var contourScratch:BitmapData=patch.scratch;
         if(sources!=null){
            if(patch.copyVersion!==contourSourceVersion){
               var plan:Array=[];
               for each(var source:Object in sources){
                  var region:Rectangle=patch.rect.intersection(source.rect);if(region.isEmpty())continue;
                  var dest:Point=new Point(region.x-patch.rect.x,region.y-patch.rect.y);region.offset(-source.x,-source.y);
                  plan.push({data:source.data,region:region,dest:dest});
               }
               patch.copyPlan=plan;patch.copyVersion=contourSourceVersion;
            }
            plan=patch.copyPlan;
            var full:Boolean=plan.length==1 && plan[0].dest.x==0 && plan[0].dest.y==0 && plan[0].region.width==contourScratch.width && plan[0].region.height==contourScratch.height;
            if(!full)contourScratch.fillRect(contourScratch.rect,0);
            for each(var command:Object in plan)contourScratch.copyPixels(command.data,command.region,command.dest,null,null,!full);
         }else{
            contourScratch.fillRect(contourScratch.rect,0);
            var m:Matrix=front.transform.matrix;m.tx-=left*CELL+patch.rect.x;m.ty-=top*CELL+patch.rect.y;
            contourScratch.draw(front,m,front.transform.colorTransform,null,null,true);
         }
         var delta:Object=contourScratch.compare(patch.pixels);
         if(delta is uint&&uint(delta)==0)continue;
         if(delta is BitmapData)BitmapData(delta).dispose();
         var swap:BitmapData=patch.pixels;patch.pixels=contourScratch;patch.scratch=swap;
         var nextAlpha:BitmapData=patch.next;
         nextAlpha.copyChannel(patch.pixels,patch.pixels.rect,origin,BitmapDataChannel.ALPHA,BitmapDataChannel.ALPHA);
         delta=nextAlpha.compare(patch.alpha);
         if(!(delta is uint&&uint(delta)==0)){
            swap=patch.alpha;patch.alpha=nextAlpha;patch.next=swap;contourDirty=true;patch.runs=null;
            if(delta is BitmapData)BitmapData(delta).dispose();
         }
         }
         if(contourDirty){buildContourClip(loc);contourDirty=false;contourUpdates++;}
         contourFog.paletteMap(floorField,floorField.rect,origin,alphaMap,zeroMap,zeroMap,zeroMap);
         if(airPixels.parent!=parent)parent.addChild(airPixels);
         airPixels.x=left*CELL;airPixels.y=top*CELL;
         if(airClip.parent!=parent)parent.addChild(airClip);
         airPixels.mask=airClip;
         if(bright){
            if(onClip.parent!=parent)parent.addChild(onClip);
            if(solidClip.parent!=parent)parent.addChild(solidClip);
            wallPixels.mask=solidClip;base.mask=onClip;
            if(baseClip.parent)baseClip.parent.removeChild(baseClip);
         }else base.mask=baseClip;
      }

      private function buildContourClip(loc:*):void {
         rebuildClip(loc); // Positive complement of support patches, never holes.
         onClip.graphics.copyFrom(baseClip.graphics);
         baseClip.graphics.beginFill(0xffffff);onClip.graphics.beginFill(0xffffff);
         airClip.graphics.clear();airClip.graphics.beginFill(0xffffff);
         solidClip.graphics.clear();solidClip.graphics.beginFill(0xffffff);
         for each(var patch:Object in contourPieces){
            var area:Rectangle=patch.rect;
            // A patch's material alpha and tile heights fully determine its
            // contour. Exploration can change the surrounding support without
            // changing this patch; keep exactly the same maximal row runs.
            var rectangles:Vector.<int>=patch.runs as Vector.<int>;
            var rectangleIndex:int;
            if(rectangles==null || patch.geometryVersion!=contourGeometryVersion){
               rectangles=new Vector.<int>();
               var pixels:Vector.<uint>=patch.alpha.getVector(patch.alpha.rect);
               var w:int=patch.alpha.width, ax:int=area.x, right:int=area.right;
               var previous:Object={},row:int=0;
               for(var y:int=area.top;y<area.bottom;y++,row+=w){
                  var current:Object={},start:int=ax,x:int=ax,role:int=-1;
                  var tileEnd:int=ax,tileRole:int=2;
                  var tileRow:int=(int(y/CELL)+1)*(cols+2),subY:int=y%CELL;
                  for(var offset:int=0;x<right;x++,offset++){
                     if(x>=tileEnd){
                        var tileX:int=int(x/CELL);
                        tileEnd=(tileX+1)*CELL;
                        var h:int=heights[tileX+1+tileRow];
                        tileRole=h>0 && subY>=CELL-h?0:2;
                     }
                     var nextRole:int=(pixels[row+offset]>>>24)>0?1:tileRole;
                     if(nextRole!=role){
                        if(role>=0){
                           var key:String=start+":"+x+":"+role;
                           rectangleIndex=int(previous[key])-1;
                           if(rectangleIndex>=0)rectangles[rectangleIndex+3]++;
                           else{rectangleIndex=rectangles.length;rectangles.push(start,y,x-start,1,role);}
                           current[key]=rectangleIndex+1;
                        }
                        start=x;role=nextRole;
                     }
                  }
                  key=start+":"+x+":"+role;rectangleIndex=int(previous[key])-1;
                  if(rectangleIndex>=0)rectangles[rectangleIndex+3]++;
                  else{rectangleIndex=rectangles.length;rectangles.push(start,y,x-start,1,role);}
                  current[key]=rectangleIndex+1;
                  previous=current;
               }
               patch.runs=rectangles;patch.geometryVersion=contourGeometryVersion;
            }
            for(rectangleIndex=0;rectangleIndex<rectangles.length;rectangleIndex+=5){
               role=rectangles[rectangleIndex+4];
               var shape:Shape=role==0?airClip:baseClip;
               var drawX:int=left*CELL+rectangles[rectangleIndex],drawY:int=top*CELL+rectangles[rectangleIndex+1];
               var drawWidth:int=rectangles[rectangleIndex+2],drawHeight:int=rectangles[rectangleIndex+3];
               shape.graphics.drawRect(drawX,drawY,drawWidth,drawHeight);
               if(role!=0){shape=role==1?solidClip:onClip;shape.graphics.drawRect(drawX,drawY,drawWidth,drawHeight);}
            }
         }
         baseClip.graphics.endFill();airClip.graphics.endFill();solidClip.graphics.endFill();onClip.graphics.endFill();
      }

      private function contourRole(pixels:Vector.<uint>,x:int,y:int,area:Rectangle,w:int):int {
         // No brightness threshold: dark texture is still solid material.
         // Retaining nonzero alpha also avoids puncturing antialiased rock edges.
         if((pixels[x-area.x+(y-area.y)*w]>>>24)>0)return 1;
         // A partial tile can still be opaque (e.g. native C;F decoding).
         // Its cut-away top is open space, not a material notch. The contour
         // field's zero-valued filter halo must not replace that original fog.
         var h:int=heights[int(x/CELL)+1+(int(y/CELL)+1)*(cols+2)];
         return h>0 && y%CELL>=CELL-h?0:2;
      }

      private function rebuildClip(loc:*,target:Shape=null):void {
         var clip:Shape=target==null?baseClip:target;
         clip.graphics.clear();clip.graphics.beginFill(0xffffff);
         // Flash's vector mask stencil can fill even-odd holes. Emit only the
         // positive complement rectangles, so drawing and masking agree.
         var ox:int=left*CELL,oy:int=top*CELL,w:int=cols*CELL,h:int=rows*CELL;
         clip.graphics.drawRect(-80,-80,loc.spaceX*CELL+160,oy+80);
         clip.graphics.drawRect(-80,oy+h,loc.spaceX*CELL+160,loc.spaceY*CELL+80-oy-h);
         clip.graphics.drawRect(-80,oy,ox+80,h);
         clip.graphics.drawRect(ox+w,oy,loc.spaceX*CELL+80-ox-w,h);
         for each(var rect:Rectangle in supportComplement)
            clip.graphics.drawRect(ox+rect.x,oy+rect.y,rect.width,rect.height);
         clip.graphics.endFill();
      }

      private function rebuildPieces():void {
         var old:Object={};
         for each(var piece:Object in pieces)old[piece.rect.toString()]=piece;
         pieces=[];
         for each(var rect:Rectangle in support){
            var key:String=rect.toString();piece=old[key];
            if(piece!=null)delete old[key];
            else {
               var stampRect:Rectangle=new Rectangle(rect.x/STEP-1,rect.y/STEP-1,rect.width/STEP+2,rect.height/STEP+2).intersection(field.rect);
               piece={rect:rect,previous:new BitmapData(rect.width,rect.height,true,0),
                  next:new BitmapData(rect.width,rect.height,true,0),output:new BitmapData(rect.width,rect.height,true,0),
                  floor:new BitmapData(rect.width,rect.height,false,0),wall:new BitmapData(rect.width,rect.height,true,0),
                  light:new BitmapData(rect.width,rect.height,false,0xffffff),version:-1,wallVersion:-1,stampRect:stampRect,
                  base:new BitmapData(rect.width,rect.height,false,0),nextBase:new BitmapData(rect.width,rect.height,false,0),outputValid:false,
                  stamp:new BitmapData(stampRect.width,stampRect.height,false,0),nextStamp:new BitmapData(stampRect.width,stampRect.height,false,0)};
               piece.display=new Bitmap(piece.output,"auto",true);piece.display.x=rect.x;piece.display.y=rect.y;
               wallPixels.addChild(piece.display);
            }pieces.push(piece);
         }
         for each(piece in old)disposePiece(piece);
      }

      private function disposePiece(piece:Object):void {
         if(piece.display.parent)piece.display.parent.removeChild(piece.display);
         piece.display.bitmapData=null;piece.previous.dispose();piece.next.dispose();piece.output.dispose();
         piece.floor.dispose();piece.wall.dispose();piece.light.dispose();
         piece.base.dispose();piece.nextBase.dispose();
         piece.stamp.dispose();piece.nextStamp.dispose();
      }

      /** Disjoint pixel rectangles around the nonzero field, with a 5px halo
       * for bilinear filtering. Avoid copying all the empty space between walls. */
      private function rebuildSupport():void {
         support=[];supportComplement=[];
         var width:int=field.width,height:int=field.height;
         var pixels:Vector.<uint>=field.getVector(field.rect);
         var active:Vector.<int>=new Vector.<int>(width*height,true);
         // Dilate contiguous source runs by the same one-sample square halo.
         for(var y:int=0;y<height;y++){
            var x:int=0,row:int=y*width;
            while(x<width){
               if(!(pixels[row+x]>>>24)){x++;continue;}
               var begin:int=x;while(x<width && pixels[row+x]>>>24)x++;
               var lo:int=Math.max(0,begin-1),hi:int=Math.min(width,x+1);
               for(var yy:int=Math.max(0,y-1);yy<=Math.min(height-1,y+1);yy++)
                  for(var xx:int=lo,base:int=yy*width;xx<hi;xx++)active[base+xx]=1;
            }
         }
         // Emit the same maximal support rectangles and their positive
         // complement in one pass. Both masks share this geometry.
         var previous:Object={},outsidePrevious:Object={};
         for(y=0;y<height;y++){
            var current:Object={},outsideCurrent:Object={};x=0;row=y*width;
            while(x<width){
               var inside:int=active[row+x];begin=x;
               while(x<width && active[row+x]==inside)x++;
               var key:String=begin+":"+x;
               var prior:Object=inside?previous:outsidePrevious;
               var next:Object=inside?current:outsideCurrent;
               var list:Array=inside?support:supportComplement;
               var rect:Rectangle=prior[key] as Rectangle;
               if(rect!=null)rect.height+=STEP;
               else{rect=new Rectangle(begin*STEP,y*STEP,(x-begin)*STEP,STEP);list.push(rect);}
               next[key]=rect;
            }
            previous=current;outsidePrevious=outsideCurrent;
         }
      }

      private function plain(node:DisplayObject):Boolean {
         var matrix:Matrix=node.transform.matrix;
         var color:*=node.transform.colorTransform;
         return matrix.a==1&&matrix.b==0&&matrix.c==0&&matrix.d==1&&matrix.tx==int(matrix.tx)&&matrix.ty==int(matrix.ty)
            &&node.alpha==1&&node.blendMode=="normal"&&node.mask==null&&node.filters.length==0
            &&color.redMultiplier==1&&color.greenMultiplier==1&&color.blueMultiplier==1&&color.alphaMultiplier==1
            &&color.redOffset==0&&color.greenOffset==0&&color.blueOffset==0&&color.alphaOffset==0;
      }

      /** Native and chunked foregrounds are untranslated pixels inside translated
       * Bitmap children. copyPixels keeps alpha exact and is much cheaper than
       * rerendering a masked display tree. Unusual transforms use the safe draw path. */
      private function foregroundSources(front:DisplayObjectContainer):Array {
         if(!plain(front)||front.scrollRect!=null)return null;
         var node:DisplayObject,bmp:Bitmap,i:int;
         for(i=0;i<front.numChildren;i++){
            node=front.getChildAt(i);
            if(node.visible&&(!(node is Bitmap)||!plain(node)))return null;
         }
         var sources:Array=[];
         for(i=0;i<front.numChildren;i++){
            bmp=front.getChildAt(i) as Bitmap;
            if(bmp==null||!bmp.visible||bmp.bitmapData==null)continue;
            var scroll:Rectangle=bmp.scrollRect;
            var clip:Rectangle=scroll==null?bmp.bitmapData.rect:scroll.intersection(bmp.bitmapData.rect);
            var ox:int=front.x+bmp.x-left*CELL-(scroll==null?0:scroll.x);
            var oy:int=front.y+bmp.y-top*CELL-(scroll==null?0:scroll.y);
            var local:Rectangle=new Rectangle(clip.x+ox,clip.y+oy,clip.width,clip.height);
            sources.push({data:bmp.bitmapData,rect:local,x:ox,y:oy});
         }return sources;
      }

      private function copyForeground(sources:Array,area:Rectangle,target:BitmapData):void {
         for each(var source:Object in sources){
            var region:Rectangle=area.intersection(source.rect);if(region.isEmpty())continue;
            var dest:Point=new Point(region.x-area.x,region.y-area.y);region.offset(-source.x,-source.y);
            target.copyPixels(source.data,region,dest,null,null,true);
         }
      }

      private function occupied(wx:Number,wy:Number):Boolean {
         var x:int=Math.floor(wx/CELL),y:int=Math.floor(wy/CELL);
         var h:int=heights[x-left+1+(y-top+1)*(cols+2)];
         return h>0 && wy-y*CELL>=CELL-h;
      }

      private function rebuildFaces(loc:*):void {
         faces=[];
         for(var y:int=top;y<top+rows;y++) for(var x:int=left;x<left+cols;x++) {
            var h:int=heights[x-left+1+(y-top+1)*(cols+2)];
            if(h==0)continue;
            var x0:int=x*CELL,y0:int=(y+1)*CELL-h;
            for(var q:int=0;q<CELL;q+=STEP) {
               edge(x0+q+STEP/2,y0,0,x0+q+STEP/2,y0-0.5,loc);
               edge(x0+q+STEP/2,(y+1)*CELL,1,x0+q+STEP/2,(y+1)*CELL+0.5,loc);
            }
            for(q=0;q<h;q+=STEP) {
               edge(x0,y0+q+STEP/2,2,x0-0.5,y0+q+STEP/2,loc);
               edge(x0+CELL,y0+q+STEP/2,3,x0+CELL+0.5,y0+q+STEP/2,loc);
            }
         }
      }

      private function edge(x:Number,y:Number,dir:int,outX:Number,outY:Number,loc:*):void {
         if(outX<0 || outY<0 || outX>=loc.spaceX*CELL || outY>=loc.spaceY*CELL || occupied(outX,outY))return;
         faces.push(x,y,dir,int(outX/CELL),int(outY/CELL));
      }

      /** Frozen geometry for each exposed face; exploration and light are
       * still sampled every update. A rebuilt shape regenerates this table. */
      private function rebuildSamples():void {
         var faceCount:int=faces.length/5,capacity:int=faceCount*Vector.<int>(kernelOffsets[0]).length;
         sampleStarts=new Vector.<int>(faceCount+1);samplePixels=new Vector.<int>(capacity);sampleAlphas=new Vector.<int>(capacity);
         sampleCells=new Vector.<int>();floorValues=new Vector.<uint>(field.width*field.height,true);
         var registered:Vector.<Boolean>=new Vector.<Boolean>(floorValues.length,true);
         var write:int=0,width:int=field.width,height:int=field.height;
         for(var i:int=0;i<faces.length;i+=5){
            sampleStarts[int(i/5)]=write;
            var wx:Number=faces[i],wy:Number=faces[i+1],dir:int=faces[i+2];
            var vertical:Boolean=dir>=2,k:int=(dir==0||dir==2)?0:1;
            var offsets:Vector.<int>=kernelOffsets[k],alphas:Vector.<int>=kernelAlphas[k];
            var along:int=Math.floor(((vertical?wy:wx)-(vertical?top:left)*CELL)/STEP);
            var edge:int=((vertical?wx:wy)-(vertical?left:top)*CELL)/STEP;
            for(var q:int=0;q<offsets.length;q++){
               var across:int=edge+offsets[q];
               var px:int=vertical?across:along,py:int=vertical?along:across;
               if(px<0||py<0||px>=width||py>=height)continue;
               var cell:int=px+py*width;
               samplePixels[write]=cell;sampleAlphas[write]=alphas[q];write++;
               if(!registered[cell]){registered[cell]=true;sampleCells.push(cell);}
            }
         }
         sampleStarts[faceCount]=write;samplePixels.length=sampleAlphas.length=write;
      }
   }
}
