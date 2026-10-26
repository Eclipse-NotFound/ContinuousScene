        private function warmNative(point:Object,index:int):BitmapData {
            if(report.nativeWarmups==null)report.nativeWarmups=[];
            var record:Object={view:index,protocol:"one fixed horizontal roundtrip then three exact invariants",checks:[]};
            report.nativeWarmups.push(record);
            var cold:BitmapData=capture();
            applyCamera(point.x+1,point.y);require(grafon.sceneViewReady(),"Warm-up away viewport not prepared");
            var away:BitmapData=capture();
            applyCamera(point.x,point.y);require(grafon.sceneViewReady(),"Warm-up return viewport not prepared");
            var baseline:BitmapData=capture();record.coldVsWarm=compare(cold,baseline);
            if(index==0 || !record.coldVsWarm.equal){savePixel("cold-"+index,cold);savePixel("warm-"+index,baseline);}
            for each(var offset:Object in [{x:1,y:0},{x:0,y:1},{x:120,y:120}]){
                applyCamera(point.x+offset.x,point.y+offset.y);
                require(grafon.sceneViewReady(),"Invariant away viewport not prepared");away=capture();
                applyCamera(point.x,point.y);require(grafon.sceneViewReady(),"Invariant return viewport not prepared");
                var restored:BitmapData=capture(),comparison:Object=compare(baseline,restored);
                record.checks.push({offset:offset,pixels:comparison});
                require(comparison.equal,"Native camera pixel baseline is still unstable after fixed warm-up");
            }
            record.passed=true;return baseline;
        }
