        private function pixelCase(point:Object,index:int):void {
            var at:int=getTimer(),result:Object={index:index,x:point.x,y:point.y,passed:false,conditions:[]};
            report.pixels.push(result);report.nodeSnapshots=[];
            report.nativeRoundtripOnly=true;
            try {
                require(world.visual.visible===true,"World must remain visible");
                applyCamera(point.x,point.y);require(grafon.sceneViewReady(),"Pixel viewport not prepared");
                inspectNodes("before-native");
                var original:BitmapData=capture();inspectNodes("after-native");
                var repeated:BitmapData=capture();report.nativeRepeat=compare(original,repeated);
                require(report.nativeRepeat.equal,"Unchanged native captures differ");
                savePixel("native-original",original);savePixel("native-repeat",repeated);
                var offsets:Array=[{x:1,y:0},{x:0,y:1},{x:120,y:120}];
                var allEqual:Boolean=true;
                for(var k:int=0;k<offsets.length;++k){
                    var offset:Object=offsets[k];
                    applyCamera(point.x+offset.x,point.y+offset.y);
                    require(grafon.sceneViewReady(),"Offset viewport not prepared");
                    var away:BitmapData=capture();
                    applyCamera(point.x,point.y);require(grafon.sceneViewReady(),"Return viewport not prepared");
                    var restored:BitmapData=capture();
                    inspectNodes("after-roundtrip-"+k);
                    var again:BitmapData=capture();
                    var item:Object={offset:offset,restored:compare(original,restored),repeat:compare(restored,again),originalVsRepeat:compare(original,again)};
                    result.conditions.push(item);allEqual=allEqual && item.restored.equal && item.repeat.equal;
                    savePixel("roundtrip-"+k+"-away",away);savePixel("roundtrip-"+k+"-restored",restored);
                    savePixel("roundtrip-"+k+"-repeat",again);
                }
                result.passed=allEqual;
                require(allEqual,"Natural camera round trips did not restore exact pixels");
            }finally{
                applyCamera(point.x,point.y);disposeOwned();result.elapsedMs=getTimer()-at;
            }
        }
