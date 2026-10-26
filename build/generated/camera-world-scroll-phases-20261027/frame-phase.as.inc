        private var exitListening:Boolean=false;
        private var frameSerial:int=0;
        private var lastExit:Object;

        private function recordExit(event:Event):void {
            if(closed || phase!=3 || pending==null)return;
            try {
                lastExit={serial:pending.serial,atMs:getTimer(),terrain:layerState(),vx:cam.vx,vy:cam.vy,
                    worldVisible:world.visual.visible,windowVisible:stage.nativeWindow.visible};
                ++report.phaseObservation.snapshots;
            } catch(error:Error){report.phaseObservation.errors.push(error.message);}
        }
        private function sameArray(a:Array,b:Array):Boolean {
            if(a==null || b==null || a.length!=b.length)return false;
            for(var i:int=0;i<a.length;++i)if(a[i]!==b[i])return false;
            return true;
        }
        private function verifyFramePhases(entry:Array,now:int):void {
            require(report.phaseObservation.errors.length==0,"EXIT_FRAME observation failed");
            require(lastExit!=null && lastExit.serial==pending.serial,"Missing matching EXIT_FRAME observation");
            require(lastExit.atMs>=pending.appliedAt && lastExit.atMs<=now,"EXIT_FRAME timestamp outside interval");
            require(sameArray(lastExit.terrain,pending.terrain) && lastExit.vx==pending.vx && lastExit.vy==pending.vy,
                "Applied scroll state changed before EXIT_FRAME");
            require(lastExit.worldVisible===true && lastExit.windowVisible===true,"Frame-end display was hidden");
            if(!sameArray(entry,pending.terrain)) {
                var nativeEntry:Array=pending.terrain.concat();nativeEntry[2]=Number(pending.vx);nativeEntry[3]=Number(pending.vy);
                require(sameArray(entry,nativeEntry),"Unexpected next-frame scroll state: "+entry+" expected="+pending.terrain);
                ++report.phaseObservation.nativeEntryRepositions;
            }
        }

