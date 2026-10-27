        private function redrawActorTiles(group:Object,changed:Dictionary):void {
            refreshActorItems(group,changed,false);
        }
        private function actorRect(node:DisplayObject):Rectangle {
            var rect:Rectangle=actorExtent(node);rect.offset(bounds.x,bounds.y);
            return new Rectangle(Math.floor(rect.x),Math.floor(rect.y),Math.ceil(rect.right)-Math.floor(rect.x),Math.ceil(rect.bottom)-Math.floor(rect.y));
        }
        private function directBitmap(node:DisplayObject):Bitmap {
            var current:DisplayObject=node;
            while(current) {
                if(current.alpha!=1 || current.filters.length || current.mask || current.scrollRect ||
                    current.transform.matrix3D || !neutralColor(current.transform.colorTransform))return null;
                if(current!==node && current.blendMode!="normal")return null;
                var bitmap:Bitmap=current as Bitmap;
                if(bitmap) {
                    if(bitmap.bitmapData==null || bitmap.smoothing)return null;
                    var matrix:Matrix=bitmap.transform.concatenatedMatrix;
                    var inverse:Matrix=root.transform.concatenatedMatrix;inverse.invert();matrix.concat(inverse);
                    if(Math.abs(matrix.a)!=1 || Math.abs(matrix.d)!=1 || matrix.b!=0 || matrix.c!=0 ||
                        matrix.tx!=Math.floor(matrix.tx) || matrix.ty!=Math.floor(matrix.ty))return null;
                    return bitmap;
                }
                var sprite:Sprite=current as Sprite;
                if(sprite==null || sprite.numChildren!=1 || sprite.graphics.readGraphicsData(false).length!=0)return null;
                current=sprite.getChildAt(0);
            }
            return null;
        }
        private function actorState(node:DisplayObject):Object {
            return {matrix:node.transform.matrix,color:node.transform.colorTransform,
                visible:node.visible,alpha:node.alpha,blend:node.blendMode};
        }
        private function actorStateEqual(a:Object,b:Object):Boolean {
            return a!=null && a.visible===b.visible && a.alpha===b.alpha && a.blend===b.blend &&
                sameMatrix(a.matrix,b.matrix) && sameColor(a.color,b.color);
        }
        private function nestedBlends(node:DisplayObject):Array {
            var output:Array=[],stack:Array=[{node:node,depth:0}];
            while(stack.length) {
                var entry:Object=stack.pop(),part:DisplayObject=entry.node;
                if(part.blendMode!="normal")output.push({className:getQualifiedClassName(part),blend:part.blendMode,depth:entry.depth,visible:part.visible});
                var branch:DisplayObjectContainer=part as DisplayObjectContainer;
                if(branch)for(var i:int=0;i<branch.numChildren;++i)stack.push({node:branch.getChildAt(i),depth:entry.depth+1});
            }
            return output;
        }
        private function releaseActorItem(item:Object):void {
            if(item.texture) {item.texture.dispose();++texturesDisposed;gpuBytes-=Number(item.width)*item.height*4;item.texture=null;}
            if(item.pixels){disposePixels(item.pixels);item.pixels=null;}
            // Native BitmapData is borrowed and is never disposed or changed.
            item.bitmap=null;
        }
        private function refreshActorItems(group:Object,changed:Dictionary,first:Boolean):void {
            var began:int=getTimer(),layer:DisplayObjectContainer=group.nodes[0] as DisplayObjectContainer;
            require(group.nodes.length==1 && layer===world.grafon.visObjs[2] && style(layer) &&
                sameMatrix(layer.transform.matrix,new Matrix()) && neutralColor(layer.transform.colorTransform),"Neutral actor layer required");
            if(first) {
                require(actorItems.length==0,"Actor cache already prepared");
                for(var i:int=0;i<layer.numChildren;++i) {
                    var node:DisplayObject=layer.getChildAt(i);
                    actorRoots.push(node);actorItems.push({node:node,texture:null,pixels:null,bitmap:null,state:null,shown:false});
                }
            }
            require(layer.numChildren==actorRoots.length,"Actor root lifecycle changed");
            var requests:Array=[],saved:Array=[];
            for(i=0;i<actorItems.length;++i) {
                var item:Object=actorItems[i];node=item.node;
                require(layer.getChildAt(i)===node,"Actor root order changed");
                var state:Object=actorState(node);
                var dirty:Boolean=first || changed[node] || !actorStateEqual(state,item.state);
                var rect:Rectangle=actorRect(node);
                item.shown=node.visible && node.alpha>0 && !rect.isEmpty();
                require(node.blendMode=="normal" || node.blendMode=="layer" || node.blendMode=="screen" || node.blendMode=="add","Unsupported actor root blend: "+node.blendMode);
                item.blend=node.blendMode;
                if(item.shown) {
                    var bitmap:Bitmap=directBitmap(node);
                    if(bitmap) {
                        if(item.pixels || item.bitmap!==bitmap || item.width!=bitmap.bitmapData.width || item.height!=bitmap.bitmapData.height)releaseActorItem(item);
                        item.bitmap=bitmap;item.width=bitmap.bitmapData.width;item.height=bitmap.bitmapData.height;
                        var matrix:Matrix=bitmap.transform.concatenatedMatrix;
                        var inverse:Matrix=root.transform.concatenatedMatrix;inverse.invert();matrix.concat(inverse);item.matrix=matrix;
                        var uploadAt:int=getTimer();
                        if(item.texture==null)item.texture=upload(bitmap.bitmapData);
                        else{item.texture.uploadFromBitmapData(bitmap.bitmapData);++uploads;}
                        ++directBitmapUploads;actorUploadMs+=getTimer()-uploadAt;
                    } else if(dirty || item.texture==null || item.bitmap!=null || item.rect==null || !item.rect.equals(rect)) {
                        if(item.bitmap || item.pixels==null || item.width!=rect.width || item.height!=rect.height) {
                            releaseActorItem(item);item.width=int(rect.width);item.height=int(rect.height);
                            require(item.width<=2048 && item.height<=2048,"Actor image bound exceeded");
                            item.pixels=newPixels(item.width,item.height);
                        }
                        item.rect=rect;item.matrix=new Matrix(1,0,0,1,rect.x,rect.y);requests.push(item);
                    }
                } else ++actorSkipped;
                item.state=state;
                if(first)actorInventory.push({index:i,className:getQualifiedClassName(node),visible:node.visible,shown:item.shown,
                    directBitmap:item.bitmap!=null,bounds:{x:rect.x,y:rect.y,width:rect.width,height:rect.height},blends:nestedBlends(node)});
            }
            // Isolate each requested root within its original parent. This retains its
            // filters/color/masks without reparenting or altering animation playback.
            if(requests.length)try {
                for each(node in actorRoots){saved.push(node.visible);if(node.visible){node.visible=false;++actorVisibilityWrites;}}
                for each(item in requests) {
                    node=item.node;node.visible=true;
                    try {
                        var drawAt:int=getTimer();item.pixels.fillRect(item.pixels.rect,0);
                        item.pixels.draw(layer,new Matrix(1,0,0,1,-item.rect.x,-item.rect.y),null,null,null,true);
                        ++copies;++actorRasterCalls;actorRasterMs+=getTimer()-drawAt;actorRasterPixels+=Number(item.width)*item.height;
                    } finally {node.visible=false;}
                    uploadAt=getTimer();
                    if(item.texture==null)item.texture=upload(item.pixels);
                    else{item.texture.uploadFromBitmapData(item.pixels);++uploads;}
                    actorUploadMs+=getTimer()-uploadAt;
                }
            } finally {
                for(i=0;i<saved.length;++i)if(actorRoots[i].visible!==saved[i]){actorRoots[i].visible=saved[i];++actorVisibilityRestores;}
            }
            actorRefreshMs+=getTimer()-began;
        }
        private function renderActorItems(camera:Matrix):void {
            for each(var item:Object in actorItems)if(item.shown && item.texture) {
                context.setBlendFactors("one",item.blend=="screen"?"oneMinusSourceColor":item.blend=="add"?"one":"oneMinusSourceAlpha");
                var m:Matrix=item.matrix;
                // Eligible borrowed bitmaps are axis-aligned, with unit scale or reflection.
                drawQuad(item.texture,m.tx+camera.tx,m.ty+camera.ty,item.width*m.a,item.height*m.d);
            }
        }
        private function verifyActorTiles():void {
            require(actorGroup && oracleImage,"Actor oracle missing");
            maskedDraw(actorGroup,scratch,scratch.rect);oracleImage.fillRect(oracleImage.rect,0);
            for each(var item:Object in actorItems)if(item.shown && item.texture) {
                var pixels:BitmapData=item.bitmap?item.bitmap.bitmapData:item.pixels;
                var matrix:Matrix=item.matrix.clone();matrix.tx-=bounds.x;matrix.ty-=bounds.y;
                oracleImage.draw(pixels,matrix,null,item.blend=="layer"?"normal":item.blend,null,false);
            }
            var left:Vector.<uint>=scratch.getVector(scratch.rect),right:Vector.<uint>=oracleImage.getVector(oracleImage.rect);
            var maxRGB:int=0,maxAlpha:int=0,different:int=0;
            for(var i:int=0;i<left.length;++i)if(left[i]!=right[i]) {
                ++different;maxAlpha=Math.max(maxAlpha,Math.abs(int(left[i]>>>24)-int(right[i]>>>24)));
                for(var shift:int=0;shift<=16;shift+=8)maxRGB=Math.max(maxRGB,Math.abs(int((left[i]>>>shift)&255)-int((right[i]>>>shift)&255)));
            }
            ++oracleCalls;var equal:Boolean=different==0;
            oracleChecks.push({call:oracleCalls,equal:equal,differentPixels:different,maxRGB:maxRGB,maxAlpha:maxAlpha,accepted:maxRGB<=2&&maxAlpha==0});
            if(oracleCalls==1){savePixel("actor-native-1",scratch);savePixel("actor-cached-1",oracleImage);}
            // Rejected image checks are retained; timing can still establish whether the
            // approach merits further work, never deployment or gameplay acceptance.
        }
