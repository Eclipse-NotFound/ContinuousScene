        private function nodeId(value:*):int {
            if(value==null)return 0;
            if(!nodeIds[value])nodeIds[value]=++nodeSequence;
            return nodeIds[value];
        }
        private function inspectNodes(label:String):void {
            var at:int=getTimer();
            var result:Object={label:label,nodes:[],roots:[],errors:[],hashPixels:0,skippedRoots:0};
            report.nodeSnapshots.push(result);
            var screen:Rectangle=new Rectangle(-64,-64,stage.stageWidth+128,stage.stageHeight+128);
            for(var layerIndex:int=0;layerIndex<6;++layerIndex) {
                var layer:DisplayObjectContainer=grafon.visObjs[layerIndex] as DisplayObjectContainer;
                require(layer!=null,"Object layer missing for metadata");
                for(var i:int=0;i<layer.numChildren;++i) {
                    var root:DisplayObject=layer.getChildAt(i),b:Rectangle=root.getBounds(stage);
                    result.roots.push({id:nodeId(root),layer:layerIndex,index:i,className:getQualifiedClassName(root),bounds:rectState(b)});
                    if(b.isEmpty() || !b.intersects(screen)){++result.skippedRoots;continue;}
                    inspectNode(root,result,layerIndex+":"+i,0);
                }
            }
            result.elapsedMs=getTimer()-at;
            require(result.errors.length==0,"Display metadata incomplete");
        }
        private function inspectNode(node:DisplayObject,result:Object,path:String,depth:int):void {
            if(depth>70 || result.nodes.length>=12000){result.errors.push("Node budget exceeded");return;}
            try {
                var m:Matrix=node.transform.matrix,cm:Matrix=node.transform.concatenatedMatrix;
                var ct:*=node.transform.colorTransform,cct:*=node.transform.concatenatedColorTransform;
                var record:Object={id:nodeId(node),parent:nodeId(node.parent),path:path,name:node.name,
                    className:getQualifiedClassName(node),bounds:rectState(node.getBounds(stage)),
                    visible:node.visible,alpha:node.alpha,blend:node.blendMode,cache:node.cacheAsBitmap,
                    mask:nodeId(node.mask),scroll:rectState(node.scrollRect),
                    matrix:fields(m,["a","b","c","d","tx","ty"]),
                    concatMatrix:fields(cm,["a","b","c","d","tx","ty"]),
                    color:fields(ct,["redMultiplier","greenMultiplier","blueMultiplier","alphaMultiplier","redOffset","greenOffset","blueOffset","alphaOffset"]),
                    concatColor:fields(cct,["redMultiplier","greenMultiplier","blueMultiplier","alphaMultiplier","redOffset","greenOffset","blueOffset","alphaOffset"]),filters:[]};
                for each(var filter:* in node.filters) {
                    var f:Object={className:getQualifiedClassName(filter)};
                    for each(var field:String in ["alpha","angle","blurX","blurY","color","distance","hideObject","inner","knockout","quality","strength","matrix"])
                        if(field in filter)f[field]=filter[field];
                    record.filters.push(f);
                }
                var bitmap:Bitmap=node as Bitmap;
                if(bitmap) {
                    var data:BitmapData=bitmap.bitmapData;
                    record.bitmap={id:nodeId(data),smoothing:bitmap.smoothing,snapping:bitmap.pixelSnapping};
                    if(data) {
                        record.bitmap.width=data.width;record.bitmap.height=data.height;record.bitmap.transparent=data.transparent;
                        var pixels:int=data.width*data.height;
                        if(pixels+result.hashPixels<=4000000) {
                            var values:Vector.<uint>=data.getVector(data.rect),hash:uint=5381;
                            for(var k:int=0;k<values.length;++k)hash=uint(Number(hash)*33)^values[k];
                            record.bitmap.hash=hash;result.hashPixels+=pixels;
                        } else result.errors.push("Bitmap hash budget exceeded");
                    }
                }
                var clip:MovieClip=node as MovieClip;
                if(clip)record.clip={frame:clip.currentFrame,total:clip.totalFrames,playing:clip.isPlaying};
                var textField:TextField=node as TextField;
                if(textField)record.text={text:textField.text,embed:textField.embedFonts,aa:textField.antiAliasType,
                    grid:textField.gridFitType,sharpness:textField.sharpness,thickness:textField.thickness};
                result.nodes.push(record);
                var parent:DisplayObjectContainer=node as DisplayObjectContainer;
                if(parent)for(var i:int=0;i<parent.numChildren;++i)inspectNode(parent.getChildAt(i),result,path+"/"+i,depth+1);
            } catch(error:Error){result.errors.push(path+": "+error.message);}
        }
        private function rectState(value:Rectangle):Object {
            return value==null?null:{x:value.x,y:value.y,width:value.width,height:value.height};
        }
