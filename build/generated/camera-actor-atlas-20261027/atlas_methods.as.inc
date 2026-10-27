        private function captureActorBatch(layer:DisplayObjectContainer,requests:Array):void {
            if(actorAtlas==null)actorAtlas=newPixels(2048,2048);
            var x:int=0,y:int=0,rowHeight:int=0,usedWidth:int=0;
            for each(var item:Object in requests) {
                require(item.width<=2048 && item.height<=2048,"Actor does not fit atlas");
                if(x+item.width>2048){x=0;y+=rowHeight;rowHeight=0;}
                require(y+item.height<=2048,"Changed actor batch exceeds atlas");
                item.slot=new Rectangle(x,y,item.width,item.height);
                x+=item.width;rowHeight=Math.max(rowHeight,item.height);usedWidth=Math.max(usedWidth,x);
            }
            var area:Rectangle=new Rectangle(0,0,usedWidth,y+rowHeight),visibility:Array=[],transforms:Array=[];
            var started:int=getTimer();actorAtlas.fillRect(area,0);
            try {
                for each(var node:DisplayObject in actorRoots) {
                    visibility.push({node:node,visible:node==null?false:node.visible});
                    if(node && node.visible){node.visible=false;++actorVisibilityWrites;}
                }
                for each(item in requests) {
                    node=item.node;
                    var original:Matrix=node.transform.matrix,matrix:Matrix=original.clone();
                    transforms.push({node:node,matrix:original});
                    matrix.tx+=item.slot.x-item.rect.x;matrix.ty+=item.slot.y-item.rect.y;
                    node.transform.matrix=matrix;++actorTransformWrites;node.visible=true;
                }
                actorAtlas.draw(layer,null,null,null,area,true);++copies;++actorRasterCalls;++atlasPasses;
                atlasRoots+=requests.length;actorRasterPixels+=area.width*area.height;
            } finally {
                for each(var transform:Object in transforms) {
                    transform.node.transform.matrix=transform.matrix;++actorTransformRestores;
                    require(sameMatrix(transform.node.transform.matrix,transform.matrix),"Actor transform restoration failed");
                }
                for each(var state:Object in visibility)if(state.node) {
                    if(state.node.visible!==state.visible)state.node.visible=state.visible;
                    // Count each originally visible root restored, including a root
                    // whose visibility was re-enabled while arranging this batch.
                    if(state.visible)++actorVisibilityRestores;
                    require(state.node.visible===state.visible,"Actor visibility restoration failed");
                }
            }
            var elapsed:int=getTimer()-started;actorRasterMs+=elapsed;atlasDrawMs+=elapsed;
            var copyAt:int=getTimer();
            for each(item in requests){item.pixels.copyPixels(actorAtlas,item.slot,new Point());++copies;}
            atlasCopyMs+=getTimer()-copyAt;
            for each(item in requests) {
                var uploadAt:int=getTimer();
                if(item.texture==null)item.texture=upload(item.pixels);
                else{item.texture.uploadFromBitmapData(item.pixels);++uploads;}
                actorUploadMs+=getTimer()-uploadAt;
            }
        }
