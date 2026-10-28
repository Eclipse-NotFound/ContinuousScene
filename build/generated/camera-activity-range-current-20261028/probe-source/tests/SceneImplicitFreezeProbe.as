package tests {
    import flash.display.DisplayObjectContainer;
    import flash.display.MovieClip;
    import flash.utils.Dictionary;

    /** Diagnostic only: one stop per observed candidate per seed. This is not
     * production freeze/resume logic. Only feed observedCandidates() from the
     * completed eight-frame sleeping observation, never a display-tree census.
     * A before B leaves pending candidates intact; consecutive B samples do not
     * stop twice. After release a candidate cannot be stopped again by this seed.
     * The caller must clear() on every exit, including an exception or abort.
     */
    public class SceneImplicitFreezeProbe {
        private var records:Array=[];
        private var seeded:int=0;
        private var stopped:int=0;
        private var resumed:int=0;
        private var released:int=0;
        private var changedWhileHeld:int=0;
        private var reasons:Object={};

        public function seed(candidates:Array):void {
            clear();
            seeded=stopped=resumed=released=changedWhileHeld=0;reasons={};
            if(candidates==null)throw new Error("Implicit freeze needs observed candidates");
            var seen:Dictionary=new Dictionary(true);
            for each(var candidate:Object in candidates) {
                if(!candidate || !candidate.unit || !(candidate.root is DisplayObjectContainer)
                   || !(candidate.clip is MovieClip))
                    throw new Error("Invalid observed implicit-freeze candidate");
                if(seen[candidate.clip])throw new Error("Duplicate implicit-freeze clip");
                seen[candidate.clip]=true;
                records.push({unit:candidate.unit,root:candidate.root,clip:candidate.clip,
                    loc:candidate.unit.loc,state:"pending",frame:0,label:null,parent:null});
                ++seeded;
            }
        }

        public function update(w:*,on:Boolean):void {
            var api:*=null,sleeping:Object=null;
            if(w && w.main && w.loc) {
                var carrier:*=w.main.getChildByName("ContinuousSceneCarrier");
                api=carrier ? carrier["nativeAPI"] : null;
                if(api && api.sleeping is Function)sleeping=api.sleeping(w.loc);
            }
            for each(var record:Object in records) {
                if(record.state=="released")continue;
                var mc:MovieClip=record.clip;
                var root:DisplayObjectContainer=record.root;
                var reason:String=null;
                if(record.state=="held" && (mc.currentFrame!=record.frame
                   || mc.currentLabel!=record.label || mc.parent!==record.parent || mc.isPlaying)) {
                    ++changedWhileHeld;reason="presentation-changed-while-held";
                }
                else if(!w || w.loc!==record.loc || record.unit.loc!==record.loc)
                    reason="location-changed";
                else if(!sleeping)reason="sleeping-dictionary-unavailable";
                else if(!sleeping[record.unit])reason="owner-awake";
                else if(record.unit.vis!==root)reason="root-replaced";
                else if(mc!==root && !root.contains(mc))reason="clip-left-root";
                if(reason!=null) {release(record,reason);continue;}
                if(!on) {
                    if(record.state=="held")release(record,"control-A");
                    continue;
                }
                if(record.state=="pending") {
                    record.frame=mc.currentFrame;
                    record.label=mc.currentLabel;
                    record.parent=mc.parent;
                    // Mark ownership before invoking native stop: clear() can
                    // still conditionally restore after a partially failed call.
                    record.state="held";
                    mc.stop();
                    ++stopped;
                }
            }
        }

        public function clear():void {
            // Best-effort release of every held clip; propagate the first error
            // after cleanup, rather than hiding it or abandoning later clips.
            var failed:Boolean=false,firstError:*=null;
            for each(var record:Object in records) {
                if(record.state=="released")continue;
                try {release(record,"clear");}
                catch(error:*) {if(!failed){failed=true;firstError=error;}}
            }
            records=[];
            if(failed)throw firstError;
        }

        public function snapshot():Object {
            var held:int=0,pending:int=0;
            for each(var record:Object in records) {
                if(record.state=="held")++held;
                else if(record.state=="pending")++pending;
            }
            var copied:Object={};
            for(var reason:String in reasons)copied[reason]=reasons[reason];
            return {version:"observed-implicit-freeze-1",diagnosticOnly:true,
                performanceEligible:false,seeded:seeded,stopped:stopped,resumed:resumed,
                released:released,held:held,pending:pending,changedWhileHeld:changedWhileHeld,
                releaseReasons:copied};
        }

        private function release(record:Object,reason:String):void {
            if(record.state=="released")return;
            var wasHeld:Boolean=record.state=="held";
            record.state="released";
            ++released;reasons[reason]=int(reasons[reason])+1;
            if(!wasHeld)return;
            var mc:MovieClip=record.clip;
            // isPlaying was false even while these clips visibly advanced.
            // Restore with play only if our exact stopped pose is still intact.
            // External play/pose/parent changes always win and cannot be restopped.
            if(!mc.isPlaying && mc.currentFrame==record.frame
               && mc.currentLabel==record.label && mc.parent===record.parent) {
                mc.play();
                ++resumed;
            }
        }
    }
}
