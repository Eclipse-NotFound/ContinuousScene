        private function warmNative(point:Object,index:int):BitmapData {
            if(report.nativeWarmups==null)report.nativeWarmups=[];
            var offsets:Array=[{x:1,y:0},{x:0,y:1},{x:120,y:120}];
            var record:Object={view:index,protocol:"one fixed full-offset preparation cycle then three exact independent invariants",preparationReturns:[],checks:[]};
            report.nativeWarmups.push(record);
            var cold:BitmapData=capture(),baseline:BitmapData=cold;
            var ordinal:int=0;
            for each(var offset:Object in offsets) {
                applyCamera(point.x+offset.x,point.y+offset.y);
                require(grafon.sceneViewReady(),"Preparation away viewport not prepared");
                var away:BitmapData=capture();
                applyCamera(point.x,point.y);require(grafon.sceneViewReady(),"Preparation return viewport not prepared");
                var returned:BitmapData=capture();
                record.preparationReturns.push({offset:offset,versusPrevious:compare(baseline,returned)});
                baseline=returned;
                if(index==0)savePixel("prepare-return-"+index+"-"+ordinal,baseline);
                ++ordinal;
            }
            record.coldVsWarm=compare(cold,baseline);
            if(index==0 || !record.coldVsWarm.equal){savePixel("cold-"+index,cold);savePixel("warm-"+index,baseline);}
            ordinal=0;
            for each(offset in offsets) {
                applyCamera(point.x+offset.x,point.y+offset.y);
                require(grafon.sceneViewReady(),"Invariant away viewport not prepared");away=capture();
                applyCamera(point.x,point.y);require(grafon.sceneViewReady(),"Invariant return viewport not prepared");
                var restored:BitmapData=capture(),comparison:Object=compare(baseline,restored);
                record.checks.push({offset:offset,pixels:comparison});
                if(!comparison.equal){
                    savePixel("unstable-baseline-"+index+"-"+ordinal,baseline);
                    savePixel("unstable-return-"+index+"-"+ordinal,restored);
                }
                require(comparison.equal,"Native camera pixel baseline is unstable after fixed full-offset preparation");
                ++ordinal;
            }
            record.passed=true;return baseline;
        }

